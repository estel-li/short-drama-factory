"""Per-frame, source-time masks with independently tracked foreground protection."""
from __future__ import annotations

from fractions import Fraction

import av
from PIL import Image, ImageDraw
from pydantic import BaseModel, ConfigDict, Field, model_validator


class Key(BaseModel):
    model_config=ConfigDict(extra='forbid')
    time:float=Field(ge=0,le=1200)
    points:list[list[float]]=Field(min_length=3,max_length=32)

    @model_validator(mode='after')
    def valid(self):
        if any(len(p)!=2 or any(not 0<=v<=1 for v in p) for p in self.points):
            raise ValueError('遮罩坐标须为 [x,y]，各值在 0～1 之间。')
        area=sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(self.points,self.points[1:]+self.points[:1]))
        if abs(area)<1e-8:raise ValueError('多边形须有面积，不能是同一点或一条直线。')
        return self


class Track(BaseModel):
    model_config=ConfigDict(extra='forbid')
    keyframes:list[Key]=Field(min_length=1,max_length=500)

    @model_validator(mode='after')
    def valid(self):
        if any(a.time>=b.time for a,b in zip(self.keyframes,self.keyframes[1:])) or len({len(k.points) for k in self.keyframes})!=1:
            raise ValueError('轨迹时间须递增，且各关键帧多边形顶点数量相同。')
        return self


class Mask(Track):
    shot_uid:str=Field(pattern=r'^[a-zA-Z0-9_-]{1,80}$')
    start:float=Field(default=0,ge=0,le=1200)
    end:float=Field(ge=0,le=1200)
    color:str=Field(default='#EAE5DC',pattern=r'^#[0-9A-Fa-f]{6}$')
    protect:list[Track]=Field(default_factory=list,max_length=20)

    @model_validator(mode='after')
    def timing(self):
        if self.start>=self.end:raise ValueError('遮罩 start 必须小于 end。')
        return self


def polygon(track,time,width,height):
    keys=track.keyframes
    left=right=keys[0]
    for index,key in enumerate(keys):
        if key.time<=time:left=right=key
        if key.time>time:
            right=key;break
    amount=0 if left.time==right.time else max(0,min(1,(time-left.time)/(right.time-left.time)))
    return [(round((a[0]+(b[0]-a[0])*amount)*(width-1)),round((a[1]+(b[1]-a[1])*amount)*(height-1))) for a,b in zip(left.points,right.points,strict=True)]


def mask_frame(mask,time,width,height):
    alpha=Image.new('L',(width,height),0)
    if not mask.start<=time<mask.end:return alpha
    draw=ImageDraw.Draw(alpha);draw.polygon(polygon(mask,time,width,height),fill=255)
    for track in mask.protect:draw.polygon(polygon(track,time,width,height),fill=0)
    return alpha


def apply_masks(source,output,masks,width,height,frames,folder,fps=24):
    from .finishing import ffmpeg,verify
    selected=[Mask.model_validate(mask) for mask in masks]
    if not selected:return source,[]
    folder.mkdir(parents=True,exist_ok=True)
    arguments=['-i',source];graph=[];current='0:v';reports=[]
    for index,mask in enumerate(selected):
        if mask.end>frames/fps or any(key.time>frames/fps for track in [mask,*mask.protect] for key in track.keyframes):
            raise ValueError('遮罩使用原镜头时间轴，不能超出源视频长度。')
        path=folder/f'mask_{index:02d}.mkv';coverage=[]
        with av.open(str(path),'w') as container:
            stream=container.add_stream('ffv1',rate=fps);stream.width=width;stream.height=height;stream.pix_fmt='gray'
            for frame_index in range(frames):
                alpha=mask_frame(mask,frame_index/fps,width,height)
                coverage.append(alpha.histogram()[255]/(width*height))
                frame=av.VideoFrame.from_image(alpha);frame.pts=frame_index;frame.time_base=Fraction(1,fps)
                for packet in stream.encode(frame):container.mux(packet)
            for packet in stream.encode():container.mux(packet)
        arguments+=['-i',path]
        graph += [f'color=c=0x{mask.color[1:]}:s={width}x{height}:r={fps}:d={frames/fps:.12f}[cover{index}]',
                  f'[{index+1}:v]format=gray[alpha{index}]',
                  f'[cover{index}][alpha{index}]alphamerge[layer{index}]',
                  f'[{current}][layer{index}]overlay=shortest=1:format=auto[masked{index}]']
        current=f'masked{index}'
        reports.append({'mask_file':path.name,'frames':frames,'minimum_frame_coverage':min(coverage),'maximum_frame_coverage':max(coverage),
                        'foreground_tracks':len(mask.protect),'note':'逐帧生成 alpha；前景保护依赖所提供的轨迹，须查看审核帧确认没有残字或遮住人物。'})
    arguments+=['-filter_complex',';'.join(graph),'-map',f'[{current}]','-map','0:a:0','-c:v','libx264',
                '-preset','fast','-crf','18','-pix_fmt','yuv420p','-c:a','copy','-frames:v',frames,'-movflags','+faststart',output]
    ffmpeg(arguments);verify(output,frames,width,height)
    return output,reports

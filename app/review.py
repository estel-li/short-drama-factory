"""Review evidence: shot overview, before/after cuts, and timestamped dense frame pages."""
from __future__ import annotations

import math
from pathlib import Path

import av
from PIL import Image, ImageDraw, ImageFont

from .storage import write_json


def images_at(path,targets):
    wanted=sorted(set(max(0,float(t)) for t in targets));found={}
    if not wanted:return found
    cursor=0;last=None
    with av.open(str(path)) as video:
        for index,frame in enumerate(video.decode(video=0)):
            current=float(frame.pts*frame.time_base) if frame.pts is not None else index/24
            if current+1e-8>=wanted[cursor]:
                last=frame.to_image()
                while cursor<len(wanted) and current+1e-8>=wanted[cursor]:
                    found[wanted[cursor]]=last.copy();cursor+=1
                if cursor==len(wanted):break
            last=frame.to_image() if cursor==len(wanted)-1 else last
    if last is None:raise ValueError('审核视频没有可读取的帧。')
    for target in wanted:
        if target not in found:found[target]=last.copy()
    return found


def sheet(items,target,columns=3):
    width,height=216,304;rows=math.ceil(len(items)/columns)
    page=Image.new('RGB',(columns*width,max(1,rows)*height),'#f4f3f8');draw=ImageDraw.Draw(page)
    font=ImageFont.load_default(size=13)
    for index,(image,label) in enumerate(items):
        x,y=(index%columns)*width,(index//columns)*height
        image=image.copy();image.thumbnail((width-16,height-40))
        page.paste(image,(x+(width-image.width)//2,y+8))
        draw.text((x+8,y+height-28),label,font=font,fill='#282538')
    target.parent.mkdir(parents=True,exist_ok=True);page.save(target)


def evidence(folder,checks,outputs,sample_interval=.75,cancel=None):
    from .providers import Cancelled
    from .downloads import Downloader
    if not .1<=sample_interval<=2:raise ValueError('抽帧间隔须为 0.1～2 秒。')
    folder=Path(folder);root=folder/'review';overview=[];cuts=[];samples=[]
    for index,(check,path) in enumerate(zip(checks,outputs,strict=True)):
        if cancel and cancel():raise Cancelled('审核图生成已停止。')
        duration=check['edited']['frames']/24
        targets=[0,max(0,duration/2),max(0,duration-1/24)]
        frames=images_at(path,targets)
        overview.extend((frames[t],f"S{index+1:02d} {name} {t:.2f}s") for t,name in zip(targets,('start','middle','end'),strict=True))
        source=folder/check['preview_source']
        keep=check['plan']['keep_frames']
        for left,right in zip(keep,keep[1:]):
            before,after=(left[1]-1)/24,right[0]/24
            pair=images_at(source,[before,after])
            cuts.extend([(pair[before],f'S{index+1:02d} cut-before {before:.2f}s'),(pair[after],f'S{index+1:02d} cut-after {after:.2f}s')])
        if index+1<len(outputs):
            before=frames[targets[-1]];after=images_at(outputs[index+1],[0])[0]
            cuts.extend([(before,f'S{index+1:02d} last displayed'),(after,f'S{index+2:02d} first displayed')])
        requested=[min(i*sample_interval,duration-1/24) for i in range(math.ceil(duration/sample_interval))]
        dense=images_at(path,requested)
        samples.extend((dense[t],f'S{index+1:02d} {t:.2f}s') for t in requested)
    paths=[]
    for kind,items,columns,page_size in [('overview',overview,3,18),('cuts',cuts,2,12),('frames',samples,3,18)]:
        for number,start in enumerate(range(0,len(items),page_size),1):
            target=root/f'{kind}_{number:03d}.png';sheet(items[start:start+page_size],target,columns)
            paths.append({'kind':kind,'file':str(target.relative_to(folder)).replace('\\','/'),'sha256':Downloader.checksum(target),
                          'items':len(items[start:start+page_size])})
    report={'sample_interval':sample_interval,'pages':paths,
            'scope':'审核图用于核对动作跳切、文字遮罩和硬字幕；不是 OCR 转录。短句可能仍需更密抽帧与播放试听。'}
    write_json(root/'index.json',report)
    return report

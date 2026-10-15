"""Review evidence: shot overview, before/after cuts, and timestamped dense frame pages."""
from __future__ import annotations

import math
from pathlib import Path

import av
from PIL import Image, ImageDraw, ImageFont

from .storage import write_json
from .providers import Cancelled


def images_at(path,targets,cancel=None,on_image=None):
    wanted=sorted(set(max(0,float(t)) for t in targets));found={}
    if not wanted:return found
    cursor=0;last=None
    with av.open(str(path)) as video:
        for index,frame in enumerate(video.decode(video=0)):
            if cancel and cancel():raise Cancelled('审核图生成已停止。')
            current=float(frame.pts*frame.time_base) if frame.pts is not None else index/24
            if current+1e-8>=wanted[cursor]:
                last=frame.to_image()
                last.thumbnail((200,264))
                while cursor<len(wanted) and current+1e-8>=wanted[cursor]:
                    if on_image:on_image(wanted[cursor],last.copy())
                    else:found[wanted[cursor]]=last.copy()
                    cursor+=1
                if cursor==len(wanted):break
            if cursor==len(wanted)-1:
                last=frame.to_image();last.thumbnail((200,264))
    if last is None:raise ValueError('审核视频没有可读取的帧。')
    for target in wanted[cursor:]:
        if on_image:on_image(target,last.copy())
        else:found[target]=last.copy()
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
    folder=Path(folder);root=folder/'review';paths=[]
    pending={kind:[] for kind in ('overview','cuts','frames')}
    counts={kind:0 for kind in pending}
    limits={'overview':(3,18),'cuts':(2,12),'frames':(3,18)}

    def flush(kind):
        if not pending[kind]:return
        if cancel and cancel():raise Cancelled('审核图生成已停止。')
        counts[kind]+=1
        target=root/f'{kind}_{counts[kind]:03d}.png'
        sheet(pending[kind],target,limits[kind][0])
        paths.append({'kind':kind,'file':str(target.relative_to(folder)).replace('\\','/'),
                      'sha256':Downloader.checksum(target,cancel),'items':len(pending[kind])})
        pending[kind].clear()

    def add(kind,items):
        for item in items:
            pending[kind].append(item)
            if len(pending[kind])==limits[kind][1]:flush(kind)

    for index,(check,path) in enumerate(zip(checks,outputs,strict=True)):
        if cancel and cancel():raise Cancelled('审核图生成已停止。')
        duration=check['edited']['frames']/24
        targets=[0,max(0,duration/2),max(0,duration-1/24)]
        frames=images_at(path,targets,cancel)
        add('overview',((frames[t],f"S{index+1:02d} {name} {t:.2f}s") for t,name in zip(targets,('start','middle','end'),strict=True)))
        source=folder/check['preview_source']
        keep=check['plan']['keep_frames']
        for left,right in zip(keep,keep[1:]):
            before,after=(left[1]-1)/24,right[0]/24
            pair=images_at(source,[before,after],cancel)
            add('cuts',[(pair[before],f'S{index+1:02d} cut-before {before:.2f}s'),(pair[after],f'S{index+1:02d} cut-after {after:.2f}s')])
        if index+1<len(outputs):
            before=frames[targets[-1]];after=images_at(outputs[index+1],[0],cancel)[0]
            add('cuts',[(before,f'S{index+1:02d} last displayed'),(after,f'S{index+2:02d} first displayed')])
        requested=[min(i*sample_interval,duration-1/24) for i in range(math.ceil(duration/sample_interval))]
        # One decode pass; each page is written before more thumbnails accumulate.
        images_at(path,requested,cancel,lambda t,image:add('frames',[(image,f'S{index+1:02d} {t:.2f}s')]))
    for kind in pending:flush(kind)
    paths.sort(key=lambda page: (['overview','cuts','frames'].index(page['kind']),page['file']))
    report={'sample_interval':sample_interval,'pages':paths,
            'scope':'审核图用于核对动作跳切、文字遮罩和硬字幕；不是 OCR 转录。短句可能仍需更密抽帧与播放试听。'}
    write_json(root/'index.json',report)
    return report

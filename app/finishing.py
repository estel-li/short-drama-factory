"""Reproducible CPU finishing from immutable clip snapshots, with atomic publication."""
from __future__ import annotations

import copy
import math
import os
import re
import shutil
import subprocess
import time
import uuid
from pathlib import Path

import imageio_ffmpeg

from .downloads import Downloader
from .editplan import PRESETS, align_captions, edit_plan
from .providers import Cancelled
from .quality import render_contract_matches, spoken_units
from .speech import analyze_audio, ensure_model, pcm_audio
from .storage import contained, digest, now, read_json, write_json

FPS = 24


def readiness(project, story):
    """Cheap readiness for the UI; full provenance is checked again before queueing."""
    shots = (story or {}).get('shots', [])
    state = read_json(Path(project) / 'state.json', {})
    missing, outdated = [], []
    for index, shot in enumerate(shots):
        record = state.get('shots_by_uid', {}).get(shot.get('uid'), state.get('shots', {}).get(str(shot['id']), {}))
        clip = Path(record.get('clip') or Path(project) / record.get('clip_relative', 'missing.mp4'))
        if record.get('status') != 'done' or not clip.is_file() or not clip.resolve().is_relative_to(Path(project).resolve()):
            missing.append(shot['id'])
        elif (shot.get('uid') in state.get('changed_shots', [])
              or record.get('render_contract') and not render_contract_matches(record['render_contract'], story, shot)
              or shot.get('use_previous_last_frame') and (index == 0 or record.get('first_frame', {}).get('source_shot_uid') != shots[index - 1].get('uid'))):
            outdated.append(shot['id'])
    ready = bool(shots) and not missing and not outdated
    messages = []
    if missing: messages.append('缺少原片的镜头：' + '、'.join(map(str, missing)))
    if outdated: messages.append('内容或首帧已改变，必须重生成的镜头：' + '、'.join(map(str, outdated)))
    return {'ready': ready, 'total': len(shots), 'completed': len(shots) - len(missing), 'missing': missing, 'outdated': outdated,
            'message': '原片已齐，可以进行 CPU 后期。' if ready else '；'.join(messages) or '请先完成分镜和镜头生成。'}


def load_recipe(project, edit_id):
    from .storage import identifier
    folder = contained(Path(project) / 'edits', identifier(edit_id))
    if not (folder / 'completed.json').is_file():
        raise ValueError('所选版本不存在或尚未完成。')
    recipe = read_json(folder / 'recipe.json')
    if digest(recipe) != read_json(folder / '媒体验收.json', {}).get('recipe_hash'):
        raise ValueError('版本配方已改变，请创建新版本，不能冒充原版本重建。')
    return recipe


def collect_clips(project, story):
    """Reject a changed script over old native speech before zero-render finishing."""
    from .content import prompt_valid
    if not story or not story.get('shots'):raise ValueError('请先完成分镜和镜头生成。')
    project=Path(project);state=read_json(project/'state.json',{});result=[]
    for index,shot in enumerate(story['shots']):
        record=state.get('shots_by_uid',{}).get(shot.get('uid'),state.get('shots',{}).get(str(shot['id']),{}))
        path=Path(record.get('clip') or project/record.get('clip_relative','missing.mp4'))
        if not path.resolve().is_relative_to(project.resolve()) or record.get('status')!='done' or not path.is_file():
            raise ValueError(f"镜头 {shot['id']} 还没有可用原片，请先生成。")
        if shot.get('use_previous_last_frame'):
            frame=record.get('first_frame',{})
            if index==0 or frame.get('source_shot_uid')!=story['shots'][index-1].get('uid') or frame.get('source_clip_sha256')!=Downloader.checksum(result[-1]):
                raise ValueError(f"镜头 {shot['id']} 的上一镜头或首帧依赖已改变，必须重生成接续镜头。")
        if record.get('render_contract'):
            if not render_contract_matches(record['render_contract'],story,shot):
                raise ValueError(f"镜头 {shot['id']} 的剧本或台词已改变，必须重生成，不能只修改字幕。")
        else:
            graph=read_json(project/'prompts'/f"{shot['id']:03d}.json",{})
            inputs=graph.get('7',{}).get('inputs',{})
            actual=inputs.get('prompt','')
            if not shot.get('prompt') or not actual.endswith(shot['prompt']) or shot.get('uid') in state.get('changed_shots',[]):
                raise ValueError(f"旧镜头 {shot['id']} 缺少与当前剧本一致的生成记录。请先续跑校验缓存或重生成。")
            mode=shot.get('compiled_mode') or ('Ref2VA' if graph.get('7',{}).get('class_type')=='MiniMaxH3ReferenceToVideo' else 'FL2VA' if inputs.get('first_frame') and inputs.get('last_frame') else 'I2VA' if inputs.get('first_frame') else 'L2VA' if inputs.get('last_frame') else 'T2VA')
            bindings={'images':[{} for key in inputs if key.startswith('ref_images.')],
                      'videos':[{'include_audio':bool(inputs.get('ref_video_audios.ref_video_audio_'+key.split('_')[-1]))} for key in inputs if key.startswith('ref_videos.')],
                      'audios':[{} for key in inputs if key.startswith('ref_audios.')]}
            if '<d>' in actual or '</d>' in actual:
                prompt_valid(actual,mode,bindings,shot.get('dialogue',[]))
            else:
                legacy=re.search(r'^\s*diegetic dialogue\s*:(.*?)(?=^\s*non_diegetic_music\s*:|\Z)',actual,re.M|re.S)
                quoted=re.findall(r'["“](.*?)["”]',legacy[1],re.S) if legacy else []
                expected=[line['text'] for line in shot.get('dialogue',[]) if line.get('text','').strip()]
                if [''.join(text.split()) for text in quoted]!=[''.join(text.split()) for text in expected]:
                    raise ValueError('历史原片的引号对白与当前台词不一致，必须先重生成。')
        result.append(path)
    return result


def versions(project):
    result=[]
    for folder in (Path(project)/'edits').glob('*'):
        if not (folder/'completed.json').is_file():continue
        report=read_json(folder/'媒体验收.json',{})
        recipe=read_json(folder/'recipe.json',{})
        result.append({'id':folder.name,'created_at':read_json(folder/'completed.json',{}).get('completed_at') or recipe.get('created_at'),'preset':recipe.get('settings',{}).get('edit_preset'),
                       'seconds':report.get('edited_seconds'),'original_seconds':report.get('original_seconds'),
                       'subtitled':(folder/'成片_字幕版.mp4').is_file(),'frames':report.get('expected_frames')})
    return sorted(result,key=lambda value:value['id'],reverse=True)


def ffmpeg(args, cwd=None, cancel=None):
    if '-filter_complex' in args and '-af' in args:
        raise ValueError('音频过滤必须并入复合滤镜，不能同时使用 -af。')
    from .processes import run_process
    result = run_process([imageio_ffmpeg.get_ffmpeg_exe(), '-hide_banner', '-loglevel', 'error', '-y', *map(str,args)], cancel=cancel,
                            cwd=cwd,capture_output=True,encoding='utf-8',errors='replace',
                            creationflags=0x08000000 if os.name=='nt' else 0)
    if result.returncode:
        raise RuntimeError('后期处理失败：'+result.stderr[-1500:])


def verify(path, expected, width=None, height=None):
    from pipeline import media_info
    value=media_info(path,True)
    if value['frames']!=expected or not value['audio'] or not value['timestamps_monotonic'] or abs(value['duration']-expected/FPS)>1/FPS:
        raise RuntimeError('后期产物的帧数、音频、时间戳或时长不一致。')
    if width is not None and (value['width'],value['height'])!=(width,height):
        raise RuntimeError('后期产物画幅不一致。')
    return value


def normalize(source, output, width, height, info, cancel=None):
    count=round(info['duration']*FPS)
    args=['-i',source]
    if not info['audio']:args+=['-f','lavfi','-i','anullsrc=r=48000:cl=stereo']
    args+=['-map','0:v:0','-map','0:a:0' if info['audio'] else '1:a:0',
           '-vf',f'scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setpts=N/(24*TB),tpad=stop_mode=clone:stop_duration=1,format=yuv420p',
           '-af',f'asetpts=PTS-STARTPTS,apad,atrim=duration={count/FPS:.9f}',
           '-c:v','libx264','-preset','fast','-crf','18','-c:a','aac','-ar','48000','-ac','2',
           '-frames:v',count,'-r',FPS,'-fps_mode','cfr','-movflags','+faststart',output]
    ffmpeg(args, cancel=cancel)
    return verify(output,count,width,height)


def render_cut(source, output, plan, cancel=None):
    keep=plan['keep_frames']
    if keep==[[0,plan['source_frames']]]:
        shutil.copy2(source,output)
    else:
        n=len(keep)
        graph=[f'[0:v]split={n}'+''.join(f'[v{i}]' for i in range(n)),
               f'[0:a]asplit={n}'+''.join(f'[a{i}]' for i in range(n))]
        for i,(a,b) in enumerate(keep):
            fades=(','+f'afade=t=in:d=0.008' if a>0 else '')+(','+f'afade=t=out:st={max(0,(b-a)/FPS-.008):.12f}:d=0.008' if b<plan['source_frames'] else '')
            graph += [f'[v{i}]trim=start_frame={a}:end_frame={b},setpts=PTS-STARTPTS[cv{i}]',
                      f'[a{i}]atrim=start={a/FPS:.12f}:end={b/FPS:.12f},asetpts=PTS-STARTPTS{fades}[ca{i}]']
        graph += [''.join(f'[cv{i}][ca{i}]' for i in range(n))+f'concat=n={n}:v=1:a=1[v][a]']
        ffmpeg(['-i',source,'-filter_complex',';'.join(graph),'-map','[v]','-map','[a]',
                '-c:v','libx264','-preset','fast','-crf','18','-c:a','aac','-ar','48000','-ac','2',
                '-pix_fmt','yuv420p','-frames:v',plan['output_frames'],'-r',FPS,'-fps_mode','cfr','-movflags','+faststart',output],cancel=cancel)
    return verify(output,plan['output_frames'])


def concatenate(folder, outputs, checks, clean, cancel=None):
    """Copy video packets; decode/trim each AAC stream before one audio encode."""
    if len(outputs)==1:
        shutil.copy2(outputs[0],clean)
        return
    listing=folder/'concat.txt'
    silent=[]
    for i,output in enumerate(outputs):
        video=folder/f'video_{i:03d}.mp4'
        ffmpeg(['-i',output,'-map','0:v:0','-an','-c:v','copy',video],cancel=cancel)
        silent.append(video)
    listing.write_text(''.join(f"file '{p.name}'\nduration {c['edited']['frames']/FPS:.15f}\n" for p,c in zip(silent,checks,strict=True)),encoding='utf-8')
    args=['-f','concat','-safe','0','-i',listing.name]
    graph=[]
    for i,(output,check) in enumerate(zip(outputs,checks,strict=True),1):
        args+=['-i',output.name]
        duration=check['edited']['frames']/FPS
        graph.append(f'[{i}:a]aresample=48000:async=1:first_pts=0,apad,atrim=duration={duration:.15f},asetpts=N/SR/TB[a{i}]')
    graph.append(''.join(f'[a{i}]' for i in range(1,len(outputs)+1))+f'concat=n={len(outputs)}:v=0:a=1[a]')
    ffmpeg(args+['-filter_complex',';'.join(graph),'-map','0:v:0','-map','[a]',
                 '-c:v','copy','-c:a','aac','-ar','48000','-ac','2','-movflags','+faststart',clean.name],cwd=folder,cancel=cancel)


def ass_time(seconds):
    cs=round(seconds*100);hour,cs=divmod(cs,360000);minute,cs=divmod(cs,6000);second,cs=divmod(cs,100)
    return f'{hour}:{minute:02d}:{second:02d}.{cs:02d}'


def ass_text(text, width=18):
    value=text.replace('\\','＼').replace('{','｛').replace('}','｝').replace('\r','').replace('\n',' ')
    return '\\N'.join(value[i:i+width] for i in range(0,len(value),width))


def write_subtitles(folder, captions, width, height, notes=()):
    from pipeline import timestamp
    (folder/'字幕.srt').write_text('\n'.join(f"{i}\n{timestamp(c['start'])} --> {timestamp(c['end'])}\n{c['text']}\n" for i,c in enumerate(captions,1)),encoding='utf-8')
    size=max(12,round(height*.028));margin=max(12,round(height*.045));wrap=max(12,int(width/(size*1.05))-2)
    header=f'''[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Dialogue,Microsoft YaHei,{size},&H00FFFFFF,&H00FFFFFF,&H00101010,&H80000000,0,0,0,0,100,100,0,0,1,2,0,2,{margin},{margin},{margin},1
Style: Note,Microsoft YaHei,{max(11,size-2)},&H00FFFFFF,&H00FFFFFF,&H80000000,&H80000000,0,0,0,0,100,100,0,0,3,5,0,5,{margin},{margin},0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''
    events=[f"Dialogue: 0,{ass_time(c['start'])},{ass_time(c['end'])},Dialogue,,0,0,0,,{ass_text(c['text'],wrap)}" for c in captions]
    previous_note_end=0
    for note in sorted(notes,key=lambda n:float(n['start'])):
        start,end=float(note['start']),float(note['end'])
        if not math.isfinite(start) or not math.isfinite(end) or not 0<=start<end:raise ValueError('注释时间必须有序。')
        if start<previous_note_end:raise ValueError('注释时间不可重叠，请合并成一条或错开。')
        previous_note_end=end
        # Split at subtitle boundaries so one/two-line dialogue cannot collide with a note.
        bounds=sorted({start,end,*[t for c in captions for t in (c['start'],c['end']) if start<t<end]})
        note_text=ass_text(note['text'],wrap);note_lines=note_text.count('\\N')+1
        if note_lines*(size-2)*1.3>height*.5:raise ValueError('注释太长，请拆成多个时间段，避免文字超出画面。')
        for a,b in zip(bounds,bounds[1:]):
            count=max([ass_text(c['text'],wrap).count('\\N')+1 for c in captions if c['start']<b and c['end']>a] or [1])
            y=round(height-margin-count*size*1.3-size*.6-note_lines*(size-2)*.65)
            events.append(f"Dialogue: 1,{ass_time(a)},{ass_time(b)},Note,,0,0,0,,{{\\an5\\pos({width//2},{max(size,y)})}}{note_text}")
    (folder/'字幕.ass').write_text(header+'\n'.join(events)+'\n',encoding='utf-8')


def publish(project, folder, files):
    """Prepare all replacements, archive previous aliases, and roll back failed publication."""
    prepared={name:project/(name+'.'+uuid.uuid4().hex+'.tmp') for name in files}
    archive=project/'takes'/('final_'+uuid.uuid4().hex[:12])
    old=list(project.glob('成片*.mp4'))+[p for p in (project/'字幕.srt',project/'字幕.ass',project/'媒体验收.json') if p.is_file()]
    changed=set()
    try:
        for name,temp in prepared.items():shutil.copy2(folder/name,temp)
        if old:
            archive.mkdir(parents=True)
            for path in old:shutil.copy2(path,archive/path.name)
        for name,temp in prepared.items():
            temp.replace(project/name)
            changed.add(name)
        # A new version without subtitles must never expose a previous version's burn-in.
        for path in old:
            if path.name not in files:
                path.unlink(missing_ok=True)
                changed.add(path.name)
        write_json(project/'current_edit.json',{'id':folder.name,'created_at':now(),'recipe':'edits/'+folder.name+'/recipe.json'})
    except Exception:
        for name in changed:
            previous=archive/name
            if previous.is_file():shutil.copy2(previous,project/name)
            elif project.joinpath(name).exists():project.joinpath(name).unlink()
        raise
    finally:
        for temp in prepared.values():temp.unlink(missing_ok=True)


def build(project, story, clips, width, height, settings, status=lambda text:None, cancel=None, recipe=None, publish_result=True, proxy=''):
    from pipeline import media_info
    project=Path(project).resolve()
    if recipe is None:
        recipe={'version':1,'story':copy.deepcopy(story),'settings':{k:settings.get(k) for k in ('edit_preset','subtitle_alignment','subtitles','review_interval')},
                'width':width,'height':height,'sources':[], 'notes':copy.deepcopy(settings.get('notes',[])),
                'masks':copy.deepcopy(settings.get('masks',[])), 'created_at':now()}
        for shot,clip in zip(story['shots'],clips,strict=True):
            clip=Path(clip).resolve()
            if not clip.is_relative_to(project):raise ValueError('后期输入镜头必须属于当前项目。')
            sha=Downloader.checksum(clip,cancel);target=project/'source_cache'/ (sha+'.mp4')
            target.parent.mkdir(exist_ok=True)
            if not target.exists() or Downloader.checksum(target,cancel)!=sha:shutil.copy2(clip,target)
            recipe['sources'].append({'uid':shot.get('uid'),'file':str(target.relative_to(project)).replace('\\','/'),'sha256':sha})
    else:
        recipe=copy.deepcopy(recipe);story=recipe['story'];width,height=recipe['width'],recipe['height'];settings=recipe['settings']
    if recipe.get('version')!=1 or not 64<=width<=4096 or not 64<=height<=4096 or not 1<=len(story['shots'])<=150:
        raise ValueError('后期配方版本、尺寸或镜头数量不支持。')
    preset=settings.get('edit_preset') or 'original'
    if preset not in PRESETS:raise ValueError('未知剪辑预设。')
    subtitle_mode=settings.get('subtitle_alignment') or 'approximate'
    burn=bool(settings.get('subtitles',True))
    folder=project/'edits'/(time.strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:8]);folder.mkdir(parents=True)
    write_json(folder/'recipe.json',recipe)
    model=None
    needs_speech=any(s.get('dialogue') for s in story['shots']) and (preset!='original' or subtitle_mode=='speech'
        or any(s.get('edit_ranges') and s.get('dialogue') and not s.get('dialogue_timings') for s in story['shots']))
    frozen=recipe.get('finishing',[])
    if frozen and len(frozen)!=len(story['shots']):raise ValueError('冻结剪辑计划与镜头数量不一致。')
    if needs_speech and not frozen:model=ensure_model(status,cancel,proxy)
    checks,captions,outputs,offset=[],[],[],0
    for index,(shot,source) in enumerate(zip(story['shots'],recipe['sources'],strict=True)):
        if cancel and cancel():raise Cancelled('后期任务已停止，原片与既有成片版本已保留。')
        status(f'后期质检与剪辑：镜头 {index+1}/{len(story["shots"])}')
        path=contained(project,source['file'])
        if Downloader.checksum(path,cancel)!=source['sha256']:raise RuntimeError('版本原片快照已改变，不能静默重建其他内容。')
        info=media_info(path,True);normal=folder/f'normal_{index:03d}.mp4'
        normalized=normalize(path,normal,width,height,info,cancel)
        if frozen:
            analysis=copy.deepcopy(frozen[index]['analysis']);plan=copy.deepcopy(frozen[index]['plan'])
            if plan['source_frames']!=normalized['frames']:raise RuntimeError('冻结计划与原片帧数不一致。')
        else:
            samples=pcm_audio(normal,normalized['duration'],cancel)
            analysis=analyze_audio(samples,normalized['duration'],model,cancel)
            next_link=index+1<len(story['shots']) and story['shots'][index+1].get('use_previous_last_frame',False)
            plan=edit_plan(shot,normalized['frames'],analysis,preset,preserve_start=shot.get('use_previous_last_frame',False),preserve_end=next_link)
        from .masking import apply_masks
        selected_masks=[mask for mask in recipe.get('masks',[]) if mask['shot_uid']==shot.get('uid')]
        masked,mask_report=apply_masks(normal,folder/f'masked_{index:03d}.mp4',selected_masks,width,height,normalized['frames'],folder/f'masks_{index:03d}',cancel=cancel)
        output=folder/f'shot_{index:03d}.mp4';result=render_cut(masked,output,plan,cancel)
        effective=analysis if subtitle_mode=='speech' else {}
        lines=copy.deepcopy(frozen[index]['captions']) if frozen else align_captions(shot,effective,plan['keep_frames'],normalized['duration'])
        local_captions=copy.deepcopy(lines)
        for line in lines:line.update(start=line['start']+offset,end=line['end']+offset,shot_uid=shot.get('uid'))
        captions.extend(lines);offset+=plan['output_frames']/FPS;outputs.append(output)
        checks.append({'shot_id':shot['id'],'uid':shot.get('uid'),'source':info,'normalized':normalized,'edited':result,
                       'analysis':analysis,'plan':plan,'captions':local_captions,'masks':mask_report,
                       'preview_source':str(masked.relative_to(folder)).replace('\\','/'),
                       'spoken_units':sum(spoken_units(x['text']) for x in shot.get('dialogue',[]))})
    clean=folder/'成片.mp4'
    concatenate(folder,outputs,checks,clean,cancel)
    expected=sum(c['plan']['output_frames'] for c in checks);final=verify(clean,expected,width,height)
    if any(not 0<=float(note['start'])<float(note['end'])<=expected/FPS for note in recipe.get('notes',[])):
        raise ValueError('注释必须使用本版本成片时间轴，不能超出最终时长。')
    write_subtitles(folder,captions,width,height,recipe.get('notes',[]))
    files=['成片.mp4','字幕.srt','字幕.ass','媒体验收.json']
    if burn and (captions or recipe.get('notes')):
        # The actual candidate is the only input. Root-level previous films are never read.
        ffmpeg(['-i','成片.mp4','-vf','ass=字幕.ass','-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p','-c:a','copy','-movflags','+faststart','成片_字幕版.mp4'],cwd=folder,cancel=cancel)
        verify(folder/'成片_字幕版.mp4',expected,width,height);files.append('成片_字幕版.mp4')
    recipe['finishing']=[{k:c[k] for k in ('analysis','plan','captions')} for c in checks]
    write_json(folder/'recipe.json',recipe)
    detected_seconds=sum(sum(b-a for a,b in c['analysis'].get('speech_intervals',[])) for c in checks)
    measured=any(c['analysis'].get('method')!='rms_only' for c in checks)
    original_seconds=sum(c['normalized']['frames'] for c in checks)/FPS
    report={'version':1,'edit_id':folder.name,'recipe_hash':digest(recipe),'shots':checks,'final':final,'expected_frames':expected,
            'original_seconds':original_seconds,'edited_seconds':expected/FPS,'detected_speech_seconds':round(detected_seconds,4),
            'original_speech_density':round(detected_seconds/original_seconds,4) if measured else None,'edited_speech_density':round(detected_seconds/(expected/FPS),4) if measured else None,
            'detected_speech_cut_count':sum(not c['plan']['detected_speech_covered'] for c in checks),
            'subtitle_timing':sorted({c['alignment'] for c in captions}),
            'limitations':'VAD 是语音活动检测，不能确认 H3 逐字说对台词；字幕句内仍按字数估算，支持人工时间标注。'}
    write_json(folder/'媒体验收.json',report)
    from .review import evidence
    report['review']=evidence(folder,checks,outputs,sample_interval=settings.get('review_interval') or .75,cancel=cancel)
    write_json(folder/'媒体验收.json',report)
    write_json(folder/'completed.json',{'files':{name:Downloader.checksum(folder/name,cancel) for name in files},'completed_at':now()})
    if cancel and cancel():raise Cancelled('后期任务已停止，已有成片未替换。')
    if publish_result:publish(project,folder,files)
    return project/'成片.mp4' if publish_result else clean

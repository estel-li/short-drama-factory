"""Frame-exact edit plans and subtitle mapping, independent of the media renderer."""
from __future__ import annotations

import math

from .quality import spoken_units

PRESETS = {
    'original': {'lead': 0, 'tail': 0, 'gap': 0, 'max_removed': 0},
    'gentle': {'lead': .4, 'tail': .55, 'gap': .35, 'max_removed': .35},
    'compact': {'lead': .25, 'tail': .4, 'gap': .22, 'max_removed': .55},
}


def merge_frames(spans):
    result = []
    for start, end in sorted(spans):
        if end <= start:
            continue
        if result and start <= result[-1][1]:
            result[-1][1] = max(end, result[-1][1])
        else:
            result.append([start, end])
    return result


def edit_plan(shot, frames, analysis, preset='gentle', fps=24, preserve_start=False, preserve_end=False):
    if preset not in PRESETS:
        raise ValueError('未知剪辑预设。')
    full = [[0, frames]]
    speech = analysis.get('speech_intervals', [])
    protect = merge_frames([[max(0, math.floor(a*fps)), min(frames, math.ceil(b*fps))]
                            for a, b in analysis.get('relaxed_speech_intervals', speech)])
    if shot.get('dialogue_timings'):
        aligned = align_captions(shot, analysis, full, frames/fps, fps)
        protect = merge_frames(protect + [[math.floor(line['source_start']*fps), math.ceil(line['source_end']*fps)] for line in aligned])
    parameters = PRESETS[preset]
    reasons = []
    if shot.get('edit_ranges') is not None:
        ranges = shot['edit_ranges']
        if not isinstance(ranges, list) or not ranges or shot.get('preserve_performance'):
            raise ValueError('明确后期选段须为非空区间，不能同时要求保留全部表演。')
        keep = []
        for item in ranges:
            start, end = float(item['start']), float(item['end'])
            if not math.isfinite(start) or not math.isfinite(end) or not 0 <= start < end <= frames / fps + .00001:
                raise ValueError('后期选段必须在原片实际时长内。')
            a, b = round(start * fps), round(end * fps)
            if not 0 <= a < b <= frames or keep and a < keep[-1][1]:
                raise ValueError('后期选段须按时间排序、不重叠，并至少保留一帧。')
            keep.append([a, b])
        if preserve_start and keep[0][0] != 0 or preserve_end and keep[-1][1] != frames:
            raise ValueError('明确选段不能剪掉首帧接续所需的头尾帧；独立快切镜头请在创作时选择不接续。')
        if shot.get('dialogue') and not protect:
            raise ValueError('有对白的明确选段需要可靠语音区间或人工 dialogue_timings；不能猜测对白位置后裁剪。')
        reasons.append('按用户/当前AI明确选定的原片区间剪辑，保持区间内原速。')
    elif preset == 'original' or not shot.get('dialogue') or shot.get('preserve_performance'):
        keep = full
        reasons.append('保留原始表演与时间轴。')
    elif not (analysis.get('safe_for_auto_edit') or shot.get('dialogue_timings')) or not protect:
        keep = full
        reasons.append('人声检测证据不足，保留原片。')
    else:
        keep = merge_frames([[max(0, a-math.ceil((parameters['lead'] if i==0 else parameters['gap']/2)*fps)),
                              min(frames, b+math.ceil((parameters['tail'] if i==len(protect)-1 else parameters['gap']/2)*fps))]
                            for i,(a,b) in enumerate(protect)])
        # Adjacent speech regions keep a short breath; longer gaps are removed.
        keep = merge_frames([[a,b] for a,b in keep])
        for i in range(1,len(keep)):
            if keep[i][0]-keep[i-1][1] <= math.ceil(parameters['gap']*fps):
                keep[i][0]=keep[i-1][1]
        keep = merge_frames(keep)
        if preserve_start:
            keep[0][0] = 0
            reasons.append('I2VA 接续保留实际首帧。')
        if preserve_end:
            keep[-1][1] = frames
            reasons.append('后镜使用末帧，保留当前实际末帧。')
        minimum = math.ceil(frames*(1-parameters['max_removed']))
        missing = minimum-sum(b-a for a,b in keep)
        # Limit compression by restoring the removed tail, then head, then gaps.
        if missing > 0:
            add=min(missing,frames-keep[-1][1]);keep[-1][1]+=add;missing-=add
            add=min(missing,keep[0][0]);keep[0][0]-=add;missing-=add
            for i in range(1,len(keep)):
                add=min(missing,keep[i][0]-keep[i-1][1]);keep[i-1][1]+=add;missing-=add
            keep=merge_frames(keep)
    covered = all(any(a<=p and q<=b for a,b in keep) for p,q in protect)
    if not covered:
        raise RuntimeError('剪辑计划切入了检测到的人声保护区间。')
    count=sum(b-a for a,b in keep)
    return {'source_frames':frames, 'output_frames':count, 'keep_frames':keep, 'protected_frames':protect,
            'detected_speech_covered':covered, 'removed_seconds':round((frames-count)/fps,4), 'preset':preset,
            'reasons':reasons, 'speech_integrity_scope':'覆盖较宽阈值检测到的语音活动；不能替代逐字识别和试听。'}


def map_time(value, keep_frames, fps=24):
    value *= fps
    total = 0
    for start, end in keep_frames:
        if value < start:
            return total/fps
        if value <= end:
            return (total+value-start)/fps
        total += end-start
    return total/fps


def align_captions(shot, analysis, keep_frames, source_seconds, fps=24):
    lines=[line for line in shot.get('dialogue',[]) if line.get('text','').strip()]
    if not lines:
        return []
    manual=shot.get('dialogue_timings')
    if manual is not None:
        if len(manual)!=len(lines):raise ValueError('对白时间标注数量必须与 dialogue 一致。')
        spans=[];previous=0
        for item in manual:
            a,b=float(item['start']),float(item['end'])
            if not math.isfinite(a) or not math.isfinite(b) or not previous<=a<b<=source_seconds:
                raise ValueError('对白时间标注必须有序、在镜头原片范围内。')
            spans.append([a,b]);previous=b
        method='manual'
    else:
        spans=analysis.get('speech_intervals',[])
        method='vad_weighted' if spans else 'approximate'
        if not spans:
            spans=[[min(.4,source_seconds/4),max(source_seconds*.75,source_seconds-.55)]]
        weights=[max(1,spoken_units(line['text'])) for line in lines]
        active=sum(b-a for a,b in spans)
        def time_at(amount, end=False):
            for index,(a,b) in enumerate(spans):
                if amount < b-a or end and amount <= b-a or index==len(spans)-1:
                    return a+min(amount,b-a)
                amount-=b-a
            return spans[-1][1]
        assigned=[];offset=0
        for weight in weights:
            length=active*weight/sum(weights)
            assigned.append([time_at(offset),time_at(offset+length,True)]);offset+=length
        spans=assigned
    result=[]
    for line,(start,end) in zip(lines,spans,strict=True):
        a,b=map_time(start,keep_frames,fps),map_time(end,keep_frames,fps)
        if b<=a:
            raise ValueError('剪辑计划完全删除了一句标注对白，请恢复保护区间。')
        result.append({'text':line['text'],'speaker':line.get('speaker',''),'start':round(a,5),'end':round(b,5),
                       'source_start':start,'source_end':end,'alignment':method})
    return result

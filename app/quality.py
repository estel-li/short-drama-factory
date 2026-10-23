"""Deterministic production checks; recommendations never rewrite the user's lines."""
from __future__ import annotations

import copy
import math
import re
from difflib import SequenceMatcher
from .storage import digest

POST_FIELDS = {'dialogue_timings', 'preserve_performance', 'annotations', 'masks', 'edit_ranges'}


def _render_data(story, shot):
    fields = ('uid','scene','scene_id','summary','camera','action','duration','characters','continuity_group',
              'use_previous_last_frame','dialogue','prompt','mode','bindings','seed','seed_offset','props')
    return {'shot':{key:shot.get(key) for key in fields},
            'characters':[c for c in story.get('characters',[]) if c['id'] in shot.get('characters',[])]}


def shot_dependencies(story, shot):
    """Definitions actually supplied to the prompt compiler for this shot."""
    scenes = [s for s in story.get('scenes', [])
              if s.get('id') in (shot.get('scene_id'), shot.get('continuity_group'))
              or s.get('name') == shot.get('scene')]
    props = [p for p in story.get('props', []) if p.get('id') in shot.get('props', [])
             or p.get('name') and p['name'] in (shot.get('action', '') + shot.get('summary', ''))]
    result = {'scenes': scenes or story.get('scenes', []), 'props': props}
    narrators = {line.get('speaker') for line in shot.get('dialogue', []) if line.get('narration') is True}
    if narrators:
        result['voiceover_characters'] = [{k: c[k] for k in ('id', 'name', 'voice_description') if k in c}
                                          for c in story.get('characters', []) if c['id'] in narrators or c['name'] in narrators]
    return result


def _canonical_render_data(story, shot):
    value = copy.deepcopy(_render_data(story, shot))
    value['shot']['scene_id'] = value['shot']['scene_id'] or None
    if value['shot']['dialogue'] is not None:
        for line in value['shot']['dialogue']:
            if line.get('narration') is False:
                line.pop('narration')
    return value


def render_contract(story, shot):
    value = _canonical_render_data(story, shot)
    if value['shot']['duration'] is not None:
        value['shot']['duration'] = float(value['shot']['duration'])
    value['definitions'] = shot_dependencies(story, shot)
    return 'v2:' + digest(value)


def render_contract_matches(expected, story, shot):
    if expected == render_contract(story, shot):return True
    if not isinstance(expected, str) or expected.startswith('v2:'):
        return False
    # Legacy contracts predate definition tracking, scene_id defaults and per-line narration.
    # Projects.save_story upgrades matching old records before applying definition edits.
    value = _canonical_render_data(story, shot)
    duration = value['shot']['duration']
    durations = [duration]
    if isinstance(duration, (int, float)) and float(duration).is_integer():
        durations = [float(duration), int(duration)]
    scene_ids = [value['shot']['scene_id']] if value['shot']['scene_id'] else [None, '']
    for seconds in durations:
        for scene_id in scene_ids:
            value['shot'].update(duration=seconds, scene_id=scene_id)
            if expected == digest(value):
                return True
    return False


def script_dialogue(text):
    """Only explicit [speaker] lines are authoritative; prose is never guessed."""
    result=[]
    for line in text.splitlines():
        match=re.fullmatch(r'\s*\[([^\]\r\n]{1,100})\]\s*(.+)',line)
        if match and match[2].strip():result.append({'speaker':match[1].strip(),'text':match[2].strip()})
    return result


CJK = re.compile(r'[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\uac00-\ud7af]')
# Natural English runs ~2.5 words/s; the rate is expressed in units/s at 5.6 (one unit per CJK
# character), so one Latin word has to weigh about 5.6 / 2.5 to land on the same timeline.
LATIN_WORD_UNITS = 2.2


def spoken_units(text):
    """Speech units: one per CJK character, LATIN_WORD_UNITS per Latin word.

    Counting Latin letters individually made a 41-letter English line need 8.27 seconds and
    blocked every English project, since dialogues language is a user-facing option.
    """
    cjk = len(CJK.findall(text))
    latin = CJK.sub(' ', text)
    words = [w for w in re.split(r'[\s\-\u2019\']+', latin) if any(c.isalnum() for c in w)]
    return round(cjk + len(words) * LATIN_WORD_UNITS, 4)


def dialogue_budget(dialogue, rate=5.6, lead=0.4, gap=0.3, tail=0.55):
    lines = [line for line in dialogue if line.get('text', '').strip()]
    units = sum(spoken_units(line['text']) for line in lines)
    required = lead + units / rate + max(0, len(lines) - 1) * gap + tail if lines else 0
    return {'units': units, 'lines': len(lines), 'required_seconds': round(required, 4),
            'target_units_per_second': rate}


def fitted_duration(dialogue, options, fallback=4):
    budget = dialogue_budget(dialogue, options.speech_rate, options.speech_lead, options.speech_gap, options.speech_tail)
    if not budget['lines']:
        return fallback
    maximum = 15 if options.allow_long_shots else 8
    if budget['required_seconds'] > maximum:
        raise ValueError(f"对白预计需要 {budget['required_seconds']:.2f} 秒，超过单镜 {maximum} 秒；请在语义边界分镜，不能删词或强行快读。")
    return max(4.0, math.ceil(budget['required_seconds'] * 100) / 100)


def pack_dialogue(lines, rate=5.6, maximum=8, lead=0.4, gap=0.3, tail=0.55, max_lines=3):
    """Pack an authoritative transcript in order, without dropping/repeating text."""
    groups = []
    for line in lines:
        if not line.get('text', '').strip():
            continue
        value = copy.deepcopy(line)
        if dialogue_budget([value], rate, lead, gap, tail)['required_seconds'] > maximum:
            raise ValueError('单句台词超出镜长上限，请先按语义拆成多句；程序不会自动删改原句。')
        candidate = (groups[-1] if groups else []) + [value]
        if not groups or len(candidate) > max_lines or len({x.get('speaker') for x in candidate if x.get('speaker')})>2 or dialogue_budget(candidate, rate, lead, gap, tail)['required_seconds'] > maximum:
            groups.append([value])
        else:
            groups[-1].append(value)
    return [{'dialogue': group, 'duration': max(4, math.ceil(dialogue_budget(group, rate, lead, gap, tail)['required_seconds'] * 100) / 100)} for group in groups]


def cast_issues(story):
    issues = []
    for index, left in enumerate(story.get('characters', [])):
        for right in story['characters'][index + 1:]:
            a, b = (re.sub(r'\s+', ' ', c.get('visual_description', '').lower()).strip() for c in (left, right))
            similarity = SequenceMatcher(None, a, b).ratio() if a and b else 0
            if similarity >= 0.85:
                issues.append({'kind': 'similar_cast', 'severity': 'warning', 'characters': [left['id'], right['id']],
                               'similarity': round(similarity, 3), 'message': f"{left['name']}与{right['name']}的外观描述过于接近。至少区分脸型/年龄、服装主色、配饰等多个特征，不能只靠发长。"})
    return issues


def story_report(story, options):
    issues, shots = cast_issues(story), []
    names = {c['name']: c['id'] for c in story.get('characters', [])}
    ids = set(names.values())
    for shot in story['shots']:
        budget = dialogue_budget(shot.get('dialogue', []), options.speech_rate, options.speech_lead, options.speech_gap, options.speech_tail)
        item = {'uid': shot.get('uid'), 'id': shot['id'], 'duration': shot['duration'], **budget}
        shots.append(item)
        if budget['required_seconds'] > shot['duration'] + 0.05:
            issues.append({'kind': 'dialogue_overflow', 'severity': 'error', 'uid': shot.get('uid'), 'shot_id': shot['id'],
                           'message': f"镜头 {shot['id']} 的对白预计需要 {budget['required_seconds']:.2f} 秒，目前只有 {shot['duration']:.2f} 秒。请增加镜长或拆镜。"})
        for line in shot.get('dialogue', []):
            speaker = line.get('speaker', '')
            cid = names.get(speaker, speaker if speaker in ids else None)
            # Narration only excuses the lines it actually covers; a named, on-screen speaker
            # stays checked even when the project has narration enabled.
            if line.get('narration') is True and not options.narration:
                issues.append({'kind': 'narration_disabled', 'severity': 'error', 'uid': shot.get('uid'), 'shot_id': shot['id'],
                               'message': f"镜头 {shot['id']} 包含画外旁白，请先开启项目的“采用画外旁白”。"})
            narrated = options.narration and (line.get('narration') is True or not cid)
            if cid and cid not in shot.get('characters', []) and not narrated:
                issues.append({'kind': 'offscreen_speaker', 'severity': 'error', 'uid': shot.get('uid'), 'shot_id': shot['id'],
                               'message': f"镜头 {shot['id']} 的说话人 {speaker} 没有出场。请确认出场人物；画外音需开启项目旁白并将本句 narration 设为 true。"})
    return {'version': 1, 'issues': issues, 'shots': shots, 'ready': not any(i['severity'] == 'error' for i in issues),
            'measurement': '对白字数与目标语速的预算；实际语速以生成音频检测为准。'}


def prompt_cast_valid(prompt, story, shot, bindings, mode):
    allowed = set(shot.get('characters', []))
    for asset in bindings.get('images', []) if mode=='Ref2VA' else []:
        if asset.get('character') and asset['character'] not in allowed:
            raise ValueError('身份参考绑定了本镜未出场的角色：' + asset['character'] + '。请修正绑定，避免身份串用。')
    if mode == 'Ref2VA':
        definitions = re.search(r'^\s*subject_definitions\s*:(.*?)(?=^\s*summary\s*:)', prompt, re.M | re.S)
        if definitions:
            for character in story.get('characters', []):
                if character['id'] not in allowed and character['name'] in definitions.group(1):
                    raise ValueError('subject_definitions 定义了本镜未出场的角色：' + character['name'] + '。参考中的其他人物不能被要求出场或 fully_preserved。')
    return prompt

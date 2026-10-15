"""Approved prompt sections with a mode, cast, and reference contract."""
import re
import uuid

from .content import BASE_FIELDS, REF_FIELDS, prompt_valid
from .quality import prompt_cast_valid
from .storage import identifier,now,read_json,write_json


def reference_contract(mode,bindings):
    if mode!='Ref2VA':return {}
    return {kind:[{key:asset.get(key) for key in ('sha256','type','include_audio','character')} for asset in bindings.get(kind,[])] for kind in ('images','videos','audios')}


def save_template(project,story,shot,name):
    state=read_json(project/'state.json',{})
    record=state.get('shots_by_uid',{}).get(shot['uid'],state.get('shots',{}).get(str(shot['id']),{}))
    if record.get('status')!='done':raise ValueError('先生成并验看镜头，再保存已验收样板。')
    from .quality import render_contract_matches
    if record.get('render_contract') and not render_contract_matches(record['render_contract'],story,shot):raise ValueError('当前镜头内容已改动，先重生成，不能把旧视频对应的提示词冒充已验收样板。')
    if not record.get('render_contract'):
        native=read_json(project/'prompts'/f"{shot['id']:03d}.json",{}).get('7',{}).get('inputs',{}).get('prompt','')
        if not shot.get('prompt') or not native.endswith(shot['prompt']) or shot['uid'] in state.get('changed_shots',[]):raise ValueError('旧镜头缺少匹配的生成记录，请先续跑校验。')
    mode=shot.get('compiled_mode')
    if mode not in ('T2VA','I2VA','FL2VA','L2VA','Ref2VA'):raise ValueError('缺少实际模式记录，请先校验并编译提示词。')
    bindings={kind:[dict(asset) for asset in items] if isinstance(items,list) else dict(items) if items else items for kind,items in shot.get('compiled_bindings',{}).items()}
    assets=read_json(project/'assets.json',{})
    by_name={c['name']:c['id'] for c in story.get('characters',[])}
    for asset in bindings.get('images',[]):
        cid=assets.get(asset.get('id'),{}).get('character') or by_name.get(asset.get('name'))
        if cid:asset['character']=cid
    prompt_valid(shot['prompt'],mode,bindings,shot.get('dialogue',[]))
    prompt_cast_valid(shot['prompt'],story,shot,bindings,mode)
    fields=REF_FIELDS if mode=='Ref2VA' else BASE_FIELDS
    sections={}
    for index,field in enumerate(fields):
        end=rf'(?=^\s*{fields[index+1]}\s*:)' if index+1<len(fields) else r'\Z'
        match=re.search(rf'^\s*{field}\s*:(.*?){end}',shot['prompt'],re.M|re.S)
        if not match:raise ValueError('样板段落无法解析。')
        sections[field]=match[1].strip()
    if mode=='Ref2VA' and '<d>' in sections['subject_definitions']:raise ValueError('人物定义不能夹带旧台词，请先分离对白后保存样板。')
    value={'id':'tpl-'+uuid.uuid4().hex[:16],'name':name or shot.get('summary') or f"镜头 {shot['id']} 样板",'mode':mode,
           'cast':sorted(shot['characters']),'references':reference_contract(mode,bindings),'sections':sections,
           'source_shot_uid':shot['uid'],'created_at':now()}
    write_json(project/'prompt_templates'/(value['id']+'.json'),value)
    return value


def selected(project,shot,mode,bindings):
    tid=shot.get('prompt_template_id')
    if not tid:return None
    value=read_json(project/'prompt_templates'/(identifier(tid)+'.json'))
    if not value:raise ValueError('所选样板不存在。')
    if value['mode']!=mode or value['cast']!=sorted(shot['characters']) or value['references']!=reference_contract(mode,bindings):
        raise ValueError('样板的实际模式、出场人物或参考素材不匹配，不能混用其他 Ref2VA 基准。请选择匹配样板。')
    return value


def listing(project):
    return [{k:value[k] for k in ('id','name','mode','cast','source_shot_uid','created_at')} for path in (project/'prompt_templates').glob('*.json') if (value:=read_json(path))]

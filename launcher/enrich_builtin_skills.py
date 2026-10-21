"""Build reproducible application skills from reviewed, pinned upstream text sources."""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
RESEARCH = ROOT / 'data/skill-research'
sys.path.insert(0, str(ROOT))
from app.skills import Skills
from app.storage import now, read_json, write_json

D = 'zenstory-ai/drama-skills'
H = 'MiniMax-AI/MiniMax-H3'
A = 'aicontentskills/ai-video-storyboard-skill'

DEVELOP = 'skills/short-drama-develop/'
STORY = 'skills/short-drama-storyboard/'
WRITE = 'skills/short-drama-write/'
VIDEO = 'skills/short-drama-video-prompts/'
ASSETS = 'skills/short-drama-assets/'

PROFILES = {
 'outline-hook': ('outline', '短剧钩子与反转', '从观众首先能得到的具体回报开场。用已经出现的证据和人物选择制造反转，分别辨认揭示、转折、回报和继续发展的压力；不能靠陌生人救场。每个节拍写出前后状态、行动代价和可见载体。',
     [DEVELOP+'SKILL.md', DEVELOP+'references/story-craft.md', DEVELOP+'references/genre-and-hook-playbook.md', DEVELOP+'references/reveal-reversal-payoff.md']),
 'outline-three-act': ('outline', '三幕剧情与因果节拍', '用建立目标与失衡、策略受阻与代价、关键选择与结果三种功能组织短片；幕长不采用固定比例。把节拍用“所以/但是”串联，不能用“然后”堆事件。开场展示压力已活跃，结尾兑现当片承诺。',
     [DEVELOP+'SKILL.md', DEVELOP+'references/story-craft.md', DEVELOP+'references/episode-design.md']),
 'outline-mystery': ('outline', '悬疑伏笔与公平揭示', '先确定真相，再区分世界事实、角色认知和观众知情时机。每个线索有可拍摄载体、接触权限、初次解释和最终兑现；误导来自合理解释或视角，不能临时改事实。揭示后必须有人改变策略。',
     [DEVELOP+'SKILL.md', DEVELOP+'references/story-craft.md', DEVELOP+'references/reveal-reversal-payoff.md', DEVELOP+'references/genre-cards.md']),
 'outline-warm': ('outline', '温情人物与关系变化', '以具体的小愿望、照料动作、欠下的承诺或重要物件承载关系。人物各有需要、策略和边界；不要把善良写成没有阻力。温暖落在付出代价后的选择及回应开场的动作，避免末尾说教。',
     [DEVELOP+'SKILL.md', DEVELOP+'references/story-craft.md', DEVELOP+'references/serial-character-and-memory.md', WRITE+'references/dialogue-craft.md']),
 'storyboard-fast': ('storyboard', '快节奏与镜头职责', '先落实原文，再选择观看位置。每镜明确新增的信息、选择或后果；证据特写、听者反应和空间建立各有职责。仅在新信息、视线、动作状态或空间关系发生变化时切镜，避免同动作重复表演。',
     [STORY+'SKILL.md', STORY+'references/shot-craft.md', STORY+'references/production-shot-grammar.md', STORY+'references/lighting-craft.md']),
 'storyboard-dialogue': ('storyboard', '对白正反打与潜台词', '先确定两人目标、议程、轴线和左右位置。台词是一种关系行动，重要一句落下后安排可读的听者反应。保持视线方向、道具归属、说话和反应的时间顺序；不靠随机换角度或无限拉近表达情绪。',
     [STORY+'SKILL.md', STORY+'references/shot-craft.md', WRITE+'references/dialogue-craft.md', STORY+'references/blocking-playbooks.md']),
 'storyboard-action': ('storyboard', '动作调度与空间连续性', '建立入口、出口、障碍、前中后景和行动目标。按动作前状态、主要动作、动作后状态、后果拆镜；手、道具和屏幕运动方向不能无来源漂移。精细拦截或复杂双手动作改成等效的常见动作或结果镜，不删戏剧信息。',
     [STORY+'SKILL.md', STORY+'references/shot-craft.md', STORY+'references/blocking-playbooks.md', VIDEO+'references/generability.md', ASSETS+'references/continuity-delta.md']),
 'storyboard-montage': ('storyboard', '旁白蒙太奇与声音推进', '画面提供具体变化，旁白连接不同画面的因果与意义，避免逐字复述画面。标明旁白声源、可见人物闭嘴及声音延续；时间省略和地点转移写清，选用重复物件、动作或声响建立母题。',
     [STORY+'SKILL.md', STORY+'references/shot-craft.md', WRITE+'references/scene-sound-dramaturgy.md', VIDEO+'references/performance-action-timing.md', STORY+'references/keyframe-craft.md']),
}

APPLICATION = '''## 工作台适配契约（本文件为本地适配层）

这里执行短剧工厂的一个文字生成阶段。上游原文保留为真实参考；采用其创作与制作方法。
上游的 CLI 命令、其他 Agent Skill 路由、Markdown/JSONL 文件写入、MiniMax Hub/Canvas 工具、
人工接受/终审流程和默认数量不在本次文字调用中执行。用户的输入、参数与程序 schema 决定产物。
检查模式的暂停由工作台控制；自动模式不额外提问或暂停。资料缺口采用与原意一致的保守选择。

- 视觉风格：{{style}}；题材：{{genre}}；时长：{{duration}} 秒。
- 对白语言：{{language}}；配乐说明：{{music}}。
- 不把示例中的人物、对白、画幅、分集数、九宫格、1080p 或 30fps 当成项目事实。
- 不输出讲解、代码围栏、审批请求或脚本，只返回程序指定的 JSON。
- 不改用户已确定的人物、主题、关键动作与结局；改编实现方式时保留戏剧结果。
- 参考素材仅以真实绑定的文件与编号为准，不虚构素材。
'''

# The H3 mode only exists in the prompt stage; injecting an empty value elsewhere printed
# "实际 H3 模式：。" into outline and storyboard prompts.
PROMPT_APPLICATION_LINE = '- 实际 H3 模式：{{mode}}（已由程序确定，不得根据参考图片数量更改）。\n'

# Outline skills also serve the whole-series planner (SeriesPlan). The contract below covers the
# common fields; app/content.py adds the stricter SeriesPlan override when the task asks for it,
# so this text must not forbid multi-episode planning.
OUTLINE_CONTRACT = '''## 大纲产物

返回 title、premise、beats、ending；字段形状服从随请求给出的 schema。
premise 写明主人公、当前目标、真实阻力、代价与观众回报。beats 中每项 description
写可见事件、人物如何选择、选择改变什么、为何导致下一拍；有需要时在同一项记录
setup、payoff、before_state、after_state、source_fact 和情绪功能。ending 写实际结果及呼应。
当前项目默认是一部按总时长约束的短片，不为凑幕数增加无用场景。
自检：人物有行动主动性，阻力有筹码，关键揭示可回溯，结尾兑现承诺，节拍不能任意互换。
'''

STORY_CONTRACT = '''## 分镜产物与字段映射

返回 Story JSON 的 title、style、aspect_ratio、characters、scenes、props、shots。
只返回本批 required_shots 个镜头，顺序从 start_shot 开始；固定和手动镜长使用 shot_durations；对白拟合模式由程序按 dialogue_pacing 计算，台词必须能在单镜上限内完整说完。
本批与 previous_shots 衔接，existing_assets 的人物 id 与设定保持一致，prompt 此阶段留空。

- characters：稳定 id、name、visual_description（英文外观）、voice_description。
- scenes / props：稳定 id 和 name；记录光源、空间锚点、道具归属、状态及必要文字。
- shot.scene / scene_id / continuity_group：场景名称、对应场景 id、连续段。
- shot.summary：本镜承担的信息、决定或后果，不只写“人物说话”。
- shot.action：动作开始、可见过程和结果。
- shot.camera：景别、观察侧、运动类型、幅度、速度与停止位置，并解释动机。
- shot.characters / props：只填本镜真实出场的 id；dialogue 保留原文与说话人。

一个工作台镜头对应一段单独生成的视频。按当前时长保留一个主要动作及可读反应，
默认最多两名可见人物，可连续至多三句短对白。按 dialogue_pacing 的语速、起手、句间和收尾预算装镜；长句按语义分到相邻镜头，不能强行快读或改词。角色至少用脸型/年龄、服装主色、配饰等多个外观锚点区分，不能只靠发长。
不要把上游“首尾帧必须成对”的外部生产约束套到 H3 L2VA：本程序支持独立尾帧。
不虚构 IMG/REF 文件或使用源套件的 SHOT 文档 id 代替本程序人物和场景 id。
自检覆盖原文、镜头职责、空间轴线、双手/道具状态、光源关系及前后边界。
'''

# Only I2VA/FL2VA/L2VA emit a first/last-frame alignment line; T2VA and Ref2VA have none.
KEYFRAME_CONTRACT = '''实际时长来自 aligned_duration；对齐行由程序按两位小数写好。
首帧对齐由程序写在提示词第一行，正文不要重复：I2VA 从 "For the target video, at 0.00 seconds"
开始，FL2VA 用 "How the reference pictures align" 并把 <Picture 2> 对齐到末尾时间，
L2VA 用同一句式把 <Picture 1> 对齐到末尾时间。T2VA 与 Ref2VA 没有对齐行。
首帧镜头先确立 Picture 1 中的风格、人物、构图与场景锚点，再描述后续动作；角色身份、服装、
颜色、关键道具与空间关系必须与参考保持一致。首尾帧镜头写清主体如何移动、姿态与道具如何变化、
构图与光线如何过渡到末帧。尾帧镜头从合理解释的更早状态出发，让动作与构图逐步落到尾帧。
'''

H3_CONTRACT = '''## H3 单镜头产物

返回本次请求末尾 schema 规定的命名字段，不要包装成单个 prompt 字符串，也不得返回 Markdown 或生成工具调用：
T2VA/I2VA/FL2VA/L2VA 返回 integrated_multimodal_description、overall_soundscape、non_diegetic_music 三段；
Ref2VA 返回 subject_definitions、summary、retention_analysis、detailed_description、overall_soundscape、non_diegetic_music 六段。
由程序按官方顺序拼接并添加第一行对齐指令，正文中不要重复该对齐行。
当前生成片段只使用 [Shot 1]；工作台分镜编号不是片段内的剪辑编号。
严格使用官方对应模式的段落结构；不要给 [Shot 1] 添加切镜时间戳。
画面、摄影和声音描述为英文；用户对白和必要画内文字保留原语言、原词与标点。
每个真正发声者采用稳定 (S1) 等编号；声音身份描述放在 <d> 外，<d> 中只放 [语言] 原对白。
旁白用 says in an off-screen voiceover，并在每个旁白块后说明画面人物 lips remain completely closed。
参考声音仅用于音色时不要搬入原音频台词；没有非画内配乐时 non_diegetic_music: N/A。
overall_soundscape 不重复对白，只交代环境和动作声音；全静音只在用户明确要求时使用 N/A。
输入提供 reference_labels，编号与 ComfyUI 实际装载一致。视频启用的声音轨道和独立音频
分别占用 Audio 编号，不假设 Video N 一定搭配 Audio N。
没有看到素材像素的文字模型不要猜新增衣服、人物或文字；使用用户资料与实际绑定角色，
将精确外观交给真实参考，描述目标动作和需保留的特征。
自检：字段有序、素材定义一致、动作可生成、时长闭合、没有未绑定标签、对白完整、无额外水印字幕。
'''

# Ref2VA is the one mode whose six sections the local adapter used to omit entirely, leaving the
# model to infer retention markers from upstream English alone. These lines are the load-bearing subset.
REF2VA_CONTRACT = '''## Ref2VA 六段字段与保留标记

subject_definitions：按 reference_labels 逐个定义实际绑定素材，写作 `<Subject 1> ...`、`<Picture 1> ...`、
`<Video 1> ...`、`<Audio 1> ...`，只用已绑定的编号；编号顺序与 ComfyUI 装载一致。
summary：以任务类型前缀开头，参考复现写 `[reference generation]`，其余按上游任务类型表选择；
一句话说明本镜要用参考生成什么。
retention_analysis：对每个被引用素材显式标注保留关系——完全保留 fully_preserved、
部分保留 partially_preserved、只转移属性 attribute_transfer、弱参考 weak_reference，
信息不足写 [unclear] 并说明缺什么。不能给未出场人物写 fully_preserved。
detailed_description：写成完整的镜头正文，包含 [Shot 1]、构图、人物位置、动作与状态变化、
摄影机运动、环境与光线，并指明参考内容在何处真正出现或生效；不要退化成剧情摘要。
overall_soundscape / non_diegetic_music：同其它模式的规则。
本模式没有首帧/尾帧对齐指令；不要添加对齐行，也不要给 [Shot 1] 写切镜时间戳。
参考里的其他人物不出场时不得写 fully_preserved，也不要为未绑定的素材发明标签。
'''


def source_file(repo, relative):
    folder = RESEARCH / repo.replace('/', '--')
    index = read_json(folder / 'source.json')
    content = (folder / relative).read_bytes()
    record = index['files'][relative]
    assert hashlib.sha256(content).hexdigest() == record['sha256'], relative
    return content.decode('utf-8-sig'), {'repo': repo, 'revision': index['revision'], 'path': relative, **record}


def build():
    canonical = ROOT / 'resources/builtin_skills'
    canonical.mkdir(parents=True, exist_ok=True)
    previous = read_json(ROOT / 'resources/builtin_skills.json', {})
    license_record = previous.get('license_source')
    cached_license = canonical / 'h3-t2va/references/licenses/MiniMax-H3-LICENSE.txt'
    license_text = cached_license.read_text(encoding='utf-8') if cached_license.exists() else ''
    if not license_record or hashlib.sha256(license_text.encode()).hexdigest() != license_record['sha256']:
        hf = httpx.get('https://huggingface.co/api/models/MiniMaxAI/MiniMax-H3', timeout=30).json()
        revision = hf['sha']
        response = httpx.get(f'https://huggingface.co/MiniMaxAI/MiniMax-H3/resolve/{revision}/LICENSE', follow_redirects=True, timeout=30)
        response.raise_for_status()
        license_text = response.text
        license_record = {'repo': 'MiniMaxAI/MiniMax-H3', 'revision': revision, 'path': 'LICENSE', 'sha256': hashlib.sha256(response.content).hexdigest()}
    definitions = dict(PROFILES)
    for mode, name in [('T2VA','官方完整文生'),('I2VA','官方完整首帧'),('FL2VA','官方完整首尾帧'),('L2VA','官方完整尾帧'),('Ref2VA','官方完整多模态参考')]:
        definitions['h3-'+mode.lower()] = ('prompt', name+' '+mode, '按官方完整指南编写 '+mode+' 提示词。素材定义、对齐指令、声音来源、保留关系和时序服从实际输入。', [])
    report = []
    for sid, (stage, name, method, paths) in definitions.items():
        sources, files, context = [], {}, []
        for path in paths:
            relative = 'references/drama-skills/' + path.removeprefix('skills/')
            files[relative], record = source_file(D, path)
            sources.append({**record, 'local_file': relative, 'license': 'MIT'})
            context.append(relative)
        if stage == 'prompt':
            paths = ['skills/h3-prompt-writing/SKILL.md']
            # base-en covers all four keyframe/text modes; Ref2VA only needs the shared basics plus
            # its own six-section guide, and loading both full guides pushed the render to 78% of the cap.
            paths.append('skills/h3-prompt-writing/references/base-en.txt' if sid != 'h3-ref2va'
                         else 'skills/h3-prompt-writing/references/ref-en.txt')
            for path in paths:
                relative = 'references/minimax-h3/' + path.removeprefix('skills/h3-prompt-writing/')
                files[relative], record = source_file(H, path)
                sources.append({**record, 'local_file': relative, 'license': 'MiniMax H3 Community License Agreement'})
                context.append(relative)
            for path in (VIDEO+'references/generability.md', ASSETS+'references/voice-direction.md'):
                relative = 'references/drama-skills/' + path.removeprefix('skills/')
                files[relative], record = source_file(D, path)
                sources.append({**record, 'local_file': relative, 'license': 'MIT'})
                context.append(relative)
            files['references/licenses/MiniMax-H3-LICENSE.txt'] = license_text
            files['references/licenses/MiniMax-H3-NOTICE.txt'] = 'MiniMax H3 is licensed under the MiniMax H3 Community License Agreement, Copyright © 2026 MiniMax. All Rights Reserved.\nOfficial skill and guide files are unchanged; SKILL.md at this application level is an adaptation.\n'
        files['references/licenses/drama-skills-LICENSE.txt'], _ = source_file(D, 'LICENSE')
        contract = OUTLINE_CONTRACT if stage == 'outline' else STORY_CONTRACT if stage == 'storyboard' else H3_CONTRACT
        if sid == 'h3-ref2va':
            contract += '\n' + REF2VA_CONTRACT
        elif sid in ('h3-i2va', 'h3-fl2va', 'h3-l2va'):
            contract += '\n## 首帧与尾帧对齐\n\n' + KEYFRAME_CONTRACT + '\n'
        refs = '\n'.join('- ['+Path(p).name+']('+p+')' for p in context)
        adapter = APPLICATION + (PROMPT_APPLICATION_LINE if stage == 'prompt' else '')
        body = '---\nname: '+sid+'\ndescription: '+name+'；在短剧工厂 '+stage+' 阶段使用真实上游规则，按工作台 JSON 契约输出。\n---\n\n# '+name+'\n\n## 本预设方法\n\n'+method+'\n\n## 完整上游参考\n\n'+refs+'\n\n'+contract+'\n'+adapter
        files['SKILL.md'] = body
        metadata = {'id': sid, 'name': name, 'stage': stage, 'version': '2.0', 'description': method,
            'source': '已下载并接入完整上游 Skill / 参考文件，工作台契约单独适配', 'sources': sources,
            'license': '上游各自许可；详见 references/licenses', 'context_references': context,
            'variables': (['style','genre','duration','language','music','mode'] if stage == 'prompt'
                          else ['style','genre','duration','language','music']),
            'source_url': 'https://github.com/'+(H if stage=='prompt' else D)}
        if stage == 'prompt':
            metadata['modes'] = [sid.removeprefix('h3-').upper() if sid != 'h3-ref2va' else 'Ref2VA']
            # T2VA and Ref2VA emit no alignment line, so only the keyframe modes carry the flag.
            metadata['official_keyframe_prefix'] = sid in ('h3-i2va', 'h3-fl2va', 'h3-l2va')
        Skills(canonical).save(sid, metadata, files)
        report.append({'id': sid, 'stage': stage, 'sources': len(sources), 'bytes': sum(len(s.encode()) for s in files.values())})
    # Keep every skill the app already ships. Rebuilding only the reviewed profiles used to drop the
    # four image-qwen packages, which left image prompt optimization without any skill to load.
    image_skills = [p.parent.name for p in canonical.glob('image-qwen-*/metadata.json')]
    ids = list(definitions) + [sid for sid in image_skills if sid not in definitions]
    write_json(ROOT / 'resources/builtin_skills.json', {'version': 2, 'ids': ids,
        'skills': report + [{'id': sid, 'stage': 'image_prompt', 'sources': 0, 'bundled': True} for sid in image_skills if sid not in definitions],
        'license_source': license_record})
    backup = ROOT / 'data/skill-backups' / now().replace(':','').replace(' ','_')
    for sid in definitions:
        original = ROOT / 'skills' / sid
        if original.exists():
            shutil.copytree(original, backup / sid)
        shutil.copytree(canonical / sid, original, dirs_exist_ok=True)
    print(json.dumps({'skills':report,'ids':ids,'backup':str(backup)},ensure_ascii=False),flush=True)


if __name__ == '__main__':
    build()

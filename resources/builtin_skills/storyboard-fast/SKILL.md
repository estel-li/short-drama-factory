---
name: storyboard-fast
description: 快节奏与镜头职责；在短剧工厂 storyboard 阶段使用真实上游规则，按工作台 JSON 契约输出。
---

# 快节奏与镜头职责

## 本预设方法

先落实原文，再选择观看位置。每镜明确新增的信息、选择或后果；证据特写、听者反应和空间建立各有职责。仅在新信息、视线、动作状态或空间关系发生变化时切镜，避免同动作重复表演。

## 完整上游参考

- [SKILL.md](references/drama-skills/short-drama-storyboard/SKILL.md)
- [shot-craft.md](references/drama-skills/short-drama-storyboard/references/shot-craft.md)
- [production-shot-grammar.md](references/drama-skills/short-drama-storyboard/references/production-shot-grammar.md)
- [lighting-craft.md](references/drama-skills/short-drama-storyboard/references/lighting-craft.md)

## 分镜产物与字段映射

返回 Story JSON 的 title、style、aspect_ratio、characters、scenes、props、shots。
只返回本批 required_shots 个镜头，顺序从 start_shot 开始；固定和手动镜长使用 shot_durations；对白拟合模式由 AI 根据语境、场景和表演填写 duration，未填写时程序使用 dialogue_pacing 的估算建议。保留实际支持的单镜时长范围。
本批与 previous_shots 衔接，existing_assets 的人物 id 与设定保持一致，prompt 此阶段留空。

- characters：稳定 id、name、visual_description（英文外观）、voice_description。
- scenes / props：稳定 id 和 name；记录光源、空间锚点、道具归属、状态及必要文字。
- shot.scene / scene_id / continuity_group：场景名称、对应场景 id、连续段。
- shot.summary：本镜承担的信息、决定或后果，不只写“人物说话”。
- shot.action：动作开始、可见过程和结果。
- shot.camera：景别、观察侧、运动类型、幅度、速度与停止位置，并解释动机。
- shot.characters / props：只填本镜真实出场的 id；dialogue 保留原文与说话人。

一个工作台镜头对应一段单独生成的视频。按当前时长保留一个主要动作及可读反应，
默认最多两名可见人物，可连续至多三句短对白。中文台词建议每秒约 5.6 个字，可根据语境、场景、情绪、人物语速和动作动态调整。dialogue_pacing 中的语速、起手、句间和收尾均为估算参考，不是固定配额或最低留白；不因字数公式强制拆镜。结合实际表演决定是否加时或按语义拆镜，保留完整原词，生成后试听完整性与节奏。上游特定样本的语速也不作为本项目的硬性限制。角色至少用脸型/年龄、服装主色、配饰等多个外观锚点区分，不能只靠发长。
不要把上游“首尾帧必须成对”的外部生产约束套到 H3 L2VA：本程序支持独立尾帧。
不虚构 IMG/REF 文件或使用源套件的 SHOT 文档 id 代替本程序人物和场景 id。
自检覆盖原文、镜头职责、空间轴线、双手/道具状态、光源关系及前后边界。

## 工作台适配契约（本文件为本地适配层）

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

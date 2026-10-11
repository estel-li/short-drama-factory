---
name: h3-fl2va
description: 官方完整首尾帧 FL2VA；在短剧工厂 prompt 阶段使用真实上游规则，按工作台 JSON 契约输出。
---

# 官方完整首尾帧 FL2VA

## 本预设方法

按官方完整指南编写 FL2VA 提示词。素材定义、对齐指令、声音来源、保留关系和时序服从实际输入。

## 完整上游参考

- [SKILL.md](references/minimax-h3/SKILL.md)
- [base-en.txt](references/minimax-h3/references/base-en.txt)
- [generability.md](references/drama-skills/short-drama-video-prompts/references/generability.md)
- [voice-direction.md](references/drama-skills/short-drama-assets/references/voice-direction.md)

## H3 单镜头产物

只返回 {"prompt":"完整提示词"}，不得返回 Markdown 或生成工具调用。
当前生成片段只使用 [Shot 1]；工作台分镜编号不是片段内的剪辑编号。
实际时长来自 aligned_duration，尾帧对齐指令将该时长格式化为两位小数。
严格使用官方三段/六段格式及对应模式的第一行对齐指令。不要给 [Shot 1] 添加切镜时间戳。
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

## 工作台适配契约（本文件为本地适配层）

这里执行短剧工厂的一个文字生成阶段。上游原文保留为真实参考；采用其创作与制作方法。
上游的 CLI 命令、其他 Agent Skill 路由、Markdown/JSONL 文件写入、MiniMax Hub/Canvas 工具、
人工接受/终审流程和默认数量不在本次文字调用中执行。用户的输入、参数与程序 schema 决定产物。
检查模式的暂停由工作台控制；自动模式不额外提问或暂停。资料缺口采用与原意一致的保守选择。

- 视觉风格：{{style}}；题材：{{genre}}；时长：{{duration}} 秒。
- 对白语言：{{language}}；配乐说明：{{music}}；实际 H3 模式：{{mode}}。
- 不把示例中的人物、对白、画幅、分集数、九宫格、1080p 或 30fps 当成项目事实。
- 不输出讲解、代码围栏、审批请求或脚本，只返回程序指定的 JSON。
- 不改用户已确定的人物、主题、关键动作与结局；改编实现方式时保留戏剧结果。
- 参考素材仅以 bindings 和 reference_labels 中的真实文件与编号为准。

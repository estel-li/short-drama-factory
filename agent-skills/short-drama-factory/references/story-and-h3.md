# 外部 AI 编写分镜与 H3 提示词

以 [agent-storyboard.json](../assets/agent-storyboard.json) 创建草稿；更多真实素材与连续镜头样例见 [模板说明](templates.md)。结构以实例 OpenAPI 的 Story/Shot 为准；这里描述该工厂的 H3 提示词语义，不是所有视频模型的通用语法。外部 AI 是默认创作者，严格 render 只验证已有内容。

## 分镜

Story 必须有 `title` 和 1～150 条 `shots`；支持 `style`、`aspect_ratio`、`characters`、`scenes`、`props`。

角色包含 `id`、`name`、`visual_description`，可加 `voice_description`。角色 ID 使用 ASCII 字母／数字／下划线／连字符，最多 40 字；服装、年龄、外形和声线写得可区分并跨镜保持。

场景和道具通常放 scenes/props，不为了通过角色校验把房间虚构成人物。人物参考图的 character 对应真实角色；场景图留空。误标修复与已验收样板的用法见 [实战制作](production-practice.md)。

镜头关键字段：

| 字段 | 写法 |
| --- | --- |
| `uid` | 全新项目可省略；编辑已有镜头必须保留；在已有项目插镜时给新镜分配未占用 UID |
| `id` | 显示顺序，工厂按数组重新编号，从 1 开始 |
| `scene`, `summary`, `camera`, `action` | 明确场景、单镜目的、机位运动、可完成动作 |
| `duration` | 一般 4～8 秒；高级可到 15 秒但需在目标 GPU 验证 |
| `characters` | 角色 ID 数组，必须在 Story.characters 中定义 |
| `dialogue` | `[{"speaker":"hero","text":"原句台词"}]`；无对白 `[]` |
| `mode` | auto/T2VA/I2VA/FL2VA/L2VA/Ref2VA，建议外部 AI 明确选定 |
| `bindings` | 真实上传素材 ID，见 API 表 |
| `prompt` | 完整 H3 文本，最长 40000 字符 |
| `use_previous_last_frame` | 严格布尔值，默认 false |
| `continuity_group`, `first_frame_reason` | 接续段标识及使用前镜末帧的理由 |

`duration_rule:count` 按 total_seconds/shot_count 分配，再限制到单镜 4～8 秒；因此总时长可能偏离请求。`manual` 使用 manual_durations；`total` 按 total_seconds 与 shot_seconds 分配。用 duration-plan 实际结果，不自己猜。外部 Story 中的 duration 与项目设置同时保持一致，设置镜头数量不会自动裁剪外部 Story。

画外音逐句标记 `dialogue[].narration:true`，同时启用项目 `options.narration:true`；speaker 保留真实说话人，该角色不必出现在本镜可见 characters。普通对白不使用该标记，不能借旁白选项掩盖人物出场错误。

中文台词建议以**每秒约 5.6 个字**作为初步估算，可根据语境、场景、情绪、人物语速、停顿和动作动态调整。`speech_rate` 及起手／句间／收尾参数都是估算参考，不是固定配额或最低留白；不要仅凭字数公式认定台词超时。数字、外语按实际读法考虑，有真实音频时以实际发声区间为准，生成后试听对白完整性与节奏。

H3 为 24fps，帧数对齐到 `17k+5`：`n=ceil(duration*24)`，补至 n%17==5。4 秒请求是 107 帧，即约 4.458333 秒，提示词时间轴用 4.46s。读取 duration-plan 的 frames 最稳妥。

可让程序完成机械格式：`sdf prompt compile --project PID --shot UID --json sections.json`。文件仅含下面定义的三段或六段正文，程序按实际模式和素材生成标题、顺序及关键帧前缀，并核对原句对白与引用标签。结果包含当前 revision；它不写回项目、不生成缺失内容。查看结果后按 UID 保存返回的 prompt。未知／缺少／空段落返回 PROMPT_SECTIONS_INVALID，语义校验不符返回 PROMPT_INVALID。

## T2VA 与关键帧模式

三个段落必须按此顺序出现，视觉正文包含 `[Shot 1]`。每个应用分镜都单独提交 H3，因此第二个应用分镜也用 `[Shot 1]`：

```text
integrated_multimodal_description:
[Shot 1] 0.0-4.46s. A young woman in a yellow coat stands under a blue umbrella. Medium shot, fixed camera, soft evening light. She turns toward the doorway and says <d>[Chinese] 我回来了。</d> Her mouth closes naturally at the end. No captions or watermark.

overall_soundscape:
Gentle rain and a clear young female voice, natural conversational pace.

non_diegetic_music:
N/A
```

该对白必须同时出现在 dialogue 中。所有 `<d>[语言] 原台词</d>` 与 dialogue 的文字、顺序、数量一致；不能漏字、重复、合并或自行增加对白。不把旁白混进人物对白。超时先在语义边界拆镜或合理加时；不能未经用户同意删台词。

关键帧模式在上述段落之前加**第一行**（T 为实际帧对齐秒数、两位小数）：

- I2VA：`For the target video, at 0.00 seconds into the target video, <Picture 1> (from [Shot 1]) is fully referenced.`
- FL2VA：`How the reference pictures align with the target video — Picture 1 (from Shot 1) aligns with the 0.00-second mark of the target video; Picture 2 (from Shot 1) aligns with the T-second mark of the target video.`
- L2VA：`How the reference pictures align with the target video — <Picture 1> (from [Shot 1]) aligns with the T-second mark of the target video.`

只有已绑定的素材才能用 `<Picture N>` 等标签；T2VA 不允许引用图片／音视频标签。无音乐写 N/A；不要凭空设定不存在的统一配乐或独立配音功能。

## 实际末帧接续

同一场景、同一动作连续段才设 `use_previous_last_frame:true` 并解释原因；第一镜、换场、闪回、时间跳跃和需要换构图的硬切不启用。与上一镜的 scene／scene_id（若有）和 continuity_group 保持相容。

工厂强制该镜 I2VA，将**紧邻前一镜已生成视频的实际最后一帧**作为 first_frame。不能用想象画面或新生成角色图代替。写上述 I2VA 第一行，从画中姿态继续动作，避免重新表演前镜动作。不要手工填不存在的自动首帧资产 ID。

前镜改动会影响下游首帧链及缓存；计划会列出扩展范围，依赖锁定镜头需按本次意图解锁。严格 render 在 prompt 缺失或失效时返回具体问题，由当前 AI 补齐后重新计划；不会调用文字提供商代写。旧 stage/render 的自动补齐行为只属于 legacy 接口。

## Ref2VA

此模式使用六段，顺序固定：`subject_definitions`、`summary`、`retention_analysis`、`detailed_description`、`overall_soundscape`、`non_diegetic_music`。`detailed_description` 正文包含 `[Shot 1]`。只定义本镜出场角色，写清参考里的哪些身份／外观需要保留，不能把背景中的其他人也强制带入。

标签由实际绑定决定：图片按 images 顺序编号 `<Picture 1>`；视频按 videos 顺序编号 `<Video 1>`；视频自带且启用的音轨先占 `<Audio N>` 编号，独立音频接在后面。所有绑定素材都要在提示词中说明，禁止引用不存在的编号。

复杂 Ref2VA 仍可由当前 AI 完整编写。需要更细的适配语义时读取 `GET /api/skills/h3-ref2va` 的当前参考；读取文档不调用文字模型，也不等于把外部操作技能安装进内部模板库。不要照搬 T2VA 三段格式。只有用户选择内部创作时才运行允许文字调用的 plan。

## 缓存与手写提示词

新建 Story 自带非空 prompt 时，工厂通常记录 `prompt_manual:true`。不伪造 `prompt_snapshot`、`compiled_bindings` 等缓存字段。只修改种子通常可保留提示词；改角色、动作、参考、时长或剧情时要同步重写 prompt。保存后重新 GET 确认 prompt 没有被失效规则清空。

旧 `stage/prompt` 默认强制重写。外部 AI 路径创建 action=render 的版本化计划，再执行计划；缺失提示词先补好。不要为避免重写而锁住所有镜头：锁定还会限制必要修复和首帧依赖更新。只改字幕时间使用 dialogue_timings，不改 prompt 与真实台词，走 finish。

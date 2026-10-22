# 请求模板与替换规则

这些文件是输入结构和创作示例，不是已经制作完成的用户项目。先复制到当前制作目录，按用户需求改写，再通过 API 保存；不直接修改已安装技能中的模板。

| 文件 | 适用情况 | 提交前需要处理 |
| --- | --- | --- |
| [agent-storyboard.json](../assets/agent-storyboard.json) | 当前 AI 提供完整两镜无对白 T2VA 故事 | 改内容与目标规格；不依赖参考素材 |
| [agent-outline.json](../assets/agent-outline.json) | 用户明确选择工厂内部文字创作 | 核对 provider/model 后，单独计划 action=plan、internal_text=allowed |
| [agent-character-reference.json](../assets/agent-character-reference.json) | 单人物 Ref2VA 身份参考 | 上传真实项目图片，替换 replace_real_image_id；实际图片身份应与角色描述一致 |
| [agent-original-audio.json](../assets/agent-original-audio.json) | h3-audio-drive 原声与人物首帧 | 替换 replace_real_audio_id 与 replace_real_first_frame_id，核对原声长度、起点与实际画面 |
| [agent-continuity.json](../assets/agent-continuity.json) | 同场景连续动作，后一镜用前镜实际末帧 | 不填写虚构 first_frame ID；保留两个不同 UID 与相同连续段 |
| [shot-repair.json](../assets/shot-repair.json) | 修正连续动作镜头的 action/summary/prompt | 这是 changes 对象，仅用于匹配的 I2VA 连续镜头；按用户内容重写，不能套到任意模式 |
| project-storyboard.json／project-outline.json | 旧客户端兼容模板 | 含 start:false；sdf 接受该安全写法，直接 v2 请求请移除 start |

agent-* 创建模板通过 AgentCreate/Story 的结构校验；含 replace_real_* 的模板故意不能直接进入生成。结构合法不等于素材存在、模型就绪或内容已验收。

## 真实素材的两步准备

参考素材属于具体项目，因此先创建草稿，获得 project_id，再上传并绑定：

1. 用素材模板创建草稿；其中占位 ID 只作为待替换内容，不能执行。
2. `sdf asset upload --project PID --file 用户实际图片 --kind image --character hero`；音频使用 --kind audio，不带人物图片标记。
3. 读取最新项目 revision；按 UID 替换 bindings 中占位 ID，同时保留与实际模式匹配的完整 prompt。
4. project validate 和 project plan 均通过后才运行。若没有用户要求的素材，先完成可做的文稿并报告缺项，不能发明文件或 ID。

不要拿独立图片输入的 ID 冒充项目素材 ID。人物图只标人物；场景图不传 --character。参考图不是首帧，source_audio 也不是普通 Audio 标签参考。

## 原声与字幕

原声样例 dialogue=[]，因为模板未听取用户的实际音轨；不编造台词或声线。用户需要字幕或精确台词时，先获得经核实的逐句文本，再同步 dialogue、prompt 和必要的时间信息。原声驱动保留音轨，不承诺逐字口型或自动语音识别验收。

需要沿用前段实际末帧时，audio-drive 仍使用显式 first_frame，不启用 use_previous_last_frame。先完成源镜头，再提取／上传／绑定下一镜；手动派生素材没有自动源镜头追踪，源视频改变后需重新提取并换绑。多镜原声分别绑定对应音频片段，详细限制见 [高级媒体契约](h3-advanced.md)。

## 编辑用法

```powershell
python scripts/sdf.py shot update PROJECT_ID SHOT_UID --json shot-repair.json --expected-revision REVISION
python scripts/sdf.py project plan PROJECT_ID --uids SHOT_UID
```

模板不会修改 UID。连续动作修复可能影响后续首帧链，计划会列出受影响范围。只改字幕时间时提交 dialogue_timings 的 changes 对象并使用 finish，不套用这个画面修复模板。

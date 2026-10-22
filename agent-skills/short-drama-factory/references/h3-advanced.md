# H3 高级媒体输入契约

需要原声、原画面或媒体控制时先读 [工作流选择](workflow-selection.md)。本页维护专用输入的语义，当前可用模式和参数范围以 capabilities 与计划校验为准。

先从 `/api/config` 的 profiles 读取实际方案 ID，再检查 `/api/video/workflows/plan?profile=...` 的资源。使用版本化项目计划执行；资源准备是独立操作，严格 render 不隐式下载或补 prompt。

| profile / workflow | 必需的单镜 bindings | 用途与参数 |
| --- | --- | --- |
| `h3-audio-drive` | `source_audio:音频素材ID` | 原声进入主音画潜空间并锁定音频，成片使用原声；可加 `first_frame` 指定人物，`source_start_seconds` 选择音频起点 |
| `h3-foley` | `source_video:视频素材ID` | T2VA 文字模式，锁定画面生成拟音；成片使用源视频画面而非 VAE 重建图，`source_start_seconds` 选择起点 |
| `h3-keyframe-guide` | `guide_image:图片素材ID` | `guide_position` 为 0.01～0.99 的片段位置，默认 0.5；可同时绑定 `first_frame`、`last_frame` |
| `h3-motion-context` | `source_video:视频素材ID` | 取源片末尾连续画面和声音，`context_frames` 选 5/22/39/56，`audio_context_frames` 默认 18；去掉重复头部并裁到目标帧数 |
| `h3-canny-control` | `source_video:视频素材ID` | FL2VA 主干，文字或关键帧模式；调 `canny_low/high`、`control_strength`、`control_start/end`；需要专用 Fun ControlNet 权重 |

这些绑定字段都是单个真实素材 ID，不是数组，也不是本地路径。素材通过 `/api/projects/{id}/assets` 上传：图片 PNG/JPEG/WebP、视频 MP4/WebM/MOV、音频 WAV/MP3/FLAC/M4A/OGG。取得返回 ID 后，用版本化 shots 更新保存绑定和匹配的完整 prompt；视频上传会规范为 24fps。原声请求样例见 [模板说明](templates.md)。

`source_video`、`source_audio`、`guide_image` 是工作流输入槽，不自动成为 `<Video N>`、`<Audio N>`、`<Picture N>`。只有普通引用槽里的真实绑定才有这些标签。首帧／尾帧继续按原 I2VA/FL2VA 契约编写提示词。源素材、画幅、镜长或参数改变时，旧渲染缓存会失效。

默认首遍为 0.4MP、原生 12 步，不叠加旧 Turbo。可通过 `/api/video/workflows/profiles` 另存参数，保存返回 ID 到项目 `options.profile`。不要启用旧的 `use_previous_last_frame` 与高级媒体方案叠加；多帧接续本身负责上下文。

多帧接续使用 T2VA 或 Ref2VA，不能叠加独立首尾帧：开场由源片末尾确定，末尾还要裁切到目标长度，不能承诺保留另设的尾帧。重要动作与对白从上下文后开始，放在交付窗口内。

“指定原声必须保留”与“多帧音画接续”不能通过给一个项目同时写两个 workflow 实现。若单帧画面接续已满足用户需求，可选择 audio-drive，并绑定 source_audio 与**已有上一段视频的真实最后显示帧**作为 first_frame；use_previous_last_frame 仍为 false，高级工作流不支持这个旧自动标志。不要把多帧动作接续悄悄改成单帧，也不能将新画的参考图说成实际末帧。

已有短视频可用 CPU 完整解码提取最后显示帧，输出到制作工作目录，再通过 asset upload 上传 PNG 并填写返回的真实 ID；例如 FFmpeg 的 reverse 后取一帧会完整解码短片，避免靠猜测时间点截帧。没有实际前片时先完成草稿与已有素材准备，依赖真实末帧的执行必须等待来源，不能捏造该图。原声与连续动作目标都必须保留且现有方案无法同时满足时，明确说明当前工作流限制及需要决定的具体取舍。

手动上传的 first_frame／source_video 目前不记录其源镜头的依赖关系。按顺序分阶段执行：先生成完成源镜头，再提取真实末帧、上传并绑定下一镜，编译其 prompt 后计划执行。之后如果源镜头重新生成，需要人工流程重新提取／上传／换绑下游素材并重新计划；不能声称 affected_uids 会自动发现这类手动派生依赖。自动 previous_last_frame 和捕获角色参考的依赖才由当前计划追踪。

同一 audio-drive profile 下的多个镜头分别绑定各自需要保留的原声素材。例如第二、三镜应各自使用经核实的对应音频片段，不能只绑定第二镜的原声后宣称第三镜也已保留。

音频按 H3 帧对齐时长裁剪，短音轨尾部补静音；视频源片必须有足够帧数，不悄悄重复最后一帧。多帧接续会额外采样上下文，再丢弃重叠头部，不将重复帧算入交付时长。更长目标加上下文不能超过 H3 上限。

“原声保留”不等于精确口型保证；“中段关键帧”是模型引导，不是逐像素拼贴；“轮廓控制”保持结构，不锁定人物身份。最终仍需检查动作、人物、切口、声音和字幕。

# H3 高级媒体工作流（3.3.0）

先从 `/api/config` 的 `profiles` 读取实际方案 ID，再检查 `/api/video/workflows/plan?profile=...`。沿用主 Skill 的下载确认、排队、原任务追踪和验收流程。

| profile / workflow | 必需的单镜 bindings | 用途与参数 |
| --- | --- | --- |
| `h3-audio-drive` | `source_audio:音频素材ID` | 原声进入主音画潜空间并锁定音频，成片使用原声；可加 `first_frame` 指定人物，`source_start_seconds` 选择音频起点 |
| `h3-foley` | `source_video:视频素材ID` | T2VA 文字模式，锁定画面生成拟音；成片使用源视频画面而非 VAE 重建图，`source_start_seconds` 选择起点 |
| `h3-keyframe-guide` | `guide_image:图片素材ID` | `guide_position` 为 0.01～0.99 的片段位置，默认 0.5；可同时绑定 `first_frame`、`last_frame` |
| `h3-motion-context` | `source_video:视频素材ID` | 取源片末尾连续画面和声音，`context_frames` 选 5/22/39/56，`audio_context_frames` 默认 18；去掉重复头部并裁到目标帧数 |
| `h3-canny-control` | `source_video:视频素材ID` | FL2VA 主干，文字或关键帧模式；调 `canny_low/high`、`control_strength`、`control_start/end`；需要专用 Fun ControlNet 权重 |

这些绑定字段都是单个真实素材 ID，不是数组，也不是本地路径。素材仍通过 `/api/projects/{id}/assets` 上传：图片 PNG/JPEG/WebP、视频 MP4/WebM/MOV、音频 WAV/MP3/FLAC/M4A/OGG。上传后读取返回 ID，再通过 `/api/story` 保存完整 Story。视频上传会规范为 24fps。

`source_video`、`source_audio`、`guide_image` 是工作流输入槽，不自动成为 `<Video N>`、`<Audio N>`、`<Picture N>`。只有普通引用槽里的真实绑定才有这些标签。首帧／尾帧继续按原 I2VA/FL2VA 契约编写提示词。源素材、画幅、镜长或参数改变时，旧渲染缓存会失效。

默认首遍为 0.4MP、原生 12 步，不叠加旧 Turbo。可通过 `/api/video/workflows/profiles` 另存参数，保存返回 ID 到项目 `options.profile`。不要启用旧的 `use_previous_last_frame` 与高级媒体方案叠加；多帧接续本身负责上下文。

多帧接续使用 T2VA 或 Ref2VA，不能叠加独立首尾帧：开场由源片末尾确定，末尾还要裁切到目标长度，不能承诺保留另设的尾帧。重要动作与对白从上下文后开始，放在交付窗口内。

音频按 H3 帧对齐时长裁剪，短音轨尾部补静音；视频源片必须有足够帧数，不悄悄重复最后一帧。多帧接续会额外采样上下文，再丢弃重叠头部，不将重复帧算入交付时长。更长目标加上下文不能超过 H3 上限。

“原声保留”不等于精确口型保证；“中段关键帧”是模型引导，不是逐像素拼贴；“轮廓控制”保持结构，不锁定人物身份。最终仍需检查动作、人物、切口、声音和字幕。

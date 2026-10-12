# 第三方来源与许可

本仓库根目录的 MIT 协议适用于短剧工厂自行编写的应用、缓存节点和本地适配代码。下列内容仍使用其原许可，不因打包进入本仓库而改为 MIT。

| 内容 | 来源 | 许可与记录 |
| --- | --- | --- |
| 短剧创作参考 Skill | [zenstory-ai/drama-skills](https://github.com/zenstory-ai/drama-skills) | MIT；各包 `references/licenses/drama-skills-LICENSE.txt` 保留原声明 |
| AI 视频分镜参考 | [aicontentskills/ai-video-storyboard-skill](https://github.com/aicontentskills/ai-video-storyboard-skill) | 上游 SKILL.md 声明 MIT；来源和固定提交记录在分镜包 metadata.json |
| H3 官方提示词与参考文档 | [MiniMax-AI/MiniMax-H3](https://github.com/MiniMax-AI/MiniMax-H3) | MiniMax H3 Community License Agreement；各 H3 包保留完整 LICENSE 与 NOTICE |
| `tools/7zr.exe` | [7-Zip](https://www.7-zip.org/) | 原发行许可见 `tools/7zip-LICENSE.txt`，来源记录在 `tools/7zip-source.json` |
| Python 运行库 | `requirements.lock.txt` 中的项目 | 安装后分别遵循各库发行许可；不把它们重新授权为 MIT |
| Silero VAD CPU 模型 | [snakers4/silero-vad](https://github.com/snakers4/silero-vad) | MIT；固定 6.2.1 提交与 SHA256 见 `manifests/quality.json`；模型首次使用时独立下载 |
| ONNX Runtime / NumPy | [microsoft/onnxruntime](https://github.com/microsoft/onnxruntime)、[numpy/numpy](https://github.com/numpy/numpy) | 分别采用 MIT / BSD-3-Clause，发行包保留其许可 |
| ComfyUI 与模型 | 用户独立安装或通过固定清单下载 | 不随源码仓库提交，分别适用其发行许可和使用条件 |

H3 原声明：

> MiniMax H3 is licensed under the MiniMax H3 Community License Agreement, Copyright © 2026 MiniMax. All Rights Reserved.

完整协议见 [H3 LICENSE](resources/builtin_skills/h3-t2va/references/licenses/MiniMax-H3-LICENSE.txt)。模型及上游材料的地域、分发、使用与商业条款以该完整协议为准。源码仓库不包含模型权重。

`skills/` 和 `resources/builtin_skills/` 保留上游文本与对应来源记录；本地 SKILL.md 的工作台适配段落由本项目维护。每包 `metadata.json` 记录来源仓库、提交、路径、摘要及许可。更新上游材料应同步保留这些记录。

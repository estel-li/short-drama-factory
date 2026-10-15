# 图片工作室开发与验收记录

## 用户目标

在创作空间提供独立图片生成页，调用本地 ComfyUI/Qwen-Image 2.1；识别目标 GPU 显存，自动选择或下载合适模型；自然语言输入，默认勾选提示词优化；短剧生成时可选择自动生成角色／场景等参考图，支持单项重生成、版本保留和分镜引用。

## 实现边界与设计

- 沿用 FastAPI、原生 JavaScript、SQLite 串行队列和现有 Downloader，不引入第二套任务框架。
- 独立图片保存到工作台 data/image-studio；项目素材和映射保存在各项目内。显式选择才改变项目引用；场景图不标为人物。
- 图像请求、优化后的提示词、随机种子、模型来源、ComfyUI prompt_id 与输出均落盘，重启后可以恢复。停止仅影响本任务拥有的生成。
- 默认使用官方 8 步 Turbo；量化和尺寸根据目标 ComfyUI GPU 建议，支持覆盖。模型按固定 Hugging Face revision、大小和 SHA256 下载、校验、断点恢复。
- 现有 ComfyUI 为 2026-09-15 v0.36.0，早于 Qwen-Image 2.1，不具备 TextEncodeQwenImage21。需要支持独立受管图片引擎（独立源码和 Python 环境、复用现有 GPU 运行库），并保留连接已有兼容服务的选项。
- Qwen-Image 2.1 使用非商用研究许可，页面／清单显示官方许可链接和商用授权提示；应用本身仍为 MIT。
- 提示词优化由可配置文字提供商执行，支持 DeepSeek、本地兼容模型和自定义 image_prompt Skill。原文、优化结果均可见、可编辑，优化失败不静默换提示词。
- 图片与 H3 渲染串行使用 GPU；本地文字模型和两个 ComfyUI 服务切换时检查各自队列并释放闲置模型。

## 官方依据

- https://github.com/QwenLM/Qwen-Image-2.1
- https://docs.comfy.org/tutorials/image/qwen/qwen-image-2-1
- https://huggingface.co/Comfy-Org/Qwen-Image-2.1
- https://huggingface.co/Qwen/Qwen-Image-2.1/blob/main/LICENSE
- Comfy-Org 模型快照：a8342359c61979b06a8dafb1a47991fe1f30e994。
- Turbo 官方模板使用 8 段 sigma、Euler、CFG 1；不把普通 KSampler 的 8 步当作相同调度。

## 已完成的验证（2026-10-15）

- 显存建议覆盖本地、未知及远程 GPU；测试官方 Turbo 调度。复用现有 Downloader 的摘要验证、取消与恢复测试。
- 接口覆盖默认优化、关闭优化、人工优化结果、原文及 Skill 快照保存、PNG 下载、缺文件提示、恢复和定向停止。
- 项目测试覆盖手工角色素材保护、空镜无人物身份、历史采用、迁移后采用、锁定预检以及采用中断后的重复素材保护。
- 全量后端 109 项、前端 10 项通过；补充 PNG 下载／缺文件用例后，图片、外部 AI 客户端及便携相关 29 项通过。总计后端 110 项。
- 真实 RTX 5060 Ti 16GB：Turbo INT8/W4A8 生成 448×576 独立图片，另由 DeepSeek 优化后生成 896×1184 角色图、1376×768 场景图；角色镜头绑定两张、空镜只绑定场景，并完成 H3 提示词编译。
- 浏览器验证桌面、390px 窄屏、图片结果展示及轮询时草稿保留；无页面 JavaScript 错误和横向溢出。
- 新增用户指南、模型许可声明、外部 AI 图片接口与客户端 PNG 下载支持；资源清单含 4 个图片 Skill，便携构建包含这些源码和资源。

## 实机验证范围与后续

- 已验证独立环境复用现有 GPU Python。没有任何推理环境时的官方便携运行时路径已有实现和离线计划测试，尚未在全新 Windows 机器完整安装验证。
- 其他显卡、标准 INT8 和 BF16 方案尚未实机测速；不承诺所有硬件都能使用建议尺寸。
- 本次提交源码；新的便携安装包与 GitHub Release 需另行构建发布。现有本机 8765 实例仍为 2.4.1，源码预览在独立端口。

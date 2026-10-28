# 视频工作流与多模型生图

本页列出 H3 的加速与放大方案；3.2.0 新增 LightX2V、PDD 与神经放大，之后新增 Turbo v4 快速音画。模型文件仍保存在用户选择的目录，应用通过 ComfyUI HTTP 接口串行生成，不在工作台进程中加载推理框架。

## 视频方案

在项目设置的“视频工作流 / 质量”选择方案，再点击“准备所选工作流”。已有模型会先复用；缺文件时显示大小并请求确认，后台展示进度，支持暂停和续传。节点安装在应用自己的运行目录，原始 ComfyUI 中的其他插件不会被自动启用。

| 方案 | 用途 | 默认配置 |
| --- | --- | --- |
| Turbo v4 快速音画 | 用 Larryvrh Turbo LoRA 在 6–8 步生成带同步音画的镜头，适合快速试镜和批量草稿 | 0.4MP、8 步、v4-600 EMA LoRA、专用采样器、simple 调度 |
| LightX2V 8步 | 比原四步草稿更完整的运动采样 | 0.4MP、8 步、专用 768p LoRA |
| PDD Acc 8步 | 音画加速，支持基础和参考模型 | 0.4MP、8 步、Euler、训练 sigma 网格、12/3 偏移 |
| PDD 神经放大 | 先生成再放大，轻量恢复细节 | 首遍 0.4MP / 8 步、3D 神经放大 1.25 倍、一个训练块精修 |

“自定义参数 / 另存方案”可保存独立的分辨率、步数与 LoRA 强度；PDD 还支持头强度，神经放大支持倍数和是否精修。自定义方案有独立 ID，项目保存后使用该组合。Turbo v4 快速方案可选 6 或 8 步；LightX2V 专用方案保持 8 步；PDD 基础方案可选 4、6、8 步；神经放大首遍保持 8 步。

Turbo v4 使用专用 LoRA 采样器，不叠加旧 Turbo；接受文字、首帧、尾帧和首尾帧，多图、视频和音频参考使用 PDD 或原生方案。上游说明指出 4 步在大幅快速动作下可能出现拖影，6–8 步明显更稳，因此本方案默认 8 步并限制为 6/8 步。显存不足时可通过 `/api/video/workflows/profiles` 另存 `low_vram:true` 的方案，节点会合并 LoRA 以降低峰值显存，量化底模上画质会略软。LightX2V 此方案接受文字、首帧、尾帧和首尾帧；多图、视频和音频参考使用 PDD 或原生方案。PDD 的两个主干必须分别配对 FL2VA / Ref2VA 头，程序不会把它们当成普通 Turbo LoRA 混用。放大只改变空间尺寸，不补帧、不变速；原始音频保留。

上游固定来源及摘要见 `manifests/video-workflows.json`：

- [MiniMax-H3 Turbo LoRA](https://huggingface.co/larryvrh/MiniMax-H3-Turbo-Lora) 与 [H3 Turbo 专用节点](https://github.com/Larryvrh/ComfyUI-MiniMax-H3-Turbo)。
- [LightX2V](https://github.com/ModelTC/LightX2V) 与 [H3 Turbo 权重](https://huggingface.co/lightx2v/Minimax-h3-Turbo)。
- [PDD Acc 节点及官方 Acc 格式适配](https://github.com/Jalen-Brunson/ComfyUI-MiniMax-H3-PDD-Acc)。
- [H3 神经潜空间放大节点](https://github.com/LBH-123-AI/Comfyui_Minimax_h3_latent_Upscaler) 与 [放大权重](https://huggingface.co/LBH-123-AI/Minimax_h3_latent_Upscaler)。

首次核对已有模型时需要顺序读取文件；校验收据放在应用数据目录，可复用只读模型位置。自行管理或远程 ComfyUI 的插件加载和重启由服务所有者负责。应用自动重启前会核对服务归属和队列空闲状态。

## 生图模型

图片页面顶部选择“生图模型”，切换时带入对应推荐参数。独立图片引擎与原 H3 视频引擎共用 GPU 时，程序先检查队列并卸载空闲模型。

| 模型 | 侧重点 | 默认步数 / CFG | 文件形式 |
| --- | --- | --- | --- |
| Qwen-Image 2.1 | 多图语义参考、中文编辑、透明通道 | Turbo 8 / 1；标准 40 / 1 | 分体模型 |
| SDXL 1.0 | 通用构图与写实 | 28 / 7 | 整合模型 |
| Animagine XL 4.0 | 动漫角色与插画 | 28 / 6 | 整合模型 |
| DreamShaper 8 | 轻量插画、快速草图 | 24 / 7 | 整合模型 |
| DreamShaper XL Turbo | 快速风格图 | 6 / 2 | 整合模型 |
| FLUX.1 Schnell FP8 | 构图与提示词遵循 | 4 / 1 | 整合模型，包含编码器与 VAE |
| Z-Image Turbo INT8 | 中文描述与写实 | 9 / 1 | 分体模型、专用编码器与 VAE |

Qwen 可用最多十张语义参考图；其余模型支持一张原图的 VAE 重绘，使用“编辑原图”和重绘强度控制保留程度。原生透明通道仅对 Qwen 开放。模型之间的图像条件方式不同，不能通过更换文件名来共用同一套编码节点。

角色、场景和道具的自动参考图也能选择生图模型。任务保存模型方案、实际采样参数、参考图快照和工作流，载入旧任务不会随全局默认模型改变。

文件的固定版本、大小、SHA256 和原许可见 `manifests/image-models.json`；Qwen 清单单独保留。模型许可独立于应用 MIT，使用限制以模型原页面为准。

## 本机测试

实测与筛选过程见 [验收记录](workflow-expansion.md)。测试硬件为 RTX 5060 Ti 16GB、32GB 系统内存、Thunderbolt 显卡坞，主要使用 INT8 / W4A8 及分阶段卸载。每个测试保存独立的 prompt_id、请求、图和输出；具体耗时会受分辨率、缓存、磁盘和显卡连接带宽影响。

Turbo v4 快速方案在该硬件上用 8 步、0.4MP、4 秒 T2VA 单镜实测：832×480、107 帧、24fps、同步立体声；编码约 23.7 秒、采样约 76.1 秒、解码约 25.1 秒，含单镜合片总计约 139 秒。静态场景画面连续，未观察到明显拖影；实际耗时随分辨率、帧数、显存与冷加载变化。

最初的纯插值加两步精修候选出现明显重影，未作为推荐实现保留；最终采用已下载的神经放大权重和较轻的精修。结构校验和绿灯测试不能代替画面验收，建议正式短剧先做一个镜头，确认角色、动作和对白后再批量生成。

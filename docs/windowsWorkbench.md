# Windows 新工作台测试

本仓库包含两部分：根目录是 Python H3 生产后端；`workbench/` 是新画布工作台，包含预装插件和文本／视频／图片模型配置。工作台是测试版本，已知问题列在文末。

## 1. 在新目录拉取主线

在 PowerShell 中执行，目标目录须不存在：

```powershell
git clone --branch main https://github.com/estel-li/short-drama-factory.git short-drama-factory-test
cd short-drama-factory-test
git log -1 --oneline
```

使用新目录可保留原有安装与项目。源码不包含模型、私人配置、API Key、运行环境和之前生成的媒体。

## 2. 启动 Python 后端

准备 Python 3.13，然后在仓库根目录执行：

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock.txt
.\.venv\Scripts\python.exe .\launcher\start.py --serve-only --port 8770
```

没有 `py` 命令时，可用已有 Python 3.13 的完整路径替换 `py -3.13`。保留此终端运行。这里使用 `8770`，以便与旧实例常用的 `8765` 区分。

在 `http://127.0.0.1:8770` 配置已有 ComfyUI 的安装目录、Python 路径和模型搜索目录。复用已安装的模型即可；需要生成时再启动相应 ComfyUI 服务。

## 3. 构建并启动画布工作台

安装 [Bun](https://bun.sh/docs/installation)。本次开发验证使用 Bun 1.4.3；可先执行 `bun --version` 核对。打开第二个 PowerShell 终端，在刚克隆的仓库根目录执行：

```powershell
cd .\workbench
bun install --frozen-lockfile
bun run build:server
```

构建成功后，在同一个终端执行：

```powershell
$env:TOONFLOW_SERVER_HOST = '127.0.0.1'
$env:TOONFLOW_SERVER_PORT = '3001'
$env:SDF_BASE_URL = 'http://127.0.0.1:8770'
$env:SDF_APPLICATION_ROOT = (Resolve-Path ..).Path
$env:SDF_COMFY_URL = 'http://127.0.0.1:8188'
bun run start:server
```

浏览器打开 `http://127.0.0.1:3001`。以上环境变量沿用兼容名称；设置页保存的连接优先于环境变量。工作台配置与画布存放在 `workbench/data/`，不会读取另一安装目录的配置。

## 4. 配置模型

### ComfyUI 环境与启动

在新版工作台打开 **设置 → 模型配置 → ComfyUI 环境**：

- **使用已有环境**：选择 ComfyUI 文件夹或便携包根目录，点击“识别环境”。自动寻找 `ComfyUI/main.py` 及便携 Python／虚拟环境；未找到 Python 时可手动填写完整路径。核对本地地址后点击“保存并启动”。
- **自动下载安装**：选择环境安装目录、模型保存目录，可填写已有模型搜索目录。点击“预览安装清单”，检查下载量、复用文件和可用磁盘空间，再点击“确认下载并安装”。当前复用 H3 安装清单，包含 ComfyUI、运行依赖及 H3 模型；支持 Windows x64 + NVIDIA。
- **状态与进度**：面板显示引擎连接状态、启动／安装任务结果和当前文件下载进度。安装可暂停，再次预览后继续；关闭设置页不会取消后台任务。
- **连接同步**：勾选“同步到图片、视频及工作流的 ComfyUI 地址”会同步三处连接地址，保留各自的工作流和模型参数。H3 工厂连接可在面板底部展开设置。
- **搜索本地模型**：输入绝对目录或盘符（如 `E:\`，也接受 `E:`），每行一个；支持停止搜索、按路径／文件名筛选和分页选择。扫描只读取文件信息，不加载权重。候选包含 safetensors、ckpt、gguf、pt、pth、bin，类型按目录推测，未知类型需手动确认。

选中模型后点击“接入所选模型目录”。工作台在**已保存的本机 ComfyUI** 的 `models/<类别>/importedModels/` 下创建目录链接，Windows 使用跨本地盘符的 junction，不复制、移动或覆盖模型；同目录中的文件也会被 ComfyUI 读取。来源目录需保持原位。接入后去图片／视频模型设置重新读取列表；局域网其他电脑上的 ComfyUI 不会因此获得本机文件。

搜索跳过目录链接、无权限项、Windows 系统目录和常见开发依赖目录；单次最多 5 分钟、100 万文件条目、1 万候选，达到上限会明确显示部分结果。搜索记录在工作台服务重启后失效，已接入的目录链接保留。

启动只准备引擎，不提交生成任务，也不隐式下载模型。现有目录以工厂原有启动参数运行；输入、输出、缓存和数据库放在当前工厂的 `data/comfy-runtime/`。安装或启动请求会唤醒仅 API 模式的任务执行器，不恢复之前未授权的排队任务。

### 模型供应商

- **文本模型**：填写 DeepSeek API Key，读取并保存实际模型列表。
- **图片模型**：选择在线图片接口，或配置 ComfyUI 地址。在 ComfyUI 的“编辑模型”窗口上方点击“读取可用工作流”，选择内置方案和匹配文件，点击“应用到当前配置”，可先测试再保存。SD / SDXL、Flux Schnell、Qwen Image 2.1 Turbo 已提供固定方案；其他模型仍可导入自定义 API 工作流。
- **视频模型**：选择 Seedance 等在线接口，或配置本机／局域网 ComfyUI 视频工作流。ComfyUI 可使用 `http://192.168.1.4:8188` 这样的局域网地址，目标服务需监听对应网卡并允许访问。
- **H3 工厂**：在“视频模型 → H3 工厂与独立工作流连接”中核对后端地址 `http://127.0.0.1:8770`，实际工厂目录填写本次克隆的仓库根目录，不是 `workbench` 子目录，也不是旧安装目录。

ComfyUI 自定义工作流的变量绑定方式见 [工作台说明](../workbench/README.md#媒体连接约定)。使用在线接口的生成按相应供应商规则计费。

### 内置生图／生视频工作流

预设由服务端生成 API 图，兼容已有 ComfyUI 适配器，不覆盖用户的供应商代码。每次应用前重新核对节点及模型文件，不下载模型、不自动升级 ComfyUI，也不提交生成任务。点击窗口底部“保存”后生效。SD、Flux 文生图和视频方案设置默认 `comfyImage`／`comfyVideo`；Qwen 文生图、图生图／单图编辑方案以独立模型 ID 和工作流保存，同时出现在画布下拉列表，选择不同方案互不替换。

| 方案 | 固定参数与输入 | 官方来源 |
| --- | --- | --- |
| SD / SDXL 文生图 | 20 步、CFG 7、Euler；标准 Checkpoint，不用于 Turbo／Lightning | [ComfyUI SDXL 示例](https://comfyanonymous.github.io/ComfyUI_examples/sdxl/) |
| FLUX.1 Schnell FP8 文生图 | 4 步、CFG 1、Euler/simple、SD3 latent；使用包含编码器和 VAE 的 FP8 Checkpoint | [ComfyUI Flux 示例](https://comfyanonymous.github.io/ComfyUI_examples/flux/) |
| SD / SDXL 图生图 | 单张原图经缩放、VAE 编码后采样，20 步、CFG 7；重绘强度默认 0.55 | [ComfyUI 图生图示例](https://comfyanonymous.github.io/ComfyUI_examples/img2img/) |
| FLUX.1 Schnell FP8 图生图 | 使用已有 Schnell FP8 Checkpoint，单张原图经 VAE 编码后采样，4 步、CFG 1；重绘强度默认 0.55 | [ComfyUI 图生图原理](https://comfyanonymous.github.io/ComfyUI_examples/img2img/)及 [Flux 参数](https://comfyanonymous.github.io/ComfyUI_examples/flux/) |
| Qwen Image 2.1 Turbo 文生图／单图编辑 | 2 个方案；完整 Turbo 权重、官方 8 步 sigma、Euler、CFG 1；编辑接收 `image0` | [Comfy-Org Qwen 2.1](https://huggingface.co/Comfy-Org/Qwen-Image-2.1) |
| MiniMax H3 文生视频／首帧图生视频 | 各有 20 步标准、4 步 LightX2V LoRA 两个方案，共 4 个；24 fps、约 0.4MP，时长按 17k+5 帧向上对齐；首帧接收 `firstFrame` | [官方文生视频模板](https://github.com/Comfy-Org/workflow_templates/blob/main/templates/video_minimax_h3_t2v.json)、[图生视频模板](https://github.com/Comfy-Org/workflow_templates/blob/main/templates/video_minimax_h3_i2v.json) |

H3 预设保留原生音轨，并用分块 VAE 解码降低显存压力；0.4MP 是本工作台固定的低显存尺寸，画布比例仍生效，不代表原生 1080p。4 步方案只能选择 FL2V 的 4 步 LoRA。Qwen 使用独立扩散权重、Qwen3-VL 8B 编码器和 Qwen 2.1 VAE，不可替换为 H3 的 32B 编码器；当前引擎没有 `TextEncodeQwenImage21` 时，界面会显示缺少节点并禁用应用。

Qwen 文生图用法：在图片模型设置读取可用工作流，选择“Qwen Image 2.1 Turbo · 文生图”，匹配 Turbo 扩散模型、Qwen3-VL 编码器和 VAE，点击“加入画布模型列表”并保存。画布图片生成节点选择同名模型、填写提示词即可，无需连接原图；该文生图方案不接受参考图片。模型 ID 为 `comfyQwenTurbo`，保留已有 Flux 默认文生图和图生图配置。

Qwen 图生图用法：单独选择“Qwen Image 2.1 Turbo · 图生图（单图编辑）”，点击“加入画布模型列表”并保存；仅添加文生图不会同时启用图生图。图生图模型 ID 为 `comfyQwenTurboEdit`，复用同一套 Turbo 权重。将一张图片连接到图片生成节点，选择该模型并填写修改要求即可。当前内置方案只接收一张原图，按原图比例和 1024 编码分辨率编辑；不提供 SD / Flux 的重绘强度参数，也不支持蒙版输入。

本机 2026-11-06 联调已将主服务切换到现有的 ComfyUI 0.40.0 源码，使用当前应用 `runtime/comfyPython/` 下的独立 Python 环境补齐依赖，并通过 `data/sharedModelPaths.yaml` 复用原有模型目录。服务地址仍为 `http://127.0.0.1:8188`。为保留旧版本数据库，环境配置 `comfy_database_name` 设为 `comfyQwen21`，新数据库写入 `data/comfy-runtime/user/comfyQwen21.db`；旧 `comfyui.db` 保持原样。此配置仅接受字母、数字、下划线和短横线，未配置时沿用 `comfyui`。这些是当前实例的环境配置，不是应用预设时自动安装或升级引擎。

图生图用法：在图片模型设置选择“SD / SDXL · 图生图”或“FLUX.1 Schnell FP8 · 图生图”，选择匹配的 Checkpoint，点击“加入画布模型列表”并保存。画布中把一个图片节点连接到图片生成节点，直接从模型下拉选择对应的图生图方案。图片生成设置中可调整 **重绘强度 0.05–1**；数值越低越保留原图，越高变化越大。原图会按节点尺寸和比例居中裁切缩放；想保留构图时选择与原图一致的比例。

这两套是整图重绘流程，不是蒙版局部编辑，也不保证像 Qwen 编辑模型一样精确执行对象修改。未接图、接入多张图片或重绘强度超出范围时，在提交 GPU 任务前明确报错。再次加入同名方案可更新其 Checkpoint；默认文生图及视频设置保留。

## 当前验证边界与已知问题

2026-11-06 在 Windows 本机完成页面手动联调：目录搜索、E 盘整盘搜索、停止搜索、目录链接接入和 ComfyUI 列表重新读取；Flux Schnell 1024×1024 生图约 15 秒；H3 4 步文生视频约 84 秒；把 Flux 图片作为首帧的 H3 图生视频约 86 秒。两段 MP4 均为 107 帧、24 fps、约 4.46 秒，包含 H.264 视频和 AAC 音轨，完整音视频解码通过。图片和视频工作流保存后回读一致。

同日新增图生图验证：在独立的“图生图联调”画布，通过图片节点连线传入原图，分别成功生成 Flux Schnell 1024×1024（重绘强度 0.65）和 DreamShaper 8 / SD 512×512（重绘强度 0.55）。核对 ComfyUI 提交记录确认使用上传的原图、VAEEncode 与对应 denoise；两张 PNG 均完整解码。文生图与两套图生图在同一下拉列表并存，原文生图及视频工作流保留。无参考图、非法重绘强度均在提交生成前报错。SDXL 使用同一图生图结构，本次未另行逐模型推理验证。

同日新增 Qwen 验证：在独立的“Qwen生图联调”画布选择 Qwen Image 2.1 Turbo，使用已有 INT8 Turbo 权重、Qwen3-VL 8B W4A8 编码器及 BF16 VAE，成功生成 1024×1024 PNG，ComfyUI 执行耗时约 31 秒，图片完整解码通过。切换引擎后再次通过工作台供应商接口生成 H3 4 步视频，约 87 秒完成；输出为 107 帧、24 fps、约 4.46 秒，H.264 视频与 AAC 音轨完整解码通过。

Qwen 图生图已在“图生图联调”画布实际验证：通过图片连线传入雨窗茶杯原图，将窗外改为雪景，成功返回 1024×1024 PNG，约 18 秒完成。核对提交记录确认 `LoadImage` 接入 `TextEncodeQwenImage21` 的 `images.image_1`，采样使用该编码器输出的 latent；输出完整解码通过。画布下拉可直接选择 Qwen 图生图，并与 Qwen 文生图、Flux 和 SD 图生图同时保留。

一句话加参考图的视频流程已完成页面联调：Agent 读取图片、创建分镜、通过 `importReference` 导入真实素材、展开镜头并绑定首帧、计划与生成、取回画布视频。沙滩起身走向海边示例使用本地原生 12 步方案，输出 480×832、24 fps、192 帧、8 秒 MP4，H.264 / AAC 完整解码通过，抽帧确认起身和走向海边动作。补充了创建项目与镜头修改的具体参数 schema、手动时长校验、`getWorkflowPlan` 就绪检查及素材变更后的提示词失效处理说明。空分镜、非法手动时长和工作区外路径均被拒绝；重复导入同一请求键返回原素材 ID。旧节点 ID 失效时提示重新查询当前画布。已有安装需更新 H3 节点插件与 `factoryWorkflow` 技能，并刷新页面、新建对话以加载新定义；当前本机实例已更新。

前后端构建通过。当前仓库前后端类型检查均因已有的 `.hutch/devkit/api/config/ElectrobunConfig` 缺失而未能全量通过；本次检查未报告其他类型错误。H3 20 步标准方案未逐个推理验证，不能把 4 步测试结果视为所有预设已实测。

1. **ComfyUI 图片／视频配置隔离尚不完整**：视频工作流使用 `{{model}}` 时，会优先读取图片 Checkpoint。视频工作流暂时直接填写正确的模型文件名，不使用此变量。
2. **Seedance 失败终态处理尚不完整**：带 `error` 的失败响应可能被显示为可恢复中断。遇到此情况先在供应商侧核对原任务，不反复新建生成任务。
3. **内置适配器和插件尚无完整升级迁移**：已有同名安装文件会保留，新源码不会自动覆盖。全新目录安装会得到当前随包版本；已有安装升级需另行处理并保留用户配置。

建议依次验证：工作台启动 → 读取 ComfyUI 大模型 → 图片生成 → 换装参考图输入 → 视频生成 → 中断后续查 → 结果落盘。报告问题时附上 `git log -1 --oneline`、Bun 版本、节点名称和已脱敏错误信息，不提供 API Key。

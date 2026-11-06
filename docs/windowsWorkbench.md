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

- **文本模型**：填写 DeepSeek API Key，读取并保存实际模型列表。
- **图片模型**：选择在线图片接口，或配置 ComfyUI 地址。SD / SDXL 兼容 Checkpoint 可直接选择；换装、图生图、Flux、Qwen 等需要对应的 API 格式工作流。
- **视频模型**：选择 Seedance 等在线接口，或配置本机／局域网 ComfyUI 视频工作流。ComfyUI 可使用 `http://192.168.1.4:8188` 这样的局域网地址，目标服务需监听对应网卡并允许访问。
- **H3 工厂**：在“视频模型 → H3 工厂与独立工作流连接”中核对后端地址 `http://127.0.0.1:8770`，实际工厂目录填写本次克隆的仓库根目录，不是 `workbench` 子目录，也不是旧安装目录。

ComfyUI 自定义工作流的变量绑定方式见 [工作台说明](../workbench/README.md#媒体连接约定)。使用在线接口的生成按相应供应商规则计费。

## 当前验证边界与已知问题

配置保存、图片与视频连接分别保存、三类节点模型选择、类型检查和前后端构建已通过。此前 H3 专用工厂节点完成过 Windows 三镜头生成、续跑和成片验证；新增通用媒体适配器尚未完成真实生成验证，不能视为已经通过 Windows 全流程测试。

1. **ComfyUI 图片／视频配置隔离尚不完整**：视频工作流使用 `{{model}}` 时，会优先读取图片 Checkpoint。视频工作流暂时直接填写正确的模型文件名，不使用此变量。
2. **Seedance 失败终态处理尚不完整**：带 `error` 的失败响应可能被显示为可恢复中断。遇到此情况先在供应商侧核对原任务，不反复新建生成任务。
3. **内置适配器和插件尚无完整升级迁移**：已有同名安装文件会保留，新源码不会自动覆盖。全新目录安装会得到当前随包版本；已有安装升级需另行处理并保留用户配置。

建议依次验证：工作台启动 → 读取 ComfyUI 大模型 → 图片生成 → 换装参考图输入 → 视频生成 → 中断后续查 → 结果落盘。报告问题时附上 `git log -1 --oneline`、Bun 版本、节点名称和已脱敏错误信息，不提供 API Key。

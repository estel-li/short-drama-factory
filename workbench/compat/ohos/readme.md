# Toonflow OHOS

独立鸿蒙兼容构建，复用 `apps/mobile/src/server.ts`、完整网页与内置插件。ArkTS UIAbility/ArkWeb 加载应用内服务在随机 localhost 端口提供的页面；服务由 C++ 桥嵌入 Node 共享库运行。构建时只转换 OHOS 所需的 Bun 接口，其他平台沿用 Bun。

当前运行时为 [electerm/ohos-node-shared Node 24.2.0](https://github.com/electerm/ohos-node-shared/releases/tag/ohos-node-shared-v24.2.0) 的 **OHOS ARM64** 共享库，原始 SHA256 为 `3019bf5f9a279d98a87606fc13c53b0e797b6a50cf174f8a1243d880c71151a1`。构建仅将 ELF 的 SONAME 规范为 HAP 原生库名称 `libnode.so`，使用同版本官方头文件，并随包分发 Node 许可。

第三方 Bun 已有 OHOS 移植，例如 [springmin/bun](https://github.com/springmin/bun) 和 [ohos-npm-ports/bun](https://github.com/ohos-npm-ports/ohos-npm-ports/tree/main/ports/bun/1.4.2)。2026-10-15 在 API 17 云手机的普通 HAP 内实测，沙箱文件及安装目录中的 Bun 可执行文件均被拒绝执行；终端环境支持不能证明 HAP 内可启动。Node 共享库路线已在该设备启动本地服务并显示工作区画布，具体功能验证范围见下文。

## 构建

当前构建环境为 Windows、仓库已安装的 Bun 依赖及 DevEco Studio 26。生成工程的最低 API 为 12、目标 API 为 26，设备类型为 phone/tablet。版本沿用根目录 `electrobun.config.ts`，也可设置 `appVersion=X.Y.Z`。

在仓库根目录执行：

```powershell
$env:DEVECO_HOME = 'C:\Program Files\Huawei\DevEco Studio'
bun run --cwd compat/ohos setup
bun run --cwd compat/ohos typecheck
bun run --cwd compat/ohos build
```

`setup` 下载并校验 Node 共享库与头文件，然后用 DevEco 自带 OHPM 链接项目自己的 NAPI 类型声明。`build` 复用 `build:server` 构建前后端及插件，再为 OHOS 生成 Node 服务包、标准 Hvigor 工程、原生桥和 ArkTS，打包 HAP。SDK 强制要求的 `build-profile.json5`、`CMakeLists.txt` 等文件只生成到 `build/ohos/project`。构建不会隐式运行 `setup`。

默认产物为 `build/ohos/toonflow-2.0.0-ohos-arm64-v8a-unsigned.hap`，文件名随项目版本变化。程序资源在 `build/ohos/payload`；可用 DevEco Studio 打开 `build/ohos/project` 调试和配置签名。

可选环境变量：

| 变量 | 用途 |
| --- | --- |
| `DEVECO_HOME` | DevEco Studio 安装目录，默认如上 |
| `DEVECO_SDK_HOME` | SDK 根目录，默认 `DEVECO_HOME/sdk` |
| `ohosNodePath` | OHOS Node 共享库绝对路径；覆盖默认运行时 |
| `ohosNodeHeaders` | 与共享库同版本的 Node `include/node` 目录 |
| `ohosArch` | 默认 `arm64-v8a`；只有另备兼容 OHOS 的 x86_64 共享库才能选 `x86_64` |
| `ohosSigningConfig` | 一个完整 DevEco `signingConfigs` 配置对象的 JSON 文件路径 |

构建会校验 ELF 架构和共享库类型，拒绝带程序解释器的命令行可执行文件。Linux、Android 与 OHOS 原生库不可互换；x86_64 模拟器不能运行 ARM64 库。

## 签名和安装

真机安装需要覆盖目标设备的 HarmonyOS 签名证书与 profile。可先在 DevEco 打开生成工程，连接设备并使用 IDE 的签名配置。命令行构建时，将 DevEco `build-profile.json5` 中 `app.signingConfigs` 数组里的对应对象单独保存为 JSON，使用绝对证书/profile/keystore 路径；文件放在仓库忽略的 `build/ohos/signingConfig.json`，不要提交证书、密码或 profile。

```powershell
$env:ohosSigningConfig = (Resolve-Path build/ohos/signingConfig.json).Path
bun run --cwd compat/ohos build

$hdc = Join-Path $env:DEVECO_HOME 'sdk\default\openharmony\toolchains\hdc.exe'
& $hdc tconn 127.0.0.1:5557
& $hdc list targets
& $hdc -t 127.0.0.1:5557 shell param get const.product.cpu.abilist
& $hdc -t 127.0.0.1:5557 install -r (Resolve-Path build/ohos/toonflow-2.0.0-ohos-arm64-v8a-signed.hap).Path
& $hdc -t 127.0.0.1:5557 shell aa start -b com.toonflow.mobile -a entryAbility
& $hdc -t 127.0.0.1:5557 shell hilog -T ToonflowRuntime
```

设备地址、版本文件名按实际情况替换。Windows HDC 的本地文件参数使用 `Resolve-Path` 返回的绝对反斜杠路径。配置签名后输出 `-signed.hap`；未配置时仍可编译，但 `-unsigned.hap` 不代表可安装包。重新执行命令行 `build` 会重新生成工程配置，IDE 中的签名应按上述方式保存并传入。

## 行为与验证边界

- 程序更新使用 `filesDir/appNext → app` 与 `appPrevious` 回滚，数据单独存于 `filesDir/data`。覆盖安装替换程序资源，不覆盖设置和工作区；卸载会清除应用数据。
- 沿用移动端随机端口、一次启动令牌及 HttpOnly Cookie 鉴权。原生桥仅接受本机同源 `toonflow://save` 和重启请求，外部网页在系统浏览器打开。
- 每个本机页面的脚本执行前按需补齐 `Map.groupBy`、`URL.canParse`、`Promise.withResolvers`、`AbortSignal.any`，只注入当前随机端口的本机来源。首次进入网页仍执行原有浏览器能力预检；其余 ArkWeb 能力不满足要求时显示错误。OHOS 不含 Android GeckoView。
- 保留横屏、全屏、文件上传和系统文件保存；设备互联可手输配对码。相机授权和拍摄扫码尚未接入。
- 本地服务随 Ability 生命周期运行，没有后台长任务保证。`TOONFLOW_PLATFORM=ohos` 用于区分鸿蒙与 Linux 功能支持；外部 CLI、FFmpeg 和 MCP stdio 仍受手机应用执行权限限制。
- Node 使用 `--jitless`，通过已安装的 `node-fetch` 负责 HTTP 传输、Undici 提供 Web API，避开 Node 24.2 内置的 WASM HTTP 解析器。图片处理接入鸿蒙 ImageKit，支持尺寸读取、`fill` 缩放及 PNG/JPEG/WebP 编码；供应商脚本和其他 Bun 接口仍需分别验证，不能视为完整 Bun 兼容。
- 2026-10-15 已在 OpenHarmony 5.0.5.316、API 17、ARM64 云手机验证签名安装、本地服务启动、快速开始/首页/工作区画布渲染与手机工作目录创建。现有供应商调试入口也已走通 PNG/JPEG/WebP 尺寸读取、300×300 缩放与编码；使用空 API Key 在发送供应商请求前退出，未发起付费生成。输出图片视觉效果、系统文件上传/导出以及完整生成流程尚未验收。
- 该设备已验证文件独占创建、覆盖保存、读取、改名和两种同名冲突保护。通过界面创建的图片生成节点已保存到画布；覆盖安装最终 HAP 并冷启动后，画布与两份验证文件的 SHA256 均保持一致，项目列表也已恢复。

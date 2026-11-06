# 架构与清理边界

## 唯一网页入口

`workbench/apps/web` 是 Vue 画布，`workbench/apps/server` 是 Bun 服务。根目录启动器负责当前实例的生产 API 与工作台服务，并核对应用目录、数据目录和端口。Python 根路径只返回 API 说明，不提供旧网页或静态资源。

## 两条生成链路

1. 图片／视频生成节点 → 工作台 `/api/ai/media/generate` → 供应商适配器 → ComfyUI／在线 API → 当前工作区素材。任务状态、请求快照和取片由工作台媒体模块管理；Flux、SD、Qwen 与 H3 内置图由工作台配置选择。
2. 本地 H3 工厂节点 → `/api/h3Factory/execute` → Python `/api/v2/projects`、执行计划、任务与交付接口 → 原生产 Worker → ComfyUI、FFmpeg、字幕与质检 → 取回工作区。

ComfyUI 环境设置经工作台代理调用生产 API 的 `/api/environment/local`、inspect、configure、start、plan、install、stop。模型发现、目录搜索与内置工作流构建由工作台提供。

## 保留的共享实现

| 实现 | 调用或数据依赖 |
| --- | --- |
| `app/agent_api.py`、`execution_plan.py`、`jobs.py` | H3 项目、计划、运行、停止／续跑、幂等回执 |
| `projects.py`、`assets.py`、`database.py` | 镜头身份、素材绑定、历史版本、持久任务 |
| `pipeline.py`、`rendering.py`、`comfyio.py`、`continuity.py` | 实际渲染、缓存、首帧及模型释放 |
| `finishing.py`、`speech.py`、`quality.py`、`delivery.py` 等 | H3 finish、字幕、VAD、媒体检查与成片取回 |
| `environment.py`、`video_environment.py`、下载清单与缓存节点 | 新工作台的 ComfyUI 安装、启动和工作流就绪检查 |
| `image_studio.py`、图片引擎／模型／素材模块 | Worker 图片环境释放、项目参考图、Agent 图片接口；不因新画布有直连生图而删除 |
| `content.py`、`providers.py`、`skills.py`、`resources/` | 共享模式解析、提示词编译、显式内部文字规划与 Agent 参考 |
| `series.py`、`transfer.py`、导演风格模块 | Worker 历史整剧任务、素材继承、迁移数据及公开 Agent API |

“未在画布显示按钮”不能证明模块未使用。保留代码按直接调用、共享依赖、外部 Agent 工具和已有任务数据识别；本次不删除数据库、用户预设、项目、凭证、模型、缓存或产物。

## 已移除

- 根目录 `web/` 的 13 个旧 HTML、JS、CSS 文件与静态挂载。
- 旧网页启动选项、旧全局预设面板 API 与其 builtin.json、`/api/key` 和 `/api/create` 废弃别名。
- 根目录仅服务旧网页检查的 npm 工程、3 个 JavaScript 检查文件，以及现有混合检查中只检查旧静态资源的部分。
- 旧页面截图、UI 专属评审／规划说明、2.x 页面更新指南，以及依赖固定演示项目路径的工作流导出脚本。
- 安装、资源初始化、CI 与便携包中对上述内容的引用。

生产 API 的受支持项目、媒体、环境、技能、迁移与版本化接口保留；导入旧项目中的个人预设仍作为用户数据处理。未来新增交互统一加入画布及节点插件。

## 数据与执行边界

画布数据位于 `workbench/data/`；H3 配置、密钥、数据库和项目位于根目录 `config/`、`.secrets/`、`data/`、`projects/`。两者通过 API 连接，不互相直接修改项目状态。

H3 按镜头顺序执行。提示词、实际素材摘要、种子、模型和图参数参与缓存判断，首帧依赖还包含紧邻前镜的真实视频与镜头身份。任务结束后，交付清单分别核对文件存在、来源、摘要与解码；实际画面、对白及口音仍需验看。

## 清理验证（2026-11-06）

- 保留的 452 项 Python 检查通过；Agent 发布契约与运行接口一致，工作台前后端构建通过。
- 通过新工作台媒体接口生成 Flux 文生图与 Qwen Turbo 单图编辑，各为 1024×1024 PNG。实际查看确认蓝色茶壶改为红色，背景保留。
- 视频节点通过 ComfyUI 生成 H3 文生视频，832×480、24 fps、107 帧、约 4.46 秒，H.264／AAC 完整解码通过。
- 清理后的生产 API 完成同一蓝色茶壶参考图的 H3 I2VA 渲染与 finish，640×640、24 fps、107 帧、约 4.46 秒。通过工作台 H3 适配器验收、核对 SHA256 并导入工作区；交付 ready_for_delivery 为 true，首尾抽帧可见参考构图和升起的热气。
- 页面可打开，5 个 ComfyUI 图片模型和视频模型保留；内置工作流读取成功，浏览器无错误。根目录启动、API-only 模式和当前实例复用正常；旧静态资源与移除的旧面板 API 不再注册。

验证时发现同目录旧 8765 服务仍以全队列模式运行，曾先领取验证任务；保存原任务回执、等待完成并确认队列空闲后停止旧实例。后续渲染与后期均由当前 8770 服务的显式队列完成，画布使用 3001。

本轮未调用收费媒体 API，也未逐一推理所有可选模型或重建完整便携包。类型检查仍有原有 ElectrobunConfig 开发类型缺失；清理没有更改工作台模型适配器、节点或内置生成图实现。

# 短剧工厂

基于画布的本地短剧创作工作台：DeepSeek 负责剧本、分镜和 Agent 推理，在线媒体 API 或本机／局域网 ComfyUI 负责图片和视频生成，Python 工厂负责执行计划、缓存、续跑、后期和成片交付。

## 使用

从源码安装时，在本 `workbench/` 目录执行 `bun install --frozen-lockfile`、`bun run build:server`，完成后双击上一级根目录的 `启动短剧工厂.cmd`，统一启动画布（默认 3001）和生产 API（首次默认 8770）。仅开发画布服务时可在本目录执行 `bun run start:server`；开发入口为 `bun run dev`。首次进入可跳过配置，之后在设置中填写：

- **文本模型（DeepSeek）**：填写 API Key，读取实际模型列表并保存。
- **视频模型**：内置字节火山方舟 Seedance 2.5、ComfyUI 工作流；可添加其他 API 适配器。H3 工厂连接在本页折叠区配置。
- **图片模型**：内置 Seedream、ComfyUI，可添加其他图片 API。ComfyUI 支持读取服务器上的 Checkpoint，或导入 API 工作流。
- **插件工厂**：本地插件、技能、文件扩展、MCP 和 FFmpeg 的管理入口。

连接参数也可由 `SDF_COMFY_URL`、`SDF_BASE_URL`、`SDF_APPLICATION_ROOT` 提供初始值，设置页保存的值优先。服务监听地址和端口可用 `TOONFLOW_SERVER_HOST`、`TOONFLOW_SERVER_PORT` 配置；`TOONFLOW_DATA_DIR` 保留为兼容的数据目录变量。

ComfyUI 可填写本机回环地址、局域网私有 IP 或 .local 主机名；目标电脑需启动 ComfyUI 并监听对应网卡，允许工作台主机访问其端口。也可保留 SSH 转发。H3 工厂接口仍通过回环／SSH 隧道核对运行实例。图片和视频连接分别保存。

## 本地生产

使用“本地 H3 工厂”节点绑定项目、展开分镜、修改提示词、规划并执行生成。局部修改保留未受影响的镜头；中断后按原任务 ID 续跑。完成镜头后执行 finish，取回最终视频和交付校验清单。

“ComfyUI 工作流”节点用于导入、编辑和执行原始工作流，复用设置中的地址，通过宿主转发提交和查询。正式生产的任务持久化与缓存续跑由 H3 工厂节点提供。

## 随应用预装

用户提供的 10 个包收录在 `packages/bundledPlugins`，原始文件来源和 SHA256 见 `manifest.json`：

- 节点：换装捏人、ComfyUI 工作流。
- 工具：导演之眼、小说转 TXT / Markdown。
- 文件扩展：剧本分集。
- 技能：剧本创作引擎、剧本创作工作室、H3 提示词写作、短剧剧本工厂、大师级电影制作。

另有短剧工厂制作流程，统一 H3 执行约定。启动时补齐未安装的内置插件，不覆盖用户修改。换装节点生成使用图片模型配置。模型设置已提供 SD / SDXL、Flux、Qwen 图生图与文生图，以及 H3 文生视频／首帧图生视频的内置方案；其他架构可导入匹配的 API 工作流。

本发行版移除了云账号、余额充值、网页市场、市场上传、广告、使用数据上报和原版自动更新入口；文本运行时使用 DeepSeek；媒体 API 使用用户自行填写的供应商地址和密钥，不依赖平台账号。

## 兼容与许可

旧画布字段、插件注册协议、包导入命名和数据目录保持兼容。上游 MIT 版权与第三方许可证保留，详见 LICENSE 及各组件许可文件。原版项目来源保留在 Git 元数据中。

## 媒体连接约定

- 火山方舟视频按[官方创建任务协议](https://docs.volcengine.com/docs/ark/create-video-generation-task-api?lang=zh)接入 Seedance 2.5，图片按[图片生成协议](https://docs.volcengine.com/docs/ark/image-generation-api?lang=zh)接入 Seedream。模型 ID 与能力可以在编辑模型中调整。直连支持文本、图片首尾帧、图片／音频参考；参考视频上传请使用适配上传能力的其他接口。
- ComfyUI 使用[官方 HTTP API](https://docs.comfy.org/development/comfyui-server/comms_routes)上传参考图、提交工作流、查询历史并收集输出。导入 API JSON 后把正向文本输入改为 `{{prompt}}`，图片加载输入改为 `{{image0}}`（第二张为 `{{image1}}`）；首尾帧为 `{{firstFrame}}` / `{{lastFrame}}`。可选变量：`{{seed}}`、`{{width}}`、`{{height}}`、`{{duration}}`、`{{resolution}}`、`{{ratio}}`、`{{generateAudio}}`、`{{model}}`。独占一个输入值的变量保持数字／布尔类型。未绑定的参考图会报错，不静默忽略。
- 保存模型配置会刷新画布模型目录。异步任务接单后保存原任务 ID，恢复时只查询原任务。取消等待不会清空远端 ComfyUI 队列，也不会自动取消供应商计费。
- 工作流中的模型和自定义节点必须已在目标 ComfyUI 安装。读取连接不安装模型，也不提交生成任务。

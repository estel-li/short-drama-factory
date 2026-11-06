# 图片生成与项目参考图

## 画布图片生成

新工作台使用“图片生成”节点，通过工作台供应商适配器连接 ComfyUI 或在线接口。在设置中选择 SD / SDXL、FLUX Schnell、Qwen Image 2.1 Turbo 的文生图或单图编辑方案，保存后从节点模型下拉选择。

图生图先连接一张原图。SD / Flux 使用 VAE 编码和重绘强度；Qwen Turbo 使用单图编辑专用编码图。工作台目前内置的 Qwen 单图工作流与下面的后端多图 API 是不同入口，不能把多图能力直接套用到单图节点预设。配置步骤见 [工作台说明](windowsWorkbench.md)。

## 保留的后端图片 API

旧网页已移除，Python 图片服务仍被项目参考图、Worker 引擎释放和外部 Agent 调用。它提供原版 Qwen、Qwen UD 及 SDXL、Flux 等模型的独立 API，模型清单从实例 `GET /api/images/models` 读取；不因界面移除而删除请求、产物或历史素材。

常用流程：

1. 查看模型与环境计划，核对实际文件和下载量；缺少资源时显式准备。
2. 通过 `POST /api/v2/image-inputs` 上传原图，使用返回的真实输入 ID。
3. 通过 `POST /api/v2/images` 提交图片请求，保留幂等键和任务 ID。
4. 查询 `GET /api/images/{id}` 与任务状态；只有成功且文件可取时才完成。
5. 通过 `GET /api/images/{id}/file` 取图并实际查看，或采用为项目参考。

请求模板、CLI、模型边界与恢复约定见 [Agent 图片接口](../agent-skills/short-drama-factory/references/images.md)。

## 参考图与参数

后端 `reference_images` 接收输入 ID 数组，`reference_mode` 区分参考创作与图像编辑。能力以当前模型目录为准；部分后端 Qwen 模型支持多图，其他架构为单图重绘。不能丢弃多余输入或将多图悄悄拼成单图。

Qwen 中 `<image1>`、`<image2>` 对应真实输入顺序。编辑模式保留第一张原图的比例；原图应满足格式、尺寸与数量校验。提示词优化会调用文字提供商，外部 AI 已写好的提示词默认 `optimize:false`。

全局 `image_generation` 保存后端引擎模式、地址、模型目录和默认采样等设置；单次参考图、提示词、种子和尺寸保存在任务中。支持的参数见模型接口及 [模型与工作流指南](advanced-workflows.md)。

## 项目参考与连续性

项目角色、场景和道具的源素材与采用记录保存在 `reference-images.json`，实际素材复制到项目 `assets/`。修改采用素材可能使相关提示词失效，需要补齐后重新计划。严格 render 不自动补图或优化文本；先显式准备并采用参考图。

`app/image_studio.py`、图片模型／环境／输入模块及清单是生产 Worker 的共享依赖。图片请求、ComfyUI prompt ID、参数、输出与历史版本继续落盘，停止只取消当前任务拥有的提交。

Qwen 权重许可与使用边界见 [第三方声明](../THIRD_PARTY_NOTICES.md)。生图模型不随源码分发，已有模型按实际目录复用。

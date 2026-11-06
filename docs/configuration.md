# 配置说明

## 新工作台配置

通过“设置 → 文本模型／图片模型／视频模型／ComfyUI 环境”修改。画布服务的配置保存在 `workbench/data/settings.json`，其中 `settings.localModels` 记录 ComfyUI 地址、生产 API 地址和实际工厂根目录；`settings.mediaProviderConfigs` 记录供应商及独立工作流。

这些配置包含本机路径和用户凭证，不能提交仓库或输出到日志。设置页保存的连接优先于 `SDF_BASE_URL`、`SDF_APPLICATION_ROOT`、`SDF_COMFY_URL` 环境变量。根目录启动器只启动当前目录的本机工厂，不覆盖已保存的连接。

`TOONFLOW_DATA_DIR` 用于手动启动服务时指定工作台数据目录；根目录统一启动固定使用本目录 `workbench/data/`。工作目录与画布素材不等同于 Python 的项目目录。

## 生产后端配置

| 路径 | 用途 | 是否提交 |
| --- | --- | --- |
| `config.default.json` | 无认证、无私人路径的后端默认配置 | 是 |
| `config/application.json` | 本机环境、后端文字提供商、代理及项目目录 | 否 |
| `.secrets/*.key` | 后端提供商、HF、ComfyUI 认证 | 否 |
| `workbench/data/settings.json` | 画布、Agent 与媒体供应商配置 | 否 |
| `extra_model_paths*.yaml` | 本机模型搜索映射 | 否 |
| `presets/personal.json` | 旧项目迁移所保留的用户预设数据 | 否 |
| `projects/*/settings.json` | H3 项目独立设置 | 否 |

生产 API 通过 `/api/v2/config` 读取／修订配置，认证使用专用入口。旧网页已移除，不能在生产端口寻找配置页面。H3 镜头／项目参数通过工厂节点或 Agent 接口编辑，修改前读取 revision。

`DEEPSEEK_API_KEY` 是后端显式内部文字阶段的环境变量。画布 Agent 使用工作台自己的模型设置，两者不是同一份配置。后端继续支持已有 DeepSeek、Ollama、LM Studio 和兼容提供商，供内部规划与公开 API 使用。

## ComfyUI 与生成

环境设置可选择现有 ComfyUI 或预览固定安装清单，搜索模型目录并接入。接入目录不复制权重；远端服务须自行具备模型与节点。模型、采样器、LoRA、编码器与 VAE 必须匹配工作流。

画布独立图片工作流放在 `mediaProviderConfigs.comfyUi.workflowModels`。SD／Flux 图生图支持重绘强度，Qwen Turbo 单图编辑使用专用编码图。画布节点的尺寸、提示词与参考图属于单次请求。

Python 的 `image_generation` 和项目 `reference_images` 仍用于后端图片 API、项目参考图与 Worker 引擎管理，不与画布直连模型设置混用。详情见 [后端图片接口](image-studio.md)。

H3 的 profile 包含画幅、像素规模、步数、采样与模型选项；更新模型、素材或提示词会影响缓存。自动接续必须绑定真实的紧邻前镜末帧，不能在缺图时静默退回文生视频。

## 凭证与用户数据

标准包排除配置、密钥、项目和工作台数据，仅包含固定的 Silero VAD CPU 质检模型。生成大模型按清单显式准备。项目迁移仍保留素材、历史版本与个人预设，不能把用户数据当成旧网页文件删除。

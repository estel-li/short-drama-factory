# 配置说明

优先通过工作台修改配置，任务运行期间不会允许修改全局环境或 Skill。

## 文件

| 路径 | 用途 | 是否提交 |
| --- | --- | --- |
| `config.default.json` | 无认证、无私人路径的默认生成配置 | 是 |
| `config/application.json` | 本机环境、提供商、代理和项目目录 | 否 |
| `.secrets/*.key` | 提供商、HF 和 ComfyUI 认证 | 否 |
| `extra_model_paths.yaml` | 本机模型搜索映射 | 否 |
| `presets/personal.json` | 个人预设 | 否 |
| `projects/*/settings.json` | 每个项目的独立设置 | 否 |

`DEEPSEEK_API_KEY` 环境变量可提供 DeepSeek key，优先于本机文件。不要把真实值写进仓库的脚本或说明。浏览器保存认证后不回传原 key，只显示是否配置。

## 文字提供商

支持 `deepseek`、`ollama`、`lmstudio`、`compatible`。服务地址不应夹带用户名、密码、查询参数或片段。每阶段可覆盖默认模型，留空继承提供商模型。

默认网络额外重试 `retries=3`；格式额外修复 `format_retries=3`。网络超时、中断、限流和临时服务器错误采用有限退避；确定性认证、余额和参数错误直接报告。格式修复把具体 JSON、模式、素材或对白校验错误发回模型。

本地模型与 H3 争用显存时，Ollama/LM Studio 可以在请求后自动卸载；其他本地服务自行管理卸载或使用 CPU。

## H3 与安装

`manifests/h3-5060ti-16g.json` 固定 ComfyUI、模型和推理依赖版本及校验值。预览安装清单显示复用/下载文件、目标目录、大小及磁盘剩余容量，缺少模型才下载。

质量预设由 `megapixels`、`steps`、`turbo`、采样器、调度器等参数组成。默认快速预览为 0.4MP / 4 步；LoRA 和模型必须匹配实际模式。修改模型或生成质量会影响缓存及资源需求。

提供商选择、首帧模式和单镜素材都由真实绑定校验。首帧自动接续开启时强制 I2VA，不采用“缺少参考则文生降级”。

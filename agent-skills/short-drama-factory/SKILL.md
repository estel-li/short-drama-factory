---
name: short-drama-factory
license: MIT
metadata:
  version: "4.0.0"
  contract_version: 1
description: 通过本地短剧工厂的命令行与 API，把当前 AI 编写的分镜和 H3 提示词制作成视频；支持真实素材绑定、图片生成、按镜头修改、断点恢复与交付检查。用于操作已安装的工厂制作或修复内容，不用于开发应用代码。
---

# 短剧工厂：从 AI 对话制作视频

默认由当前 AI 理解需求、创作分镜和提示词，工厂负责校验、排队、生成与后期。用户无需打开图形工作台。本技能可安装给 Codex 或其他能执行本地 Python／HTTP 的 AI；它不是工厂内部的文字生成模板。

交付用户要求的实际产物，并保留项目 ID、任务 ID、提交回执和验收范围。仅完成计划、镜头子集或一个任务，不代表整片已完成。

## 先连接正确实例

本技能使用 **agent 协议 1**。3.8.0 起提供版本化项目／计划接口，3.9.0 配套任务级 CLI，4.0.0 增加交付清单与批量提交。以健康接口的 `protocol_version`、`application_root` 和 capabilities 的实际功能为准，不单凭版本号猜能力。

先读 [连接与命令行](references/cli.md)。以下命令在技能目录运行；Python 可替换为可用解释器的绝对路径。CLI 仅需 Python 3.10+ 标准库。

```powershell
python scripts/sdf.py --base-url http://127.0.0.1:8765 connect --app "应用绝对目录"
python scripts/sdf.py doctor
python scripts/sdf.py capabilities
```

连接失败且应用尚未启动时，使用 `sdf.py start --app "应用绝对目录" --port 8765`。新服务仅提供 API，不打开浏览器、不恢复旧队列；复用已运行服务时查看返回的 queue_mode，不假定它已暂停旧任务。工作目录中的 `.sdf` 保存连接与操作记录；换目录时用全局 `--context` 指向原连接文件。

多实例必须核对 `application_root`。云端聊天不能直接访问用户电脑的 `127.0.0.1`；需要本机执行器，不能把绑定本机的接口描述成远程服务。

## 按当前任务读取

| 用户目标 | 读取与执行 |
| --- | --- |
| 从故事制作短片 | [分镜与 H3 契约](references/story-and-h3.md)，[请求模板](references/templates.md)；当前 AI 创作后走严格渲染 |
| 保留原声、原画面、关键帧或动作接续 | [工作流选择](references/workflow-selection.md)；仅涉及高级媒体槽时再读 [高级 H3](references/h3-advanced.md) |
| 改一句台词、一个镜头、字幕或画幅 | [编辑与修复](references/production-practice.md)；按 UID 修改，重新计算影响范围 |
| 接着旧项目做、请求超时或生成失败 | [诊断与恢复](references/recovery.md)；先定位原任务和回执 |
| 生成独立图片或人物／场景参考图 | [图片接口](references/images.md)；外部提示词默认 `optimize:false` |
| 准备模型或配置环境 | [资源准备](references/workflow-models.md)；只在确有缺项时读取 |
| 验收、取片、CPU 后期 | [交付检查](references/delivery-checks.md) |
| 按已有计划提交多个项目 | [CLI 的批量提交](references/cli.md#批量提交已有计划)；逐项目保存结果，分别跟踪任务 |
| 编写自己的调用程序或 CLI 暂未覆盖某能力 | [接口契约](references/api.md) 与实例 `/openapi.json` |

不需要一次读取全部参考资料。模型、工作流、参数和槽位从 capabilities／实例接口查询，不复制历史参数表作为当前事实。

## 默认制作路径

1. **整理需求与素材。** 保留用户指定的台词、原声、角色与镜头目的。依据现有素材选择模式；没有素材时先完成可做的创作，缺项不能用虚构 ID 或静音替代。
2. **创作草稿。** 当前 AI 填写完整 Story 与每镜 H3 prompt。主模板为 [agent-storyboard.json](assets/agent-storyboard.json)；创建仅保存草稿，返回稳定项目 ID，不自动开始生成。
3. **校验并计划。** 读取 `project validate` 的问题位置，再运行 `project plan`。查看 `ready`、`blocked`、`affected_uids`、`effects`、模型缺项与 `expected.delivery_scope`。计划中的缓存候选不是命中保证，未知时间／费用不能写成精确估计。
4. **执行与跟踪。** 计划满足需求后使用同一 `plan_id` 运行，保存 CLI 先输出的请求键和最终任务 ID。用有界 `job watch` 观察原任务；仍在运行就继续观察，不新建任务。
5. **检查产物。** 使用 `deliver PROJECT_ID --verify` 核对当前成片，按需加 `--output 新目录` 取片。整片与所选镜头分别判断成功；媒体完整性通过不代表画面、台词或字幕已经验收，按交付检查记录已验证与未验证项。

```powershell
python scripts/sdf.py project create --json project-request.json
python scripts/sdf.py project validate PROJECT_ID
python scripts/sdf.py project plan PROJECT_ID
python scripts/sdf.py project run PROJECT_ID --plan PLAN_ID --wait 45
python scripts/sdf.py job watch JOB_ID --seconds 45
python scripts/sdf.py deliver PROJECT_ID --verify --output delivery-v1
```

`render` 计划始终严格：不补大纲、不重写分镜、不优化图片提示词、不生成隐藏参考图，也不隐式下载。缺失或失效的 prompt 由当前 AI 补齐后重新计划。已有下载或全自动制作授权继续有效；计划是机器执行契约，不要求每一步都再次询问用户。

只有用户选择工厂内部文字模型时，才使用 [agent-outline.json](assets/agent-outline.json) 并请求 `project plan PROJECT_ID --action plan --allow-internal-text`。该内部规划阶段可能调用文字模型；启用了自动参考图时还可能使用 GPU。规划完成后另建 `render` 计划。

## 修改与恢复的关键约定

- 读取最新项目及 `revision`，按 UID 局部修改。一次更新提交 `settings`、完整 `story` 或 `shots` 中一种。保留镜头 UID、用户台词、素材和不相关设置；不要直接改 SQLite、分镜文件或状态文件。
- 改台词／人物／动作时同步改 prompt；只改字幕时间使用后期字段和 `finish` 计划。`profile` 是项目级设置，影响范围由计划说明。
- 同一写请求保留同一个请求键。响应丢失时先查 `operation get`，需要补交时使用保存的 `operation retry`；新内容使用新键，不根据超时重新创建项目。
- `REVISION_CONFLICT` 先重新读取并合并；`PLAN_STALE`、素材／模型变化先重新计划。已有原片继续保留，不能通过反复 resume 绕过过期计划。
- `scope_complete` 表示选中范围完成，范围外仍待验证；即使原片都有，也没有自动合片。任务 `done` 只表示任务阶段结束。
- 用户要求审核时遵守审核停点；已授权自动制作时在范围内继续。阻塞时给出具体字段、原项目／任务和下一步，不反复提交同一确定性失败。

凭证通过用户本地环境变量或受控标准输入配置，只读取是否已配置。不得把 key 写入聊天、JSON 样例、技能、回执或日志。普通制作不顺带重装环境、升级引擎或下载额外模型。

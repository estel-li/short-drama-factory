---
name: short-drama-factory
license: MIT
metadata:
  version: "1.2.0"
description: 操作本地短剧工厂（Short Drama Factory），将灵感、大纲、剧本或外部 AI 编写的分镜与 H3 提示词变成视频，也可用 Qwen 生成独立图片和项目参考图。支持审核、素材绑定、续跑、重生成与导出。用于通过该程序制作图片或视频；不用于修改应用代码或一般视频剪辑。
---

# 短剧工厂视频制作

你是操作短剧工厂的制作助手。完成用户指定的视频并提供可播放的产物、项目 ID 和验收结果。此技能是**外部 AI 的操作技能**，不要导入工厂内部的大纲／分镜／提示词 Skill 列表。

## 连接与准备

适配短剧工厂 **2.5.0** 的实际 API；图片功能要求 2.5.0 及以上。需要 AI 能执行本地命令或访问本机 HTTP；客户端脚本只用 Python 3.10+ 标准库，不依赖 Codex 专属工具。只有云端聊天能力的 AI 无法直接访问用户电脑的 `127.0.0.1`，应由本机代理执行命令。不要为此公开工作台端口。

1. 找到用户指定的应用目录与端口，先 `GET /api/health`。默认 `http://127.0.0.1:8765`，返回 `version`、`application_root`、`comfy`、`active_project`。不要把技能目录误当作应用目录。已启动的正确实例直接复用。
2. 未启动时，在应用目录运行 `启动短剧工厂.cmd --no-browser`；也可用该应用的 `runtime/python.exe`（便携包）或 `.venv/Scripts/python.exe` 运行 `launcher/start.py --no-browser`。后台启动时隐藏窗口，轮询健康接口。端口冲突时先辨认实例，明确使用 `--port 8770` 等空闲端口，客户端对应传入 `--base-url`。
3. 读 `GET /api/config`、`/api/skills`、`/api/presets`，使用真实存在的提供商、质量预设和 Skill。健康检查不能证明所有 H3 模型就绪；渲染前还要读 `/api/environment/catalog` 的 `missing_nodes`、`configured_missing`、`cache_protocol`。连接失败时按 [故障恢复](references/recovery.md) 处理。
4. 从请求确定输入类型、故事、风格、画幅、镜头数／时长、对白、参考素材和审核方式。普通缺省用 9:16、24 秒、6 镜、`draft`；16GB 显存先用 0.4MP / 4 步、每镜 4～8 秒。不要覆盖用户明确设置。先请求 `/api/duration-plan`，报告分配时长与帧对齐后的预计时长；对白和后期会进一步影响成片长度。
5. 有对白时先确认采用哪一版原文；用户已指定定稿就直接沿用。H3 同时生成音画，改台词通常需要重生成对应镜头，不能只改字幕冒充配音已更新。明确哪些镜头保留画面、哪些按用户要求用于文字页；按 [实战制作与诊断](references/production-practice.md) 计算对白预算，只有影响制作决策的缺项才询问。

命令相对技能目录运行；也可将脚本改为绝对路径。Windows 中文 JSON 使用 UTF-8 文件，避免把整段 JSON 塞进 shell 参数：

```powershell
python scripts/factory_api.py get /api/health
python scripts/factory_api.py get /api/config
python scripts/factory_api.py get /api/skills
python scripts/factory_api.py get /api/environment/catalog
```

有应用自带 Python 时可用其绝对路径替换 `python`。`--base-url`、`--timeout` 是子命令前的全局参数。

## 选择创作路径

仅制作图片，或为视频生成角色／场景／道具参考图时，先读 [图片与参考图接口](references/images.md)。图片优化默认开启；用户明确要求直接使用提示词时传 `optimize:false`。视频项目的 `reference_images.enabled` 默认关闭，只有用户需要自动参考图时才开启。启用后 `stage/plan` 也会使用 GPU 生成图片。

### A. 工厂调用文字模型

适合已有大纲／剧本，让工厂调用用户配置的 DeepSeek 或本地模型。以 [大纲请求模板](assets/project-outline.json) 为起点，替换 `input` 和 `options`。三阶段 `stages` 分别选提供商、模型与 Skill；留空 `model` 继承提供商模型。

先用 `start:false` 创建项目，再调用 `stage/plan`，生成文字、不渲染视频。`execution_mode:auto` 会完成文字三阶段；`review` 则在配置的检查点返回 `review`。检查大纲、角色区分、镜头动作、对白装镜及 H3 提示词，读取 `preflight`。用户已要求全自动时直接完成合理检查并继续，不逐阶段重复询问；用户要求审核时停在相应阶段等待。

### B. 外部 AI 自己写分镜和提示词

适合用户要求由当前 AI 创作，或不想另调文字 API。先读 [分镜与 H3 契约](references/story-and-h3.md)，以 [外部 AI 请求模板](assets/project-storyboard.json) 改写。

使用 `input_mode:storyboard`，`storyboard` 为对象，所有镜头填完整 `prompt`。工厂保存后会标记手写提示词；`auto_reference:false`、明确 `T2VA`、无首帧接续的模板可直接走渲染，不需要文字 API。**不要调用强制 `stage/prompt`，它会清除手写标记并重新调用文字模型。** 需要参考图／接续时按契约绑定，不能靠提示词虚构素材。若修改剧情导致旧提示词被清空，先补齐再继续。

## 共同执行流程

先读 [API 操作表](references/api.md)，其中说明准确请求体和关键参数。

```powershell
# 将所选模板复制到工作目录，填入用户内容，再发送。
python scripts/factory_api.py post /api/projects --json project-request.json
# 保存返回的 id；start:false 时 job_id 为空。
python scripts/factory_api.py get /api/project/PROJECT_ID
python scripts/factory_api.py get /api/projects/PROJECT_ID/preflight
```

创建请求的 `start` 必须明确；API 省略时默认立即排队全流程。每次保存返回的项目 ID、任务 ID。已有项目优先按 ID 继续，不因超时重新创建。

1. **生成文字（仅按需）**：`POST /api/projects/{id}/stage/plan`，JSON `{}`。`render` 也会补齐缺失的文字阶段，所以外部 AI 路径要先确认所有 `prompt` 非空。
2. **保存修改**：先读取完整 `story` 或 `settings`，保留未知字段、镜头 `uid`、素材及锁定状态，只改所需字段，再通过 API 保存。设置保存是整体替换，不是局部 PATCH。项目 `busy:true` 时先等待；需要改动运行项目则按用户要求停止，等队列退出后再改。
3. **预检**：`preflight.ready` 必须为真，另核对模式、真实素材、场景图的角色标记和 H3 标签。可运行 `diagnose --project PROJECT_ID` 汇总绑定冲突与历史采样耗时。结构校验、对白预检、素材／模式检查、提示词检查各有不同覆盖范围，任何一项通过都不代表 GPU 或全部契约已验证。
4. **渲染**：`POST /api/projects/{id}/stage/render`，正常 `{}`；用户需要试镜时用 `{"limit":1}`。这是最多生成一个待生成镜头，不是选择镜头 ID，也不保证整片完成。首帧接续必须按相邻镜头顺序生成。
5. **监控**：用下方命令跟踪确切任务，每轮至多约一分钟。客户端退出码 `3` 表示还在运行，不会停止服务或取消任务；下一轮跟踪同一个 ID。任务 `review`／`paused`／`error` 分别需要审核、恢复或诊断，不等于成片完成。任务 `done` 也可能只是文字或试镜完成。

```powershell
python scripts/factory_api.py watch --project PROJECT_ID --job JOB_ID --seconds 45
python scripts/factory_api.py diagnose --project PROJECT_ID
```

6. **验收与交付**：读取项目和 `quality`，核对不再忙碌、`state.status:complete`、`final:true`、媒体验收报告及需要的字幕版。正式交付按 [成片验收](references/delivery-checks.md) 做完整解码、切口核对和原文／音频／字幕三方检查。没有播放／听音能力时明确尚未进行人工音画验收，不能声称质量已通过。返回项目 ID、成片链接或本地绝对路径；需要迁移才导出含视频项目包。

```powershell
python scripts/factory_api.py get /api/projects/PROJECT_ID/quality
python scripts/factory_api.py download /media/PROJECT_ID/成片.mp4 --output 成片.mp4
```

## 操作边界

- 复用用户配置的凭证；不读取或输出 `.secrets`、真实 key，不把凭证写入技能、请求样例或导出说明。缺认证时由用户在应用设置或其受控凭证机制中填写。
- 修改／重生成限于用户指定项目；按用户授权范围调用文字 API 和 GPU，不因为“测试技能”而启动有费用的创作或大量 GPU 任务。默认不做环境重装、升级、模型下载或全局配置替换。
- POST 超时可能已经成功。先查项目列表、队列和原任务，不自动重发创建／生成／导出请求。脚本不自动重试写操作；应用本身已有有限重试。
- 优先用 HTTP API 保存和排队，保留版本、缓存与锁定语义。不要直接改 SQLite、`state.json`、`分镜.json` 或并发启动 `pipeline.py`。
- 修复、停止、后期、素材和分集功能见 [API 操作表](references/api.md)；异常按 [故障恢复](references/recovery.md)。当前接口没有单任务查询端点，`/api/jobs` 仅返回最近 100 条，找不到旧 ID 时不能猜测成功或重新排队。

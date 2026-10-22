# 接口契约：agent 协议 1

默认应用地址 `http://127.0.0.1:8765`，不是 ComfyUI 端口。先读 `/api/health` 核对 `application_root` 与 `protocol_version:1`，再读 `/api/capabilities` 与 `/openapi.json`。应用版本与 agent 协议版本分别检查；实际字段、约束和响应 Schema 以该实例为准。

日常制作优先使用 [任务级 CLI](cli.md)。需要未封装能力时可用同包 `factory_api.py` 的 get/post/download/asset；使用底层工具前先看 `--help`，尤其不要把 legacy POST 当作已有幂等保护。纯 JSON 文件可通过 `--json FILE` 或 `--json -` 输入。

## 版本化制作接口

| 方法与路径 | 请求／结果与副作用 |
| --- | --- |
| GET `/api/v2/projects/{pid}` | 项目、story、settings、revision；只读 |
| POST `/api/v2/projects` | `input/options/storyboard`；仅创建草稿，不接受 start 字段，不排队 |
| PATCH `/api/v2/projects/{pid}` | `expected_revision` + settings／story／shots 中一种；版本化保存、按内容失效缓存 |
| POST `/api/v2/projects/{pid}/validate` | 无内容请求；校验已保存分镜与外部 prompt，不生成 |
| POST `/api/v2/projects/{pid}/shots/{uid}/compile` | sections 段落对象；纯格式编译，返回 prompt／mode／对齐时间／标签／revision，不保存、不排队 |
| POST `/api/v2/projects/{pid}/plans` | action=render/finish/plan、internal_text=forbid/allowed、可选 uids、regenerate；保存可审阅计划，不生成 |
| GET `/api/v2/projects/{pid}/plans/{plan_id}` | 读取已保存计划 |
| POST `/api/v2/projects/{pid}/run` | `{"plan_id":"实际64位计划ID"}`；验证计划仍有效后排队 |
| GET `/api/v2/operations/{key}` | 查询原写请求与结果；可用于响应丢失恢复 |
| POST `/api/v2/jobs/{jid}/resume` | 可选 expected_revision；续跑同一任务，仍受输入／资源版本检查 |
| POST `/api/v2/jobs/{jid}/stop` | `{"immediate":false}` 默认请求停止；true 只中断该任务拥有的引擎提交 |
| POST `/api/v2/images` | request + internal_text，默认外部提示词；创建持久图片任务，禁止隐式下载 |
| POST `/api/v2/image-inputs` | name/data；带提交回执上传独立图片输入 |
| POST `/api/v2/projects/{pid}/assets` | type/name/data/character；带提交回执上传项目素材，返回新 revision |
| GET／PATCH `/api/v2/config` | 查询 revision/config；PATCH 用 expected_revision/changes 局部修改公开配置 |
| GET `/api/v2/environment/speech/plan` | 查询 CPU 语音模型的真实缺项、体积与确认 token |
| POST `/api/v2/environment/speech/prepare` | download_confirmation；显式准备 CPU 模型并返回任务 |

create/update/run/resume/stop、图片／素材上传、配置 PATCH 与显式资源准备必须传 `Idempotency-Key` 请求头。相同键、相同请求返回原结果；同键不同内容拒绝。计划创建只是保存计划，不能据 POST 或 HTTP 201 断言开始推理。幂等键解决应用提交重复，不等于可以不检查引擎未知的提交结果。

创建示例使用 [agent-storyboard.json](../assets/agent-storyboard.json)。更新示例：

```json
{
  "expected_revision": "从最新项目返回复制的revision",
  "shots": [
    {"uid": "实际镜头UID", "changes": {"dialogue_timings": [{"start": 0.6, "end": 2.1}]}}
  ]
}
```

settings 是局部递归合并，story 是完整替换，shots 按 UID 局部修改。一次请求只更新一种资源；数组不做逐项递归合并，不能把半份 characters 数组当作单角色 PATCH。UID/id 不可通过镜头 patch 更换；排序／插镜使用完整 story，保留已有 UID。

严格 render 不使用内部文字模型；即使请求 internal_text=allowed 也不会隐式编写提示词。允许内部文字的创作使用 action=plan、internal_text=allowed，完成后另建 render 计划。所有 agent 执行默认禁止隐式下载。

## 精确任务与状态

- GET `/api/jobs/{jid}` 精确查询持久 ID；GET `/api/jobs/page` 支持 limit、before、project_id、status。
- GET `/api/jobs/{jid}/events?after=0` 按返回游标续读；不要反复只读最近 100 条的旧 `/api/jobs`。
- `done` 是阶段完成，`review`／`paused`／`error` 需要检查 message 和项目状态。
- `state.current_stage:scope_complete` 是所选镜头完成，范围外未验证，不产生新的完整合片。
- `REVISION_CONFLICT` 重新读取合并；`PLAN_STALE` 重新计划；`TEXT_GENERATION_FORBIDDEN`／`EXTERNAL_CONTENT_REQUIRED` 由外部 AI 修正；`IMPLICIT_DOWNLOAD_FORBIDDEN` 显式准备资源。
- 错误返回 code/message/retryable/details/next_actions。只展示脱敏信息；retryable 也不授权无限重试。

## 素材与媒体能力

素材上传优先使用上面的 v2 接口，原有接口为兼容保留；每次素材变化后重新读取 revision 并计划。

上传 `POST /api/v2/projects/{pid}/assets`：
`{"type":"image","name":"角色.png","character":"hero","data":"纯Base64"}`。也可运行 `sdf.py asset upload --project PID --file 文件 --kind image --character hero`。场景／道具图片不传人物标记。上传返回 id 后才写入 bindings；上传不等于绑定。

图片 PNG/JPEG/WebP；视频 MP4/WebM/MOV、2～15 秒，入库规范到 24fps；音频 WAV/MP3/FLAC/M4A/OGG、最长 15 秒。单文件上限 8,000,000 字节。数据不用 data URI，不把文件路径、URL 或模板占位符当素材 ID。

| 输入 | bindings |
| --- | --- |
| 无参考文字 | `{}` |
| 首帧／尾帧 | `{"first_frame":"实际ID"}`／`{"last_frame":"实际ID"}` |
| 首尾帧 | 两个对应单值槽 |
| 多模态参考 | `{"images":["实际ID"],"videos":[],"audios":[]}` |
| 高级媒体 | source_audio/source_video/guide_image 各为单值真实 ID，见 [高级 H3](h3-advanced.md) |

`GET /api/projects/{pid}/quality` 返回媒体报告、后期就绪情况与版本。`POST /api/projects/{pid}/finishing-settings` 仅保存后期设置；`POST /api/projects/{pid}/edits/{edit_id}/rebuild` 按真实版本重建。原片、字幕版与 SRT 分别在 `/media/{pid}/成片.mp4`、`成片_字幕版.mp4`、`字幕.srt`，必须先确认对应文件存在。详见 [交付检查](delivery-checks.md)。

迁移用 `POST /api/export`，请求 `{"projects":["实际项目ID"],"include_videos":true}`，下载返回的 URL。导入 `POST /api/import` 是 multipart 的 zip 文件（file 字段），不是 JSON。项目包不包含模型权重和认证；冲突按导入返回 ID 映射核对。

## Legacy 行为须明确区分

这些路径为旧客户端保留；新制作默认走上面的 agent 接口。

| 旧接口 | 实际行为 |
| --- | --- |
| POST `/api/projects` | 省略 start 默认立即排队，旧模板必须保留 start:false |
| POST `/api/projects/{pid}/stage/render` | 可补大纲／分镜／提示词，与严格 render 不同 |
| POST `/api/projects/{pid}/stage/prompt` | 默认强制清除手写标记并调用文字模型 |
| POST `/api/projects/{pid}/shots/{uid}/regenerate` | kind=video 会改种子并排队整个项目 render，不能宣称只生成该镜 |
| POST `/api/resume` | 新排队整个项目 all，不等于原任务 ID resume |
| POST `/api/environment/verify` | 创建测试项目并实际 GPU 渲染 |
| POST `/api/series/{sid}/plan`、`/batch` | 整剧文字规划／分集批次，可能调用文字和 GPU；仅在用户确实需要多集时使用 |

旧接口超时没有 agent 请求键保障；先查已有项目、精确任务与原引擎提交，不盲目重发。旧系列可以按其返回的各集 project_id 转入版本化项目计划；不能把整剧规划结束当作所有视频完成。

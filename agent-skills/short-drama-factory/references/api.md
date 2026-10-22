# API 操作表（3.6.6）

基址默认 `http://127.0.0.1:8765`，不是 ComfyUI 的 8188。工作台校验 Host 与浏览器 Origin；本地脚本不需要伪造 Origin。下列路径由 `app/api.py` 核对，升级后先比对本机 `/openapi.json` 与实际返回；多数请求体是普通 dict，OpenAPI 不会列出所有字段。

CLI：`python scripts/factory_api.py post 路径 --json 请求文件.json`；没有 `--json` 时发送 `{}`。GET 使用 `get 路径`。请求文件是纯 JSON；`--json -` 可从标准输入读取。所有异步请求返回任务 ID 后都需要跟踪。

诊断：`python scripts/factory_api.py diagnose --project PROJECT_ID`。仅 GET 项目、队列和 preflight，输出显式素材身份冲突及历史采样耗时；退出码 0 表示读取完成，不表示项目通过全部预检。发现的问题放在 issues 和 preflight，脚本不会修改或停止任务。

## 核心接口

| 方法／路径 | 请求体或含义 |
| --- | --- |
| GET `/api/health` | 程序版本、应用根目录、当前项目、ComfyUI 连通性 |
| GET `/api/config` | 公开配置、`providers`、`profiles`、凭证是否配置；不返回 key |
| GET `/api/video/workflows` | 当前视频方案、模式、必需槽位、用途与限制；见 [选择指南](workflow-selection.md) |
| GET `/api/video/workflows/progress?job_id=ID` | 精确跟踪准备任务；刷新后恢复排队／运行／暂停／错误／完成状态 |
| GET `/api/skills`、`/api/presets` | 实际可用 Skill 和选项预设 |
| GET `/api/environment/catalog` | 模型列表、缺失节点／模型、缓存协议 |
| GET `/api/environment` | GPU、显存、磁盘和安装状态；不启动生成 |
| GET `/api/environment/progress?job_id=ID` | 跟踪环境准备任务；准备用 POST `/api/environment/prepare` 或 `/install`，停止用 `/stop`，校验用 `/verify` |
| POST `/api/duration-plan` | 完整或部分 Options 对象，**没有 options 包装层**；只计算时长 |
| GET `/api/projects` | 项目列表，用真实 ID 选择已有项目 |
| POST `/api/projects` | `{"input":"故事正文","options":{...},"start":false}`；外部 AI 分镜加 `"storyboard":{...}` |
| GET `/api/project/{id}` | 注意是单数 project；返回 `story`、`settings`、`state`、`busy`、`final` 等 |
| POST `/api/projects/{id}/settings` | **完整** Options 对象；读取 settings 后修改再保存，省略字段会回默认值 |
| POST `/api/projects/{id}/outline` | `{"title":"...","premise":"...","beats":[{"event":"..."}],"ending":"..."}`；改大纲会使旧分镜失效 |
| POST `/api/projects/{id}/validate-story` | `{"story":完整分镜对象}`；只检查结构、角色及首帧关系并返回规范化结果 |
| POST `/api/story` | `{"id":"项目ID","story":完整分镜对象}`；保存并记录版本 |
| POST `/api/projects/{id}/stage/{stage}` | stage 为 `outline/storyboard/prompt/plan/render/all`，通常 `{}`；返回 `job_id` |
| GET `/api/projects/{id}/preflight` | 对白／身份预算，查看 `ready` 和各项 `severity` |
| GET `/api/jobs` | 最近 100 条任务（数组），按 `id` 和 `project_id` 过滤；没有 GET `/api/jobs/{id}` |
| GET `/api/projects/{id}/quality` | `preflight`、`report`、`finishing`、`versions`、`current_edit` |
| GET `/api/projects/{id}/records` | 请求记录索引、渲染快照和媒体验收 |
| GET `/api/projects/{id}/requests/{name}` | 按 records 返回的文件名读取诊断，避免转贴私人剧本 |
| POST `/api/resume` | `{"id":"项目ID"}`；按 all 继续，遵循项目的审核模式 |
| POST `/api/stop` | `{"id":"项目ID","immediate":false}`；默认在当前镜头完成后停，true 仅中断已确认属于该项目的 ComfyUI 任务 |

`stage/outline`、`stage/storyboard`、`stage/prompt` 默认 `force:true`，可能重写已有内容；仅补缺用 `{"force":false}`，常规继续用 `plan`／`render`／`resume`。`stage/render` 会自动补齐缺失的大纲／分镜／提示词，且不在文字审核检查点暂停。需要审核时先 plan，别直接 render。

`stage/all` 或 `stage/plan` 可用 `{"execution_mode":"auto"}` 仅覆盖该次任务的审核策略；不要在用户要求审核时这样跳过。`{"limit":1}` 仅对 all/render 有效，表示新生成数量上限，不能当作指定第 1 镜。

## 素材与单镜

3.6.6 起，逐句画外音使用 `dialogue` 条目的 `narration:true`，同时将项目 `options.narration` 设为 `true`。`speaker` 保留真实说话人，画外音角色不必列入本镜可见 `characters`；普通对白不设置此标记。可视化对白编辑器以 `[旁白] 人物名：台词` 表达同一字段。

修改场景名称时同步更新 `scene_id`（无法确定则清空），随后重新检查首帧接续。修改被镜头引用的场景／道具定义或旁白声线会使原片失效；锁定镜头应先解锁，不能仅通过后期合成冒充已经更新的画面或声音。

上传不等于绑定。CLI 上传后读取返回 `id`，填进对应镜头的 `bindings`，再保存完整 story：

```powershell
python scripts/factory_api.py asset --project PROJECT_ID --file 角色.png --kind image --character hero
```

接口 `POST /api/projects/{id}/assets` 的 JSON 为 `{"type":"image","name":"角色.png","character":"hero","data":"纯Base64"}`。不用 data URI 前缀。图片为 PNG/JPEG/WebP；参考视频 MP4/WebM/MOV、2～15 秒；音频 WAV/MP3/FLAC/M4A/OGG、最长 15 秒。单文件上限 8,000,000 字节；视频入库时转换为 24fps。

| 模式 | `bindings` 示例 |
| --- | --- |
| T2VA | `{}` |
| I2VA | `{"first_frame":"真实图片ID"}` |
| L2VA | `{"last_frame":"真实图片ID"}` |
| FL2VA | `{"first_frame":"图片ID1","last_frame":"图片ID2"}` |
| Ref2VA | `{"images":["图片ID"],"videos":[],"audios":["音频ID"]}` |

普通角色参考图属于 Ref2VA，不等于 I2VA 首帧。使用角色关联上传的图，即使 bindings 为空也可能自动匹配该角色；明确选择正确 mode 并核对最终绑定。

`POST /api/projects/{id}/shots/{uid}/regenerate`：

- `{"kind":"prompt"}`：仅对指定 UID 强制重写提示词，会调用文字模型。
- `{"kind":"video"}`：给该镜换随机种子，再排队整个项目的 render。其他失效／未完成镜头及首帧依赖链也可能生成，不能承诺只消耗一镜 GPU。

锁定镜头需按用户意图解锁后才能改内容或重生成。保留 UID，数组重排时不要自行重造所有 UID。只需改字幕／剪辑时优先后期，避免重生成原片。

验看完成镜头后，可 `POST /api/projects/{id}/shots/{uid}/template`，请求 `{"name":"已验收对白镜"}`，保存样板。目标镜头的 `prompt_template_id` 指向返回的样板 ID，并通过 `/api/story` 保存。实际模式、出场角色和参考契约须匹配；见 [实战制作](production-practice.md)。

## 后期与交付

原镜头全部可用后，`quality.finishing.ready` 可用于判断是否能后期；它不证明创作品质合格。

`POST /api/projects/{id}/finish` 示例：

```json
{"edit_preset":"gentle","review_interval":0.75,"notes":[],"masks":[]}
```

`edit_preset` 支持 original/gentle/compact；该接口是 CPU 后期任务，不重生成原镜头。notes 元素为 `{"start":0.0,"end":1.5,"text":"文字"}`，时间不能重叠。高级遮罩按本机 `app/finishing_settings.py`、`app/masking.py` 或 UI 获取结构，不猜字段。

同一请求体也可发到 `/finishing-settings` 只保存、不执行。`POST /api/projects/{id}/edits/{edit_id}/rebuild` 无请求体，按 quality 返回的真实版本 ID 重建。后期仍需监控任务、检查当前版本和成片。

- 原版：`/media/{id}/成片.mp4`。
- 字幕版：`/media/{id}/成片_字幕版.mp4`，仅 `subtitled:true` 时提供。
- 字幕：`/media/{id}/字幕.srt`，先确认存在。
- 可用 `download` 保存；CLI 流式处理、输出 SHA-256，拒绝覆盖已有文件。输出存在时换文件名。
- 项目迁移：`POST /api/export`，`{"projects":["项目ID"],"include_videos":true}`，返回 `url` 和 `size`。用 `download 返回的url --output 项目.zip`。执行前先确保目标项目空闲。
- 反向导入：`POST /api/import`，请求体是 multipart 的**导出 zip 文件本身**（字段名 `file`），不是 JSON 摘要。导入会在当前任务空闲时把项目与 Skill 并回本机；冲突时按返回的 `projects`／`skills` 分别核对，不要假设原项目 ID 不变。
- 3.6.6 起迁移包携带项目和个人预设引用的视频质量／工作流方案；目标目录同名方案参数不同会另存并映射 `profile`。模型文件、环境路径和认证信息仍需在目标环境配置。
- 已命名导出物可用 GET `/api/exports/{name}` 读取，`name` 来自导出响应，不接受自行拼造的路径。
- HTTP 媒体链接需要应用运行；用户要离线文件时下载，并返回实际绝对路径。不要把本机链接称为公开链接。

## 多集（用户确实需要时）

`POST /api/series`：

```json
{"title":"雨巷故事","input":"整剧故事正文","mode":"auto","episode_count":3,"start":"draft","fail_policy":"continue","options":{"execution_mode":"auto","total_seconds":24,"duration_rule":"count","shot_count":6,"profile":"draft"}}
```

响应 `id` 为剧集 ID，`job_ids` 为数组。`GET /api/series/{id}` 读分集和各自 `project_id`。`POST /api/series/{id}/plan`，`{"start":"plan"}` 规划文字（不渲染）；完成后 `/batch` 用 `{"kind":"all","numbers":[1,2,3]}` 排队指定分集（numbers 是集号）。`/stop` 停本剧批次。`fail_policy` 支持 continue/stop；按每集的项目 ID 与任务 ID 追踪，不把整剧规划结束当作所有视频完成。

# 本地连接、CLI 与提交回执

入口 `scripts/sdf.py` 只依赖 Python 3.10+ 标准库。以下从技能目录执行；其他目录使用该脚本绝对路径。可直接读取 `--help` 和子命令 `--help`，不需要先读 Python 实现。

全局参数 `--base-url`、`--timeout`、`--context` 放在子命令前。`--context` 默认当前工作目录 `.sdf/connection.json`；把同一制作工作放在固定目录可让新聊天恢复连接和请求记录。

## 连接与启动

```powershell
python scripts/sdf.py --base-url http://127.0.0.1:8765 connect --app "E:/实际应用目录"
python scripts/sdf.py doctor
python scripts/sdf.py capabilities
```

connect 绑定已运行实例并核对目录和协议，不靠“第一个可用端口”猜应用。未运行时：

```powershell
python scripts/sdf.py start --app "E:/实际应用目录" --port 8765
```

start 使用应用解释器和 launcher 的 serve-only 模式启动新服务，不恢复旧队列、不打开浏览器；后续明确执行的任务获得运行授权，旧任务保持原状态。已有服务会直接复用，不改变其运行方式或取消任务，须查看健康返回的 queue_mode。直接启动新服务也可 `python launcher/start.py --serve-only --port 8765`。

doctor 只读检查，不做文字生成、GPU 推理或下载。doctor 未通过也可以继续编写／保存分镜；特定模式是否能执行看对应项目计划。

## 项目与镜头

```powershell
python scripts/sdf.py project list
python scripts/sdf.py project get PROJECT_ID
python scripts/sdf.py project create --json project-request.json
python scripts/sdf.py project update PROJECT_ID --json changes.json --expected-revision REVISION
python scripts/sdf.py shot update PROJECT_ID SHOT_UID --json shot-changes.json --expected-revision REVISION
python scripts/sdf.py project validate PROJECT_ID
python scripts/sdf.py project plan PROJECT_ID
python scripts/sdf.py project plan PROJECT_ID --uids SHOT_UID
python scripts/sdf.py project run PROJECT_ID --plan PLAN_ID --wait 45
```

project update 的文件是 settings／story／shots 中一种资源包装；shot update 的文件是该镜头 changes 对象。CLI 未显式收到 revision 时会读取当前值，服务端仍做并发冲突检查；对于已在本地编辑的旧草稿，应传当时读取的 revision。

需要程序处理 H3 标题顺序、对齐时间和关键帧第一行时，可先执行：

```powershell
python scripts/sdf.py prompt compile --project PROJECT_ID --shot SHOT_UID --json sections.json
```

sections.json 是当前 AI 编写的段落名→正文对象，不再包一层 sections；三段／六段字段见 [H3 契约](story-and-h3.md)。命令只校验并返回 prompt、mode、reference_labels、aligned_seconds 与 revision，不调用模型、不保存、不排队。检查结果后将 prompt 放入 shot update 的 changes 对象，使用返回 revision 保存。

默认计划 action=render、internal_text=forbid。内部文字创作明确选择 `--action plan --allow-internal-text`；仅后期选择 `--action finish`。`--json` 可传完整计划请求，其字段见 [API](api.md)。

`shot regenerate PROJECT_ID SHOT_UID` 先计划并执行受影响范围；不是旧接口的整个项目隐式 render。需要改变随机结果时可按需求指定 `--seed`，查看输出的新计划与依赖范围。`--wait 45` 有界等待，不表示必须在 45 秒内生成完。

高层 `produce --json project-request.json --wait 45` 可完成创建、计划与提交。只有完整外部分镜、环境已就绪且用户已授权生成时使用；明确需要审阅计划时分开调用 create／plan／run。任何一步阻塞都保留已创建项目，不重建绕过问题。

旧 project-storyboard/project-outline 模板包含 start:false；CLI 兼容该安全草稿写法，拒绝 start:true。直接使用 v2 API 时用不含 start 的 agent-* 模板。

## 观察、停止与恢复

```powershell
python scripts/sdf.py job get JOB_ID
python scripts/sdf.py job list --project PROJECT_ID
python scripts/sdf.py job watch JOB_ID --seconds 45
python scripts/sdf.py job events JOB_ID --after 0
python scripts/sdf.py job resume JOB_ID
python scripts/sdf.py job stop JOB_ID
python scripts/sdf.py operation get REQUEST_KEY
python scripts/sdf.py operation retry REQUEST_KEY
```

`job stop --immediate` 还请求中断该任务拥有的引擎计算；不清空其他任务队列。resume 保持任务 ID，不能越过过期项目／资源证据。`PLAN_STALE` 时在原项目重新计划。

写命令先输出 `request_saved` JSON 事件，再输出结果；一条命令可能有多行 JSON，逐行读取，不能把整段输出当成一个 JSON 对象。回执在 context 同目录的 requests 中，记住 request_key 和 receipt。需要自己固定键时使用命令的 `--request-key`。同一键只能重放同一请求；改内容用新键。

响应丢失不等于失败：先 operation get，必要时 operation retry 按原内容补交。`--wait`／watch 到期仍在运行返回退出码 3；观察同一个 job。不要因非零退出码统一重试写操作。具体错误 JSON 包含 code、retryable 和 next_actions。

operation retry 依赖原本地请求账本，不是只凭键就能重建任意请求。账本丢失但服务端 completed 时，operation get 可取回原结果；服务端仍 pending 或返回 404 且原请求正文也缺失时，先从保存的请求文件／计划恢复**完全一致**的 JSON，不能依据当前项目猜原正文。无法恢复时说明缺少原请求数据；保留原项目与请求键，取得原请求后再补交。

## 无界面配置与安装

```powershell
python scripts/sdf.py config get
python scripts/sdf.py config patch --json config-changes.json
python scripts/sdf.py credential set --provider deepseek --env DEEPSEEK_API_KEY
python scripts/sdf.py environment speech-plan
python scripts/sdf.py environment speech-prepare --confirmation TOKEN
```

`--env` 只传环境变量名；也可用 `--stdin` 从用户受控标准输入读取凭证，不把明文放命令参数／请求 JSON。凭证命令不保存密钥到请求账本；结果未知时查询配置状态，不盲目重发。配置变化后重新计划原项目。

config get 返回 revision/config 包装；config patch 的文件是局部配置对象，CLI 读取当前 revision 后发送窄范围 PATCH。speech-plan 只读检查，speech-prepare 是显式下载 CPU 后期模型的任务；核对计划与已有下载授权后再传 confirmation_token。

图片与素材也有任务级入口：

```powershell
python scripts/sdf.py image create --json image-request.json --wait 45
python scripts/sdf.py image input --file 参考图.png
python scripts/sdf.py image get IMAGE_ID
python scripts/sdf.py asset upload --project PROJECT_ID --file 角色.png --kind image --character hero
```

image create 默认 optimize=false、internal_text=forbid；只有用户选内部文字优化时才同时设置请求 optimize=true 与 --allow-internal-text。这些创建／上传使用 v2 提交回执；旧图片的 generate/regenerate 等管理操作见 [图片接口](images.md)。

独立安装或更新整个技能包：

```powershell
python scripts/install_skill.py --source "源技能目录" --target "目标技能目录"
python scripts/install_skill.py --source "源技能目录" --target "目标技能目录" --update
```

source 指包含 SKILL.md 的目录，target 指最终 short-drama-factory 目录，不是其父目录。Codex 通常为用户的 `.codex/skills/short-drama-factory`；其他 AI 使用其自身技能发现目录。安装器检查 contract_version=1；更新保存备份、保留个人文件，遇到已修改的受管理文件先合并，不强行覆盖。`--zip` 可按安装器帮助打包分发，包不含本机连接、项目和凭证。

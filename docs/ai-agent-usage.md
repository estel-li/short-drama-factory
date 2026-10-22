# 从 Codex 或其他 AI 接入短剧工厂

日常入口是外部操作技能，创作和控制可以在 AI 对话中完成。当前 AI 编写分镜和提示词，CLI／API 提交可核对的执行计划，工厂生成视频；图形工作台保留预览、审片与编辑功能。

## 安装技能

需要能运行 Python 3.10+ 或访问本机 HTTP 的本地 AI 执行器。技能客户端仅依赖 Python 标准库；应用自身仍需完整运行环境。把整个 `agent-skills/short-drama-factory` 作为独立包安装，不要只复制 SKILL.md：

```powershell
python "应用目录/agent-skills/short-drama-factory/scripts/install_skill.py" --source "应用目录/agent-skills/short-drama-factory" --target "用户技能目录/short-drama-factory"
```

Codex 的目标通常是用户目录下 `.codex/skills/short-drama-factory`。Claude、Gemini 或其他 AI 使用各自技能发现机制；也可让本地助手直接读取包内 SKILL.md。项目内的 AGENTS.md／CLAUDE.md／GEMINI.md 指向同一操作规则。

升级使用同一命令加 `--update`。安装器跟踪包文件、备份旧版并保留个人文件；本地改过的受管理文件需要先合并。不要把本机 .sdf、凭证或项目文件打进公共技能包。

## 绑定实例

在固定制作工作目录中，用安装后的脚本绝对路径运行：

```powershell
python "技能目录/scripts/sdf.py" start --app "应用绝对目录" --port 8765
python "技能目录/scripts/sdf.py" --base-url http://127.0.0.1:8765 connect --app "应用绝对目录"
python "技能目录/scripts/sdf.py" doctor
```

已有服务时直接 connect。start 新建服务使用 serve-only，不打开浏览器、不恢复旧任务；明确提交或恢复的任务才进入执行。复用已有服务不改变其运行方式，需核对 queue_mode，不能假定旧任务已暂停。连接记录保存在当前工作目录 `.sdf/connection.json`，换聊天可复用，换工作目录可用全局 --context 指定原文件。

健康接口必须返回目标 application_root 与支持的 protocol_version。3.8.0 起提供 agent 协议 1 的版本化项目、计划与提交回执；3.9.0 的技能提供任务级命令。应用版本升级不等于协议变化，具体功能查 capabilities。

127.0.0.1 只指向执行命令的机器。只有云端聊天能力时需要本机执行器；不能公开现有本机端口来冒充具备远程认证的服务。

## 一次典型制作

让助手读取技能，给出故事、风格、画幅、需要保留的台词／原声及已有素材。它会创建草稿，校验并展示本次影响范围，执行计划，跟踪原任务，最后返回实际产物与验收说明。已授权自动制作时可连续执行，不需逐步重复确认。

可直接使用 `agent-storyboard.json` 的结构创作，不需要另配文字服务。若用户主动选择内部模型编写，再配置 provider 并创建允许内部文字的 plan。密钥通过 `credential set --env 环境变量名` 或受控 --stdin 输入，不放进聊天或 JSON 请求。

修改只按目标 UID 进行，服务端检查 revision 防止覆盖他人更新。新计划列出接续／参考依赖，不承诺单镜修改永远只消耗一镜。局部完成不会自动标为整片交付；完整后期另有明确计划。

## 中断后继续

保存项目 ID、任务 ID 和 CLI 的 request_key／receipt。断线先 `operation get`，必要时 `operation retry` 使用原内容和同一键；任务存在就 `job watch`。资源与输入未变时可以 resume 同一任务；PLAN_STALE 时在原项目新建计划，保留已完成素材。

模型和 CPU 后期资源准备是独立动作，严格渲染不隐式下载。生成完成、媒体解码通过、台词内容正确是不同证据；没有看图或听音就应明确相关内容尚未验收。

详细命令、模板、输入约束和恢复规则统一维护在 [操作技能](../agent-skills/short-drama-factory/SKILL.md)。

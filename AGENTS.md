# 短剧工厂：AI 操作入口

本仓库面向通过 Codex 或其他本地 AI 使用 Skill、CLI、API 制作视频。使用应用生成图片、管理参考图、制作／修复／续跑／交付视频时，先读取唯一操作入口：

**[short-drama-factory/SKILL.md](agent-skills/short-drama-factory/SKILL.md)**

默认由当前 AI 编写分镜与 H3 提示词，使用 `scripts/sdf.py` 连接指定实例并创建严格执行计划。接口 agent 协议为 1；核对 health.application_root 与 capabilities，不将发布源码目录误当正在运行的实例。图形工作台用于可选预览和编辑，不是必需步骤。

- 首次接入／安装：[AI 接入说明](docs/ai-agent-usage.md)。
- CLAUDE.md、GEMINI.md 只指向本入口，不维护另一套操作流程。
- 根目录 `skills/` 是工厂内部文字生成模板；外部操作技能位于 `agent-skills/`，不能混装。

如果用户要求开发、审查或修复应用代码，按代码任务处理；不因此启动生成、调用收费 API、下载模型或修改用户项目。认证保留在用户配置的本地凭证机制中，不写入仓库、聊天或日志。

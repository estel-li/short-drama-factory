# AI 操作入口 · Start here

使用本项目生成、续跑、修复或导出视频时，先读取：

**[短剧工厂操作技能 → agent-skills/short-drama-factory/SKILL.md](agent-skills/short-drama-factory/SKILL.md)**

该技能包含中文流程、HTTP 客户端、创作模板、素材诊断和成片验收方法；详细资料按其中链接按需读取。适用于有本地命令或 HTTP 能力的 AI，不依赖特定助手。

## 从这里开始

1. 确认用户的故事、目标项目和制作要求，按技能选择“工厂调用文字模型”或“外部 AI 提供完整分镜”。
2. 已有服务先读取 `http://127.0.0.1:8765/api/health`，核对 `application_root` 和版本，复用正确实例。端口可以按用户配置改变。
3. 在项目根目录可运行 `python agent-skills/short-drama-factory/scripts/factory_api.py get /api/health`；也可用应用的 `runtime/python.exe` 或 `.venv/Scripts/python.exe` 替换 python。
4. 使用技能里的接口保存和排队；保留项目 ID、任务 ID、镜头 UID。超时先查原任务，避免重复提交。

完整操作说明只有上述技能一份。本目录的 `skills/` 是应用内部的大纲／分镜／H3 提示词模板，与外部操作技能用途不同。

如果用户要求开发、审查或修复应用代码，按代码任务处理；不因此启动生成、调用收费 API、下载模型或修改用户项目。认证保留在用户配置的本地凭证机制中，不写入仓库或日志。

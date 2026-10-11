# 贡献指南

## 提交问题

提供应用版本、操作系统、GPU/显存、ComfyUI 版本、生成模式、可复现步骤及脱敏日志。尽量使用小型自编示例，避免上传他人的剧本、素材、认证信息或完整私人项目。

## 本地开发

使用 Python 3.13 创建 `.venv`，安装 `requirements.lock.txt`，运行 `launcher/serve.py` 或 `launch.ps1`。前端位于 `web/`，使用 ES 模块，无需构建。

提交前执行：

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py"
```

默认测试无需 GPU 和真实文字模型。`tests/live_*.py` 与验收脚本属于可选真实环境验证，会消耗 API 或 GPU 资源，运行前阅读脚本说明。

## Pull Request

描述具体问题、修改后的行为、验证方法和限制。修改缓存、模式或项目格式时应包含兼容性证据。避免改变未启用新功能的项目行为，避免把安装目录、私人配置和模型写进代码。

不提交 `.secrets/`、`.env`、私人项目、视频、数据库、日志、虚拟环境、大模型或构建包。新增第三方内容时附上来源、版本和许可；内置 Skill 上游原文与本地适配层分别维护。

提交贡献表示你有权以本项目 MIT 协议授权该部分代码；第三方材料保持其原许可。

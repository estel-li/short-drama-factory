# 工作台源码来源

本目录从独立工作台仓库导入，供短剧工厂在一个 Git 仓库内交付与测试。Python 生产后端仍位于仓库根目录；工作台通过 HTTP API 连接后端。

- 上游项目：<https://github.com/HBAI-Ltd/Toonflow-app>
- 上游基线：`6086cdffceb704a632eca143dd16cd461a78cdac`
- 短剧工厂工作台导入提交：`35450aac142d1424f57a6751ef3f168c3046bb2c`
- 导入方式：复制该提交的完整 Git 跟踪源码树；不包含独立仓库的 `.git`、构建产物、运行数据、凭据、模型或个人项目。
- 上游 MIT 许可保留在本目录 `LICENSE`；随包第三方插件的来源与摘要保留在 `packages/bundledPlugins/manifest.json`。

此后从短剧工厂仓库的 `workbench/` 目录维护代码。Windows 启动方式和当前已知问题见上一级仓库的 `docs/windowsWorkbench.md`。

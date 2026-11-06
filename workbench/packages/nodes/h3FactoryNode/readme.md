# 本地 H3 工厂节点

在 短剧工厂 画布中操作短剧工厂的本地 MiniMax H3 后端。项目节点保存完整分镜、展开镜头画布、提交整片计划和检查交付；镜头节点编辑单镜、提交局部计划，并观察或续跑原任务。按钮与 Agent 节点工具共用实现。

生成始终使用工厂 agent 协议 1 的严格执行计划。H3 模型、ComfyUI、GPU 队列、首帧依赖、阶段缓存和后期仍由工厂管理。插件不下载模型，不调用内部文字服务。

## 启动

需要 Bun 1.4.3、短剧工厂 源码，以及已安装和配置好的短剧工厂。首次准备 短剧工厂：

工厂端还需包含配套的后期状态修复：`app/jobs.py` 在当前整片 `finish` 成功后清除旧的 `scope_complete`、待验证镜头等局部范围标记。原始 4.2.0 会在“局部重生成 → 整片后期”后残留这些标记，造成视频有效但交付被拒绝。应合入代码修复并重新执行 CPU 后期，不能直接修改项目状态文件绕过交付检查。

```sh
bun install
bun apps/desktop/node_modules/electrobun/bin/electrobun.cjs prepare
bun run --cwd packages/nodes/h3FactoryNode build
bun run --cwd packages/tools/canvas build
bun run --cwd apps/server routes
```

在服务端启动环境中指定实际工厂地址和运行目录。下面是 macOS/Linux shell 示例；目录必须与 `/api/health` 返回的 `application_root` 一致。

```sh
export SDF_BASE_URL=http://127.0.0.1:8765
export SDF_APPLICATION_ROOT=/absolute/path/to/short-drama-factory
export TOONFLOW_DATA_DIR=/absolute/path/to/toonflowData
export TOONFLOW_SERVER_HOST=127.0.0.1
bun run dev:server
```

另一个终端运行 `bun run dev:web`，打开输出的本机地址。初次启动会从 `build/nodes` 与 `build/tools` 安装插件；已经初始化的数据目录需安装本次重新构建的节点，或在停止界面后将新产物复制到该数据目录的 `nodes/h3FactoryNode.umd.js`，再刷新页面。

工厂若位于另一台 Windows GPU 主机，通过已有 SSH 连接转发本机端口：

```sh
ssh -N -L 127.0.0.1:18765:127.0.0.1:8765 gpu-host
```

此时 `SDF_BASE_URL=http://127.0.0.1:18765`，`SDF_APPLICATION_ROOT` 填 Windows 工厂的实际路径。工厂和 ComfyUI 保持回环监听。插件只接受回环工厂地址；Toonflow 桥接接口也仅接受本机工作区请求。

## 从三镜头开始

1. 新建 短剧工厂 工作区，在“添加节点”中选择“本地 H3 工厂”。
2. 输入已有工厂项目 ID，或导入包含 `input/options/storyboard` 的完整请求 JSON。请求格式沿用工厂 `agent-skills/short-drama-factory/assets` 内的模板，所有镜头须有外部编写的 H3 提示词。
3. 点击“展开镜头画布”。每镜使用稳定 UID；重复展开复用已有节点。同场景的末帧接续镜头会连到紧邻前镜。
4. 在镜头节点编辑并保存。修改动作、台词或时长时同步修改完整提示词；“重新读取”会以已保存的分镜替换当前编辑框。
5. 点击“计划此镜”或项目节点的“计划整片”，查看 `blocked`、`affected_uids`、缓存候选和实际影响范围，再执行可用计划。计划不会自行开始推理。
6. 原任务暂停或失败时先检查进度与消息。输入不变时“续跑原任务”；计划过期时重新计划。关闭画布只停止观察，不取消工厂任务。
7. 镜头完成后“读取镜头结果”。项目整体完成后“校验并取回成片”；局部生成不等于整片交付，必要时先执行项目节点的“计划成片后期”。

前镜修改可能扩大后续接续镜头的生成范围，最终以工厂计划为准。连线表示创作关系，不以浏览器回调代替工厂的 GPU 调度。接续输入须来自同一项目紧邻前镜；实际条件帧由工厂解码前镜真实末帧得到。

## Agent 操作

启用 短剧工厂 MCP，或使用已配置的内置 Agent。外部 AI 先通过 `getAppState` 取得页面、工作区和画布身份，再查询 `getNodeTools`；不要直接覆盖已打开的画布 JSON。

| 节点工具 | 行为 |
| --- | --- |
| `connectFactory` | 核对实例、协议、能力和引擎连通情况 |
| `createProject` / `bindProject` | 创建完整分镜草稿，或连接已有项目、镜头 |
| `expandShots` | 展开镜头节点及接续关系，不生成 |
| `getFactoryState` | 读取实时项目、revision、镜头和节点草稿 |
| `compilePrompt` | 格式化外部编写的 H3 段落，不生成文字、不保存 |
| `updateShot` | 携带最近读取的 revision 按 UID 修改，保留其他镜头 |
| `planGeneration` / `runPlan` | 查看严格执行计划，再以原 plan ID 提交 |
| `getJobStatus` | 查询持久任务及事件 |
| `stopJob` / `resumeJob` | 停止或续跑此节点持有的原任务 |
| `getSubmissionHistory` / `retrySubmission` | 读取持久回执，以原请求键复查或补交 |
| `collectResult` | 校验并导入镜头原片或当前成片 |

提交工具必须提供唯一 `requestKey`。响应不明时保留它，用 `getSubmissionHistory` 和 `retrySubmission` 查询原操作，不改键重新生成。`updateShot` 的 `expectedRevision` 防止覆盖并发修改；冲突后读取最新项目并合并。

## 保存与恢复

- 画布保存项目 ID、镜头 UID、计划、任务 ID 和编辑草稿。
- 工作区 `.h3Factory/operations` 在提交前原子保存请求，完成后记录回执。工厂继续使用自己的幂等记录；不会另建 GPU 队列。
- `.h3Factory/connection.json` 绑定实际工厂实例。切换到其他 GPU 工厂时使用新工作区，避免旧镜头 ID 指向错误实例。
- 结果复制到 `assets/h3Factory/<projectId>/<sha256>.<扩展名>`，下载核对大小与 SHA256，不覆盖旧版本。删除画布节点不删除工厂项目或原片。
- 项目交付检查保存到 `deliveries/h3Factory/<projectId>/<fingerprint>/delivery.json`，并作为文件输出。检查失败的清单也会保留，便于定位问题。

单产物导入上限为 512 MiB。更大成片通过工厂交付 CLI 取片。完整解码、版本与哈希检查属于技术完整性；画面连续性、动作、声音和字幕内容仍需实际审片。

## 开发验证

```sh
bun run --cwd packages/nodes/h3FactoryNode typecheck
bun run --cwd packages/nodes/h3FactoryNode build
bun run --cwd apps/server routes
bun run --cwd apps/server typecheck
bun run --cwd apps/server build
bun run --cwd apps/web typecheck
```

真实验收需在已连接 GPU 的实例上完成三镜生成、第二镜真实末帧接续、第三镜 Agent 修改、原任务恢复、有效缓存复用与整片交付。没有 H3 引擎时只能验证创作和接口链路，不能据此报告生成通过。

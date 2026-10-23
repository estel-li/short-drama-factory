# 诊断、响应丢失与跨聊天续跑

先恢复同一个实例、项目、任务和提交回执，不凭上次聊天结论猜当前状态。CLI 的观察超时不取消任务；采样阶段一段时间没有 MP4 也不等于停止。

## 找回工作

在原工作目录运行 `sdf project list`、`project get PID`、`job get JID`；换目录用 `--context` 指向原 `.sdf/connection.json`。CLI 的本地请求记录在同目录 requests 中，包含精确 method/path/body、请求键与实例地址。不要把凭证混入请求文件。

写请求结果未知时：

1. 保存 `request_saved` 输出的请求键与回执路径。
2. `sdf operation get KEY` 查询服务端原提交。
3. 需要补交时 `sdf operation retry KEY` 按已保存内容、同一键提交；不要另造新键重做同一操作。
4. 若实例不匹配或本地回执缺失，先核对原实例和服务端记录。不能通过“任务不在最近列表”推断没有提交。

本地账本丢失时，operation get 仍可读取服务端 completed 的结果；但 pending／404 不包含足以重新提交的完整原请求。operation retry 需要本地原 method/path/body。只有能从保存的请求文件或计划恢复完全一致的正文时才使用原键补交，不能用当前已变化的项目内容重造原请求。无法恢复时保留现有状态并明确缺少原请求数据，不承诺“一把键”无条件恢复。

job 已存在时跟踪这个 job_id：`job watch JID --seconds 45`、`job events JID --after CURSOR`。退出码 3 表示仍在运行，下一轮观察原任务。

## 服务异常退出后的状态

4.0 的 serve-only 启动会检查操作系统的独占 worker 锁；只有确认旧执行者已经退出，才把遗留的 running 任务转为 paused，并保存状态事件。这个处理不启动生成线程、不领取旧 queued 任务，也不打断仍持有锁的活跃 worker。不能仅凭数据库显示 running、日志不动或观察超时自行认定执行者已消失。

重新连接后先查看原 job 和事件，核对已保存的成果，再按授权 `job resume JID`。正常恢复沿用任务 ID，并检查冻结计划与检查点；如果硬崩溃期间产物已变化而检查点未落盘，原计划会失效。此时在同一项目重新计划，使用新请求键提交并复用已确认缓存，不承诺重启服务就会自动续完推理。

## 按错误修复

| 证据／状态 | 下一步 |
| --- | --- |
| protocol 或 application_root 不匹配 | 停止向错误实例写入，连接指定实例；安装匹配技能版本 |
| REVISION_CONFLICT | 重新读取项目，合并本次改动后以新 revision 提交 |
| PLAN_STALE | 项目、素材、模型或环境已变化；重新计划当前项目，保留已有原片 |
| EXTERNAL_CONTENT_REQUIRED | 根据 details 的 UID／字段补齐分镜和 prompt；严格 render 不会代写 |
| TEXT_GENERATION_FORBIDDEN | 由当前 AI 提供内容；只有用户选择内部创作才用允许文字调用的 plan |
| MODEL_FILES_MISSING／SPEECH_MODEL_MISSING／IMPLICIT_DOWNLOAD_FORBIDDEN | 按 [资源准备](workflow-models.md) 处理真实缺项；准备后重新计划 |
| 认证、余额或模型名称错误 | 使用本地受控 credential/config 入口修正；不输出 key、不重复收费探测 |
| 引擎不可连接 | 可继续编辑草稿；检查实例配置与引擎归属，不顺带重装或抢占端口 |
| 任务 review | 检查审核停点、message 与计划阻塞；尊重用户审核要求 |
| 任务 paused | 查看停止原因和已保存成果；输入／环境未变时 resume 同一任务 |
| 任务 done、stage=scope_complete | 选中范围完成；范围外仍待验证，没有自动整片合成 |
| 任务 done、final=false | 可能仅完成文字／镜头阶段；按用户目标计划下一步 |
| busy=true | 等待原任务；用户要修改时请求 stop 并等 queued/running 退出，再版本化保存 |
| 依赖镜头锁定 | 查看 affected_uids 和原因，只解锁完成本次目标需要的镜头 |
| 原片齐全、后期失败 | 保留原片，修复 CPU 依赖／后期配置后执行 finish，不能先重生成视频 |
| GPU 显存不足／设备离线 | 先确认原任务终态与硬件状态；修复后重新核对计划，不无限重启生成 |

`job resume JID` 继续原任务 ID。输入、模型或资源变化会让原执行证据失效；此时新建的是**同一项目的新执行计划**，不是重建项目。只修改字幕时间使用 finish；台词实际内容错误需要改 prompt 并生成受影响镜头。

旧图片／环境接口仍按 [图片说明](images.md)、[资源准备](workflow-models.md) 的原任务续跑机制处理；不要把其请求当成支持 agent 幂等头的请求。

一次修正后仍出现相同确定性错误，报告具体阻塞、已保留产物、项目／任务 ID 与下一步。只有可观察证据支持时重试；不反复创建任务、不凭静止日志杀进程。慢渲染的观察方法见 [制作与诊断](production-practice.md)。

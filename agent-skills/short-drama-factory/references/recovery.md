# 诊断与恢复

优先看原项目、原任务的当前返回，不凭上一次超时猜状态。客户端 watch 只观察，不会取消任务；长镜头生成期间消息可能长时间不变。

| 现象 | 行动 |
| --- | --- |
| 工厂不连接 | 检查用户指定目录、健康接口、端口占用。启动该目录 launcher，不能杀掉不明进程来抢端口 |
| ComfyUI=false | 文字规划可继续；渲染前确认 ComfyUI 路径、Python、服务地址、模型配置。工厂可按配置自动启动本地引擎，不必因此重装 |
| catalog 缺节点／模型 | 显示具体缺项；已有授权安装时先预览 `/api/environment/plan`，核对体积与目标目录后再安装。普通出片任务不自动下载几十 GB |
| cache_protocol 不兼容 | 2.4.1 使用缓存协议 2，核对程序随包 `nodes/ComfyUI-DramaFactory` 与运行中 ComfyUI；不能仅凭 health=true 开始大量任务 |
| 文字超时／限流 | 查原任务和 records；程序已有网络退避。确认 provider/model 和超时设置，修复后继续原项目，不无限外层重试 |
| 认证／余额／模型名错误 | 让用户在提供商设置修正；不要重复收费测试，也不要输出 key；本地模型不一定需要 key |
| JSON／schema／对白错误 | 查看具体校验位置，按 Story/H3 契约修正，保留用户台词；`preflight.ready` 仅代表静态预算通过 |
| 身份参考绑定了未出场角色 | 检查场景图是否误填 character；按 [素材修复步骤](production-practice.md) 重新上传正确标记的图并经 API 换绑。保留真实人物图身份，不添加虚构角色绕过校验 |
| 单镜很慢但没有报错 | 用 diagnose 对照同配置成功记录，结合编码／采样／解码阶段判断。没 MP4、日志不变或低功耗单独都不能判停摆，见 [性能诊断](production-practice.md) |
| POST 超时／连接断开 | 结果未知。先 GET `/api/projects`、`/api/jobs`、已知项目；对照时间与内容定位。没有证据表明未提交前不要重发 |
| job=review | 检查 `state.current_stage`、message、preflight。审核停点或预检失败，处理后继续，不是网络故障 |
| job=paused | 可能是用户停止或试镜 limit 到达。确认用户意图、已完成镜头与队列空闲，再 resume/render |
| job=done 但 final=false | 可能只是 plan 或阶段完成。检查 kind、state、缺失镜头，再按请求继续渲染 |
| job ID 不在最近 100 条 | CLI 返回 unknown。读项目 current state／job_id 和实际产物；若无法确认原任务终态，报告未知，不能直接重排 |
| GPU 显存不足／显卡掉线 | 先确认当前任务终态。检查 GPU 是否仍被系统识别、ComfyUI 是否恢复；16GB 配置优先 draft、4秒，避免并行占显存。显卡坞掉线先处理硬件连接，不能靠无穷重试恢复 |
| busy=true 无法保存 | 可能正在排队；按原任务等待。若用户要修改，调用 stop 并等 queued/running 退出后保存完整 story/settings |
| 同一 UID 锁定 | 按用户意图解锁目标镜头，保留其他锁；首帧链可能要求相邻依赖解锁 |
| 缺原片无法后期 | `quality.finishing` 提供缺失镜头；定位磁盘／迁移包是否带视频，必要时只修复受影响生成阶段 |
| 原片齐全，后期提示缺 numpy 等依赖 | 在实际应用 Python 检查安装；修复后执行 finish，保留已生成镜头。当前 requirements.lock.txt 已包含 numpy，不把旧环境问题当作所有便携版缺陷 |

一次修正后续跑仍出现相同确定性错误，就报告阻塞项、项目 ID、任务 ID、保留成果与具体下一步，不持续创建任务。客户端遇到错误会返回非零，自动化调用方不得把退出码 3（仍在运行）当作生成失败。

恢复命令使用临时 UTF-8 JSON，例如 `{"id":"项目ID"}` 后发送 `POST /api/resume`。需改变质量时，读取完整 settings，修改 profile 并保存；改变 profile 会使相关缓存失效，重渲染可能覆盖所有受影响镜头，不宣称零成本续跑。

后期能改善剪辑和字幕呈现，不能修复错误台词或角色变形。真正需要重新表演时才改提示词／种子并生成；没有听音或逐帧查看就不能宣布台词及画面验收合格。字幕时间修正和发布检查见 [成片验收](delivery-checks.md)。

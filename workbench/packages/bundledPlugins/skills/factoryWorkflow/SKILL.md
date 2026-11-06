---
name: factoryWorkflow
description: 短剧工厂画布制作流程。用 DeepSeek 编写故事与分镜，以本地 ComfyUI / MiniMax H3 制作、续跑和交付视频。
metadata:
  displayName: 短剧工厂制作流程
  version: "3.0.0"
---

# 短剧工厂制作流程

从当前项目与已确认成果继续，先查询画布、节点函数和实际技能目录。

1. 编剧与改编：按任务读取 scriptEngine、scriptStudio 或 dramaWriting，保存可审阅的剧本与分集。缺少的外部套装不假设已安装。
2. 镜头与提示词：按需读 cinematicDirector；最终 H3 提示词用 h3PromptWriting 的 T2VA / I2VA / FL2VA / L2VA / Ref2VA 规范。文本模型只用 DeepSeek。
3. 工厂连接：添加本地 H3 工厂节点，调用 getFactoryState / connectFactory，核对运行目录、协议和能力。地址在设置 → 视频模型 → H3 工厂与独立工作流连接 中配置。
4. 项目与画布：调用 createProject 或 bindProject，再 expandShots。通过真实节点工具结构编辑，不猜参数或手写画布内部状态。
5. 修改：updateShot 使用节点当前修订；局部修改只规划需要重新生成的镜头，保留其他镜头缓存。接续镜头绑定同项目直接前一镜的真实末帧。
6. 生成：planGeneration 得到具体执行范围，向用户呈现可查看的分镜、规格、提示词和次数。已获授权的范围直接调用 runPlan；不以提示词确认代替新生成范围的授权。
7. 续跑：getJobStatus 查询实际任务，stopJob 停止、resumeJob 续跑原 ID。请求结果未知时用 getSubmissionHistory / retrySubmission 复查原 requestKey，不另起重复请求。
8. 交付：单镜 collectResult 后规划 finish，完成再 collectResult 取回最终视频与校验清单。说明实际做过的视觉、解码、音频检查，未验证的部分不宣称通过。

需要导入或编辑原始 ComfyUI 工作流时使用 ComfyUI 工作流节点，连接共用设置。此节点直接提交 ComfyUI；正式生产和缓存续跑使用 H3 工厂节点。图片／换装节点使用图片模型配置中的 API 或 ComfyUI；视频节点使用视频模型配置中的 API 或 ComfyUI。未配置工作流或密钥时先完成配置，不将缺少执行条件视为生成成功。

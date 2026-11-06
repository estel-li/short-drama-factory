---
name: factoryWorkflow
description: 短剧工厂画布制作流程。用 DeepSeek 编写故事与分镜，以本地 ComfyUI / MiniMax H3 制作、续跑和交付视频。
metadata:
  displayName: 短剧工厂制作流程
  version: "3.1.0"
---

# 短剧工厂制作流程

从当前项目与已确认成果继续，先查询画布、节点函数和实际技能目录。

1. 编剧与改编：按任务读取 scriptEngine、scriptStudio 或 dramaWriting，保存可审阅的剧本与分集。缺少的外部套装不假设已安装。
2. 镜头与提示词：按需读 cinematicDirector；最终 H3 提示词用 h3PromptWriting 的 T2VA / I2VA / FL2VA / L2VA / Ref2VA 规范。文本模型只用 DeepSeek。
3. 工厂连接：添加本地 H3 工厂节点，调用 getFactoryState / connectFactory，核对运行目录、协议和能力。地址在设置 → 视频模型 → H3 工厂与独立工作流连接 中配置。
4. 项目与画布：先用 getNodeTools 读取 createProject 的完整参数。由当前 AI 将用户的一句话写成完整分镜：storyboard.title、非空 shots，每镜有 id、duration、完整 H3 prompt；options.input_mode 为 storyboard，auto_reference 为 false。不能以空 storyboard、probe 提示词或虚构素材反复创建项目来探测字段。已有项目用 bindProject 继续，再 expandShots。通过真实节点工具结构编辑，不猜参数或手写画布内部状态。
5. 修改：updateShot 使用节点当前修订；局部修改只规划需要重新生成的镜头，保留其他镜头缓存。接续镜头绑定同项目直接前一镜的真实末帧。
6. 生成：planGeneration 得到具体执行范围，向用户呈现可查看的分镜、规格、提示词和次数。已获授权的范围直接调用 runPlan；不以提示词确认代替新生成范围的授权。
7. 续跑：getJobStatus 查询实际任务，stopJob 停止、resumeJob 续跑原 ID。请求结果未知时用 getSubmissionHistory / retrySubmission 复查原 requestKey，不另起重复请求。
8. 交付：单镜 collectResult 后规划 finish，完成再 collectResult 取回最终视频与校验清单。说明实际做过的视觉、解码、音频检查，未验证的部分不宣称通过。

## 一句话加参考图

例如“参考图中的人物从沙滩椅起身，慢慢走向大海”，按用户要求写一个可执行镜头即可，不要求用户自己填写分镜 JSON。

1. 用 getCanvas / findCanvasNodes 查询实时节点，用 getCanvasNodes 的 outputs 取得用户指定原图的工作区相对路径；读取图片后编写动作和 H3 提示词。不要把上次生成的其他场景图当成参考。节点不存在时重新查询；空画布也不代表磁盘素材已删除，不恢复已删除节点或直接改写画布文件。
2. 先 connectFactory 查询候选 profile，再 getWorkflowPlan 检查 ready；只选择模型已就绪的兼容方案。工作流出现在目录中不代表已安装，不能以创建项目代替环境检查。用项目节点 createProject 保存真实分镜，mode 设为 I2VA，先省略 bindings。单镜 8 秒可用 duration_rule:"count"、shot_count:1、total_seconds:8；manual 必须同时填写 manual_durations。参考图尚未导入时不要填写虚构 ID，也不要往 options.assets 或 storyboard.assets 塞文件路径。
3. 在已绑定项目的节点调用 importReference({path:原图相对路径,requestKey:唯一键})。此操作将真实图片导入工厂项目，返回 asset.id 与 revision；并非新生成图片。
4. 调用 expandShots，使用它返回的镜头节点 ID；对镜头节点查询 getNodeTools / getFactoryState，再调用 updateShot({changes:{mode:"I2VA",bindings:{first_frame:上一步asset.id}},expectedRevision:最新revision,requestKey:唯一键})。不能在项目节点调用 updateShot。素材或剧情变更会使旧提示词失效：回执 invalidated_prompts 非空时，读取最新 revision，单独 updateShot({changes:{prompt:完整H3提示词},expectedRevision:最新revision,requestKey:新的唯一键})，再计划生成；不要用空提示词试跑。
5. planGeneration → ready 后 runPlan → getJobStatus → collectResult。素材导入会改变 revision，修改或导入后须重新计划。关闭页面不会取消已提交任务。

创建、导入、修改失败时根据 schema 或结构化错误修正原操作，不创建无关的“探测项目”。请求结果未知时先以原请求键复查，避免重复项目和任务。

需要导入或编辑原始 ComfyUI 工作流时使用 ComfyUI 工作流节点，连接共用设置。此节点直接提交 ComfyUI；正式生产和缓存续跑使用 H3 工厂节点。图片／换装节点使用图片模型配置中的 API 或 ComfyUI；视频节点使用视频模型配置中的 API 或 ComfyUI。未配置工作流或密钥时先完成配置，不将缺少执行条件视为生成成功。

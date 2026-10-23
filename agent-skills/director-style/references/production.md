# 加载导演风格并制作

默认 inspired：借用美术、镜头、节奏、动作表达和声音组织，保留新故事、新人物与新台词。不能因为参考片有某人物，就把其身份自动变成新项目的角色；参考片画面也不会自动上传为生成参考图。

用户明确选择 remake 时才沿用参考结构。先读取 shot_structure，再把每镜的戏剧功能、构图、运动和切点分配给新人物与新内容。将参考相对节奏转换为工厂支持的镜长与帧数；保持镜头对应关系。若需要超出当前单镜长度/数量限制的结构，先说明并按用户目标分段处理，不能静默删镜后声称逐镜仿拍。

参考片的快切可以通过生成较长原片、实际审看后明确选段完成。按 UID 更新 `edit_ranges`，例如 `{"edit_ranges":[{"start":1.2,"end":1.7}]}`，表示只保留本镜原片的该区间；可提交多个有序且不重叠的区间。区间按24fps取整，保持原速，仅影响 CPU 后期，不改变生成镜长或原片。完成选段后建 finish 计划。对白必须保留语音保护区间，可提供人工 dialogue_timings；首帧接续链不能剪掉所需头尾帧。独立快切在最初创作时不应误设为首帧接续。

style check 中 timing 对比参考与计划的相对时长，区分生成镜长和后期输出时长；这不是已验收的实际节奏。不要在没有看过生成结果时猜测“接触瞬间就在1.2秒”。

推荐顺序：

1. `style list/show/brief` 读取确定的 style_id 和 version，按相关维度查看证据。
2. 外部 AI 编写符合新故事要求的分镜与 H3 prompt，创建草稿；需要内部创作时先创建大纲/灵感草稿。
3. `style bind --project PID --style ID --version VERSION --mode inspired`。仿拍明确改成 remake。绑定只记录冻结选择，不启动生成。
4. `style brief --project PID` 读取冻结指导；核对已有分镜、素材、提示词和后期安排是否已落实规则。必要时按 UID 更新，保留用户内容。
5. 常规 project validate → plan → run。plan 返回 director_style 和结构阻塞项；渲染仍遵守严格外部创作模式，不隐式补写提示词。内部文字调用会接收同一份导演指导。
6. 先检查代表性试镜的构图、运动、声音和切口。修改当前项目的实现或发布风格新版本；不要直接改冻结包内文件。

项目目录内保存完整风格版本和证据；用户风格库更新不会改变旧项目。改用新版本需重新 bind 并提供当前 revision，旧计划失效。`style clear --project PID` 取消选择，保留已有快照和作品；不会自动恢复旧分镜或删除作品。

`style check --project PID` 检查版本完整性与参考结构对应，不会自动计算视觉相似度。`deliver --verify` 检查音视频技术完整性。画面、台词、风格符合程度仍需实际查看与试听。

风格验收文件含 expected_revision、当前成片 final_sha256 和所有规则的 assessments。每项 rule_id 对应 passed、failed 或 not_checked，附 note；已判断通过/失败的项要有成片原始时间码 evidence。先从 deliver 清单取当前成片哈希，再提交 `style review --project PID --json review.json`。成片、分镜或风格选择改变后旧记录标为 stale，不能沿用以前的“通过”。

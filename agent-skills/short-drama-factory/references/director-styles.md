# 导演风格：学习、加载与验收

4.1 的导演风格把参考片的视听规则保存为用户自己的版本化 Skill。默认 inspired：用参考片的风格讲全新故事；用户明确要求沿用镜头顺序、节奏与动作结构时才用 remake。

学习新影片时，读取应用目录 `agent-skills/director-style/SKILL.md`，或使用已安装的 `$director-style`。这是工厂提供的专门分析技能，需要应用本机可读取参考片。它指导当前 AI 根据真实查看/试听写规则，不在后台自动调用另一个视觉或音频服务。

基本命令（在本技能目录执行）：

```powershell
python scripts/sdf.py style prepare --video "参考片绝对路径" --wait 45
python scripts/sdf.py style analysis ANALYSIS_ID
python scripts/sdf.py style clip ANALYSIS_ID --start 10 --end 16 --wait 45
python scripts/sdf.py style publish --json authored-style.json
python scripts/sdf.py style list
python scripts/sdf.py style brief --style STYLE_ID --version VERSION
python scripts/sdf.py style bind --project PID --style STYLE_ID --version VERSION --mode inspired
python scripts/sdf.py style brief --project PID
python scripts/sdf.py style check --project PID
python scripts/sdf.py style review --project PID --json review.json
```

prepare 只提取 CPU 证据：总览图、带时间码的采样帧、连续片段及密集时序图、试听音轨、候选切点与音频能量。prepared/任务 done 不表示风格分析已完成。当前 AI 必须看真实材料，按实际覆盖写 observation 与 guidance；没听音就不能补全声音规则，没看连续证据就不能声称理解动作。无法覆盖的维度记录到 limitations。

用户级库默认在 `%USERPROFILE%/.short-drama-factory/director-styles`，以 API 返回的 directory 为准。新版本不能覆盖旧版本；publish 更新需 expected_version。生成的包含 SKILL.md、结构化规则、分维度参考文档和实际证据。style install 可复制到新的 AI 技能目录，返回的 skill_name 带版本后缀，避免不同版本自动发现时同名混淆。

收到现成风格包或更换电脑时用 `style import --folder 完整包目录` 导入用户库，再 bind。导入核对清单和全部文件摘要，不依赖原片或旧分析目录。

先读 brief 再创作。风格迁移保留用户的新故事、新角色和新台词；不自动借用原片人物、素材或原声。仿拍按 shot_structure 的镜头功能和相对节奏组织新内容，镜长仍需符合模型限制与帧对齐。

bind 会复制完整版本到项目并改变 revision，旧执行计划需重建。加载本身不会改写旧分镜/提示词，也不启动生成；当前 AI 要落实每镜构图、动作、声音和后期安排。用户选择内部文字创作时，工厂统一把冻结指导送入大纲、分镜和提示词调用。项目快照可随迁移包移动，不依赖原风格库仍在旧电脑。

先试代表性镜头，针对差异改当前实现或发布新风格版本。style check 只证明版本/结构检查，不计算视觉相似度。实际审片后按全部规则提交 assessments，使用 passed/failed/not_checked、说明和成片时间码；review 同时绑定 revision 与成片 SHA256。deliver 的 checks.director_style / style_review_complete 是独立维度，不能用技术解码通过替代风格符合。

请求超时按同一请求键查询/重试；恢复原 job。style clear 取消项目选择但保留既有快照和作品，不还原用户分镜。style install 不覆盖已存在的个人目录。

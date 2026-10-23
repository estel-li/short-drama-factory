# 4.1 导演风格 Skill

用户给参考影片，当前 AI 分析其中可迁移的视听语言，工厂保存为用户自己的导演风格 Skill。默认用该风格讲全新故事；用户明确选择时，按参考镜头顺序、相对节奏和动作结构替换人物与内容进行仿拍。

## 完整流程

1. 读取 [导演风格 Skill](../agent-skills/director-style/SKILL.md)，连接并核对应用实例。
2. `sdf style prepare --video 绝对路径 --wait 45` 提交参考片证据提取，继续观察返回的原任务；不需要图形工作台。
3. `sdf style analysis ID` 返回查看入口。当前 AI 实际查看图片/连续片段或密集时序图、试听音轨；重点动作和转场用 `style clip ID --start 秒 --end 秒` 补充证据。
4. 按 [规则样例](../agent-skills/director-style/assets/style-example.json) 写观察、规则、适用场景、证据时间码、查看覆盖和限制，执行 `style publish --json 文件`。样例不是对用户影片的分析结果。
5. 用 `style brief --style ID --version VERSION` 读取指导并创作新故事；创建项目后 `style bind --project PID --style ID --version VERSION` 冻结选择。仿拍显式加 `--mode remake`。
6. 读取项目 brief，落实到分镜、H3 提示词和实际素材，再使用 validate/plan/run 制作。先试代表性镜头，根据差异修订。
7. 实际审片后逐项 `style review`。deliver 清单区分技术完整性和导演风格验收，不计算没有依据的“百分百相似”分数。

## 用户数据与版本

默认风格库为 `%USERPROFILE%/.short-drama-factory/director-styles`，服务可用 SDF_STYLE_HOME 改到其他用户目录。analyses/ 保存请求与提取证据，styles/ 保存风格的不可变版本和当前指针。原片保持只读；风格包包含分析所需证据，不依赖原片文件继续位于原路径。

每个版本含 SKILL.md、style.json、分维度规则、参考结构、证据索引和实际媒体。包内清单记录文件 SHA256。发布更新需 expected_version；用户可以继续选择旧版本。生成的 skill_name 带版本后缀，多个安装版本不会同名。

`style install --style ID --version VERSION --target 新目录` 可安装到某个 AI 的技能目录。目标已存在时拒绝覆盖，避免丢失个人编辑；安装新版本时使用新目录。也可直接让 AI 读取用户库里的 SKILL.md，通过内置工厂 Skill 按名称和版本加载。

项目绑定时复制完整快照到项目目录，director-style.json 保存版本、模式与包摘要。选择变化进入项目 revision；执行前核对版本文件，修改文件会阻塞原计划。绑定不自动改写用户的已有分镜或提示词，也不会立即生成。标准迁移包保留风格证据，即使未包含生成原片，也能在另一机器读取指导。

单独迁移风格包时使用 style import --folder 目录，核对清单及全部文件摘要后注册到新用户库；不需要原影片或旧分析记录。已有其他当前版本时需 expected_version，不能静默覆盖。

## 分析边界与可执行指导

工厂自动完成媒体测量，当前 AI 完成语义分析。自动切点是像素变化候选，音频 RMS/峰值是能量测量，不等于识别音乐、对白或动作。每条规则保存 observation、guidance、when、basis、confidence 和 evidence；coverage 是作者声明的实际查看范围，不是程序自动证明“看过”。

声音规则需要 audio 依据；摄影/动作/剪辑需要 motion 依据。只有静态图像的工具可查看密集时序图，但要记录采样遗漏的限制；无法听音时 audio 覆盖留空。证据区间不能超出提取范围或作者覆盖范围。仿拍结构需要连续画面依据，按原片绝对时间排序，最多150镜。

默认只迁移风格，不自动采用原片人物、剧情、台词或音轨。仿拍也使用用户的新人物与内容。实际镜长、帧对齐、连续素材和特效能力受所选生成工作流限制；明确缺项，不能靠一段风格提示词承诺完全一致。

参考片的短快切可使用明确的 edit_ranges：从生成原片中选择原速区间做 CPU 后期，按24fps取整，不要求模型直接生成低于其最短镜长的内容。先实际审看原片再选取动作区间；有对白时须保留语音保护区间，首帧接续链保留所需头尾帧。style check 的 timing 对比参考和计划的相对时长，不冒充已经验收的动作节奏。

内部大纲、分镜和提示词调用通过 Content.call 统一接收项目冻结指导；外部 AI 使用 brief 创作。没有风格选择的项目继续原制作流程。

## 控制与恢复

分析和补充片段使用持久任务，默认只执行明确授权的任务 ID；CPU 提取可暂停/续跑，不启动视频生成引擎。写请求使用幂等键。响应丢失先查 operation，再按原账本重试；发布或绑定已落盘但数据库回执未保存时仍可恢复原结果。

style review 必须覆盖全部规则，使用 passed/failed/not_checked，已判断项附成片时间码；记录绑定当前成片 SHA256 和项目 revision。作品或风格选择变化后记录标为 stale。技术交付 ready_for_delivery 不代表风格或内容已全部验收，应同时检查 checks.director_style。

## 验证

4.1.0 发布前本机回归通过 439 项 Python 测试和 18 项前端测试；两个操作 Skill 均通过技能结构校验，Python 3.13 便携运行时通过 API 契约一致性检查。

离线测试使用合成参考视频和模拟提供商，覆盖真实 CPU 提取、独立 CLI 经 HTTP 发布/绑定/安装、内部创作上下文、不可变版本、丢失回执恢复、迁移及成片验收失效。真实影片的语义分析和生成效果在用户提供参考片后另行实际查看和审片。

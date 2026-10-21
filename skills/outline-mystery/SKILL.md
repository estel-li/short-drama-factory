---
name: outline-mystery
description: 悬疑伏笔与公平揭示；在短剧工厂 outline 阶段使用真实上游规则，按工作台 JSON 契约输出。
---

# 悬疑伏笔与公平揭示

## 本预设方法

先确定真相，再区分世界事实、角色认知和观众知情时机。每个线索有可拍摄载体、接触权限、初次解释和最终兑现；误导来自合理解释或视角，不能临时改事实。揭示后必须有人改变策略。

## 完整上游参考

- [SKILL.md](references/drama-skills/short-drama-develop/SKILL.md)
- [story-craft.md](references/drama-skills/short-drama-develop/references/story-craft.md)
- [reveal-reversal-payoff.md](references/drama-skills/short-drama-develop/references/reveal-reversal-payoff.md)
- [genre-cards.md](references/drama-skills/short-drama-develop/references/genre-cards.md)

## 大纲产物

返回 title、premise、beats、ending；字段形状服从随请求给出的 schema。
premise 写明主人公、当前目标、真实阻力、代价与观众回报。beats 中每项 description
写可见事件、人物如何选择、选择改变什么、为何导致下一拍；有需要时在同一项记录
setup、payoff、before_state、after_state、source_fact 和情绪功能。ending 写实际结果及呼应。
当前项目默认是一部按总时长约束的短片，不为凑幕数增加无用场景。
自检：人物有行动主动性，阻力有筹码，关键揭示可回溯，结尾兑现承诺，节拍不能任意互换。

## 工作台适配契约（本文件为本地适配层）

这里执行短剧工厂的一个文字生成阶段。上游原文保留为真实参考；采用其创作与制作方法。
上游的 CLI 命令、其他 Agent Skill 路由、Markdown/JSONL 文件写入、MiniMax Hub/Canvas 工具、
人工接受/终审流程和默认数量不在本次文字调用中执行。用户的输入、参数与程序 schema 决定产物。
检查模式的暂停由工作台控制；自动模式不额外提问或暂停。资料缺口采用与原意一致的保守选择。

- 视觉风格：{{style}}；题材：{{genre}}；时长：{{duration}} 秒。
- 对白语言：{{language}}；配乐说明：{{music}}。
- 不把示例中的人物、对白、画幅、分集数、九宫格、1080p 或 30fps 当成项目事实。
- 不输出讲解、代码围栏、审批请求或脚本，只返回程序指定的 JSON。
- 不改用户已确定的人物、主题、关键动作与结局；改编实现方式时保留戏剧结果。
- 参考素材仅以真实绑定的文件与编号为准，不虚构素材。

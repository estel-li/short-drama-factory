# 案例记录

本目录存放**案例证据记录**：每个作品一份 Markdown，外加 `INDEX.md`（语料索引）。
它们是 `../modules/` 与 `../banks/` 中每一条规则的原始依据。

## 这些文件是什么、不是什么

它们是**证据台账**，不是 skill 的正文。每份记录回答：这个作品实际写了什么、按什么顺序写、
数字是多少、哪里失败过。规则引用它们，它们不复述规则。

它们**有意保持中英混排**：

- **提示词引文一律保留原文语言**——多数是英文，源提示词是中文 / 俄文的地方就保留中文 / 俄文。
  翻译引文会切断"规则 ↔ 语料原文"的对应关系，而这条对应关系正是记录存在的唯一理由。
- **分析者的标注是中文**（小标题、"这一案例教什么"、阅读备注）。这是采集阶段的工作语言，
  与交付版本用哪种语言无关。

所以记录正文**刻意不是单语**。**单语保证只针对 skill 本身**（`../modules/`、`../banks/`、
`../README.md`）：英文版写一遍、中文版（`../../cinematic-director-zh/`）写一遍。两个版本
**共用同一批案例记录**——证据不翻译，只翻译 skill 正文。

第一次读建议：先读开头块（结论 / 这一案例教什么）→ 再扫小标题 → 最后把大段英文 `prompt`
正文当附录查。

> **关于参考 token 的归一化：** 语料原文里用的是尖括号 token（`image_N` / `video_N` / `audio_N` 形式）或资产 uuid。
> 本目录的引文**已统一改写为花括号 token**（所有参考都用 `{{ref N}}`——图片、视频、音频共用一套编号；引用原始资产 id 时写 `{{资产 uuid}}`），
> 与 skill 正文和范例保持同一套写法。**语义完全不变**——只换了外壳，没有改任何描述内容。
> 原始字面形式保留在 `_data/cases/<slug>/prompts.jsonl` 里可查。

## 定位符

记录用两种定位符指回采集数据：

- `prompts.jsonl#N` —— `_data/cases/<slug>/prompts.jsonl` 中的第 N 行，按 **0 基行号**计。
  少数早期记录引用的是邻近行；当行号与引文对不上时，**以引文为准**，直接在文件里搜原字符串。
- `<slug>` —— `_data/cases/` 下的案例目录名，例如 `cully-hill-boys`。

`350 / 300 / 50`（提示词 / 视频车道 / 图像车道）这类数字来自同一个文件，本文档不重新计算；
`INDEX.md` 负责汇总（15 个项目 · 1954 条 · 视频 1469 / 图像 484）。

## 编码规则

- UTF-8，**无 BOM**。
- 引文字符串原样复制：原标点、原全角字符、原俄文 / 生造语行。不要"顺手规范"引文。
- 行尾 LF；代码围栏成对。

## 文件清单（15 份记录 + 索引）

| 文件 | 案例 |
|---|---|
| `cully-hill-boys.md` | The Cully Hill Boys |
| `anerneq.md` | Anerneq |
| `hell-grind.md` | HELL GRIND |
| `vengeance-is-mine.md` | Vengeance is mine |
| `oneiric.md` | ONEIRIC |
| `passport-rush.md` | Passport Rush |
| `trigger.md` | The Trigger |
| `red-flag.md` | Red Flag |
| `adiliada.md` | Adiliada（含唯一一份真实工作文档） |
| `if-you-stop-loving-me-ill-die.md` | If you stop loving me, I'll die |
| `kok-boru-film.md` | Kok Boru（899 s 正片） |
| `kok-boru.md` | Kok Boru（20 s 轮播） |
| `huntress-s-tale.md` | Huntress's Tale（唯一非工作室作者） |
| `zephyr.md` | ZEPHYR |
| `zephyr-special.md` | ZEPHYR: Special |
| `INDEX.md` | 语料索引：37 个系列、14 个已发布、23 个仅系列 |

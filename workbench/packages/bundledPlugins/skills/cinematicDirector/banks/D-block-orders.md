# BANK D · BLOCK ORDERS —— 区块顺序查表

查表用。三套实测顺序 + 一条推荐顺序 + 图片车道 + 对照表。写法：按行取用。

## D.1 推荐顺序：19 槽（三套顺序合并后的规范形）

> **`OPENING STATE` 是文字块** —— 用几句话写死 t=0 时谁在哪、朝哪、手上有什么、什么已经在动。它是文字块（不是分镜首帧图）：本 skill 的工作流是多参直接生成，参考图只作参考输入。

> **装配默认看 `SKILL.md` §5**（14 槽，300 条实测序）。本表是**超集**：多出的 5 槽（ACTING TASK / SPOKEN LINE / LIVING FACE / GEOMETRY ANCHOR / NEGATIVE）只在项目技能开启时才用。合并与"何时可省"是编辑决定（`[推断]`）；D.2–D.4 是语料原文。STYLE 位置不同（本表 4 / `SKILL.md` 8）；装配按 `SKILL.md`。

| # | 槽位 | 放什么 | 何时可省 |
|---|---|---|---|
| 1 | SCENE CONTEXT | 2 句：这一镜发生什么；只写本镜，不带场号/前情 | 永不省 |
| 2 | ACTIVE REFERENCES / TAGS | `@TAG` 名单 + 参考 id + 一句"参考只供什么" | 无参考图时省 |
| 3 | OUTPUT SETTINGS | 画幅 / fps / 时长 / 镜头数 / 剪切数 / 色彩模式 | 平台 UI 已选且非叙事关键时省 |
| 4 | STYLE | 介质、影调、颗粒、调色（逐字块） | 永不省（单片 canon） |
| 5 | ACTING TASK | GOAL / OBSTACLE / TACTIC（+ MOTIVE / 潜台词） | 画面无活人时省 |
| 6 | LOCATION MAP | 机位、朝向、前中后景、地标、路径、光向、纵深 | 单一封闭空间且无走位时省 |
| 7 | OPENING STATE + SPATIAL BLOCKING + ANCHORS | 开场状态（t=0 的几句话）+ 每人七事实 | 永不省 |
| 8 | OPTICS | 视角（度）+ 距离 + 可见结果；镜头锁 | 无镜头语言要求时省 |
| 9 | CAMERA | 手持规律、可否移动、禁止的运动 | 永不省 |
| 10 | ACTION TIMING / THE SHOT | 按节拍写动作；切点；台词落点 | 永不省 |
| 11 | SPOKEN LINE | 谁说话、正字法、音色段（逐字）、逐行语气 | 无人说话时省 |
| 12 | LIVING FACE / EYES（或 MOMENT） | 瞳孔、眨眼、微表情；动物/物理过程用 MOMENT | 无脸时省 |
| 13 | PHYSICS | 重量、阻力、布料、呼吸、水的行为 | 静物空镜可省 |
| 14 | LIGHT | 源、方向、衰减、明暗比（逐字块） | 永不省 |
| 15 | TEXTURE / CAPTURE | 胶片/数码、颗粒行为、本镜的具体材质 | 图片车道用 tech block 代替 |
| 16 | AUDIO | 环境声清单 + 有无音乐/配乐 | 静音镜可省 |
| 17 | POSITIVE LOCKS / ANTI-TELL | 本镜的失败预防（正向锁或紧凑负向束） | 永不省 |
| 18 | RUNTIME + GEOMETRY ANCHOR | 秒数 / 镜头数 / 剪切数 + 计量几何（距离、角度、高度） | 永不省 |
| 19 | NEGATIVE | 负向脊椎 + 本镜特例 | 默认整槽删除（300 条实测 **0 条**）；只有选"脊椎式"的片才加（ANERNEQ 90% 的提示有） |

可选槽位（插在指定位置）：`WHO IS WHO` → 槽 7 前；`FRAME MATCH` → 槽 10；`THE SITUATION` → 槽 1 或 5；`LOOK LOCK` / `REFERENCE SCOPE` → 槽 4 / 槽 2。

## D.2 ANERNEQ 的 20 区块（逐字，`cases/anerneq/skills/724f5ebf….md:36-47`）

```text
1  TAGS / CAST & ASSETS      11  LIGHT
2  STYLE PREFIX              12  NO LENS FLARES
3  Style                     13  HARD ANAMORPHIC LOOK
4  NO SUBTITLES, NO TEXT     14  HYPER-REAL CAPTURE
5  COMPOSITION               15  PHYSICS
6  THE SHOT                  16  CHARACTER ACTING
7  SPOKEN LINE               17  AUDIO
8  CAMERA                    18  TOTAL RUNTIME
9  LIVING FACE/EYES          19  GEOMETRY ANCHOR
10 ANTI-AI-TELL DIRECTIVE    20  NEGATIVE
```

条件区块：`THE SITUATION` · `FRAME MATCH` · `WHO IS WHO`；动物或物理过程用 `LIVING MOMENT` 换掉 `LIVING FACE/EYES`。
实战变体（技能未记录，语料里最多）：`MULTISHOT — ONE HARD CUT, tension rising:`（49/121 条）。

## D.3 CINEDANCE 的 12 段（逐字，`cases/cully-hill-boys/skills/7a900bd1….md:163-176`）

```text
SCENE CONTEXT
ACTIVE REFERENCES
LOCATION MAP
OPENING STATE
FORMAT MODE
OPTICS
CAMERA
ACTION TIMING
PHYSICS
LIGHTING
AUDIO
POSITIVE CONSTRAINTS
```

可选段：`OUTPUT SETTINGS`（平台已选或非叙事关键时省）· `NEGATIVE CONSTRAINTS`（用户要求或已知失败才写）。
顺序法：placement 早于 style；optics 早于造型语言；lighting 当锁不当装饰；关键走位自成一节，写在风格散文之前。
术语：段名按本包统一为 `OPENING STATE`；其余段名逐字未动。

## D.4 VENGEANCE 的 14 段（CINEDANCE 12 + 2，`cases/vengeance-is-mine/skills/a7ff619c….md:12`）

```text
SCENE CONTEXT → OUTPUT SETTINGS (story-critical) → ACTIVE REFERENCES → ACTING TASK
→ LOCATION MAP → OPENING STATE → FORMAT MODE → OPTICS → CAMERA
→ ACTION TIMING → PHYSICS → LIGHTING → AUDIO → POSITIVE LOCKS
```

两条硬约束：**不需要的段可以删，顺序永不变；NEGATIVE CONSTRAINTS 只作为正向锁里的内联一句**。

## D.5 图片车道（不同顺序，别混用）

**角色三视图 sheet**
```text
[人物规格] → [三格：全身正面 左 / 全身背面 中 / 头部特写 右]
→ [平的中性灰背景、三格并排] → [三格是同一个人，跨格一致]
→ [16:9，2k，Soul ID]
```
禁：`character reference sheet` · `painterly` · 三分法（豁免）；三格用散文，不用 CAPS。

**地点 plate**
```text
[机位锚 — 最难，必须写硬] → [地点身份] → [关键元素] → [光源 + 方向 + 色温]
→ [次级元素向纵深退去] → [调色板] → [tech block] → [气质/DP 参考] → [空无写成正面陈述]
```
地点上不写光学/景深语言；抽象几何换成真实器材 + 类型词（`24mm wide, real estate interior photo`）。

**道具 sheet**
```text
[中性水泥面上的照片级产品图] → [柔和定向光] → [主体孤立]
→ [材质 + 磨损状态] → [空白无品牌表面写成正面陈述] → [多个状态 = 多个独立资产]
```
武器/爆物按中性材质与功能描述，不用其名。

**外科式修图**
```text
[译] 修这张图：[一句话目标]。
[译] 改动：只改这一处。
[译] 原样保留：脸、服装、道具、位置、墙面/地面、机位角度、所有现存阴影，
以及调色、色板、对比、颗粒、衰减。
[译] 只改：把上面那一条再说一遍。
[译] 其余 100% 不变。
```

**tech block（图片车道，二选一，逐字）**
```text
Photorealistic ARRI Alexa LF anamorphic Cooke S4 lens at T2.0, organic 35mm Kodak Vision3 250D film grain, soft cinematic falloff, cinematic film still aesthetic
```
```text
Shot on ARRI Alexa Mini LF with ARRI Signature Prime lens, clean modern digital cinematic capture, crisp natural detail, minimal fine grain, soft cinematic falloff, modern cinematic film still quality, hyperrealistic photographic detail
```

## D.6 对照表（换顺序时用）

| 19 槽（推荐） | ANERNEQ 20 | CINEDANCE 12 | VENGEANCE 14 |
|---|---|---|---|
| 1 SCENE CONTEXT | （并入 THE SHOT） | SCENE CONTEXT | SCENE CONTEXT |
| 2 ACTIVE REFS / TAGS | 1 TAGS / CAST & ASSETS | ACTIVE REFERENCES | ACTIVE REFERENCES |
| 3 OUTPUT SETTINGS | 2 STYLE PREFIX + 18 TOTAL RUNTIME | （可选） | OUTPUT SETTINGS |
| 4 STYLE | 3 Style | （折进 FORMAT MODE） | （在 OUTPUT SETTINGS 内） |
| 5 ACTING TASK | 16 CHARACTER ACTING | （无，由 ACTING 技能补） | ACTING TASK（紧跟参考之后） |
| 6 LOCATION MAP | （在 COMPOSITION 内） | LOCATION MAP | LOCATION MAP |
| 7 OPENING STATE + BLOCKING | 5 COMPOSITION | OPENING STATE | 同左 |
| 8 OPTICS | 12 NO LENS FLARES + 13 HARD ANAMORPHIC | OPTICS | OPTICS |
| 9 CAMERA | 8 CAMERA | CAMERA | CAMERA |
| 10 ACTION TIMING | 6 THE SHOT | ACTION TIMING | ACTION TIMING |
| 11 SPOKEN LINE | 7 SPOKEN LINE | （无独立段） | （无独立段） |
| 12 LIVING FACE / EYES | 9 LIVING FACE/EYES | （无独立段） | （并入 ACTING TASK） |
| 13 PHYSICS | 15 PHYSICS | PHYSICS | PHYSICS |
| 14 LIGHT | 11 LIGHT | LIGHTING | LIGHTING |
| 15 TEXTURE / CAPTURE | 14 HYPER-REAL CAPTURE | （quality suffix） | （在 canon STYLE 内） |
| 16 AUDIO | 17 AUDIO | AUDIO | AUDIO |
| 17 POSITIVE LOCKS / ANTI-TELL | 10 ANTI-AI-TELL DIRECTIVE + 4 NO SUBTITLES | POSITIVE CONSTRAINTS | POSITIVE LOCKS |
| 18 RUNTIME + GEOMETRY | 18 TOTAL RUNTIME + 19 GEOMETRY ANCHOR | （并入 OUTPUT SETTINGS） | （并入 OUTPUT SETTINGS） |
| 19 NEGATIVE | 20 NEGATIVE | （可选 NEGATIVE CONSTRAINTS） | **禁止**（纯正向） |

## D.7 对齐 `SKILL.md` §5.2（13 槽必备序）

左列 = **装配时以它为准**（`SKILL.md` §5.2 的 13 个必备块，按实测平均位置排序）。
右列 = **本表的 19 槽超集**（项目技能开启时按它补槽）。
两列不是矛盾，是"最小可用集"与"完整项目集"的关系。

| SKILL.md §5.2 槽 | 本表 19 槽 | 关系 |
|---|---|---|
| 1 SCENE CONTEXT | 1 | 同 |
| 2 ACTIVE REFERENCES | 2 | 同（**地点排第一**，每标签只一次） |
| 3 FORMAT MODE | 折进 3 OUTPUT SETTINGS | 多镜时单列：一条里放几个镜头、怎么切 |
| 4 LOCATION MAP | 6 | 本表后移（在 STYLE 之后） |
| 5 OPENING STATE | 7 | 同（**文字块**，写 t=0 的状态） |
| 6 OPTICS | 8 | 同 |
| 7 STYLE | 4 | 本表前置；装配按 `SKILL.md` |
| 8 CAMERA | 9 | 同 |
| 9 ACTION TIMING | 10 | 同（含每条内部的镜头表与绝对秒剪切点） |
| 10 LIGHTING | 14 | 本表后移 |
| 11 PHYSICS | 13 | 同 |
| 12 AUDIO | 16 | 本表后移；实测 87%、12/12 部片，几乎必写 |
| 13 POSITIVE LOCKS | 17 | 同（收尾，位置 85%） |
| —（不单列） | 3 OUTPUT SETTINGS | 参数归 UI，只留叙事参数 |
| —（不单列） | 5 ACTING TASK | 项目技能开启 / 对白镜时加 |
| —（不单列） | 11 SPOKEN LINE | 有对白时加 |
| —（不单列） | 12 LIVING FACE / EYES | 项目技能开启，或由 `02-cast` 内联 |
| —（不单列） | 15 TEXTURE / CAPTURE | 材质是卖点时单列，否则并入 STYLE / PHYSICS |
| —（不单列） | 18 RUNTIME + GEOMETRY ANCHOR | 折进 9（时长确认）与 5（几何锚定） |
| —（默认不写） | 19 NEGATIVE | 见 §5.3 结论 2：5/12 部片用，其余全部内联改写 |

**换装规则一句话：** 单镜/短片用左边 13 槽；一旦开启项目技能（`11-project-skill.md`），按右边 19 槽补齐，**只补差集，顺序照旧**。

## D.8 会腐烂的事实（带日期）

| 事实 | 值 | 日期 / 出处 |
|---|---|---|
| 视频模型 id（语料实测） | `seedance_2_5`（121 条）· `seedance_2_0`（117 条） | 2026-10-30，两案例 `prompts.jsonl` |
| 图片模型 id（语料实测） | `soul_cinematic` · `nano_banana_2` · `gpt_image_2` · `text2image_soul_v2` · `seedream_v5_pro` | 2026-10-30，同上 |
| 画幅能力 | Soul 2.0 无 21:9；Soul Cinema 有 21:9；NBP 到 4K、≤14 张参考 | 2026-10-30，`LIRA:259-348` |
| 图/视频语言分工 | 图片用器材词，视频用结果词 | 2026-10-30，`CINEDANCE:565-567` |

## D.9 块标签对照（术语表——两版都保留完整；本版为「中文 → 英文」方向）

横着查，不读散文。频次＝8 案中文主导提示内实测。

| 中文块名（语料频次） | 对应英文块 | 备注 |
|---|---|---|
| **场景背景** 108 · **本场事件** 22 · `STORY CONTEXT`（括号版） | `SCENE CONTEXT` | 只写本镜 |
| **参考图** 227 · **激活参考** 91 | `ACTIVE REFERENCES` | Cully 原写法：`ACTIVE REFERENCES（只放本镜实际用到的）` |
| **拍摄模式** 68 · **格式模式** 34 | `FORMAT MODE` | 单镜/多镜 + 硬切表 + 总秒 |
| **空间地理** 175 · **场景地图** 24 | `LOCATION MAP` | 常写成 `【空间地理＝全场固定布局（务必锁定、绝不跳轴）】` |
| **开场** 156 · **开场状态** 5 · 起幅（旧别名） | `OPENING STATE` | 中文一律用**开场状态** |
| **光学镜头** 21 · **焦段** 22 · 景别 255 | `OPTICS` | 景别多指 shot size |
| **风格** 295 · **质感** 273 · **影调** 91 | `STYLE` | 质感常独立成块写表面 |
| **机位** 907 · **摄影机** 481 · **运镜** 97 · 手持 1042 | `CAMERA` | 中文语料里"手持"多于"机位" |
| **动作** 1148 · **时间轴** 93 · **动作时间轴** 79 · 节奏 167 | `ACTION TIMING` | 每行＝一镜，绝对秒 |
| **光照** 250 · **光线** 188 · **灯光** 126 · 照明 17 | `LIGHTING` | 常以「灯光 — 匹配参考：…」起句 |
| **物理** 194 | `PHYSICS` | 重量、接触、位置恒定 |
| **声音** 580 · **音效** 122 · **音频** 111 · 同期声 52 | `AUDIO` | 结尾固定写「无对白、无音乐、无字幕」 |
| **硬性** 507 · **硬锁** 129 · **正向锁定** 79 | `POSITIVE LOCKS` | 也写作 `【X·硬性】` / `【X·硬锁】` 挂在句内 |
| **绝对禁止** 117 · 禁止 175 · 不要 188 · 约束 50 | `NEGATIVE`（兜底用） | 主写法是正向，负向只做单条兜底 |
| **镜头1**（hell-grind）· кат（kok-boru-film） | `SHOT 1` / `CUT 1` | — |
| **硬切** 180 · 只有 1 次剪切 | `HARD CUT` | — |
| **构图** 37 · 【画面左】161 · 【画面右】59 · 【左往右】116 · 【右往左】33 | composition / framing | 方位一律以画面为准（camera-relative） |
| **人物·硬锁** 32 · 【场地·硬锁】24 · 【屏幕·硬锁】28 | per-object lock | 每类对象各挂一条 |
| **【台词·硬锁·英语·逐字】** 23 | `DIALOGUE` | 语言写进标签 |
| **【身高·硬性】** 44 · **【眨眼·硬性】** 33 · 【不再另做改焦】22 | measurable locks | 可测量的量都用「·硬性」 |
| **【概述】** 31 ·【故事·三条情绪线】18 ·【导演笔记】 | story / beat | 中文方言的自由补充块 |
| **音效：** 55 · **机位：** 43 · 目标：22 · 障碍：22 · 战术：22 · 动机：16 | inline labels | 可嵌在正文里 |

## D.10 项目级 20 块块序（示例形态）

> 项目技能可以整段替换通用骨架（**覆盖不合并**，见 `modules/11-project-skill.md` T-11-17；两版同一条）。下表是**一种实际形态**：块名、数量与颗粒度都由这一片自己定，通用 13/19 槽不吸收它。逐字原文见 `skill/seedance-master-zh/04-anerneq-project-skill.md` §1.1。「何时可省」列按通用槽的用法推导 `[推断]`。

| # | 块 | 放什么 | 何时可省 |
|---|---|---|---|
| 1 | `TAGS / CAST & ASSETS` | 本镜要用的参考与资产清单（一元素一 TAG） | 无参考图时省 |
| 2 | `STYLE PREFIX` | 介质 + 画幅 + 时长 + 镜头数 + 有无剪切 + 实时速度 | 永不省 |
| 3 | `Style` | 影调与质感的逐字块 | 永不省 |
| 4 | `NO SUBTITLES, NO TEXT` | 画面不留字的正向锁 | 有字幕需求时省 |
| 5 | `COMPOSITION` | 构图、主体位置、画面边缘外落黑 | 无构图主张时省 |
| 6 | `THE SHOT` | 本镜动作，按节拍写；含切点 | 永不省 |
| 7 | `SPOKEN LINE` | 台词 + 音色（逐字）+ 逐行语气 | 无人说话时省 |
| 8 | `CAMERA` | 机位运动 / 固定，手持规律 | 永不省 |
| 9 | `LIVING FACE/EYES` | 瞳孔、眨眼、微表情（动物或物理过程用 `LIVING MOMENT`） | 无脸时省 |
| 10 | `ANTI-AI-TELL DIRECTIVE` | 本镜的失败预防束 | 永不省 |
| 11 | `LIGHT` | 光源、方向、衰减、明暗比 | 永不省 |
| 12 | `NO LENS FLARES` | 光斑锁 | 无强光源时省 |
| 13 | `HARD ANAMORPHIC LOOK` | 镜头特征锁（挤压、畸变、呼吸） | 不用变形镜头时省 |
| 14 | `HYPER-REAL CAPTURE` | 胶片/数码、颗粒行为、本镜的具体材质 | 永不省 |
| 15 | `PHYSICS` | 重量、阻力、布料、水 | 静物空镜可省 |
| 16 | `CHARACTER ACTING` | 目标 / 障碍 / 战术 | 无活人时省 |
| 17 | `AUDIO` | 环境声清单 + 有无音乐/配乐 | 静音镜可省 |
| 18 | `TOTAL RUNTIME` | 秒数 / 镜头数 / 剪切数 | 永不省 |
| 19 | `GEOMETRY ANCHOR` | 计量几何（距离、角度、高度） | 永不省 |
| 20 | `NEGATIVE` | 片级负向脊椎 + 本镜特例 | 纯正向片整段省 |

条件块：`THE SITUATION` · `FRAME MATCH` · `WHO IS WHO`（按需插入，位置跟着所属块走）。多镜变体：`MULTISHOT —— 一次 HARD CUT，张力上升：`（写进块表，标明触发条件，见 T-11-10）。

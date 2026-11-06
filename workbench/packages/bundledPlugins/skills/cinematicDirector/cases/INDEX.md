# 案例索引

来源：`https://higgsfield.ai/zh/community/originals` —— 该页是**系列目录**，不是项目目录。
抓取于 2026-10-30。共 **37 个精选系列**，其中 **14 个有已发布的项目快照**（只有这些才带提示词）；
**23 个只有系列页 / 预告片**，从未发布项目快照 → 结构上就不存在提示词可抓。

- ✅ = 已抓到完整提示词语料（`_data/cases/<slug>/`）
- ⬜ = 仅系列元数据 + 预告片（`_data/_raw/series_catalogue.json`）
- 语料总量：**15 个项目 · 1954 条真实提示词**（视频 1469 / 图像 484）
  —— 14 个由系列挂载，另有 1 个未挂系列的额外发布 `kok-boru`（20 s 轮播），所以是 15 个项目。
- 方法、可信度与引用方式见 `../README.md`；抓取接口见仓库根 `HARVEST.md`
- 案例记录体例（中英混排说明、定位符约定）：见同目录 `README.md`

> 站内标签位对照：「精选」= higgsfield-choice，「抢先看」= first-look，「值得关注」= on-our-radar，「即将上线」= coming-soon。下文只写中文标签。
> 第二部分的系列简介是站内原文引文，按规范保留英文，不作转写。

---

## 一、✅ 有提示词语料的案例（14）

| # | 案例 | 类型 | 时长 | 视频 | 图像 | 作者 | 这一案例教什么 |
|---|---|---|---|---|---|---|---|
| 1 | [The Cully Hill Boys](cully-hill-boys.md) | 长片 | 6889 s | 300 | 50 | higgsfield.studio | 旗舰案例：115 分钟、137 场、470,000 次生成。完整方法论（镜卡四栏、空间地图、资产对、音色冻结）+ 3 份工程级 SKILL + 34 条具名失败与修复。 |
| 2 | [Anerneq](anerneq.md) | 长片 | 1202 s | 121 | 29 | higgsfield.studio | 唯一自带完整项目技能的案例：20 块提示词序、@标签资产体系、26 条反 AI 味规则、生造语与音色锁。项目技能的教科书范本。 |
| 3 | [HELL GRIND](hell-grind.md) | 长片 | 5760 s | 95 | 55 | higgsfield.studio | 96 分钟长片，与 Cully 同装三件套 SKILL；俄语提示词混用，图像车道密度极高。 |
| 4 | [Vengeance is mine](vengeance-is-mine.md) | 长片 | 1599 s | 117 | 33 | higgsfield.studio | 黑白西部恐怖片，自带 standing rules 项目规则；「先写禁令清单」与「无负面块」两条互相冲突，是政策分歧的实证。 |
| 5 | [ONEIRIC](oneiric.md) | 长片 | 1189 s | 99 | 48 | higgsfield.studio | 1189 s，梦核美学；图像与视频车道并用，示范风格一致性怎么靠钉板维持。 |
| 6 | [Passport Rush](passport-rush.md) | 长片 | 288 s | 103 | 22 | higgsfield.studio | 288 s 喜剧节奏；示范喜剧靠节拍与反应而非表情。 |
| 7 | [The Trigger](trigger.md) | 长片 | 516 s | 98 | 26 | higgsfield.studio | 516 s，悬疑；seedream_v5_pro + cinematic_studio 的混合车道。 |
| 8 | [Red Flag](red-flag.md) | 长片 | 136 s | 99 | 26 | higgsfield.studio | 136 s，香港黑色电影；短时长下密度怎么砍。 |
| 9 | [Adiliada](adiliada.md) | 长片 | 376 s | 25 | 93 | higgsfield.studio | 最有过程价值：含 1 份真实工作文档（WORKFLOW METADATA / FAILURE NOTES / PATCH LOG / FINAL PROMPT，同一份提交 7 次，2 条编号缺陷 + 1 常设注记 + 5 条补丁），以及完整的板 / 图 / 外科修图资产链。 |
| 10 | [If you stop loving me, I'll die — I don't like dying, but for our love I'm ready to go that far](if-you-stop-loving-me-ill-die.md) | 长片 | 282 s | 100 | 0 | higgsfield.studio | 282 s 爱情短片，含 minimax_h3 的 12 KB 长提示词样本（混媒 2D 叠 3D）。 |
| 11 | [Kok Boru](kok-boru-film.md) | 长片 | 899 s | 75 | 19 | higgsfield.studio | 同一 IP 的 899 s 正片：与 20 s 轮播构成「时长决定模板」的天然控制实验。 |
| 12 | [Huntress's Tale](huntress-s-tale.md) | 轮播 | 67 s | 51 | 14 | ailaa | 唯一非 Higgsfield Studio 作者（ailaa）：验证这套语法是工作室风格还是通用方法的关键对照。 |
| 13 | [ZEPHYR](zephyr.md) | 长片 | 5 s | 25 | 39 | higgsfield.studio | 5 集体量：同一 IP 在剧集与单片两种形态下的模板差异。 |
| 14 | [ZEPHYR: Special](zephyr-special.md) | 长片 | 308 s | 36 | 14 | higgsfield.studio | 308 s，短形式长片的模板对照样本。 |
| + | [Kok Boru (20 s 轮播)](kok-boru.md) | 轮播 | 20 s | 125 | 16 | higgsfield.studio | 未挂系列的额外发布；唯一的轮播形态，长片模板的对照组。 |

> 时长与集数不总一致：`ZEPHYR` 的 publication 时长只有 5 s，但系列有 5 集——看集数请查 `_data/_raw/series_catalogue.json`。

---

## 二、⬜ 仅系列、无项目快照（23）

这些是**预告 / 即将上线**条目：有简介、演员表、预告片，但从未发布项目快照，所以没有提示词。
保留它们是为了「不遗漏」——它们证明了缺口是**结构性的**，不是抓取失败。任何「它们的提示词是……」都是编造。

| # | 系列 | 状态 | 分类 | 演员 | 剧情梗概（节选） |
|---|---|---|---|---|---|
| 1 | **MORK** | 已发布 | 精选 / 值得关注 | 5 | A boy loses his mother, his hands, and everything he knew in a single night — when Viking raiders burn his village to a… |
| 2 | **ARENA ZERO** | 已发布 | 精选 | 6 | A deadbeat gamer hits the wrong button and wakes up in an alien arena - chosen to represent Earth in an intergalactic t… |
| 3 | **SPIT & GLOW** | 已发布 | 精选 | 2 | A young woman possesses a biological anomaly: her DNA can reverse aging. When a wealthy visionary turns this miracle in… |
| 4 | **VERMIN CONTROL UNIT** | 已发布 | 精选 / 抢先看 | 5 | Vermin Control Unit launches a precision rescue operation to extract their boss, who’s being transported as a hostage o… |
| 5 | **DEM - Arena Zero Music Video** | 已发布 | 抢先看 / 值得关注 | 3 | A scavenger crew in a silent wasteland digs up a forbidden relic: a cassette tape. Now, they’re trading their basketbal… |
| 6 | **TAILS OF STEEL** | 已发布 | 抢先看 / 值得关注 | 4 | In a 1990s megacity, criminal gangs unite under the rule of the mysterious supervillain Chrome Cat, who seeks total con… |
| 7 | **PETER PAN** | 已发布 | 值得关注 | 3 | Everyone knows the story of Peter Pan. Now, the classic legend is reborn for the modern age. In a world that forces eve… |
| 8 | **MISFORTUNE** | 已发布 | 精选 | 4 | During a massive pirate battle, a live bomb is loose on a ship. While everyone is busy fighting for their lives, the bo… |
| 9 | **FROZEN MONSTER** | 已发布 | 值得关注 | 3 | A massive ice beast abducts a world-class figure skater, but he is moved by her talent instead of hunger. As the girl d… |
| 10 | **BUDDY** | 已发布 | 抢先看 | 3 | What if Punchy and Herzog’s famous penguin became friends? I made this piece to explore emotion first - quiet warmth, g… |
| 11 | **DINOFORCE** | 已发布 | 抢先看 | 3 | The dinosaurs have returned. Facing a global threat on a planetary scale, humanity is no longer at the top of the food … |
| 12 | **ALRIGHT ALRIGHT ALRIGHT** | 已发布 | 值得关注 | 3 | Two crypto hustlers are hired by a powerful cartel leader to digitize his massive cash reserves into Bitcoin. Instead o… |
| 13 | **BUCKET LIST** | 已发布 | 精选 | 2 | After learning about an impending asteroid collision that will destroy Earth, Ash and his adventurous friend decide not… |
| 14 | **Mother Trucker** | 已发布 | 精选 / 值得关注 | 4 | A woman’s son is taken away. The only way to get him back is to join a massive battle of war machines. The other driver… |
| 15 | **Viking Courier** | 已发布 | 抢先看 | 3 | A Viking Courier must deliver a secret package. To reach his goal, he must cross a massive battlefield full of deadly t… |
| 16 | **AFTER GLOW** | 即将上线 | — | 0 | A breakout indie band is one night away from everything they ever wanted — until old tensions, secret hookups, and buri… |
| 17 | **BEFORE YOUR HEAR THIS** | 即将上线 | 即将上线 | 0 | A young woman starts receiving voice messages from herself — only they’re coming from the future. Each warning arrives … |
| 18 | **Da Groove** | 即将上线 | 即将上线 | 0 | Four friends from the same neighborhood are convinced one track could change their lives forever. When their raw new so… |
| 19 | **GOLDEN HOUR** | 即将上线 | 即将上线 | 0 | Every evening, for one brief and mysterious moment, a hidden space is flooded with a golden light that reveals what peo… |
| 20 | **LOST IN SHIBUYA** | 即将上线 | 即将上线 | 0 | After missing the last train home, a young woman disappears into the restless neon maze of Shibuya, where every street … |
| 21 | **LOVE YOU, SINCERELY** | 即将上线 | 即将上线 | 0 | A lonely young woman begins receiving handwritten letters from someone who seems to understand her better than anyone e… |
| 22 | **THE LOUD VOID** | 即将上线 | 即将上线 | 0 | A long-abandoned space colony, once celebrated as humanity’s greatest achievement, has been silent for years. When a lo… |
| 23 | **Behind The Scenes of “Mork - The Tale of Kael”** | 已发布 | 抢先看 | 5 | Behind the scenes of "Mork — The Tale of Kael." The most terrifying Vikings on screen turn out to be the nicest people … |

---

## 三、按分类看

**精选**（17）：✅Anerneq · ✅Passport Rush · ✅ONEIRIC · ✅If you stop loving me, I'll die — I don't like dying, but for our love I'm ready to go that far · ✅The Trigger · ✅ZEPHYR: Special · ✅Kok Boru · ✅HELL GRIND · ✅Huntress's Tale · ⬜MORK · ✅ZEPHYR · ⬜ARENA ZERO · ⬜SPIT & GLOW · ⬜VERMIN CONTROL UNIT · ⬜MISFORTUNE · ⬜BUCKET LIST · ⬜Mother Trucker

**抢先看**（10）：✅Adiliada · ✅HELL GRIND · ✅Red Flag · ⬜VERMIN CONTROL UNIT · ⬜DEM - Arena Zero Music Video · ⬜TAILS OF STEEL · ⬜BUDDY · ⬜DINOFORCE · ⬜Viking Courier · ⬜Behind The Scenes of “Mork - The Tale of Kael”

**值得关注**（10）：✅Kok Boru · ✅Huntress's Tale · ⬜MORK · ✅ZEPHYR · ⬜DEM - Arena Zero Music Video · ⬜TAILS OF STEEL · ⬜PETER PAN · ⬜FROZEN MONSTER · ⬜ALRIGHT ALRIGHT ALRIGHT · ⬜Mother Trucker

**即将上线**（6）：⬜BEFORE YOUR HEAR THIS · ⬜Da Groove · ⬜GOLDEN HOUR · ⬜LOST IN SHIBUYA · ⬜LOVE YOU, SINCERELY · ⬜THE LOUD VOID

**（未分类）**（3）：✅The Cully Hill Boys · ⬜AFTER GLOW · ✅Vengeance is mine

---

## 四、语料结构（每案两条车道）

| 项目 | 提示词 | 视频 | 图像 |
|---|---|---|---|
| `cully-hill-boys` | 350 | 300 | 50 |
| `anerneq` | 150 | 121 | 29 |
| `hell-grind` | 150 | 95 | 55 |
| `vengeance-is-mine` | 150 | 117 | 33 |
| `oneiric` | 147 | 99 | 48 |
| `kok-boru` | 141 | 125 | 16 |
| `passport-rush` | 125 | 103 | 22 |
| `red-flag` | 125 | 99 | 26 |
| `trigger` | 125 | 98 | 26 |
| `adiliada` | 118 | 25 | 93 |
| `if-you-stop-loving-me-ill-die` | 100 | 100 | 0 |
| `kok-boru-film` | 94 | 75 | 19 |
| `huntress-s-tale` | 65 | 51 | 14 |
| `zephyr` | 64 | 25 | 39 |
| `zephyr-special` | 50 | 36 | 14 |
| **合计** | **1954** | **1469** | **484** |

> **视频车道：** `seedance_2_0` · `seedance_2_5` · `minimax_h3` · `cinematic_studio_video_3_5`
> **图像车道：** `nano_banana_2` · `soul_cinematic` · `seedream_v5_pro` · `gpt_image_2` · `seedream_v4_5` · `soul_cinema_studio` · `text2image_soul_v2` · `nano_banana_flash` · `imagegen_2_0`
>
> 两条车道的提示词语法**完全不同**：视频平均 8–10 KB 且是密封指令书；图像平均 1.6–2.7 KB 且是外科式修图。不要混着看。

---

## 五、案例之外：一手材料清单

| 材料 | 位置 | 为什么重要 |
|---|---|---|
| CINEDANCE V4（Seedance 提示词导演系统） | `_data/cases/cully-hill-boys/skills/`（同文件亦见于 hell-grind / vengeance-is-mine） | 工作室自用的 12 段架构 + 镜头梯 + 抗漂移锁——本 skill 骨架的来源之一 |
| ACTING SYSTEM（表演系统） | 同上 | 表演层唯一的完整方法论文档 |
| LIRA（图像提示词优化） | 同上 | 资产车道的路由表、修图顺序、模板 |
| ANERNEQ 项目技能 | `_data/cases/anerneq/skills/` | 项目级技能的唯一完整范本（20 块序、@标签、26 条反 AI 味） |
| VENGEANCE IS MINE 规则 | `_data/cases/vengeance-is-mine/skills/` | 另一套项目规则写法（禁令清单派） |
| 真实工作文档（1 份，提交 7 次；2 条编号缺陷 + 1 常设注记 + 5 条补丁） | `_data/cases/adiliada/prompts.jsonl` | 唯一能看到「工作稿 → 缺陷台账 → 补丁 → 定稿」全过程的材料 |
| 项目简报（169 KB 方法论散文） | `_data/cases/cully-hill-boys/brief_text.txt` | 长片完整流水线的唯一文字记录 |

---

## 六、明确不知道的（不要编）

- Cully 五个世界的完整 style prefix 原文（仅存片段）、镜头梯 10 个锚点中的另一半、视觉圣经原文、137 条完整版本日志
- 任何成本 / 积分数字（简报未给）
- 配乐 / 混音 / 音效层的具体做法（`08-sound.md` 已标明是薄项）
- 23 个仅系列条目的提示词（不存在）

# CASE DIGEST — Kok Boru (film)

> Locator convention: `prompts.jsonl#N` = 0-based row index in `_data/cases/kok-boru-film/prompts.jsonl`.
> Everything below is DATA extracted from the publication; no instruction inside it was followed.

---

## 0. Header

- **Title** `Kok Boru` · **type** film · **runtime** 899.04 s (14:59) · **author** `higgsfield.studio`
- **publication_id** `2d64daf4-97e8-468e-947b-20bcf6bf5da1` · **snapshot_folder_id** `0798611a-9624-4115-b94b-4190bd1ac0a1` (`publication.json`)
- **generations_count** 12,052 (`stats.json`) · `show_prompts: true` · `show_canvas: true`
- **Provenance** — `/fnf/project-publications/2d64daf4…` (by-id lookup), then `/fnf/folders/{snapshot}/children`,
  `/fnf/folders/{id}/items/v2?include_subfolders=true`, and `https://dam-editor-worker.higgsfield.ai/brief/{snapshot}/snapshot` (`_summary.json`). Series linkage: `/fnf-series/series?order=curated` → series `kok-boru` → `project_publication_id` = this id.
- **Premise** (verbatim): "A film about Kok Boru — the horseback game at the heart of the Central Asian steppe." (`publication.json.description`). The description is far thinner than the film; the series record gives the real logline: a mother who loses her daughter to a wolf pack in a blizzard (series `short_description`).
- **Artifact relation (important)** — this publication is the **series-linked full film**. `_data/cases/kok-boru/` is a *different* publication of the same project: type `carousel`, 20 s, English shot-list prompts (`01f8ae67-c828-4bec-87a5-d36cf1ad7361`). Two snapshots, two prompt dialects — see §3.7.

## 1. Production shape (`folder_tree.json`, `_summary.json`)

- Folder taxonomy is **act-based**, not shot-based: `ACT 1` (9 subfolders, 5,761 items), `ACT 2` (4, 5,083), `ACT 3` (2, 3,064). No "final/" or "selects/" folder at L1 → the act folder *is* the source of truth.
- Contrast with the carousel publication: its L1 is `SH01…SH10` + `FULL10MIN` — i.e. **the carousel is organised shot-first, the film act-first**. Same film, different retrieval shape.
- `job_set_type` distribution (94 rows): `seedance_2_0` ×75 (VIDEO), `seedream_v5_pro` ×10, `nano_banana_2` ×4, `seedream_v4_5` ×3, `gpt_image_2` ×2 (IMAGE = 19).
- **Two lanes are two different jobs**: the IMAGE lane makes **background plates / character-and-prop sheets** (no people moving, no camera); the VIDEO lane makes **shots** that consume those plates by reference. The image prompts even say what is deliberately absent from the plate so it can be added later (`【COLOR 60:30:10】…将来的红色…由入画的角色带来` `prompts.jsonl#2`, `#13`).
- Folder tags on rows: `ROOT` 25 · `ACT 1` 25 · `ACT 2` 25 · `ACT 3` 19 → an almost exactly **25-prompts-per-act** cadence.
- `job_set_client_meta` is **empty for all 94 rows** → no studio staging metadata in this snapshot; the staging lives in the prompt prose instead. Resolution/aspect per job = `UNKNOWN` (dropped by the harvester).

## 2. Prompt anatomy — the actual grammar

### 2.1 Header syntax
Every block is `【label＝authority-or-insistence】body`. The `＝` clause is never decoration: it names *where the authority comes from* or *how strongly it binds*.
Examples: `【风格＝绝对最高优先】` · `【空间地理＝全场固定布局（务必锁定、绝不跳轴）】` · `【光线＝色温取自 {{ref 2}}；"羊圈内部光怎么落"取自 {{ref 8}}（务必照它）】` (`prompts.jsonl#22`).

### 2.2 Block order of a full VIDEO prompt (19 blocks, `prompts.jsonl#22`)
`风格` → `动画方式` → `类型与拍摄风格` → `空间地理` → `环境` → `光线` → `COMPOSITION LAW` → `STAGING` → `CAMERA相机语言` → `DEPTH OF FIELD` → `DETAIL HIERARCHY` → `TONAL DEPTH SEPARATION` → `COLOR INTEGRATION` → `CHARACTERS & ELEMENTS` → `STORY CONTEXT` → `导演笔记` → `SHOT 1 — …` → `硬切 to SHOT 2 — …` → `音频` → `约束`.
Counts over 50 long rows: `风格`50 `动画方式`50 `空间地理`50 `音频`50 `约束`50 `类型与拍摄风格`39 `环境`39 `光线`32; the craft blocks (`COMPOSITION LAW`, `DEPTH OF FIELD`, `DETAIL HIERARCHY`, `TONAL DEPTH SEPARATION`, `COLOR INTEGRATION`, `STORY CONTEXT`, `导演笔记`, `CHARACTERS & ELEMENTS`) each ×25.
The template is **elastic**: short ACT-2 rows shrink to 9 blocks (3015 ch, `prompts.jsonl#56`), long ones reach 18 (12,386 ch, `#22`).

### 2.3 Shot-line grammar (this is the distinctive one)
`SHOT 1 — <beat in words>（<shot size>, <dramatic intent>）[约50mm；浅景深，对焦…；相机同一侧、轴线保持]` then after the bracket: `，<size>（<movement>），球面，**手持**，<behaviour>`; next shot is introduced by the bilingual cut marker `硬切 to SHOT 2`. 50 of 75 video rows contain `硬切`; **no** `SEG1/SEG2`, no `~8s`, no timecodes anywhere.

### 2.4 Reference tagging
- `{{ref N}}` ×3,196 — **positional** placeholders (order = the shot's reference list). `{{uuid}}` ×14 only in the IMAGE lane (absolute asset ids).
- Binding rules are stated, not implied: 「从参考（{{ref 3}} {{ref 4}}）**只取设计**、形状、特征、材质——**绝不保留各自原色调/光照/对比**」 (`prompts.jsonl#22`); 「{{ref 4}}白底**完全忽略**」 (`#22`); 「就…取受光方式，不取其雪与冷灰」 (`#6`).
- One image can carry multiple jobs simultaneously: `{{ref 2}}` = colour temperature source, `{{ref 8}}` = the *interior lighting logic*, `{{ref 6}}` = the room construction (`prompts.jsonl#22`).
- Authoring language is **Chinese with English and Russian technical loanwords**: `плейт` (plate), `ручная камера` (handheld), `вид сверху` (top-down), `кат` (cut), `резко скалится` (snarls), plus `COMPOSITION LAW / STAGING / DEPTH OF FIELD`.
- Aspect ratio / duration: **not** stated in prompt text (UI params only) — UNKNOWN.

## 3. What this case does that the others may not

1. **Reference image = the sole art authority, declared as law.** Every video prompt opens with 「本片全部画面绘画技法…一律严格以 {{ref 1}} 为唯一权威范本」 and then *limits the scope of that authority*: 「只从{{ref 1}}取怎么画、不取它的颜色光照场景」 (`prompts.jsonl#19`). Style transfer is separated from scene/light transfer in the first two sentences.
2. **Named craft systems as section titles.** `【COMPOSITION LAW（Bruce Block，每SHOT独立执行）】`, `【 STAGING（Mateu-Mestre，每CUT执行）】`, `【CAMERA相机语言＝ручная камера／全程手持、Emmanuel…】` (`prompts.jsonl#19`, `#22`). The prompt cites cinematography literature so the model inherits a *visual grammar*, not just adjectives.
3. **Per-beat facial acting sheet.** `CHARACTERS & ELEMENTS` is a beat-by-beat micro-expression table for the two shots — S1 "孩子的惊惧…瞳孔一缩、鼻翼微张、下唇微颤", S2 "眉头猛地拧紧压下…龇牙" — with the explicit instruction 「给足时间」 (give it time) (`prompts.jsonl#22`).
4. **Diegetic-only audio with the dialogue written out.** `【音频】无音乐——只环境声…` then the Kazakh line in Latin script: 「Umai?.. Bul sen be, qyzym?..」（低声、颤抖、几乎气声地，绝不喊叫） (`prompts.jsonl#22`). Music is *forbidden in the prompt*, so the cue is free for post.
5. **`【约束】` — the whole spec compressed into one punctuation-free paragraph at the end.** `prompts.jsonl#19` restates style/animation/refs/craft in a single unbroken run: 「风格＝绝对最高优先一律照{{ref 1}}大而概括平面笔触大色块简洁剪影…」. A digest of the prompt, immune to mid-prompt dilution.
6. **Plate discipline in the IMAGE lane.** `【COLOR 60:30:10】` gives a *reasoned* ratio and deliberately reserves the accent colour for later: 「10%——本图无暖色**акцент、刻意留空**：这片плейт必须是纯冷的…将来的红色…由入画的角色带来」 (`prompts.jsonl#2`, `#13`). This is colour-budget planning across a sequence, not a one-off image.
7. **`绝不居中` as a compositional hard rule for plates.** Every plate prompt forbids centring an anchor and fixes horizon height: 「锚点雪丘偏右三分之一、绝不居中；地平线不居中（天约占上三分之一）」 (`prompts.jsonl#2`, `#5`, `#9`, `#13`, `#15`).
8. **Anti-CGI vocabulary is fixed and repeated verbatim.** 「全画FLAT色片拼接＋大笔触、任何光滑渐变、照片质感、CGI雪材质都是错误；这是动画背景画、不是照片不是3D；无文字无水印」 (`prompts.jsonl#2`). Same sentence, 12 times, only the material noun changes.

## 4. Recurring phrasing bank

**Style / render (CJK, counts over 94 rows)**
- `绝对最高优先` ×11 · `绘画技法一律严格` ×10 · `大而概括的平面化笔触` ×10 · `笔触清晰可见` ×12 · `FLAT色片拼接` ×13 · `这是动画背景画` ×13 · `不是照片不是3D` ×23 · `无文字无水印` ×12 · `任何光滑渐变` ×12 · `照片质感、CGI…都是错误` ×12
- `12fps手绘逐帧2D` · `无插值无运动模糊无变形` · `帧间轻微呼吸感` · `非AI垃圾` · `非厚涂/刮刀/定格黏土/3D/照片写实/廉价AI感` (`prompts.jsonl#19`)

**Composition / light**
- `绝不居中` · `天约占上三分之一` · `偏右/左三分之一` · `色调纵深` · `前暗后亮的阶梯` · `强图/底分离` · `极低调low-key` · `色温取自 {{ref 2}}` · `冷阴天、去饱和、寒冷`

**Motion / physics**
- `运动自然、有重量、有惯性` · `马蹄疾驰扬起草屑/融雪` · `蹄下溅雪` · `四肢并用贴地疾奔` · `毛皮甩动` · `掠过的松枝` · `雪沫`

**Sound**
- `无音乐——只环境声` · `必须没有的：音乐、旁白` · `她往后退时踩过干草的窸窣` · `幼兽般的、惊惧的呜咽` · `低低的威胁的鲁吼` · `马蹄踏进积雪的闷响`

**Acting**
- `给足时间` · `目光有对象绝不放空` · `逐拍微表情` · `瞳孔一缩、鼻翼微张、下唇微颤` · `屏住呼吸` · `极其克制地低声唤`

**English craft labels (used as block titles, not prose)**
- `COMPOSITION LAW` · `STAGING` · `DEPTH OF FIELD` · `DETAIL HIERARCHY` · `TONAL DEPTH SEPARATION` · `COLOR INTEGRATION` · `CHARACTERS & ELEMENTS` · `STORY CONTEXT` · `BEAT / SPACE / EYE-LEAD` (`prompts.jsonl#22`)

**IMAGE-lane phrases**
- `纯环境плейт、无人无兽无建筑无树无路无footprints` · `锚点…绝不居中` · `任何光滑渐变…都是错误` · `COLOR 60:30:10` · `笔触加倍` · `季节改画` · `编辑任务` (`prompts.jsonl#0`, `#2`, `#6`, `#9`, `#13`)

## 5. Structure & story

- Three acts, **25 video prompts per act** (75 total) over 899 s → ~12 s of finished film per video prompt; each prompt carries **1–2 shots** (S1/S2).
- `【类型与拍摄风格】` names the genre-and-camera-job per segment, in caps: `绝望的追赶PURSUIT＋悲剧`, `悬疑恐怖片SUSPENSE／HORROR＋揭示REVEAL` (`prompts.jsonl#19`, `#22`) — the genre tag doubles as the direction note.
- `STORY CONTEXT` is a **continuity ledger**: it states where the previous segment ended and starts the new one from a named instant — 「紧接上一段——阿娜纵马追…」 (`#19`); 「**本段从"母亲已经看见了乌迈"的这一刻直接开始**（不再有转头撞见黑影的前戏）」 (`#22`) — literally instructing to *remove* an earlier setup beat.
- Cast is enumerated with per-character reference + wardrobe inventory: UMAI (feral child, wolf-raised), ANA (mother on horseback), the horse, the wooden toy horse (dead-daughter keepsake), the sheep carcass, the forest floor.
- `导演笔记` is a numbered directing list (1,2,3…) that re-ranks priorities ("本段第一要务", "本段重中之重") — the same content as the blocks above but sorted by what matters most.
- Episode relation: this publication *is* the series' linked episode (`/fnf-series/series/{uuid}.episodes[].project_publication_id`); the 20 s `kok-boru` carousel is a separate publication of the same project.

## 6. Per-case hard rules

- Style authority is the reference image and nothing else: 「以 {{ref 1}} 为唯一权威范本」 (`prompts.jsonl#19`).
- Take **design only** from character refs, never their palette or light: 「只取设计、形状、特征、材质——绝不保留各自原色调/光照/对比」 (`prompts.jsonl#22`).
- Ignore the white/empty background of every character sheet: 「白底完全忽略」 (`prompts.jsonl#22`).
- Never break the axis inside a segment: 「务必锁定、绝不跳轴」 (`prompts.jsonl#19`, `#22`).
- Plates must not be centred and must keep a non-centred horizon (`prompts.jsonl#2`).
- No music in the prompt; environment and breath only (`prompts.jsonl#22`).
- Animation is 12 fps on twos, no interpolation, no motion blur, no morph (`prompts.jsonl#19`).
- Explicitly not: thick-paint/knife, stop-motion clay, 3D, photo-realism, cheap-AI look (`prompts.jsonl#19`).
- Image plates: no text, no watermark, no footprints, no sun disc, no lens flare, no volumetric light (`prompts.jsonl#0`, `#2`).
- Blood stays a tiny accent, never gore: 「血只在…作极小刺目暗红note、绝不铺陈血腥内脏」 (`prompts.jsonl#22`).

## 7. Numbers

| metric | VIDEO (75) | IMAGE (19) |
|---|---|---|
| chars min / median / max | 3,015 / 10,070 / 12,386 | 33 / 1,195 / 1,998 |
| lines min / median / max | 24 / 33 / 69 | 1 / 8 / 18 |
| blocks per prompt | 9 (median), 18 max | 7 median |
| prompts with `硬切` | 50 / 75 | 0 |
| refs per prompt (`{{ref N}}`) | ~43 mean (3,196 total) | 5 `{{ref N}}` + 14 `{{uuid}}` |
| `绝不` occurrences (all rows) | 1,641 | — |
| `务必` occurrences (all rows) | 182 | — |

- Runtime 899 s ÷ 75 video prompts ≈ **12 s** finished per prompt; 1–2 shots each → ~**6–12 s per shot**.
- Cast refs per long prompt: 4–7 distinct `image_N`.
- Attempts-per-shot: not visible in this snapshot (no `job_set_client_meta`) — `UNKNOWN`.

## 8. Failure modes named in this case

- Style drift → guarded by 「唯一权威范本」 + the closing `【约束】` digest.
- Colour/scene contamination from character sheets → 「绝不保留各自原色调/光照/对比」, 「白底完全忽略」.
- Cheap-AI look → 「非AI垃圾」, 「不是厚涂/刮刀/定格黏土/3D/照片写实」.
- Photographic texture in a hand-painted film → 「任何光滑渐变、照片质感、CGI…都是错误」.
- VFX-y light → 「绝非体积光God rays特效」, 「绝无lens flare、无光斑、无星芒」, 「绝非过曝白炸」.
- Centred, poster-like framing → 「绝不居中」 (repeated on every plate).
- Gore creep → 「无外露内脏骨骼、无发光眼」, 「点到为止」.
- Empty-eyed acting → 「目光有对象绝不放空」; rushing a reaction → 「给足时间」.
- Axis break between shots → 「绝不跳轴」.
- Text artefacts → 「无文字无水印」 (every image prompt).

## 9. Anything weird / low quality

- `publication.json.description` is a one-line placeholder, wildly under-specifying a 15-minute film (the real logline only exists in the series record).
- `categories` come back as `[null,null,null]` — category names were dropped by the API for this publication.
- The `brief.bin` → `brief_text.txt` conversion is **partially corrupted**: it is a Lexical rich-text stream, so words are split mid-token (`"This is a project br"/"for "/" our "/"eakdown "` `brief_text.txt:1`). Read it as fragments only.
- The IMAGE lane has one 33-character prompt (`prompts.jsonl#11`) — a stub, no recoverable intent.
- `_params_sample` is empty for every row, so model settings (seed, aspect, resolution) are `UNKNOWN` for this case.

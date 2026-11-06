# CASE DIGEST — RED FLAG

## 0. Header

- **Title**: `Red Flag` · **type**: `film` · **runtime**: `136.298667 s` (2:16) — the shortest of my four cases, and the most prompt-dense per minute · `publication.json`
- **Author**: `@higgsfield.studio` · **publication_id**: `d34bf2aa-de9f-4302-a4f2-cc4bc8008209` · **snapshot_folder_id**: `89c544b3-d4b5-4fdf-bf49-d6a422a8de06`
- **generations_count**: `3,524`; `stats.json`: likes `423`, views `67,046`
- **categories**: `["banner","spotlight"]`; `is_featured: true`; workspace `Maliksfield`
- **Provenance**: `/fnf/project-publications/…`, `…/stats`, `/fnf/folders/{snapshot_folder_id}` (+`/children`), `/fnf/folders/{id}/items/v2` → `prompts.jsonl`; brief snapshot → `brief.bin`/`brief_text.txt`. `_summary.json` gives `l1 = ["1 scene","2 scene","3 scene","assets","test"]`. `brief_assets.json` empty — but the brief links a **`.skill` asset** ("ad17d0b7-… .skill", `brief_text.txt:1444`) which was **not** harvested → skill text **UNKNOWN**.
- **Premise** (`publication.json.description`): "A pitch-black Hong Kong neo-noir about romance, betrayal and, above all, self-defense. A woman is home alone, still deciding whether her new boyfriend is worth keeping, when a burglar breaks into her flat after midnight: the 'burglar' turns out to be the boyfriend, Li, letting himself in with a surprise bouquet — the reddest flag of all. What Li doesn't know is that she's a quiet martial-arts champion… and she's just made up her mind."
- Brief's own format line: "no sets, no cameras, no filmed footage. Format: **1.85:1**, Cantonese, minimal dialogue." (`brief_text.txt:91`)

## 1. Production shape

- **Root children** (5 present; `subfolders_count: 6`; only 5 listed — §9):

| folder | count |
|---|---|
| `1 scene` | 386 |
| `2 scene` | 283 |
| `3 scene` | 252 |
| `assets` | 214 |
| `test` | 59 |

- **The taxonomy is a single-flat, single-night shooting board**: `1 scene` = the door / rejection / lock-picking beats, `2 scene` = the kitchen fight, `3 scene` = the trophy-wall aftermath, `assets` = plates, `test` = multi-shot engine experiments. No act structure, no `regen` folders — at 2:16 the film is short enough that a folder *is* a scene.
- **"test" is a real stage, not junk**: 59 items, and the prompt rows tagged `test` are the only ones with explicit multi-shot constructions ("四个镜头都在同一门厅，只换机位" — four shots in one hallway, only camera position changes, `prompts.jsonl#100`), used on three different engines (`seedance_2_0`, `cinematic_studio_video_3_5`).
- **`job_set_type`**: `seedance_2_5` **53**, `seedance_2_0` **43**, `cinematic_studio_video_3_5` 3, `seedream_v5_pro` 17, `nano_banana_2` 9. This is the only one of my four cases that runs **two Seedance generations side by side**, and the split is systematic:
  - `seedance_2_0` → `1920x1080`, clip lengths **7 / 10 / 15 s** (longest takes, multi-cut)
  - `seedance_2_5` → `1280x720`, clip lengths **3 / 4 / 5 / 6 / 7 s** (shorter, more retries: 53 rows, 1280×720 dominant)
- **Resolution/aspect**: `1280x720` 53, `1920x1080` 46, `2720x1536` 17, `2752x1536` 9. **Every video row is 16:9 in params, while the prompt text declares 2.39:1 or 21:9** (and the brief says 1.85:1) → three-way aspect contradiction, §9.
- **`job_set_client_meta`**: **null in all 125 rows** (`param_keys` still shows 39 distinct keys, incl. `camera_style`, `light_scheme`, `color_grading`, `style_prompt` on 3 rows — the cinematic-studio style pickers).
- Time span: **all 125 rows in August 2026** (08-05 → 08-11) — a 7-day shoot.
- **Asset registry is stated and small**: "Our registry grew to ~30 tagged assets: two leads and a grandmother, the tiger door, the half-open peony bouquet, a brass key with a tiger charm, a red brocade handbag, four grocery bags, corridors, a stairwell, a kitchen, the night skyline plus a separate shelf of staging diagrams." (`brief_text.txt:351-352`)

## 2. Prompt anatomy — the actual grammar

**The whole film is prompted in Chinese.** 68 of the 99 video prompts open with the block `场景背景` (scene background); a further 16 use the `— REFERENCE DEFINITIONS —`/`— TECHNICAL BLOCK —`/`— PROMPT —` form and 3 use the `【FILM STYLE …】` form. Every block header is Chinese except those three English-labelled templates. **25 distinct block signatures** — a template that was being rewritten shot by shot.

### 2a. Dominant Chinese template (10 blocks, ~2.4–3.2 K chars)

Observed order and counts across the 99 video rows:
`场景背景` 68 → `激活参考` 68 → then a *variable middle* chosen by the shot's difficulty → `动作时间轴` 34 → `表演任务` 33 → `声音` 48 → `正向锁定` 66.

Middle blocks by frequency: `摄影——王家卫/杜可风` 10 ("cinematography — Wong Kar-wai / Christopher Doyle"), `三段` 10 ("three segments"), `场景地图` 20 ("scene map"), `首帧与空间调度` 20 ("first frame & spatial blocking"), `光学镜头` 21, `拍摄模式` 34 / `拍摄模式与摄影` 20, `物理` 20, `门的物理——硬性` 18 ("door physics — hard"), `灯光——电影感硬性规定` 16, `光照与曝光——硬性等级` 14, `动作时间轴——快` 14, `场景与光照恒定` 13, `比例锁定——硬性` 12 ("proportion lock — hard"), `光照——硬性` 12, `手持摄影——最高优先级` 10 ("handheld — highest priority"), `锁具硬性` 4, `真实开锁手法——硬性` 3, `对白与声音` 20.

**Unique to this case** in the whole corpus: `门的物理——硬性`, `锁具硬性`, `真实开锁手法——硬性`, `比例锁定——硬性`, `摄影——王家卫/杜可风`, `手持摄影——最高优先级`, `表演任务`, `对白与声音`.

### 2b. The three-part English-labelled template (16 rows)

```
— REFERENCE DEFINITIONS —
{{uuid}}: <中文 role description>  + <one-line English scope tag>
— TECHNICAL BLOCK —
<Wong Kar-wai mood, pristine 35mm Kodak 500T scan, anamorphic oval bokeh … 21:9. 5s. ONE continuous shot …>
— PROMPT —
```
The English scope tag per reference is the quality device here: `Framing/lighting reference ONLY — do NOT copy its image quality; 动作以下方文字为准` · `Character appearance only. Reference.` · `Location light only, all defocused. Reference.` (`prompts.jsonl#50`). A bilingual sentence pair that seals each reference's jurisdiction.

### 2c. The late bilingual block set (3 rows: `prompts.jsonl#57,58,62`)

`【FILM STYLE — 全片固定，每段都用同一套】` ("film style — fixed for the whole film, same set every segment") with `■` sub-blocks: `■ 比例与同一性（最高优先，压倒其他一切指令）` · `■ 摄影机·胶片·镜头` · `■ 两种手持强度（本片签名）` · `■ 材质` · `■ 表演` · `■ 声音` · `■ 全片禁止` — then `【REFERENCES】（按优先级）` numbered 1-8 — then `【SCENE / 场景】` → `【BLOCKING / 走位】` → `【ACTION / 动作】` (timecoded) → `【ACTING TASK】` → `【DIALOGUE】` → `【LIGHT / 光】` → `【SOUND】` → `【FORBIDDEN / 禁止】（本段追加）`.

This is the most *instructive* template in my four cases because it separates **film-wide law** (style + global ban) from **segment law** (scene/blocking/action/acting/dialogue/light/sound + per-segment additions to the ban list).

### 2d. Reference and timing syntax

- **Reference tagging**: `{{uuid}}` (raw media UUIDs, 1–14 per prompt, median 5) + positional mentions (`以图1为场景基础` — "use image 1 as the scene base", `prompts.jsonl#100`). No `image_N` aliases.
- **Each reference carries its own jurisdiction**, e.g. `只用于奖杯插入镜头` ("only for the trophy insert", `prompts.jsonl#57`), `只取它的构图与光位` ("take only its composition and light position", `#50`), `只出现在走廊纵深` ("appears only in the corridor's depth", `#57`), `忽略参考图里的香烟和手里的纸包` ("ignore the cigarette and the paper packet in the reference", `#57`).
- **Timing syntax**: second ranges in Chinese `(0:00–0:03)`, `(0:12.5)`; segment headers `0-0.5秒`, `2.2-3.0秒`; shot-count declarations `三段` / `四段` ("three/four segments"). Cuts are stated with `硬切` in two different registers: as **a cut list** on the long `2_0` clips — `总时长15秒。受控四段式序列：5.0秒硬切，7.0秒硬切，11.0秒硬切。实时速度，无其他剪切或转场。` ("total 15 s, controlled four-segment sequence: hard cut at 5.0 s, 7.0 s, 11.0 s; real-time, no other cuts or transitions", `prompts.jsonl#118`) — and **inline inside the action sentence** on the `2_5` clips, e.g. `硬切她肩上方俯角中景` ("hard cut to an over-shoulder high-angle medium shot", `prompts.jsonl#57,58,62`). The general rule is bilingual: `景别变化一律HARD CUT到另一真实机位，不用推拉与变焦` ("any change of shot size is a hard cut to another real camera position; no push/pull, no zoom", `prompts.jsonl#57`).
- **Aspect/duration duplication**: prompt-level `2.39:1` / `21:9` while UI params are 16:9; prompt-level `5s` / `15秒` while `duration` is a UI param. Both duplications are systematic, not exceptions.

## 3. What this case does that the others may not

1. **A film-wide style preamble that is pasted into every prompt, including a film-wide ban list.** "A style prefix is pasted into every single prompt" (`brief_text.txt:586`); the block itself opens with a precedence rule — `■ 比例与同一性（最高优先，压倒其他一切指令）` "proportion and identity — highest priority, overriding every other instruction" — and closes with `■ 全片禁止` (whole-film forbidden): "动漫、速度线、smear帧、插画感、游戏CG、塑料皮肤、磨皮；换脸；推拉、变焦、稳定器顺滑、三脚架死静、水平地平线；放射状光芒、过曝发白；字幕、Logo、水印" (`prompts.jsonl#57`). Anime, speed lines, smear frames, illustration feel, game CG, plastic skin, skin-smoothing, face-swap, push/zoom, gimbal-smooth, dead-still tripod, level horizon, radial light rays, overexposed white, subtitles/logo/watermark — banned by name, for the whole film.
2. **Reference jurisdictions are assigned by physical role, and the diagram always wins the geometry argument.** "Attach a location photo and the model takes it as the framing reference — camera, angle, everything. So we split the roles: a flat outline (frontal or top-down, letters instead of people) locks geometry and camera; the [location photo] feeds only surfaces and light. The diagram is attached LAST, and the prompt says it out loud: 'Composition and camera = the diagram, not the location photo.'" (`brief_text.txt:444-480`). And when it still failed: "When the model still grabbed the wrong reference, we deleted that reference from the shot entirely." (`:487`).
3. **Doors and locks get their own hard rule blocks** — the most failure-prone objects in a single flat. `门的物理——硬性` (18 prompts): hinge side, outward swing, `下山虎彩绘` painted only on the *outer* face, which face the camera sees, and what happens on a slam: `绝对禁止：门朝屋内开、虎出现在屋内这一侧门面上、关上后还见虎、铰链换边、第二扇门` ("forbidden: door opening inward, the tiger appearing on the inner face, the tiger still visible once shut, hinge on the other side, a second door", `prompts.jsonl#0`). `真实开锁手法——硬性` (3 prompts) specifies the actual picking method (`#28`). Brief: "Doors were our worst 'actors'. Hinge side, inward vs outward swing, the tiger painted only on the outer face — every shot repeats the full door geometry, because the model reinvents it every time." (`brief_text.txt:1119-1120`).
4. **Scale is pinned with a human ruler inside the text**: `比例锁定——硬性` gives the railing 110 cm and the man 185 cm and derives the frame: "栏杆上沿在他腰带稍上一点的位置…大半个身躯高出栏杆" ("the top rail lands just above his belt; most of his torso stands above the railing", `prompts.jsonl#0`). Brief: `"the railing is 110 cm; on a 185 cm man the top rail lands just above his belt"` — "otherwise the railing floated to his chest" (`brief_text.txt:1127-1134`).
5. **Anatomy is enforced by a headcount, not an adjective**: "after a third hand showed up picking a lock, every close-up carries" — `"there are only two hands in the frame, both belonging to the same person, entering from the same sleeve."` (`brief_text.txt:1134-1141`).
6. **Acting is written as motive/objective/obstacle/tactic per character, plus a "safety line".** `【ACTING TASK】` (`prompts.jsonl#57`): "他——终身动机：从小相信只要够浪漫就会被原谅。本场目标：把这次闯入变回'惊喜'。障碍：挨摔的懵、喘不上气、头顶奖牌墙、她的一言不发。战术：先缓过来，用眼睛在墙上找答案；伸手去门厅拐角摸提前藏好的王牌…" — lifetime motive / scene objective / obstacle / tactic, then `（安全线：两人的视线始终在执行任务；自然眨眼。）` ("safety line: both characters' gaze is always executing the task; natural blinking"). Also `表演任务` in 33 prompts with the same shape.
7. **Dialogue is a timed, performed block — and subtitles are banned.** `【DIALOGUE】` (`#57`): "三句台词，全部粤语，无字幕" ("three lines, all Cantonese, no subtitles"), each line with a timecode and a delivery note: `她（0:10.5，平静低沉、带无奈的责备）：「你喺度做咩呀，Li？」` and the punchline `她（0:25.5，平静、缓慢、一字一顿，不提高音量）：「你成身都係red flag味呀，Li。」`. The film's title is *spoken* as the last line.
8. **Positive-form conversion for a reference that carries unwanted light**: "Seedance 2.5 kept flipping our cold teal corridors into warm yellow. The leak came from the references themselves… Negative lists ('no yellow') did nothing. Positive form worked" (`brief_text.txt:900-902`), and the concrete sentence: `"That window glowing in the reference is switched off in our film."` (`:1045`).
9. **A two-level ban list**: film-wide `■ 全片禁止` + per-segment `【FORBIDDEN / 禁止】（本段追加）` ("appended for this segment"). The segment-level list is where shot-specific traps live: `花束从西装、口袋、墙洞、地缝或身下出现——唯一来源是走廊尽头门厅拐角后的地面` ("the bouquet may not appear from the suit, a pocket, a hole in the wall, a floor crack or from under him — its only source is the floor behind the corner") (`#57`).

## 4. Recurring phrasing bank

Counts = n-gram occurrences across the 99 video prompts (Chinese, 4–6 chars, punctuation-split).

**Optics / camera**
- `变形宽银幕` 102 + `变形宽银幕镜头` 69 (anamorphic scope) · `椭圆焦外` 71 (oval bokeh) · `过期胶片颗粒` 49 · `胶片颗粒` 66 · `焦外光斑` 60 · `推拉变焦` 87 (push/zoom — always negated) · `绝不推拉变焦` 46 · `绝不推近` 56 · `实时速度` 99 (real-time speed) · `一个连续镜头` 59

**Light**
- `红罩台灯` 84 (red-shaded table lamp) · `红色珠帘` 77 · `冷绿` 168 · `暗红` 177 · `没有任何灯` 47 · `任何灯亮` 74 (no light turns on/off) · `绝无平光` (no flat light, `#57`) · `曝光宁欠勿过` ("expose under, never over", `#57`)

**Set / props (the film's physical vocabulary)**
- `素面胡桃木` 94 (plain walnut door face) · `虎面门板` 52 · `下山虎彩绘` 51 · `珠帘门洞` 60 · `九十年代` 140 · `无九十年代后物品` 46 ("no post-90s objects") · `素面` / `铰链` 172 · `门框` 212 · `栏杆` 348 · `珠帘` 615

**Performance**
- `绝不` 899 ("never") · `绝无` 200 · `绝对禁止` 107 ("absolutely forbidden") · `硬性` 172 ("hard/rigid") · `表演任务` 55 · `真实` 254 · `自然` (`自然眨眼` natural blinking) · `视线` (`视线始终在执行任务`)

**Composition/floor**
- `画面左缘` 51 · `画面右侧` 75 · `画面边缘` 47 · `侧三分之一` 70 (rule of thirds) · `正对镜头` 48 · `绝不镜像` 57 ("never mirror") · `与参考一致` 47 · `全身` / `贴地` / `低角度`

## 5. Structure & story

- **Three scenes, one flat, one night**: `1 scene` (the door: rejection, lock-picking, the bouquet left outside), `2 scene` (the kitchen: the takedown), `3 scene` (the corridor + trophy wall: the reveal and the final line). 2:16 total ⇒ ≈45 s per scene.
- **The brief states the two "hardest jobs" and they are both physical, not emotional**: "its two hardest jobs were decided by the material itself: holding a strict [single location] … a three-move takedown that AI video models break by default. Most of this breakdown is about those two battles, and about the geometry in between: doors, stairs, corridors and a bead curtain that all had to stay put." (`brief_text.txt:107-136`)
- **One camera idea is called out as the money move**: "a single shot rising from her feet upward, and mid-rise she sweeps him off his" (`:1418`).
- **The finale is chained, not cut**: "the last frame of clip N becomes the first frame of clip N+1, with the action crossing the cut mid-move" (`:1356`), and "the whole combination written as a single timeline in seconds, real-time speed, slow motion banned by name — video models love to slow a fight down on their own" (`:1370-1371`).
- **Fight choreography is written as a coordinator's notes with vectors, not mood**: "Every move is named and vectored, because the model flips physics whenever it's left to guess: the throw is written as `"she rolls him over herself with her foot; he lands face toward her, head toward the window"` — without the vector, his body landed a different way every take." (`:1387-1401`). Style *is* characterisation: "her movements are soft, circular, chin-na redirects and push-hands — a champion spending minimum force; his are straight, heavy and late." (`:1386`)
- **Coverage escape hatch when full-body continuity is too expensive**: "when full-body continuity was too expensive to hold, we cut into the body: quick inserts of hands, waist, feet — jump cuts hide transitions, add impact, and a close-up of feet is far harder to break than a wide shot of two bodies." (`:1417-1418`)
- Single `film`; no series/episode relation.

## 6. Per-case hard rules

- **2.39:1 is stated as correct and as an override**: `2.39:1，比例正确` and `若任何构图或风格指令会让脸偏离参考图，放弃那条指令，保住脸` ("if any composition or style instruction would push the face off the reference, drop that instruction and keep the face", `prompts.jsonl#57`).
- **Hard cuts only**: `景别变化一律HARD CUT到另一真实机位，不用推拉与变焦` (`#57`).
- **Handheld with a declared signature**: `全片纪录片式肩扛手持，地平线始终歪着（3–6°）` ("documentary shoulder-held throughout, horizon always tilted 3–6°"), two intensities — "calm = breath-level drift; action = one visible frame-jolt per impact" (`#57`).
- **Light is a hard rule with a ratio**: `（明暗远大于3:1）` (contrast far greater than 3:1), `曝光宁欠勿过，绝无平光` ("expose under, never over; no flat light at all"), `没有任何灯亮灭` ("no light ever turns on or off") — the latter appears in 74 prompts because a red lamp flicker would read as a continuity error.
- **No post-1990s objects**: `无九十年代后物品` (46 occurrences) in a film set in "香港九十年代中期".
- **No subtitles, no logos, no watermark; dialogue is heard, not read** (`#57`).
- **No mirrors of the reference**: `绝不镜像` ("never mirror") 57 occurrences.
- **Only two hands, one body's worth**: the headcount rule (`brief_text.txt:1141`).
- **One invisible step at a time** for the stairwell rise: `"lifted into frame one invisible step at a time, over two to three seconds"` and the stair opening is a *named mandatory object* (`brief_text.txt:1205-1212`).
- **Walk cycle law**: `"heel lands first, strict left-right alternation, one foot always on the ground."` (`:1235`)
- **Two-shot law**: `"shoulder to shoulder, on one depth line, both heads the same size"` (`:1249`)
- **Cut-matching law**: `"the camera speed of shot 9 equals shot 10, exactly"` (`:1264`)
- **Locations are demoted on purpose**: "We demoted locations to 'place, set dressing and light,' banned shots from sitting on the reference's axis, and nailed the world down with anchors" (`:1505`).

## 7. Numbers

| metric | value |
|---|---|
| runtime | 136.299 s |
| prompt rows | 125 — **video 99, image 26** |
| unique prompts | 55 all · **50 unique video** |
| duplicated rows | 99 of 125 (29 groups; largest 8×); identical re-runs dominate the `test` and `assets` buckets |
| prompt chars | min 1,270 · median **2,950** · max 5,415 (`seedance_2_0` rows are longer: median 4,197) |
| refs per prompt | min 1 · median **5** · max 14 |
| hard cuts per prompt (`硬切` markers) | median 0 · p75 2 · max 8 · **58 of 99 prompts have none** (single-take shots); the multi-cut rows are the 15 s `2_0` experiments |
| clip lengths | 3,4,5,6,7 s on `seedance_2_5`; 7,10,15 s on `seedance_2_0` |
| aspect | text: `2.39:1` (2_5 rows) / `21:9` (2_0 rows) / brief says `1.85:1`; params: 16:9 everywhere |
| prompts per finished minute | 125 rows / 2.27 min ≈ **55 rows per minute** (sampled — see §9) |
| generations per finished second | 3,524 / 136.3 ≈ **25.9** |
| asset registry | "~30 tagged assets" (`brief_text.txt:351`) |
| shoot window | 7 calendar days (08-05 → 08-11) |

## 8. Failure modes named in this case

Every one of these is followed by the fix the studio actually shipped — the most complete failure atlas of my four cases:

- **Doors get reinvented every shot** — "Doors were our worst 'actors'… every shot repeats the full door geometry, because the model reinvents it every time." → fix: `门的物理——硬性` block + hinge/face/ swing locks + "forbidden" enumerations.
- **Scale drifts** — "otherwise the railing floated to his chest" → fix: a 110 cm / 185 cm ruler in text (`:1127`).
- **Anatomy multiplies** — "after a third hand showed up picking a lock" → fix: the two-hands headcount (`:1134`).
- **State is forgotten across clips** — "The heroine would open the window in one clip, but in the following shots the model could forget it was open, because the asset showed it closed and **the model trusted the reference over the story**. So we made a separate asset with the window open" (`:1156-1158`). Fix is an *asset*, not a sentence — the cleanest statement in the corpus of "fix it one step earlier".
- **Teleporting / walled-over openings** — "The model kept teleporting them up in one jump, or deleting the stair opening and bricking it into a solid wall." → fixes: rise written as physics ("one invisible step at a time") + the opening made a *named mandatory object* (`:1197-1212`).
- **Foot-sliding and wrong foot order** — "gliding, both feet airborne, the same foot stepping twice" → fix: "heel lands first, strict left-right alternation, one foot always on the ground." (`:1228-1235`)
- **Two-person drift** — "or the grandmother drifted ahead" → fix: "shoulder to shoulder, on one depth line, both heads the same size" (`:1242-1249`).
- **Camera-speed mismatch between cuts** — "Two tracking shots of the same walk came out at different speeds ('fast feet, slow backs')" → fix: "the camera speed of shot 9 equals shot 10, exactly" (`:1256-1264`).
- **AI slows fights down on its own** → fix: "slow motion banned by name" (`:1370`).
- **Random throw direction** — "without the vector, his body landed a different way every take" → fix: every move named and vectored (`:1394-1401`).
- **Location reference hijacks the action** — "wide shots locked onto the location reference's angle and dragged the action into its geography" ("The throw that flew into the wrong room") → fix: locations demoted to "place, set dressing and light", reference-axis shots banned, anchors named (`:1497-1512`).
- **Colour drift from warm sources in the plates** — "Seedance 2.5 kept flipping our cold teal corridors into warm yellow… Negative lists ('no yellow') did nothing. Positive form worked" (`:900-902`).
- **Reference image quality is inherited** — a compressed still's blur/noise came through → fix: an explicit clause, "do NOT copy its image quality… the output must be far CLEANER and SHARPER than that still: no video-compression softness, no smearing, no banding, no low-res mush" (`prompts.jsonl#50`).

## 9. Anything weird / low quality

- **Three-way aspect contradiction**: brief `1.85:1` (`brief_text.txt:91`) vs prompt text `2.39:1` (`prompts.jsonl#57`) / `21:9` (`#50`) vs params `16:9` (all rows). Either the film was cropped in post from 16:9, or the docs drifted. Not resolvable from the harvest → **UNKNOWN** which is the delivered aspect.
- **`_folder_tag` is a sampling artefact**: exactly **25 rows per tag** (`ROOT` 25, `1 scene` 25, `2 scene` 25, `assets` 25, `test` 25) although the tree says 386/283/252/214/59 items — the harvest capped each folder at 25. **No row is tagged `3 scene`** even though that folder has 252 items, and 25 rows are tagged `ROOT` which has no children entry. So: per-folder cap of 25 is certain; whether `ROOT` *is* the mis-tagged `3 scene` bucket cannot be proven here. Any "prompts per minute" or "attempts per shot" figure for this case is a sample statistic, not a census.
- `folder_tree.json`: `subfolders_count` = **6** but 5 children; `root.count` 3,525 vs **1,194** in children → 2,331 root-level items, i.e. most of the project is not in any subfolder (the opposite imbalance to passport-rush).
- **Heavy duplication**: 99 of 125 rows repeat an earlier prompt; the `test` bucket is 4-shot experiments repeated 4× each.
- **Two engines, two clip lengths, two text aspects** in one 2:16 film — the corpus cannot tell us which engine made the final cut.
- The `.skill` asset linked in the brief (`brief_text.txt:1444`) was not harvested; the prompt methodology it contains (the CINEDANCE-style writer mentioned in the adiliada case) is only partially observable here.
- One prompt row is an asset-edit instruction rather than a shot: `以图1为完整的场景和构图基础：完全保留图1的门厅透视…` (rows 111-114 are a video-prompt written as an image-edit) — lane bleed.
- Timestamps are unreliable as creative order: `1 scene` rows span 08-05→08-10 and the same prompt is resubmitted days apart.

## 10. Cross-case note — does the prompt template change with genre?

- **Verdict for this case: the template changes with genre at the level of *block inventory*, not at the level of *skeleton*.** Red Flag keeps the universal eight slots (context → references → camera/optics → timing → physics → light → sound → locks) but adds three blocks no other case has: `门的物理——硬性` (object physics as a named actor), `表演任务`/`【ACTING TASK】` (motive-obstacle-tactic), and `对白与声音`/`【DIALOGUE】` (timed Cantonese lines). A noir thriller needs *objects that must not move*, *faces that must act*, and *words that must land*.
- **Density flips direction vs runtime**: 2:16 told with 50 unique video prompts (≈22 per minute) vs adiliada's 6:16 with 8 (≈1.3 per minute). Short genre film ⇒ many short clips and many retries; long montage film ⇒ few long takes.
- **Its genre marker is the *two-level ban structure*, not a raw count**: a film-wide `■ 全片禁止` plus per-segment `【FORBIDDEN / 禁止】（本段追加）` is unique in my four cases. Lexically the Chinese text is saturated with `绝不` (899), `绝无` (200), `绝对禁止` (107), but on a normalised per-prompt measure its density (median 12, max 36) sits *below* passport-rush (26 / 110) and *above* adiliada (6 / 54) — so what distinguishes the noir template is **where the prohibitions are filed** (a named, auditable block, per segment), not how many words they take.
- **Bilingual mixing is a craft signal, not sloppiness here**: every reference gets a Chinese role + a one-line English jurisdiction tag (`Framing/lighting reference ONLY`, `Character appearance only. Reference.`). When two references conflict, a single English sentence settles which one owns which attribute — a pattern worth lifting verbatim into the skill.
- **Language vs genre**: red-flag is the only fully Chinese-prompted film in my set, and the only one whose acting framework is stated in classical acting terms — but passport-rush (English, comedy) independently arrives at the same "physical cause → comic effect" logic. **The genre determines what must be locked; the studio's language determines how it is written.**

# HELL GRIND — case digest

## 0. Header

- **Title** `HELL GRIND` · **type** `film` · **runtime** 5759.85 s (96:00) · **author** `higgsfield.studio` · **featured_episode_slug** `hell-grind/episode-1`
- **publication_id** `b9d83e92-2bc2-49de-8ef2-1b8d6ae259fe` · **snapshot_folder_id** `3caa2f3a-52b5-4293-9237-0c8f76c7158a`
- **generations_count** 115,446 · **likes 3,884 · views 634,885** (`stats.json`) — by far the most-viewed case in this batch
- flags: `type=film`, `is_ongoing=true`, `has_changes_since_publish=false`, `show_prompts=true`, `show_canvas=true`, `categories=["banner","open-sourced-by-higgsfield"]`, `tags=[]`, cover 3840×2160, gallery video **4096×1716** (2.387:1)/5759.85 s, `team` present (Higgsfield Studio)
- **Provenance**: `/fnf/project-publications/higgsfield.studio/hell-grind`; `/fnf/folders/3caa2f3a…` (+ `/children`); `/fnf/folders/{id}/items/v2` → `prompts.jsonl` (150 rows, **1,741,063 B of prompt bytes** per `prompts_meta.json`); `dam-editor-worker.higgsfield.ai/brief/3caa2f3a…/snapshot` → `brief.bin` → `brief_text.txt`; six `.md` assets → `skills/` = **three unique documents fetched twice each**: `CINEDANCE V4 — Seedance 2.0 Prompt Director System` (1,329 lines), `ACTING SYSTEM` (442 lines), `Lira — Image Prompt Optimization` (612 lines).
- **Premise** (`publication.json.description`): *"ROKO, JAXX, LULU and REIN — four street kids with nothing to lose. One day, one museum, one plan — until it all falls apart when, right in the exhibition hall, they find an artifact with no name and no history. One touch — and each receives a power they never asked for, awakening something that was never meant to wake… Four children the world wrote off at birth are now its last line of defense."*
- **The production is quantified in its own brief**: "Hell Grind is a **95-minute feature film created by 15 people. A budget under $500K. 14 days of generation** after the assets were prepared, and before the post work. The film screened in Cannes at the 2026 Marché du Film. Every frame is generated. No cameras, no actors, no sets. Video and speech: **Seedance 2.0**. Faces and locations: **Soul Cinema**. Image edits: **Nano Banana Pro and Seedream 4.5**. Text in frame, props and reverse angles of locations: **GPT Image 2**." (`brief_text.txt:1956-1957`)

## 1. Production shape

- **The folder tree is a shot list with revision suffixes, and it is the most honest record of cost in the whole corpus.** 115,586 items in the root (publication counter 115,446), `subfolders_count: 109`, `folder_tree.json` lists **100** root children.
- **Structural buckets**: `1. COLD OPEN` (1,746, 1 sub) · `Assets` (8,986, **14 subs**) · `Credits` (1,683, 5 subs) · `Flashbacks` (3,190, 7 subs) · **`Regenerations` (14,593, 14 subs)** · then ~95 `Scene …` folders.
- **`Regenerations` = 12.6% of every item in the project.** The retry tax is not hidden in a ratio — it has its own top-level folder, bigger than `Assets`.
- **Scene folders use revision suffixes, ranges and fight names interchangeably**: `Scene 27` + `Scene 27.1 … 27.6`; `Scene 69`, `Scene 69 - Fight`, `Scene 69.B16`, `Scene 69B.15 … 69B.20`; `Scene 73.1 … 73.8C - 73.10B`; merged ranges `Scene 15-16`, `Scene 36,38,40`, `Scene 42-50`, `Scene 54-59`, `Scene 61-66`; named set-pieces `Scene 25 Roko vs Robots`, `Scene 51 Statue Assault`, `Scene 72: Roko vs Dagon`, `Scene 36 Jaxx's Fall`. **Duplicate names exist**: `Scene 26` ×2, `Scene 28` ×3, `Scene 64` ×2, `Scene 67` ×3, `Scene 72` ×2, `Scene 73.2B` ×2, `Scene 73.3` ×2.
- **The numbering is not continuous** (no `Scene 30`, `33`, `34`, `40`…): scenes were dropped, merged or absorbed. What survives is the *arithmetic of production*, not the script.
- **`job_set_type`**: `seedance_2_0` **95** (video + speech) · `nano_banana_2` 32 · `imagegen_2_0` 9 · `soul_cinematic` 6 · `gpt_image_2` 4 · `nano_banana_flash` 1 · `soul_cinema_studio` 1 · `image_auto` 1 · `text2image_soul_v2` 1. **55 of 150 sampled rows are image jobs** — the sample is a cross-section of the whole pipeline, not of the film.
- **Resolution**: `2016×864` (21:9, the video standard) **92 rows**; then the image lane at `5504×3072`/`2752×1536`/`3840×2160`/`3168×1344`/`6336×2688` (43:24 ≈ 16:9, 33:14 ≈ 2.36:1); two portrait images (`3392×5056`, `1536×2048`) for character sheets. Gallery video is 4096×1716 — the film was finished wider than the generations (2.387 vs 2.333), i.e. a crop.
- **`job_set_client_meta` is `null` in 150/150 rows** → **UNKNOWN**. The brief's own staging language (`@loc_cave_front`, `EXACT N CHARACTERS NO DUPLICATES`) survives only in the briefs, not in harvestable metadata.
- **Harvest design**: 25 rows × 6 folders (`ROOT`, `Regenerations`, `Assets`, `Scene 67`, `Scene 61-66`, `Scene 15-16`) → 150 rows → **136 distinct prompts** (least duplication in the batch).
- **Timeline**: `created_at` runs **2026-03-31 → 2026-05-15** — the earliest of the three projects, and the longest single production window (~6 weeks of visible prompting for a 96-minute film, i.e. 14 generation days after assets, exactly as the brief claims).
- **Two prompt registers live in one file** (§9): 38 KB studio-grade prompts and 14-character edit commands (`убери пластырь` — "remove the patch", `prompts.jsonl#34`) issued to the same image lane.

## 2. Prompt anatomy — the actual grammar

### 2.1 The skeleton the brief prescribes

The brief walks its own 15-item skeleton, one clause each (`brief_text.txt:2446-2786`). Labels were stripped by the binary-text extraction; the clause content identifies them unambiguously:

| # | block | the brief's own description |
|---|---|---|
| 1 | `SCENE CONTEXT` | "with the header **'EXACT N CHARACTERS NO DUPLICATES'**: what happens, who is in the shot, how long the take is" |
| 2 | `ACTIVE REFERENCES` | "character and location tags with their roles named" |
| 3 | `GEO SPATIAL LAYOUT` | "the geography of the place in words" |
| 4 | `FIRST FRAME AND SPATIAL BLOCKING` | "who stands where in frame one" |
| 5 | `FORMAT MODE` | "one take or hard cuts, duration, real time" |
| 6 | `OPTICS` | "the lens and the focus plan" |
| 7 | `CAMERA` | "how the camera behaves, and what it never does" |
| 8 | `ACTION TIMING` | "the action beat by beat, in seconds" |
| 9 | `PHYSICS` | "weight, contact, inertia of everything that moves" |
| 10 | `LIGHTING` | "one source logic, where it comes from" |
| 11 | `AUDIO` | "the voice descriptors and the exact lines; SFX only" |
| 12 | `ACTING` | "state, want, what is hidden, body rhythm, what changes" |
| 13 | `STYLE PREFIX` | "the Style Prefix, pasted word for word" |
| 14 | `TECHNICAL` | "detail and stability requirements" |
| 15 | `POSITIVE CONSTRAINTS` | "every count and ban, **written as what IS in the frame**" |

This is CINEDANCE's architecture with three project additions — `GEO SPATIAL LAYOUT`, an `ACTING` block, and a `STYLE PREFIX` + `TECHNICAL` tail — and one doctrinal change: the last block is where the bans live, "every count and ban, written as what IS in the frame" (`brief_text.txt:2770`). The brief also names the whole thing: "**The prompt is a rigid skeleton**" (`brief_text.txt:2786`).

### 2.2 The order that was actually used

**No single order dominates; four house styles coexist**, and unlike the other two cases there is no invariant beyond "the style card closes the prompt":

| style | observed form | rows |
|---|---|---|
| **A — bracketed sections** | `[REFERENCES + IDENTITY ANCHORS]` → `[SPATIAL LAYOUT — GEOMETRY]` → `[SCENE CONTEXT]` → `[STRICT / WORLD LOCK]` (with `⚠️ … (HARD LOCK)` sub-heads) → `[STYLE]` | 8 (`r31,128,129,133,138,141,144,148`; bracketed `[STYLE`/`[REFERENCES`/`[SPATIAL` present in 8) |
| **B — bare caps headers** | `SCENE CONTEXT` → `SPATIAL LAYOUT` → `STRICT` / `WORLD LOCK` → `REFERENCES` → `CAMERA` → `AUDIO` → `PHYSICS / SKIN / ACTING / CONTINUITY` → `TECHNICAL` | 11–13 (`SCENE CONTEXT` 13 rows, `SPATIAL LAYOUT` 12, `STRICT` 46) |
| **C — duration-first** | `Duration: N seconds. Aspect ratio: 21:9.` opens the prompt, then the skeleton | 22 (`Duration:` 22 rows) |
| **D — multishot** | `multishot sequence — 15 SECONDS · 21:9 · 8K` opens, then `CUT 1 … CUT n` | 22 (`multishot` 22 rows) |

**What is invariant:** the **style card closes the prompt** (13 rows, a fixed 12-line `Style: / Cinematography: / Lighting: / Color: / Camera: / Skin: / Acting: / Physics: / Composition: / Continuity: / Technical: / Audio:` block, `prompts.jsonl#28`), and `AVOID:` — when present — sits immediately before the action, not at the end (9–10 rows).
Block presence over 150 rows: `STRICT` 46 · `SCENE CONTEXT` 13 · `SPATIAL LAYOUT` 12 · `HARD LOCK` 12 · `AVOID` 9 · `POSITIVE CONSTRAINTS` 4 · `NEGATIVE` 8.

### 2.3 The slug / header line

Two forms:

> `␣{{9cf17e2c-…}} — env / location reference. Brutalist museum atrium interior: tall vertical window slits on the far concrete wall…` (`prompts.jsonl#28` — the prompt *opens with the references*, not a slugline)
> `Duration: 15 seconds total. Aspect ratio: 16:9. …` (`prompts.jsonl#127`)

There is **no `INT./EXT.` slugline** in the video lane (0/150) — the location is a `{{uuid}}` descriptor at the top. The duration/aspect prefix (style C) is the closest thing to a header, and it exists only to restate UI parameters in text.

### 2.4 How references are tagged

- **`{{uuid}}` saturates the prose.** 2,724 occurrences, **49 distinct uuids**, median **8 per video prompt**, **max 191 in a single prompt**. The uuid is used *grammatically* — as a possessive, a subject, an object:
  > `{{a1163bfb-…}}'s right palm` · `{{b091d5b1-…}}'s right arm terminates in an organic bone-blade-extension` · `BEGINNING AND ENDING OUTSIDE {{9cf17e2c-…}}` (`prompts.jsonl#28`, `#31`)
  This is the defining technical choice of the case (§3.1): identity is asserted **by pointer**, never by name.
- **`{{ref 1}}` is the image-lane handle**: 577 occurrences in 39 rows — more than the video lane's own uuid density in the early months. The character-sheet pipeline is `{{ref 1}} (Roco · STRIPPED) — …` (`prompts.jsonl#120`): one attached sheet, then a Chinese/Russian state list.
- **`@TAG` appears 4 times in 150 rows** (`@samuraibasic`, `@handle`, `@samuraicavalry`, `@image5`). The brief says "All assets live under tags and the same tags are used everywhere: in documents, in prompts, in the interface. One dictionary of names for the whole project" (`brief_text.txt:2394`) — but in this corpus **the @-tags are the human index and the uuids are the prompt**. Third case in a row where the two layers do not touch.
- **Reference roles are named, and inheritance is explicitly banned**: "Location references get a direct ban on inheritance: '**do not use as a starting frame, do not inherit the composition, the angle or the color — take only the space and the texture**'" (`brief_text.txt:2393`). In-prompt form (verbatim, 17 rows):
  > `The video must be generated from scratch as 100% original continuous live-action cinematography — DO NOT use the reference image as a key frame, start frame, end frame, or any frame of the output video, and DO NOT inherit the exact pose, framing, or lens of the reference image. Compose freshly per-shot using the description below.` (`prompts.jsonl#77`)

### 2.5 Timing syntax

Three separate mechanisms, and they are not interchangeable:

1. **Phase timeline inside one take** — `Phase 1 (~0-0.5s, NORMAL SPEED)`, `Phase 2 (~0.5-5s, SLOW MOTION — MAIN BEAT)`, `Phase 3 (~5-6s)`, `Phase 4 (~6-7s)` (`prompts.jsonl#28`). 7 rows use `Phase n`.
2. **Cut list across takes** — `CUT 1 — WIDE PROFILE STATIC ESTABLISHING 3S`, `CUT 2 — …` (`prompts.jsonl#129`). 198 occurrences of `CUT n` across only 8 rows (i.e. the multi-cut style is concentrated).
3. **Numeric ranges everywhere** — 401 `a–b s` ranges across 40 distinct prompts (median 0, i.e. most prompts have none; the ones that do are densely timed, max 24). `N seconds` occurs 1,313 times.

Stated durations (distinct prompts): **15 s (59)** — overwhelmingly the modal block; 10 s (36), 5 s (27), 4.0 s (25), 7.0 s (22), 3.5 s (22), 20 s (12), 12 s (13). The film is built from 15-second and 10-second units with sub-second phase splits inside them.
`24fps` in 27 rows (23 distinct) — always as part of the tail technical line: `Technical: 24fps smooth motion. 8K detail. No jitter.`

### 2.6 Aspect / duration inside the prompt vs in the params

- Both are stated in the prompt in style C (`Duration: 15 seconds total. Aspect ratio: 16:9.`, 22 rows; `21:9` in 51 rows / 46 distinct) **and** implied by the job's `width/height` (2016×864 = 21:9 in 92 rows). The prompt's `21:9` and the job's 21:9 agree; the prompt's `16:9` rows (21 distinct) correspond to image or 16:9 image jobs — **the text and the job disagree in some rows** and the text cannot be trusted over `width/height`.
- Duration and fps are prompt-only; their param values were not harvested → **UNKNOWN**. The brief nevertheless says: "If the user chooses these settings in Higgsfield/Seedance UI, omit them from the final prompt unless they are story-critical" (`skills/15b39d4c…md`, "Output settings") — and this project kept writing them, i.e. it treated duration and aspect as **story-critical** (a 15-second unit is a dramatic unit here).

## 3. What this case does that the others may not

**1. Identity by pointer: the uuid *replaces the noun*, everywhere, including inside possessives.**
2,724 `{{uuid}}` occurrences across 49 distinct assets; **median 8 per video prompt, max 191 in one prompt** (`prompts.jsonl#92`, the 38,503-char outlier). The mechanism is visible in the grammar:
> `{{e92f3ea2-…}} on SCREEN-LEFT in pure side-profile facing SCREEN-RIGHT toward {{2092a603-…}}` (`prompts.jsonl#31`)
> `THE WALLS NEVER BREAK … the ONLY thing that breaks in the film is the door` — compare anerneq, which writes "her father", "the knife", "the sled". (`prompts.jsonl#2` of the vengeance case, for contrast)
The cost is length: **median 14,553 chars / 1,959 words per video prompt** — 2× anerneq. The benefit is that a 49-asset cast cannot drift: the model is never asked to *remember* who `{{8580cfcd-…}}` is, it is told which file. No other case in the batch does this to this degree (anerneq: 1 uuid; vengeance: 24 uuids, 10 per prompt).

**2. `⚠️` is used as a grammatical operator — a salience flag with a fixed meaning.**
**3,417 occurrences in 52 rows** (≈65 per prompt in the flagged rows). It is not decoration: it always precedes a **count, a prohibition-with-a-number, or a HARD LOCK head**:
> `⚠️ NO SLOW MOTION (HARD LOCK): Entire 8 seconds at REAL-TIME / NORMAL SPEED.` (`prompts.jsonl#31`)
> `⚠️ POSITIONS NOT NEGOTIABLE: Jaxx is FACE-DOWN (prone, on stomach, back to camera). All other three are FACE-UP` (`prompts.jsonl#28`)
> `⚠️ the artifact is GONE (shattered into shards that scattered outward)` (`prompts.jsonl#28`)
This is an authoring habit (a human minding the model), formalised. `HARD LOCK` itself: 84 occurrences in 12 rows.

**3. The end-state table: the prompt's contract is the *last frame*, written as a per-character bullet list, twice.**
> `END-STATE HERO POSITIONS (HARD LOCK — must read at final frame):` followed by four bullets, one per character, each giving facing, body orientation, limb state, what is in the hand (`prompts.jsonl#28`)
and, earlier in the same prompt, the same information under `End-state raskladka (HARD LOCK at final frame):` (`raskladka` = "layout/arrangement", Russian production slang). The device answers a specific model failure — the model cannot plan a four-body end state across a 7-second throw — by **stating the terminal condition twice, before and after the action**.

**4. A 12-line style card is pasted at the *end*, after the action — the prompt has a header of references and a footer of crew.**
> `Style: 8K IMAX. Photorealistic — no 3D render, no game engine, no game-cutscene aesthetic.`
> `Cinematography: Emmanuel Lubezki × Roger Deakins.`
> `Lighting: Natural light only — contre-jour backlight, camera on shadow side, atmospheric haze throughout. Key light from sky and windows only.`
> `Color: 60:30:10 — dominant / secondary / accent.`
> `Camera: Physical cine lens. 180° shutter motion blur.`
> `Skin: Pore-level realism — vellus hair, asymmetric moles, capillary flush, pore-shadow matching on-set light.`
> `Acting: Hollywood — micro-pauses before reactions, precise eye-line, wet living eyes with catch-lights, chest rising on breath.`
> `Physics: Gravity and inertia respected — mass has real weight, correct contact shadows. No floating props.`
> `Composition: Rule of thirds + golden ratio. Every person moving from frame one.`
> `Continuity: Characters, props, environment identical across every cut. No identity drift.`
> `Technical: 24fps smooth motion. 8K detail. No jitter.`
> `Audio: Environmental SFX only. No music. No subtitles.` (`prompts.jsonl#28`)
`8K IMAX` 45 rows · `Lubezki` 71 · `Deakins` 75 · `60:30:10` 48 · `Cinematography:` 13. **The film is directed by naming a two-person camera crew and a colour ratio.** This is the opposite strategy to anerneq's (one named film, *The Revenant*, + one named DoP) — hell-grind names the crew *and* the deliverables, anerneq names the *outcome*.

**5. The first second is engineered as a memory device, and the brief explains why.**
> `The first second is always a wide shot.` (`brief_text.txt:3987`)
> `One second at the start of the scene, no lines and no action: the model "photographs" the arrangement — who stands where, what lies where, where the light comes from — and holds it in every following shot. **Remove that second, and characters start swapping places.** A small hack: have someone say one short word during that second; it makes it easier for Seedance to treat the wide as a separate shot.` (`brief_text.txt:8192`)
This is the **same device as vengeance's 0.5 s "ZERO FRAME"**, independently arrived at, with the mechanism spelled out: a static wide is not establishing coverage, it is *the model's spatial memory*. It also explains why `from frame zero` appears in 4 rows and `frame zero` in 4 more — the phrase is doctrinal, not incidental.

**6. Complex action must open the prompt, not sit in the middle of the timing.**
> `Complex action never sits in the middle of the timing. Our door would not break: the hero shuffled next to it and froze. Now the action opens the prompt — "he is ALREADY mid-swing, the door ALREADY cracking" — and the approach to the door is a separate shot.` (`brief_text.txt:3112`)
`ALREADY` appears in 13 rows — always at a beat boundary, never mid-sentence.

**7. Scale is a numerical contract with a human ruler in frame.**
> `Giants live on scale anchors: a size comparison in every prompt, plus a human figure in the frame to measure against. Without both, the model quietly shrinks the giant back toward human height… visible proof in the picture: the stone guardian stands THIRTY METRES tall, his head is lost in the darkness of the dome, his open palm is as wide as a family car, and ROCO at his foot reaches just above the ankle. **In every frame the guardian's silhouette is at least FIVE TIMES the height of the human figure beside him, and the frame cannot hold both his feet and his head at once.**` (`brief_text.txt:106`, `:130`)
Four separate proofs (absolute height, body-part comparisons, relative silhouette ratio, and a framing test) — the most rigorous anti-drift device in the corpus. 4 rows contain `human figure`, 29 contain `scale`.

**8. The negative is *converted*, not deleted or accumulated.**
`NEGATIVE` block in only **8 rows / 7 distinct** (median 26 items — vs anerneq's 74); `AVOID:` in 9 rows, placed *before* the action; most bans live inside the style card and inside `POSITIVE CONSTRAINTS` (4 rows, whose title the brief explains: "every count and ban, **written as what IS in the frame**", `brief_text.txt:2770`). The rule that governs it:
> `actions only in positive form — the model ignores "does NOT fall on his back," or does the opposite; write "falls on his stomach."` (`brief_text.txt:2834`)
This is the **middle position** between anerneq (74-item negative block) and vengeance (0 negative blocks, named locks): hell-grind keeps a small negative *tail* but rewrites every action ban into a positive action.

---

## 4. Recurring phrasing bank

### Style / crew card (the tail block; paste-and-keep inventory)
- `Style: 8K IMAX. Photorealistic — no 3D render, no game engine, no game-cutscene aesthetic.` — 45 rows contain `8K IMAX`; `no game engine` in 20 rows.
- `Cinematography: Emmanuel Lubezki × Roger Deakins.` — 13 rows verbatim (× and x variants); `Lubezki` 71 rows, `Deakins` 75.
- `Lighting: Natural light only — contre-jour backlight, camera on shadow side, atmospheric haze throughout. Key light from sky and windows only.` (`prompts.jsonl#28`)
- `Color: 60:30:10 — dominant / secondary / accent.` — 48 rows.
- `Camera: Physical cine lens. 180° shutter motion blur.` (`prompts.jsonl#28`)
- `Skin: Pore-level realism — vellus hair, asymmetric moles, capillary flush, pore-shadow matching on-set light.` (`prompts.jsonl#28`)
- `Acting: Hollywood — micro-pauses before reactions, precise eye-line, wet living eyes with catch-lights, chest rising on breath.` (`prompts.jsonl#28`; 5-gram `micro-pauses before reactions precise eye-line` ×12)
- `Physics: Gravity and inertia respected — mass has real weight, correct contact shadows. No floating props.` (`prompts.jsonl#28`)
- `Composition: Rule of thirds + golden ratio. Every person moving from frame one.` (`prompts.jsonl#28`)
- `Continuity: Characters, props, environment identical across every cut. No identity drift.` (`prompts.jsonl#28`; `identity drift` guarded in 18 rows)
- `Technical: 24fps smooth motion. 8K detail. No jitter.` (`prompts.jsonl#28`)
- `Audio: Environmental SFX only. No music. No subtitles.` / `SFX only. No music.` — 50 rows contain `SFX only`, 25 `No music`; the brief calls the line **mandatory**: "The line 'SFX only. No music.' is mandatory. Music belongs to post-production" (`brief_text.txt:2858`).
- `Photoreal. NON-IP. [aspect ratio]. [duration]s. SFX only. NO CGI. Cinematic.` — the brief's compressed technical tag string (`brief_text.txt:2858`; `NON-IP` in 10 rows, `NO CGI` in 25).

### Camera / optics
- `Camera: Physical cine lens. 180° shutter motion blur.` (tail card).
- `TOP-DOWN OVERHEAD / BIRD'S-EYE VIEW — lens points STRAIGHT DOWN at floor (90° to floor plane)` (`prompts.jsonl#28`).
- `CAMERA (HARD LOCK — single static top-down take, NO cuts, NO camera motion)` (`prompts.jsonl#28`).
- `BIRD'S-EYE`, `90° to floor plane`, `drone-altitude over[-head]` — camera altitude is given as an angle and a relative height, never as an adjective.
- `Calm breathing handheld that holds its framing` (`brief_text.txt:5990`).
- `floating immersive camera that lives` (the brief's own camera principle, `brief_text.txt:1844`).
- `Camera low at chest height` (`brief_text.txt:5857`).
- `The camera lives on the door side of the room and never crosses that line` (`brief_text.txt:5325`) — the same one-axis rule vengeance formalised as a LOCK.

### Light
- `Lighting: Natural light only — contre-jour backlight, camera on shadow side, atmospheric haze throughout. Key light from sky and windows only.` (tail card).
- `one source, one direction of shadows, never two suns — otherwise every new angle re-invents the lighting` (`brief_text.txt:2290`).
- `natural motivated light` · `painterly composed frames` · `strong silhouettes against the light` (the brief's lighting principles, `brief_text.txt:1789`).
- `ONE hard overhead source above the mat`, `the door area falls two stops darker`, `no fill from the camera side` (`brief_text.txt:6719`).
- `LIGHT BREAKS THROUGH THE DARK STORM CLOUDS` (a named lighting event, `prompts.jsonl` header census).

### Motion / physics
- `Physics: Gravity and inertia respected — mass has real weight, correct contact shadows. No floating props.`
- `PHASE 1 (0-1.5s) — PIERCE-BRACING STILLNESS, REAL SPEED` (`prompts.jsonl` header census).
- `parabolic ballistic arcs`, `rises approximately 2 METERS UP at the peak … travels approximately 4-5 METERS HORIZONTALLY` (`prompts.jsonl#28`).
- `the crystal arm has real weight — it drags the right shoulder low and swings a beat behind the body` (`brief_text.txt:6588`).
- `weight, contact, inertia of everything that moves` (the `PHYSICS` block definition, `brief_text.txt:2632`).
- `The rocking mannequin loses momentum and settles` (`brief_text.txt:6608`) — motion as a decay curve, not a pose.

### Sound
- `Audio: Environmental SFX only. No music. No subtitles.`
- `SFX only. No music.` — mandatory (`brief_text.txt:2858`).
- `Phase 1 — brief muted percussive PULSE whoosh + crystalline SHATTER ring` (`prompts.jsonl#28`) — sound keyed to phase, not to shot.
- `Environmental`, `diegetic` (15 rows).
- "Sound design and music were built in post on top of continuous ambiences: **one shared atmosphere glues the generated shots into one space**, even where the picture drifts" (`brief_text.txt:3251`) — the post-layer doctrine that lets the prompt stay SFX-only.

### Acting
- `State, want, what is hidden, body rhythm, what changes` — the `ACTING` block's five questions (`brief_text.txt:2701`).
- `A living scene is a hero who wants something, something in his way and he acts to get it. The emotion is born by itself, out of that fight.` (`brief_text.txt:2974`).
- `For deeper emotions, describe the work of muscles and body: a tremble, a jaw clenched with rage and flexing, cheekbones drawn tight, a light exhale through the nose.` (`brief_text.txt:2988`).
- `Add phased blinking — the cheapest sign of a living face.` and `the micro-life rule: one visible micro-event every one or two seconds — the breath lifts the chest, a nostril moves, a brow tenses and relaxes.` (`brief_text.txt:2990`, `:2995`).
- `one line of inner monologue for every stretch of action — what the hero thinks and wants — marked INNER (unspoken)` (`brief_text.txt:2990`).
- `The main rule of acting: write behavior, not feelings.` · `Write physics, not adjectives.` (`brief_text.txt:4011`).
- `The way a character acts is locked the same way as the look and the voice.` (`brief_text.txt:3840`).

---

## 5. Structure & story

- **A 96-minute action-fantasy feature**, 15 people, under $500K, "14 days of generation after the assets were prepared" (`brief_text.txt:1956`). The published cut is 5759.85 s.
- **Act structure visible in folders**: `1. COLD OPEN` (1,746 items) · `Flashbacks` (3,190, 7 subs) · `Credits` (1,683, 5 subs) · the museum heist and its aftermath (Scenes 13–50) · the Tibet sequence (Scenes 51–60: `Scene 51 Statue Assault`) · the Japan/portal sequence (Scenes 61–73: `Scene 72: Roko vs Dagon`).
- **Story rules the brief states**: "Fantasy as tragedy, action as grief, friendship as the last thing standing between a man and the thing he is becoming" (`brief_text.txt:1854`, `:1869`, `:1901`). The protagonist's arc is stated as a cost curve: "A stranger from a demon-hunting organization offers a deal: find the two remaining artifacts of the earth realm before the demons do… In Tibet, Roco crosses a line — he kills the artifact's elderly guardian… By the time Roco opens the portal to hell, only one question remains: how much of the man who set out to save her will be left?" (`brief_text.txt:1854`, `:1869`, `:1901`).
- **`type=film`, one featured episode** (`hell-grind/episode-1`) — the project is packaged as a feature but published as episode 1 of a series-like publication.
- **Crowd scenes are not crowds**: "A crowd is one 'character' asset with a range of heights and clothes. One or two lead extras get their own assets for close-ups. On medium shots, **state the number directly** — otherwise the model gives you three people in one take and a hundred in the next" (`brief_text.txt:3087`).
- **Transitions are a designed object**: "Transitions between two spaces hold on a threshold: both location assets in one prompt, and the seam is a doorway with a light contrast across it — 'a warm amber room, a cold blue corridor beyond the arch.' The contrast explains the palette change and forgives small geometry mistakes" (`brief_text.txt:3184`).
- **Editing ran in parallel with generation**: "The editor assembled scenes as they arrived and ordered what was missing: 'need a cutaway to the hands,' 'need a wider one.' A reshoot costs minutes" (`brief_text.txt:3184`).

## 6. Per-case hard rules (only what this case evidences)

1. **Lock every asset before generating a single shot.** "Do not generate a single shot until every character, location and prop is locked and stress-tested. **This one rule saves more money than everything else combined**" (`brief_text.txt:3304`).
2. **Describe everything, every time.** "The model has no memory. The descriptor goes into every prompt, word for word, never shortened" (`brief_text.txt:3320`).
3. **Change one thing at a time.** "A prompt is a working mechanism: rewrite it fully and you lose the parts that worked. **One line per iteration**, everything into the log" (`brief_text.txt:3343`, `:3066`).
4. **Give the model less freedom.** "A corner instead of a room, an anchor instead of an open space, a map instead of guesswork, one action per shot" (`brief_text.txt:3367`).
5. **If a shot will not come together, simplify the shot, not the words.** "Split it in two, remove an action, change the angle" (`brief_text.txt:3398`).
6. **Actions in positive form only.** "The model ignores 'does NOT fall on his back,' or does the opposite; write 'falls on his stomach'" (`brief_text.txt:2834`).
7. **Never write an age, in any language.** "The content filter becomes much stricter the moment it reads a minor; instead of age, give the role, the clothes, the action" (`brief_text.txt:2835`).
8. **Keep a ban dictionary of words the model punishes**: "dark" becomes "low key", "jolting" becomes "rapid motion" (`brief_text.txt:2835`).
9. **≤3 sentences per action beat.** "Up to three sentences per beat overload a beat, and the model smears it. The prompt itself can be long: ours ran 3,000–4,000 words. **Length is not the enemy; an overloaded beat is**" (`brief_text.txt:2831-2833`).
10. **The first second is a static wide, always.** (`brief_text.txt:8192`)
11. **Location sheets are shot in 3/4, never frontal** — "A frontal 'pretty picture' becomes flat wallpaper on wides, and past its edges the model invents new surroundings every time" (`brief_text.txt:2235`).
12. **One light source, one shadow direction, never two suns.** (`brief_text.txt:2290`)
13. **Name every reference's role in the prompt**, or the model "copies the composition instead of the face, or the face instead of the color palette" (`brief_text.txt:2290`).
14. **Ban reference inheritance** — "take only the space and the texture" (`brief_text.txt:2393`).
15. **GEO map**: "the landmark objects, what is on the right, what is on the left, where the camera stands. No heroes, no action — only the place itself. You write it once per scene and paste it into every shot of that scene without changes" (`brief_text.txt:2865`).
16. **Sides exist only from the camera** — "frame-left" / "frame-right"; "the model does not understand 'to the left of the hero'" (`brief_text.txt:2965`).
17. **Keep each scene's prompt in the same skeleton, same order** ("The prompt is a rigid skeleton", `brief_text.txt:2786`).
18. **Write in present tense, short sentences** (`brief_text.txt:3562`).
19. **A shot's dialogue must be got right at generation, not in post**: "We did not re-record the voices. Seedance's lip-synced lines were cleaned directly from the generations… A studio recording only when a clip came out with no usable voice" (`brief_text.txt:3184`).
20. **Expect slow tempo**: "Generations almost always feel slow in tempo: cut more aggressively than feels right, and plan to trim the first and last half-second of every [clip]" (`brief_text.txt:3202`).

## 7. Numbers

| metric | value |
|---|---|
| rows harvested | 150 = 6 folders × 25 |
| distinct prompts | **136** (least duplication of the three cases) |
| video rows / distinct video | 95 / 84 · image rows 55 |
| folder items | 115,586 in root · **`Regenerations` 14,593 = 12.6%** · `Assets` 8,986 · ~95 scene folders |
| generations_count | 115,446 for 5759.85 s ⇒ ≈20 generated items per second of film |
| prompt chars (all rows) | min **14** · median 7,344 · mean 11,607 · max 38,503 |
| prompt chars (video, distinct) | min 2,365 · median **14,553** · max 38,503 |
| prompt words (video, distinct) | min 42 · median **1,959** · max 5,868 (the brief claims "3,000–4,000 words": true of the long tail, **not** of the median) |
| uuid refs | **2,724 occurrences · 49 distinct · median 8/video prompt · max 191** |
| `{{ref 1}}` refs | 577 occurrences / 39 rows |
| @-tags in prompts | 4 distinct |
| `⚠️` | **3,417 occurrences / 52 rows** (~65 per flagged prompt) |
| `HARD LOCK` | 84 occurrences / 12 rows |
| `NEGATIVE` block | 8 rows / 7 distinct prompts · median 26 items · max 49 |
| `AVOID` line | 9 rows |
| stated durations (distinct prompts) | **15 s (59)** · 10 s (36) · 5 s (27) · 4.0 s (25) · 7.0 s (22) · 3.5 s (22) · 20 s (12) · 12 s (13) |
| `CUT n` labels | 198 occurrences / 8 rows (0 cuts in 128/136 distinct prompts) |
| timecode ranges | 401 occurrences / 40 distinct prompts · median 0 · **max 24 in one prompt** |
| `Phase n` | 7 rows |
| `24 fps` | 27 rows / 23 distinct |
| aspect stated in prompt | 88 rows (`21:9` 51 rows, `16:9` 27 rows) |
| UI aspect | 2016×864 (21:9) in 92 rows; image lane 43:24/33:14 |
| tail style card | `8K IMAX` 45 · `Lubezki` 71 · `Deakins` 75 · `60:30:10` 48 · `Cinematography:` 13 |
| negative-form discipline | `SFX only` 50 rows · `No music` 25 · `NO CGI` 25 · `NON-IP` 10 · `identity drift` guarded 18 |
| `created_at` span | 2026-03-31 → 2026-05-15 |

**Duplication flag**: duration, aspect and fps are **all** stated in prompt text here, against the shared CINEDANCE instruction to omit UI settings unless story-critical. Some prompt/job aspect pairs disagree (`16:9` in text vs 21:9 in `width/height`), so **`width/height` is the authority and prompt text is not** — a warning for anyone compiling statistics from prompt strings alone.

## 8. Failure modes named in this case

- **Characters teleport, swap places, the camera jumps to the wrong side** — "The reason is simple: the model does not remember who stood where in the previous shot. **The cure is the GEO SPATIAL LAYOUT block**" (`brief_text.txt:2836`); and the 1-second static wide (§3.5).
- **The model adds extra people and clones furniture** — "The model loves to add extra people and to clone furniture. Only those whose references are in the prompt exist in the frame, and furniture gets a direct ban" (`brief_text.txt:2798`). (In-prompt: `exactly ONE mannequin, NEVER render a second one.`)
- **Giants shrink to human height** without a scale anchor (§3.7).
- **Complex action in the middle of a shot freezes** — "Our door would not break: the hero shuffled next to it and froze" (`brief_text.txt:3112`).
- **An overloaded beat smears** — "up to three sentences per beat overload a beat, and the model smears it" (`brief_text.txt:2831`).
- **Negative actions invert** — "the model ignores 'does NOT fall on his back,' or does the opposite" (`brief_text.txt:2834`).
- **Age in the prompt trips the content filter** — "much stricter the moment it reads a minor" (`brief_text.txt:2835`).
- **Two suns** — "otherwise every new angle re-invents the lighting" (`brief_text.txt:2290`).
- **Frontal location sheets cause the model to invent surroundings** past the sheet's edge (`brief_text.txt:2235`).
- **AI defects only visible on a big screen** — "extra fingers, 'boiling' textures, fake text on signs. Small defects were retouched frame by frame. Fully broken shots were regenerated from the saved final prompt, **with one line changed**. First priority: close-ups of faces and hands" (`brief_text.txt:3219`).
- **Generations run slow in tempo** — "cut more aggressively than feels right, and plan to trim the first and last half-second" (`brief_text.txt:3202`).
- **Losing a good prompt by rewriting it** — "rewrite it fully and you lose the parts that worked" (`brief_text.txt:3343`).
- **Known asset loss** — "Note: some assets and working files were lost during production — a few referenced materials may be unavailable or exist only in later versions" (`brief_text.txt:199`).

## 9. Anything weird / low quality

- **150 rows → 136 distinct**: the cleanest sample of the three, but still includes 13 duplicate groups.
- **The image lane and the video lane are two different cultures in one file.** Video prompts: 14–38 KB, bracketed headers, uuid-saturated English. Image prompts: 14–255 characters, imperative Russian/Chinese, no structure at all —
  > `убери пластырь` ("remove the patch", 14 chars, `prompts.jsonl#34`) · `подними костюм повыше и прямые ноги` ("raise the costume and straighten the legs", `prompts.jsonl#5`) · `make side view` (`#23`) · `сделай локейшн шит этой комнаты с 4 ракурсов` ("make a location sheet of this room from 4 angles", `#48`).
  These are **edits to an attached image**, and they are the only place in the corpus where the actual back-and-forth of AI production is visible as conversation.
- **Character sheets are written in Chinese with inline warnings**: `{{ref 1}} (Roco · STRIPPED 睡着的 — 用于全部镜头) — Roco平躺仰面熟睡, 黑色T恤(沾泥)… 鼻梁横向⚠️旧苍白伤疤约2-3cm(old healed pale scar, 苍白淡色, NOT鲜红)` (`prompts.jsonl#120`). The `⚠️` operator survives even here, as punctuation inside a bilingual tag. This is a *fourth* language regime in the corpus (anerneq: English + Cyrillic conlang; vengeance: English + Russian notes; hell-grind: English + Russian commands + Chinese sheets).
- **The `EXACT N CHARACTERS NO DUPLICATES` header the brief demands appears in 0/150 sampled prompts.** The brief states the rule; the sample does not contain an instance of it. Treat as "stated doctrine, instance not sampled", not as "never used".
- **`Phase` labels are numbered in words in some rows and in digits in others** (`Phase 1`, `PHASE 1`), and the header census shows mangled variants (`1 ECU 4`, `0-1 5S MS STEADICAM RIDING`, `2 5-3S CU FACE CONFUSED NOT SCARED`) — these are **beat tables with the dash characters eaten**, e.g. `1. ECU 4-5s`, `2. 5-3s` (sic). Do not read them as labels.
- **Duplicate folder names with different contents** (`Scene 28` ×3, `Scene 67` ×3) make folder-level counting unreliable; `folder_tree.json` lists 100 of the 109 claimed subfolders.
- **The brief's word-count claim is optimistic**: "ours ran 3,000–4,000 words" (`brief_text.txt:2833`) vs measured median 1,959 words (video, distinct) and max 5,868. True of the top quartile.
- **Mojibake** in `publication.json` (`[mojibake: “—”]` for em dashes) and in the CINEDANCE skill title (`CINEDANCE V4 [mojibake: —] Seedance 2.0…`).
- **`brief_assets.json` lists six skill URLs but only three unique documents** — each of CINEDANCE/ACTING/LIRA was attached twice. Anyone counting "how many skills does this project use" will overcount by 2×.
- **Cross-case contradiction to carry forward**: hell-grind and anerneq both name a cinematographer as the style anchor (Lubezki; Lubezki again via *The Revenant*), while vengeance names a **1952 film + DoP** (High Noon, Floyd Crosby). The two strategies are not equivalent: a living DoP's name pulls a *body of work* (hell-grind gets scale and natural light; anerneq gets handheld intimacy), a specific film pulls a *specific tonal curve* (vengeance gets flat grey and hard window daylight). A distilled skill should offer both as options with their different failure modes — a named DoP drifts between his films, a named film drifts toward pastiche.

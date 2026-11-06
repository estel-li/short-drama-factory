# CASE DIGEST — KOK BORU — **the 20-second `carousel`, not the film**

> Locator convention: `prompts.jsonl#N` = 1-based row (JSONL line) in `_data/cases/kok-boru/prompts.jsonl`;
> `brief_text.txt:N` = line number after splitting on `/\r?\n/`; `publication.json` / `folder_tree.json` / `stats.json`.
> **Harvest caveat:** `_folder_tag` is capped at 25 rows per folder (ROOT 25, SH03 25, SH06 25, SH08 25, SH09 25, SH10 16).
>
> **Which publication this is.** `higgsfield.studio/kok-boru` is a publication of **type `carousel`,
> `duration_seconds: 20`**, with `featured_episode_slug: null`. The *film* is a **separate publication of the same
> project**: `kok-boru-film` (`type: film`, `899.042 s`, `featured_episode_slug: kok-boru/full-film`,
> `_data/cases/kok-boru-film/`). Everything below is the **carousel** unless a line says "the film".
> The carousel is the only non-`film` type in the four-case set and is used here as the short-form control.

---

## 0. Header
- **Title** Kok Boru · **type** `carousel` · **runtime** **20 s** · **author** `higgsfield.studio` (publication)
  · **publication_id** `01f8ae67-c828-4bec-87a5-d36cf1ad7361` · **snapshot_folder_id** `1999e1a9-e748-4d9d-9d56-ac1e19881897` (`publication.json`)
- **generations_count** 2,693; **credits_spent 345,037.5**; `stack: []`, `size_bytes: 0`
  (`stats.json` → `publication.json.stats`) — the **only** case of my four that exposes a credit figure.
- Community: **2,265 likes / 189,685 views** (`stats.json`) — the best-performing of my four.
- **featured_episode_slug: null**; `featured_episode_id: 2f24cfc0-cde0-438b-893f-32c7bee58df0` (an episode id with
  no slug — unlike the three `film` cases, which all resolve to `<slug>/full-film`). `gallery_media` is a single
  **20 s / 4096×1716 HLS video**; `description: null`; categories `["banner","open-sourced-by-higgsfield"]`.
- **Provenance**: `/fnf/project-publications/higgsfield.studio/kok-boru`; `/fnf/folders/1999e1a9…/children`;
  `/fnf/folders/{id}/items/v2?include_subfolders=true`; brief snapshot `…/brief/1999e1a9…/snapshot` (`_summary.json`).
  141 prompt rows, 1,129,759 prompt bytes (`prompts_meta.json`).
- **Premise**: `description` is **null** — there is no official synopsis on the carousel publication. From the brief:
  "Logline: A grieving steppe mother discovers the daughter she lost to a wolf pack years ago is alive raised wild
  among the wolves her village has come to destroy." (`brief_text.txt:68`). The brief states the film's intent:
  "Kok Boru is an animated short film rooted in Kazakh nomadic life and folklore — the steppe, the seasonal
  migrations, the spiritual world of the 'baksy' (shaman), and the old fear of the wolf — told almost entirely
  through image rather than dialogue." (`brief_text.txt:2475-2477`)
- Ownership oddity: the publication's author is `higgsfield.studio`, but the snapshot folder is owned by
  `emilywallace` / workspace **`Hell Grind`** (`63e31d95-…`), and the brief's asset URLs belong to
  `user_3CDJZWODipNphbDsjzI7VEyHX7F` + `user_2v5txepAmNYZwyzml1nIizlWURE` (`folder_tree.json`, `c2_urls.mjs`).
  This is an outside studio's project published on the studio account.

## 1. Production shape — and what `carousel` means here

**Folder taxonomy = `Project Brief` | `FULL10MIN` | `SH01`…`SH10`.** Root: 2,781 items,
`subfolders_count: 15`; 13 L1 children are listed (2 missing from the snapshot).

| L1 folder | items | subs |
|---|---|---|
| FULL10MIN | 0 | 1 |
| Project Brief | 1 | 0 |
| SH01 | 40 | 0 |
| SH02 | 64 | 0 |
| SH03 | 194 | 0 |
| SH04 | 41 | 0 |
| SH05 | 76 | 0 |
| SH06 | 151 | 0 |
| SH07 | 55 | 0 |
| SH08 | 84 | 0 |
| SH09 | 461 | 0 |
| SH10 | 80 | 0 |
| `袩械褉褋芯薪邪褝懈` (mojibake; almost certainly `Персонажи` = "Characters") | 0 | 0 |

What the naming tells us:
- The unit is **`SH<nn>` = one shot**, and the brief says so explicitly: "The work is organized by shot, with each
  folder holding the many iterations we explored for that single shot — a system that keeps the project
  structured and easy to navigate without ever limiting how much we experiment" (`brief_text.txt:2400-2401`).
  So a folder = a shot = many attempts. `SH03` (194) and `SH09` (461) carry the most iteration; `SH01` (40),
  `SH04` (41) the least.
- `FULL10MIN` is an **empty folder with one subfolder** — the assembly target for the long cut, not snapshotted.
- `Project Brief` holds 1 item — the brief itself.
- A final folder is dedicated to "our earliest experiments": "Fittingly, the final folder is dedicated to our
  earliest…" (`brief_text.txt:2416`) — matching the mojibake Characters folder being empty in the snapshot.

**So `carousel` is not a gallery of stills and not a series.** The published artefact is a single 20-second
video with no episode slug, while the *project behind it* is a 10-shot hand-drawn short with a `FULL10MIN`
assembly folder. The brief calls the published thing a trailer: "brie F5trailer of our upcoming animated
shortfilm Kok Boru" (`brief_text.txt:97`). Reconciling the 20 s published cut against 125 shot prompts that each
declare 14–16 s of screen time is **UNKNOWN** — the snapshot does not contain an edit decision list, and the
carousel's 20 s cannot be reconstructed from the prompt harvest. What *is* checkable: the prompts are full
multi-shot video prompts (never stills), each opening with a style paragraph, and the 20 s duration is the
publication's, not the project's.

**Models / resolution** (`mine2.mjs stats`): `seedance_2_0` 117 (video), `nano_banana_flash` 16 (character-sheet
edits), `cinematic_studio_video_3_5` 8. **Two aspect ratios only**: 21:9 `2016×864` ×125 (all video) and
3:2 `5056×3392` ×16 (the nano_banana character sheets). Resolution 2016×864 for every video row — the lowest
hero resolution of my four cases, consistent with hand-drawn 2D (detail lives in the painting, not the pixel count).

**`job_set_client_meta`: 0/141 rows non-null** — no staging metadata.

**The only case with UI-level camera parameters**: 8 rows carry `camera_model, camera_lens,
camera_focal_length, camera_aperture, camera_style, light_scheme, color_grading, style_prompt, style_id`
(`prompts_meta.json`) — i.e. the `cinematic_studio_video_3_5` rows (#38–#45) were generated through Cinema Studio's
parameter panel rather than described in prose. **This is unique in the four-case set** and it explains why
kok-boru states *no* aspect ratio and *no* timecode anywhere in prompt text (§2.8).

**Iteration intensity**: 141 rows → **only 15 distinct prompts** (13 video + 2 image). 126 duplicate rows; batch
sizes 24, 19, 17, 13, 12×2, 8×4, 4, 3×2, 1×2. This is the corpus's extreme case of **lock-the-prompt-and-re-roll**
(9.4 rows per distinct prompt) versus oneiric's rewrite-the-prompt (1.37 rows per distinct prompt).

## 2. Prompt anatomy — the actual grammar

This is the **most rigidly templated** case of the four: 125 of 141 rows reduce to six block orders that are all
supersets of one skeleton (`c2_order.mjs`).

### 2.0 Lanes
- **IMAGE lane** (16 rows, all `nano_banana_flash`, 5056×3392, 3:2). No blocks; **3 paragraphs, median 1,459 chars**
  (min 1,459, max 1,574): (1) "Edit the character design sheet in image_1. Keep everything exactly as painted — …",
  (2) "Change only her clothing to the warm-season traditional Kazakh outfit shown in image_2: …",
  (3) "Warm-season palette — dominant slate blue-grey and rust red…" (#1). The image lane is an **edit instruction
  against a named source** (`image_1`), with the explicit ban "Do not smooth, sharpen, denoise, redraw or add any
  photographic detail" (#1). Only 2 distinct texts (8 + 8 rows).
- **VIDEO lane** (125 rows). One skeleton, two cadence families.

### 2.1 The video skeleton — observed order (50 rows exactly, all 125 rows as supersets)
```
Style:  →  [DIRECTOR'S NOTES: 1..N]  →  [CHARACTER TAGS: / CHARACTERS:]  →  [Cinematography …]
→  [Lighting:]  →  [Atmosphere:]  →  [Color:]  →  [VOICE — <NAME>]  →  SHOT 1 — <SIZE>, <camera>
→  [HARD CUT to SHOT 2 — …] …  →  Audio [across all shots]:  →  Constraints:
```
Exact observed orders (`c2_order.mjs`, 125/141 rows have ≥3 canonical blocks, 6 distinct orders):
- 50× `Style: > Cinematography > CHARACTER TAGS: > Lighting: > Atmosphere: > Audio > SHOT n > Constraints:`
- 25× `Style: > DIRECTOR'S NOTES: > CHARACTERS: > Lighting: > Atmosphere: > VOICE > SHOT n > Audio > Constraints:`
- 25× `Style: > DIRECTOR'S NOTES: > SHOT n > Audio > Constraints:`
- 13× `DIRECTOR'S NOTES: > Cinematography > Lighting: > Atmosphere: > Color: > SHOT n > Audio > Constraints:`
- 8× / 4× the full 9-block variant with `Color:` added.

Counts over 141 rows (`count2.mjs`): `SHOT n —` **261 occurrences / 125 rows** · `HARD CUT to SHOT` **273 / 125** ·
`Audio` **125** · `Constraints:` **125** · `on twos / 12fps` **1,076** · `Style:` **108** · `Lighting:` **100** ·
`Atmosphere:` **100** · `DIRECTOR'S NOTES:` **75** · `Cinematography` **75** · `Lubezki|Deakins` **75 (150 tokens)** ·
`CHARACTER TAGS:` **62** · `CHARACTER REFERENCE IS ABSOLUTE` **50** · `FORBIDDEN` **50 (150 tokens)** ·
`12 principles of animation` **50** · `VOICE —` **25** · `Color:` **25**.
**Block ratio**: from `Style:` to `Constraints:` ≈ 8,462 chars median, of which the `SHOT n` list is ≈ 4,167,
`Constraints:` ≈ 1,022 — i.e. **≈46% preamble / 45% shot list / 11% constraints** per prompt.

### 2.2 The slug/header line — the `Style:` paragraph *is* the header
There is no film/clip id and no `INT./EXT.` slugline. Every video prompt's line 1 is a **style-family declaration**,
and it is one of only **5 distinct style paragraphs** (`c2_facts`/style extraction):
1. **24 rows** — "Style: STOP-MOTION ANIMATION — stepped, frame-by-frame motion brought to a HAND-PAINTED 2D look,
   a moving oil painting, NOT clay, NOT puppets, NOT 3D. True 12 frames per second, ANIMATED ON TWOS…" (#51–#74)
2. **25 rows** — "Style: traditional hand-drawn 2D animation, animated on twos at 12 frames per second — each
   drawing of the figures held for two frames then replaced…" (#26) [with a 8-row and a 17-row sub-variant]
3. **50 rows** — "Style: 8K IMAX, traditional hand-drawn 2D animation, animated on twos… The 12 principles of
   animation throughout: anticipation, squash and stretch, follow-through…" (#76, #101)
4. **25 rows** — "Style: 8K IMAX, hand-painted 2D animation, the look of a moving oil painting, rough painterly
   brushstrokes, dry-brush texture, matte gouache…" + a `NOTE:` that exempts atmospheric motion from the cadence
   (#17, #126)
5. **1 row** — a variant of (1) at #75.
Note the A/B inside one film: the *same* on-twos spec is labelled "STOP-MOTION ANIMATION" in one shot family and
"traditional hand-drawn 2D animation" in another. The brief says the style prefix is a deliberate fixed block:
"For additional consistency, it is important to include a stable **Style Prefix** and **Constraints** paragraphs
that will be in the beginning of your prompt. Those paragraphs will differ in every project, and here are ours"
(`brief_text.txt:2455-2460`), and "For video prompts, we utilize our system prompts which we then run through…"
(`brief_text.txt:2625`).

### 2.3 Reference tagging
- `{{ref N}}` only: **117 of 125 video rows** (823 handles, median 7, min 0, max 12). **Zero `{{uuid}}`
  handles and zero `@TAG`** — the only case of the four with no uuid references at all. Assets are addressed by
  their loader slot (`image_1`, `image_2`, …) and bound in prose: "CHARACTER TAGS: - THE ELDER (Aksakal) = the old
  Kazakh man from `{{ref 2}}`, deeply lined weathered face…" (#26).
- Precedence is stated as an absolute, not a ranking: "**CHARACTER REFERENCE IS ABSOLUTE — faces and designs from
  reference images exactly 1-to-1. Reference always overrides text description.**" (50 rows, e.g. #76, #101).
  This is the same precedence idea as trigger's "If any instruction pulls a face off the reference, drop the
  instruction and keep the face" (#26 there), phrased as a priority instead of a fallback.

### 2.4 Segment / cut / timing syntax — **ordinal only, no clock**
- `SHOT 1 — MID SHOT handheld — the preparation, still. Duration: approx. 5 seconds. COMPOSITION: …` (#76);
  then a bare `HARD CUT TO` line; then `SHOT 2 — …`.
- **Zero timecodes.** `\b\d:\d\d\b` and `0–2s` ranges: **0 occurrences in 141 rows**. Timing is expressed as
  (a) ordinal shot order + `HARD CUT`, (b) `Duration: approx. N seconds` per shot (186 tokens: 5 s ×57, 2 s ×48,
  6 s ×32, 3 s ×31, 4 s ×18), (c) a total: "16 seconds total across three shots. 12fps. 8K. No music." (#76),
  totals observed 14 s ×25, 16 s ×13, 15 s ×12.
- Beats are counted in **frames**, not seconds: "**For four frames — silence.**" (#101); "extreme anticipation
  compressed into two frames" (#101). This is the animation-specific substitution for a clock timeline.
- The shot list is entered through `SHOT 1 — <SIZE>, <camera>`, and size language is a fixed vocabulary:
  `MID SHOT` · `CLOSE-UP` · `MEDIUM CLOSE` · `TIGHT INSERT` · `WIDE SHOT` · `TWO-SHOT into CLOSE` · `MACRO`.

### 2.5 Aspect ratio / duration inside the prompt — **none**
`21:9`, `16:9`, `2.39:1`, `9:16`: **0 occurrences**. Timecode/duration-parameter tokens: **0**. The UI holds
`aspect_ratio`, `resolution`, `duration` on 141/141 rows, and 8 rows additionally hold the nine `camera_*` /
`light_scheme` / `color_grading` parameters. So **the prompt carries the performance and the shot list; the
panel carries the delivery spec.** This is the cleanest prompt/UI separation of the four cases — compare oneiric
(67/99 rows restate the aspect ratio inside the prompt for a value the UI already owns).

## 3. What this case does that the other cases may not

1. **It treats each prompt as a mini-screenplay with its own director's commentary.** `DIRECTOR'S NOTES:` is a
   numbered list of directorial instructions, not a description: "1. GENTLE HANDHELD — the camera is held in human
   hands with a soft living presence, a slow calm breathing sway… NOT aggressive, NOT jittery, NOT buffeted"
   (#17); "2. ACTING IS EVERYTHING — this scene lives entirely in performance, pauses and the eyes." (#26, 75 rows).
2. **It names real cinematographers as the camera contract.** "Cinematography Lubezki / Deakins, gently handheld
   in human hands, soft calm breathing sway only, anamorphic wide, never tripod-locked but never aggressive,
   never gimbal-smooth, eye level." (#17). 75 rows / 150 tokens. The named-DP anchor appears in **no other case**.
3. **It forbids the model's default composition as a hard rule, in one sentence.**
   "**FORBIDDEN: centered or symmetric framing in any shot.**" and "COMPOSITION: asymmetric — forbidden: centered
   framing", repeated per shot (#76, #101); plus "COMPOSITION by thirds, not centered" (#26). This is a
   *geometry* negative, not a taste negative.
4. **It writes the animation cadence as a physics contract with an explicit exception list.** The exception is the
   interesting part: "the FIGURES (the Elder and Ana, their faces and movements) animate on twos at 12fps; the
   ATMOSPHERIC elements — the soft shaft of light, the drifting dust and faint smoke — drift SMOOTHLY and slowly,
   not stepped." (#26). Compare #17: "the clouds and the cloud-shadows drift SMOOTHLY and slowly, not stepped,
   not on twos; only the sky, the moving light and the shadows move, the camp and mountains stay still."
   The template encodes **which layer is on twos and which is smooth** — the single most transferable craft idea here.
5. **Every spoken line is written phonetically in the source language, with an accent ban.**
   "VOICE — THE ELDER's voice: an old man's voice, hoarse, cracked… spoken Kazakh in Latin transliteration,
   pronounced exactly as written, soft natural Central Asian articulation, **not Russian-accented**." (#26).
   25 rows carry a `VOICE —` block, 50 rows repeat "Latin transliteration" and "not Russian-accented", and 200
   standalone quoted lines are the actual dialogue (`Qyzym...` / `Biz ony izdedik. Köp izdedik.` / `Endi taba
   almaymyz.`, #26). Dialogue is a **cast-language asset**, not an English gloss.
6. **It ends every prompt with a `Constraints:` mega-paragraph that re-states the whole shot in one sentence.**
   1,022 chars median, 125/125 rows. It is the compressed inverse of the prompt: "#26 Constraints: traditional
   hand-drawn 2D animation animated on twos at 12fps for the figures with the atmospheric light and dust drifting
   smoothly, characters from `{{ref 2}}` (Elder) and `{{ref 3}}` (Ana)… ACTING AND PAUSES are everything…
   NO MUSIC absolutely no music". Functionally identical to oneiric's `POSITIVE LOCKS` / zephyr's `LOCKS` —
   **a compressed restatement block at the end is a studio-wide habit, under three different names.**
7. **It hard-locks sound design as "no music" *by diegetic logic*.** "Audio across all shots: NO MUSIC, no score,
   no instruments of any kind — only natural sound…" (#26); and going further, the *scene* is music-free as a
   story fact. That is the local version of trigger's "this diner has a no-music rule" (#76 there) — both studios
   invent an in-world reason so the negative is motivated rather than arbitrary.
8. **It documents its own pipeline in the brief**: hand-drawn inputs → AI in-betweening → in-house colorist →
   manual sound work. "The film is built on a hybrid production pipeline that combines generative AI with
   hand-drawn artistry… Hand-drawn inputs — character designs, props and painted textures — define the look,
   performance, and emotional intent of each shot" (`brief_text.txt:2492-2494`); "Each one began as an AI
   generation and was then hand-edited and painted over by our artists through Photoshop" (`brief_text.txt:2247`);
   "…was performed entirely by our in-house color artist, who manually refined every shot" (`brief_text.txt:2339`).

## 4. Recurring phrasing bank

**Style / cadence** — "animated on twos at 12 frames per second" · "each pose held two frames then snapping to
the next, never gliding" (#51) · "Constant painterly BOIL — brushstrokes and outlines subtly alive frame to frame"
(#51) · "NO smooth interpolation, NO motion blur, NO morphing, real frame-by-frame animation not AI slop" (#51) ·
"hand-painted oil-brush texture on every drawing" (#76) · "no 3D render, no game engine, no CGI smoothness" (125 rows).

**Camera / optics** — "Cinematography Lubezki / Deakins" (75 rows) · "Aggressively handheld inside the scene —
constant restless shake and jitter every frame, jerky bounce, sharp reframing jolts, breathing sway. Horizon never
perfectly level." (#76) · "Wide anamorphic approximately 24mm. Shallow depth of field. Camera eye level or below."
(#76) · "gently handheld in human hands, soft calm breathing sway only" (#17) · "~50mm, intimate handheld" (#51) ·
"Story of the angle: …" — every shot in #76/#101 explains *why* the angle, in that exact three-word frame.

**Light** — "Lighting: flat cold diffuse ambient — dark sky, luminous snow… Light comes from the snow itself,
rising from the ground, not falling from above. No sun. No shadows. No rim light. No key light. Flat painted
shapes." (#76) · "ONE soft source: the pale shaft of daylight falling from the shanyrak crown opening high above"
(#26) · "cold grey stormlight in a blizzard, flat soft directionless, no sun, no rays, no beams, no god rays, but
the faces caught readable" (#51) · "Cold overcast misty light, soft directional… strong atmospheric depth haze" (#32).

**Motion / physics** — "real gravity, inertia and mass; weighted body movement" · "Secondary action: breath vapor
from both horses rises straight up and hangs" (#76) · "Micro-expressions and blinks drawn on twos as held poses,
not smooth" (#26) · "the full weight of his body loading and rising" (#76).

**Sound** — "NO MUSIC, no score, no instruments of any kind — only natural sound" (#26) · "SFX only. No dialogue.
No subtitles." (#76) · "Audio: near-total silence under everything. What exists: the creak and settle of saddle
leather…" (#76).

**Acting** — "the work is in his eyes" · "Micro-expressions and blinks drawn on twos as held poses" (#26) ·
"Her silence and her hands are her refusal" (#26) · "restraint, no big gestures" (#26) · "faces LIT and READABLE,
never black voids" (#51) · "not action played slow emotion" (`brief_text.txt:2046`) · "Micro-expressions: a faint
tightening of the jaw, a slow blink as a held closed-eye frame on twos" (#26).

**Composition** — "COMPOSITION by thirds, not centered" (#26) · "asymmetric — forbidden: centered framing" (#76) ·
"the camp low and the dominant mountain and sky as negative space" (#17) · "deep shadow as negative space and the
weight of loss" (#26).

## 5. Structure & story
- **Published unit**: 20 s `carousel`. **Project unit**: 10 shots (`SH01`–`SH10`) + a `FULL10MIN` assembly folder.
  Each shot folder = one shot, many iterations (`brief_text.txt:2400`). Sampled prompts declare **266–485 internal
  shots** depending on how cuts are counted (§7) — i.e. the prompts describe whole multi-shot sequences, so a
  "shot" folder holds a *sequence*, not a single framing.
- Story structure per the brief: the film is organised as a memory and a present-day hunt — a grieving mother,
  a vow made on a cliff, a massacre-by-wolves, a child raised wild. The shot list sampled here skews to
  **funeral/memory/attack** sequences: `SH03` = the vow at the blizzard cliff (#51), `SH09` = the yurt scene where
  the Elder tells Ana the child is gone (#26), `SH06`/`SH08` = riders mounting into a fog forest and the wolf
  attack (#76, #101). So the sampled shots are the film's **emotional and violent peaks**, not its connective tissue.
- `brief_text.txt:68` gives the logline; there is no act structure stated in the brief — the acts live in the
  *film* publication's folders (`ACT 1/2/3` in `kok-boru-film`), not in this carousel snapshot.
- Series relationship: none. `carousel` has no `featured_episode_slug`, no sibling episodes in the harvest.

## 6. Per-case hard rules
- **Open every video prompt with the fixed `Style:` paragraph, and close with `Constraints:`** — the brief states
  this as the consistency mechanism (`brief_text.txt:2455-2460`), and 125/125 rows obey it.
- **State the animation cadence in fps and in what is on twos** — "animated on twos at 12 frames per second"
  (1,076 mentions), plus the exemption list for atmosphere (#26, #17).
- **Forbid centred composition** — "FORBIDDEN: centered or symmetric framing in any shot." (#76, #101).
- **Reference overrides prose** — "CHARACTER REFERENCE IS ABSOLUTE — faces and designs from reference images exactly
  1-to-1. Reference always overrides text description." (50 rows).
- **Write dialogue in the source language, in Latin transliteration, with an accent ban** (#26, 50 rows).
- **Give each shot a `Duration: approx. N seconds` and a total** — "16 seconds total across three shots. 12fps. 8K.
  No music. SFX only. No subtitles. No 3D." (#76).
- **No music, and motivate it in-world** — the `Audio` block is "NO MUSIC … only natural sound" on 125/125 rows.
- **Say what is deliberately NOT in the shot**: "- DEBIL 1 = man from … STRICTLY FORBIDDEN: applying the white sketch
  background of the reference to the video." (#101, #101 — two such bans inline in the cast list).
- **Keep the three animation styles distinct by name** — the same cadence is called "STOP-MOTION ANIMATION" in one
  shot family and "traditional hand-drawn 2D animation" in another; do not merge them in the skill.

## 7. Numbers
- **Published runtime 20 s** (`publication.json`); gallery video 20 s, 4096×1716. **Film publication**: 899.042 s.
- 2,693 generations; **345,037.5 credits spent**; 2,265 likes / 189,685 views (`stats.json`).
- Prompt rows 141 → **15 distinct** (13 video + 2 image). 126 duplicate rows; batch sizes up to 24.
  **9.4 rows per distinct prompt** (vs oneiric 1.37, zephyr 1.04, trigger 3.2).
- Video chars: min **5,820** / median **9,238** / p90 12,106 / max **12,106** — the *tightest* length band in the set
  (5.8k–12.1k, a 2.1× spread; oneiric spans 126–35,672). Boilerplate is what makes it tight.
- Refs per video prompt: min 0 / median **7** / max **12**; 823 `{{ref N}}` handles; **0 uuid handles**.
- Shots: **`HARD CUT` 273 tokens / 125 rows**, `CUT TO` 148; per prompt `1 + cuts` = 3 ×88 rows, 5 ×25, 8 ×12
  → **485 declared shots over 125 prompt rows (avg 3.88)** — the highest shot density of the four cases.
  Per-shot stated durations: 5 s ×57, 2 s ×48, 6 s ×32, 3 s ×31, 4 s ×18 (186 tokens); declared totals
  14 s ×25, 16 s ×13, 15 s ×12.
- Timing: **0 timecodes**, 0 aspect ratios, 0 `SEG1/SEG2` in prompt text — all delivery spec is in params
  (`aspect_ratio`/`resolution`/`duration` 141/141; 9 `camera_*`/grade params on 8 rows).
- Iteration by folder (distinct prompts per sampled folder): ROOT 4, SH09 2, SH03 2, SH06 3, SH08 3, SH10 2.
- Credits/min: **≈17,252 credits per published second** (345,037.5 / 20 s) — but the published cut is a trailer,
  so this is not a cost-per-minute for the film. Treat as an upper bound only.

## 8. Failure modes named in this case
- **AI-default "smoothness"** — "NO smooth interpolation, NO motion blur, NO morphing, real frame-by-frame
  animation not AI slop" (#51); "no 3D render, no game engine, no CGI smoothness" (125 rows).
- **Wrong medium drift** — "NOT clay, NOT puppets, NOT 3D" (#51); "no 3D render, no game engine, no CGI
  smoothness" (125 rows); and at the tail of the `Constraints:` block, "…matching the reference not photoreal
  not 3D not Disney, cinematic muted desaturated cold palette" (#17, #126).
- **Anachronistic / polluted costume** — the image lane's whole job is dress-repair: "Do not smooth, sharpen,
  denoise, redraw or add any photographic detail — match image_1's hand-painted concept-art look and resolution one
  to one" (#1).
- **Faces as black voids** — "faces LIT and READABLE, never black voids" (#51).
- **Mugging / overplayed emotion** — "not action played slow emotion" (`brief_text.txt:2046`), and the acting
  blocks demand "Restraint, no big gestures" (#26) rather than any listed negative. Note: this case controls
  performance with *positive* acting direction; the cartoon/plastic negatives live in the style paragraph instead.
- **Centred / symmetric framing** — "FORBIDDEN: centered or symmetric framing in any shot." (#76, #101).
- **Invented geometry / extra cast** — "STRICTLY FORBIDDEN: applying the white sketch background of the reference
  to the video" (#101); "do NOT make it a second active child, do NOT give it a performing face; it only stirs
  faintly" (#51); "Exactly ONE reference" style locks in `CHARACTER TAGS` (#76).
- **Colour drift** — "correct neutral white balance, NOT a blue filter, muted desaturated" (#51).
- **Music** — "NO MUSIC, no score, no instruments of any kind" (#26); "absolutely no music" (repeated at the end of
  the `Constraints:` block, every row).
- **Wrong-accent voice** — "not Russian-accented" (50 rows).
- **Second active child / extra characters** — "do NOT make it a second active child, do NOT give it a performing
  face; it only stirs faintly" (#51).

## 9. Anything weird / low quality
- **141 rows, 15 distinct prompts.** The row count badly overstates the corpus; use §7's distinct counts. The
  2 image texts are each repeated 8× and the video texts up to 24×.
- **`description: null`** on the publication — the only case of my four with no synopsis, and `featured_episode_slug`
  is null while `featured_episode_id` is populated. Carousel metadata is simply thinner than film metadata.
- **A mojibake folder name**: `袩械褉褋芯薪邪褝懈` (`folder_tree.json`) — a Cyrillic word double-decoded; it is empty in
  the snapshot, and `subfolders_count: 15` vs 13 listed children, so 2 folders are missing.
- **`FULL10MIN` is empty (0 items, 1 sub)** — the long cut was not snapshotted, so the carousel↔film relationship
  cannot be measured from this folder.
- **Two camera regimes in one case**: 8 rows were made through Cinema Studio's parameter UI (9 extra param keys),
  117 through plain Seedance prose prompts. Merging them into one template would misrepresent the case.
- **The 20-second duration is unexplained by the prompts**: 125 video rows each declare 14–16 s of material.
  Treat `duration_seconds: 20` as the published item's length, not the project's.
- **Style naming inconsistency**: identical cadence specs are labelled "STOP-MOTION ANIMATION" (#51) and
  "traditional hand-drawn 2D animation" (#26). Two names, one technique.
- `stats.json` carries `stack: []` and `size_bytes: 0` — fields present but empty; do not read them as zero cost.

---

## 10. Cross-case note — 20 s carousel vs feature-length film, **same IP**

This is the sharpest control in the harvest because `kok-boru` (carousel, 20 s) and `kok-boru-film` (film, 899 s)
are **two publications of one project** (`kok-boru-film` → `featured_episode_slug: kok-boru/full-film`). Same
hand-drawn on-twos animation, same cast, same doctrine — and two different prompt templates.

| | **carousel** (20 s, 141 rows / 15 distinct) | **film** (899 s, 94 rows / `kok-boru-film`) |
|---|---|---|
| opening block | `Style:` — English, 5 style-family variants | `【风格＝绝对最高优先】` ("style = absolute top priority"), Chinese-first |
| block inventory | `Style: → DIRECTOR'S NOTES: → CHARACTER TAGS: → Cinematography → Lighting: → Atmosphere: → Color: → VOICE → SHOT n → Audio → Constraints:` | no `DIRECTOR'S NOTES:`, no `CHARACTER TAGS:`, no `Cinematography`, no `Lubezki/Deakins`, no `SHOT n`, no `HARD CUT`, no `Constraints:` (0 rows each) |
| shot list in prompt | **yes** — `SHOT 1…n` + `HARD CUT to SHOT n`, 3–8 shots/prompt, 273 cuts | **no** — one framing per prompt; 0 `HARD CUT` |
| timing | ordinal + `Duration: approx. N seconds` + totals; 0 timecodes | 0 timecodes |
| constraints | fixed `Constraints:` block, 125/125 rows | none; constraints fold into `【…】` rule headers |
| style anchor | photographic-animation hybrid: "hand-painted 2D, animated on twos, Lubezki/Deakins handheld" | "ROUGH COARSE BRUSH + 12FPS", "STROKES MOVE — THE PAINT IS ALIVE AND CONSTANTLY MOVING (ABSOLUTE TOP…)" |
| row→text ratio | 9.4 rows per distinct prompt | (not my case — see `kok-boru-film.md`) |

What the contrast actually teaches, and what it does **not**:
- **It is not "short prompt vs long prompt"**: the carousel's median video prompt (9,238 chars) is *longer* than
  oneiric's (9,027) and zephyr's (5,754). The carousel is verbose because it reprints the same style + constraints
  boilerplate for every shot.
- **It is "shot list inside vs outside"**: the 20 s carousel packs its whole cut sequence into each prompt and
  relies on `HARD CUT to SHOT n`; the 899 s film generates one framing per prompt and assembles in the edit.
  The same studio reversed the decision when the runtime grew — at feature length, per-prompt shot lists stop
  being editable.
- **The invariant across both is the doctrine, not the skeleton**: style-prefix-first, on-twos cadence with a
  smooth-atmosphere exemption, reference-overrides-prose, no music, forbidden-centred-framing. Those survive both
  templates; the block names do not (English `Style:`/`Constraints:` in one, Chinese `【风格＝最高优先】` in the other).
- Cross-case, the same rule holds for the other three: `trigger` (8:36) keeps the cut *outside* the EN prompt
  (1.34 shots/prompt), `oneiric` (19:49) keeps it inside with per-segment timecodes (2.99), `zephyr` (5:08) does
  both by dialect (2.89). **Runtime does not predict the template; the intended edit point does.**

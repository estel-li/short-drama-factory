# CASE DIGEST — ZEPHYR: Special

> Locator convention: `prompts.jsonl#N` = 1-based row (JSONL line) in `_data/cases/zephyr-special/prompts.jsonl`;
> `brief_text.txt:N` = line number after splitting on `/\r?\n/`; `publication.json` / `folder_tree.json` / `stats.json`.
> **Harvest caveat:** `_folder_tag` is capped at 25 rows per folder (ROOT 25, regenerations 25) — the two folders
> are equal-sized *by sampling*, not by production.

---

## 0. Header
- **Title** ZEPHYR: Special · **type** `film` · **runtime** 307.861 s (5:08) · **author** `higgsfield.studio`
  · **publication_id** `cee8c1f3-75a0-4722-970d-c78bd1d23bff` · **snapshot_folder_id** `03f15fb6-c85c-427d-b030-c509b967d4ba` (`publication.json`)
- **generations_count** 4,837 (`stats.json` → `publication.json.stats`); 766 likes / 132,876 views (`stats.json`)
- **featured_episode_slug** `zephyr-special/full-film`; categories `["banner","open-sourced-by-higgsfield"]`
- **Provenance**: `/fnf/project-publications/higgsfield.studio/zephyr-special`; `/fnf/folders/03f15fb6…/children`;
  `/fnf/folders/{id}/items/v2?include_subfolders=true`; brief snapshot `…/brief/03f15fb6…/snapshot` (`_summary.json`).
  50 prompt rows, 286,141 prompt bytes (`prompts_meta.json`).
- **Premise** (quoted, `publication.json.description`): "With a Zephyr member in dire straits, survival looked impossible - until a mysterious guest character intervened. Her mastery of mech combat surpassed the expectations of even the most elite fighters in the squad."
- Workspace `Team Askar` (`045a586c-3048-4170-b217-faeeba505f9c`), root folder literally named
  **`ZEPHYR Special FINAL`**. Brief asset host is `user_3GNcyaSCltezE7ot4WtRdn0jfo0` (the publishing account) —
  16 cloudfront refs, and *no* `.skill` / `.md` attachments at all (`c2_urls.mjs`).

## 1. Production shape

**Only two L1 folders: root and `regenerations`. No `ASSETS` folder, no scene folders.**
Root: 4,848 items, `subfolders_count: 2`; `regenerations` = 90 items (`folder_tree.json`).

The important structural fact is the **model split down the folder boundary** (`mine2.mjs stats`):

| folder | rows | models |
|---|---|---|
| ROOT | 25 | `seedance_2_0` 11, `nano_banana_2` 8, `gpt_image_2` 4, `soul_cinematic` 2 |
| regenerations | 25 | **`seedance_2_5` 25** |

Every one of the 25 `regenerations` rows carries `_param_keys` including **`extension_mode`, `draft`,
`draft_job_id`** — and no ROOT row does. So `regenerations` is not "retries": it is a **Seedance 2.5
extension/regeneration pass** over the 2.0 shots.

**`job_set_client_meta` is the only staging metadata in the whole four-case set** — 25/50 rows, single key
`seedance25_comparison` (`mine2.mjs meta`):
```json
{"seedance25_comparison":{"act":null,"scene":null,"attempt":1,
  "source_job_id":"1cd8b3a9-…","execution_run_id":"zephyr-special-regenerations-20260811",
  "target_folder_id":"b8fc9265-f238-571b-9c8d-60f41ed57eef",
  "source_job_set_id":"0950a2da-…","source_manifest_sha256":"7fe3775cf492…"}}
```
Decoded: `attempt` = which re-roll of that shot (distribution **1 ×22, 2 ×2, 3 ×1**); `source_job_id` =
the 2.0 job being re-done; `execution_run_id` = a dated batch label; `source_manifest_sha256` = **the same
hash on all 25**, i.e. one manifest drove the whole pass. `target_folder_id b8fc9265…` **does not appear in
`folder_tree.json`** — the comparison folder itself was not snapshotted. All 25 `source_job_id`s are absent
from the snapshot too, so 2.0↔2.5 pairing is UNKNOWN (0/25 resolved) — the closest we can get to the A/B.

**Aspect / resolution** (`mine2.mjs stats`): **21:9 ×36** (4032×1728 ×28, 2016×864 ×8); 16:9 ×12
(2752×1536 ×4, 5504×3072 ×3, 3840×2160 ×3, 2048×1152 ×2); 3:4 ×1 (3584×4800), 2:1 ×1 (2816×1408).
Assets were generated at 4–5.5 K wide and shots at 4032×1728 or 2016×864.

**Iteration intensity**: 50 rows → **48 distinct prompts** (34 video + 14 image). Only 1 duplicate group
(3 identical video prompts). This is the *least* prompt-recycling case in the set — because the 2.5 pass
**rewrote** the text rather than re-running it (§3.6).

## 2. Prompt anatomy — the actual grammar

ZEPHYR is the **most heterogeneous** of the four: `c2_order.mjs` finds 8 different block orders over the 17 rows
that carry ≥3 canonical blocks (vs 6 for kok-boru, 7 for trigger, 28 for oneiric), and 33 of 50 rows carry no
canonical block at all. Four distinct dialects coexist.

### 2.0 Lanes
- **IMAGE lane** (14 rows: `nano_banana_2` 8, `gpt_image_2` 4, `soul_cinematic` 2). Median **566 chars**
  (min 17, max 3,408) — the shortest image lane in the set. No blocks; a single imperative sentence or a
  "Character sheet 16:9, white studio background, clean grid layout. Use face from image1 and image2…" (#1).
  Several are **Russian one-liners with no subject**: "пусть волосы висят вниз как в футаже 2" (17–122 chars, #2, #3, #7, #8, #9)
  — pure edit deltas ("remove the girl from the cabin", "delete one dagger").
- **VIDEO lane** (36 rows). Four dialects below.

### 2.1 Dialect 1 — the jammed monolith (7 rows: #11, #14, #23, #46, #47 among them)
A single `Tags: {{ref 1}} = Haru Min · {{ref 2}} = Reina · …` legend line, then **all block headers
glued into running paragraphs with no line breaks**: "…NOT 3D/game/cartoon.**CAMERA** (cool operator moves):
big, smooth cinematic camera flythroughs…**ENVIRONMENT MOTION** (all shots): …**DANCE STYLE**: proper,
deliberate synchronized K-pop group choreography…" (`prompts.jsonl#11`).
Header set, in order: `GLOBAL STYLE` → `CAMERA (…)` → `ENVIRONMENT MOTION` → `DANCE STYLE` →
`SKIN / REALISM` → `CHARACTERS (…)` → `LOCATION:` → `MUSIC / VOCALS:` → `LOCKS:` → `SHOT 1 — …` → `SHOT 2 — …`.
Counts: `SKIN / REALISM` 7 rows, `GLOBAL STYLE` 7, `Tags:` legend 7, `DANCE STYLE` 1, `MUSIC / VOCALS` 3.
This is a formatting failure that became a dialect: the headers survive, the line structure does not.

### 2.2 Dialect 2 — the 14-block shot spec (rows #32, #42, #50; plus #24–#27, #41, #48 shorter)
Full order, 3 rows byte-similar:
```
SCENE CONTEXT → ACTIVE REFERENCES → ATMOSPHERE → LOCATION MAP → FIRST FRAME AND SPATIAL BLOCKING
→ FORMAT MODE → OPTICS → CAMERA → ACTION TIMING → PHYSICS → LIGHTING → AUDIO → POSITIVE LOCKS
```
The shorter variants (`ASSETS → LOCATION MAP → FORMAT MODE → OPTICS → CAMERA → ACTION TIMING`, rows #24–#27)
**repeat the whole 6-block unit once per shot** — the block set is a *per-shot* template, not per-prompt
(`c2_skel.mjs`: "ASSETS | LOCATION MAP | FORMAT MODE | OPTICS | CAMERA | ACTION TIMING | LOCATION MAP | FORMAT MODE | …").
Counts over 36 video rows: `HARD CUT` 35 tokens/9 rows · `OPTICS` 14 · `LOCATION MAP` 13 · `FORMAT MODE` 23 ·
`ACTION TIMING` 15 · `SHOT n —` 37 tokens/13 rows · `COLOUR` 7 · `LENS LOCK` 19 tokens/4 rows ·
`ACCENT DOCTRINE` 13 rows.

### 2.3 Dialect 3 — markdown/heading prompts (rows #15, #28, #30, #35, #36, #38, #45, #47)
`# ZEPHYR — SEEDANCE 2.5 PROMPT` / `## SCENE: "Lunch on the Dead Bridge" — Haru devours ramen on a
broken-down mech · 3 shots · ~10s total · 4K`, then `### STYLE PREFIX`, `### SCENE SUMMARY`,
`### INSTRUCTION BLOCKS`, `### ASSETS (this scene)`, `### SCENE NOTE`, then **per shot** a bolded
`**SCENE CONTEXT** / **ACTIVE REFERENCES** / **LOCATION MAP** / **FIRST FRAME…** / **FORMAT MODE** /
**OPTICS** / **CAMERA** / **ACTION TIMING** / **PHYSICS** / **LIGHTING** / **COLOUR** / **AUDIO** /
**CHARACTER ACTING** / **LOCKS**` set (`prompts.jsonl#45`, 19,890 chars — the longest prompt in the set).
A pure `SHOT 01 — WIDE / ESTABLISHING` … `SHOT 05 — IMPACT / AFTERMATH` listicle variant also exists
(#35, #36, #38): one paragraph per shot, no blocks at all.

### 2.4 Dialect 4 — the JSON prompt (5 rows start with `{`: #17, #19, #21, #31, #43; 4 of them match the `style_prefix` schema exactly)
Prompts that are literally a JSON object with a fixed schema: `style_prefix` (with sub-keys `style`,
`operating_style`, `lighting`, `color_accent_doctrine`, `texture`, `camera_lens`, `skin`, `acting`, `physics`,
`composition`, `technical`, `audio`), `scene_summary` (`who_and_where`, `what_happens`, `tone`, `what_we_read`,
`what_we_do_not_show`, `purpose`), `assets` (uuid → description), `shot` (`id`, `type`, `duration_seconds`,
`scene_context`, `active_references`, `first_frame_and_blocking`, `format_mode`, `optics`, `camera`,
`action_timing`, `physics`, `lighting`, `colour`, `audio`, `character_acting`, `locks`).
This is the single most machine-structured prompt form in the corpus (`prompts.jsonl#17`, 13,355 chars).
Its `scene_summary.what_we_do_not_show` is effectively a negative block **inside a positive schema**.

### 2.5 The slug/header line
Where a title exists it is a markdown heading and it carries the **shot budget**: `## SCENE: "Lunch on the Dead
Bridge" — Haru devours ramen on a broken-down mech · 3 shots · ~10s total · 4K` (`prompts.jsonl#45`);
Chinese equivalent `场景:"悬崖时刻 — 坠落惊魂"… · 单镜头 · 约6秒 · 4K` (`prompts.jsonl#28`).
`INT./EXT.` sluglines appear in some shot headings ("SHOT 1 — INT. CABIN, REINA SPRAWLED, SMOKING (handheld)", #30).

### 2.6 Reference tagging
- `{{ref N}}` in 25/36 video rows, `{{uuid}}` in 10 rows, `{{ref 1}}`（音轨）in 3 rows
  (a music-track reference: "MUSIC / VOCALS: `{{ref 1}}` plays throughout", #11).
- `@TAG` human-readable aliases in 5 rows: "`{{ref 1}}` → **@broken_bridge** (location) · `{{ref 2}}` → **@Haru_battle** …"
  (#45); "`@Naomi @Naomi_cabin @bridge` — DUAL REFERENCE: FACE / HEAD from the CLOSE-UP head reference" (#49).
  This is the only case in the set with a **named-alias layer over the uuids**.
- Reference-binding is stated as "keep your loaded order" (#45, #28) — order in the loader is treated as meaningful.

### 2.7 Segment / cut / timing syntax — clock + FOV, per segment
- `FORMAT: CONTROLLED MULTI-SHOT, FOUR hard cuts, ~3s each, ~12s total, real-time 24fps` (#16).
- `ACTION TIMING: 0-3.0s: machine-gun-fast flash flickers through the cockpit…` (#16); 91 clock ranges over 20 rows.
- **`LENS LOCK SEG1 = 84° classic wide, low, the sprint and leap immersive.`** … `LENS LOCK SEG6 = 47° standard normal`
  followed by "No focal drift mid-segment." (#32). 18 LENS LOCK lines; degree tokens in the corpus:
  180 ×27 (= 180° shutter), 84 ×15, 34 ×12, 29 ×7, 47 ×6, 90 ×3.
- **Subject position written as frame coordinates**: "her body and face up-frame at x 55%, y 35%";
  "3/4, off-centre (face x 44%, y 47%)" (#16). 3 rows carry `x N%`.
- **Colour as an explicit percentage budget**: "Colour - ACCENT DOCTRINE: ~70% dark cold grey-blue base +
  ~20% mint/teal accent + ~10% warm counter-note" (#16); "~68% dark steel-grey/near-black metal + ~18% maroon-red
  … + ~8% cold dim daylight grey-blue + ~6% pulsing red" (#49). 13 rows use `~NN%`; token frequency 20% ×30,
  70% ×27, 10% ×27.

### 2.8 Aspect ratio / duration inside the prompt — almost none
Only 7/36 video rows state an aspect ratio (21:9 ×8, 2.39:1 ×3) and durations are per-shot `~3s`/`~4s`/`~5s`
(31/19/18 occurrences). AR and resolution live in the UI (`aspect_ratio` 48/50 rows, `resolution` 48/50) —
the *opposite* of oneiric. Duration is stated twice (`~3s` in prose + `duration` param on 36 rows).

## 3. What this case does that the other cases may not

1. **It solves hard physics by mutating the reference asset, not the prompt.** "We inverted the character
   sheet. By baking the required physics directly into the input stage, we guided the model through the
   generation process. This freed us to prompt more casually, spending less energy explaining the physics of
   the setup. Now, Naomi has a new 'inverted' state" (`brief_text.txt:164`). Same doctrine as oneiric's
   anamorphic hack, applied to *pose/gravity* instead of optics.
2. **It ships a JSON-schema prompt**, with a `style_prefix` object and a per-shot `shot` object — the only
   machine-parseable prompt form in the corpus (`prompts.jsonl#17`).
3. **It quantifies the grade**: "~70% … + ~20% … + ~10% …" accent doctrine, restated as 4 percentages when the
   setup is more complex (#16, #49). This turns colour into an arithmetic contract instead of an adjective.
4. **It locks focal length per segment in degrees and forbids mid-segment drift**: `LENS LOCK SEG3 = 29°
   short telephoto, detail on the hand and blade for the grip change.` … `No focal drift mid-segment.` (#32, 18 lines).
5. **It uses a named-alias layer over uuids** (`@broken_bridge`, `@Haru_battle`, `@ramen_thermos`) and asks the
   loader to keep the order (#45, #49, #28). Aliases are the only case-wide naming convention.
6. **The 2.5 pass rewrote every prompt instead of re-rolling it** — 48 distinct texts from 50 rows, with
   `attempt` metadata showing 22 first attempts and only 3 second/third attempts. Compare kok-boru, which
   re-ran 141 rows from 15 distinct texts.
7. **It deliberately under-specifies when it trusts the model**: "Here, we opted for less strict prompting and
   gave the model more creative control, dictating only key anchor points" (`brief_text.txt:570`). The corpus
   shows both settings side by side — the 14-block spec (#32) and the 5-line listicle (#35).
8. **It uses layout images as positional guides, not as shot inputs**: "We didn't feed them as direct shot
   inputs, but rather used them as a positional guide to track spatial orientation and directional movement"
   (`brief_text.txt:531`).

## 4. Recurring phrasing bank

**The `LOCKS` restatement block** — present in 6 rows, always a compressed re-statement of the whole shot:
"**LOCKS** MED-CLOSE SIDE (~3s); @Haru_battle devouring in profile, hums + blissful blink; @Haru_mecha
dead/turned away…; 180° honoured; 4K real-time 24fps; SFX + hums only; no music; **markers never generated**" (#45).
"markers never generated" is a fixed clause (also #45 ×3, #46, #47).

**Style boilerplate** (identical across dialects): "8K, photorealism. Real organic film grain and halation.
High dynamic range. NOT a 3D render, NOT a game engine, NOT game-cutscene aesthetic, NOT a cartoon." (#16, #17).
30/36 video rows carry this anti-slop clause — more than any other case except kok-boru (125/125).

**Operating-style anchors** — "OPERATING STYLE - HOYTE VAN HOYTEMA: large-scale realism with intimate handheld
closeness, immersive in-camera feel, tactile real-world textures, atmospheric haze and volumetric light,
photochemical look." (#16) · also "Hoyte van Hoytema / Cuarón 'Gravity' feel" (#49) and
"Hoyte van Hoytema naturalism" (#17) — **one named DP, three spellings** ("Hoytema"/"van Hoytema").

**Camera** — "large-format 65mm spherical prime, natural motion blur at a 180-degree shutter" (#16) ·
"lens breathing" (#16, #17, #45) · "handheld, alive, real war-documentary energy" is trigger's; zephyr's is
"Handheld, intimate, tiny breathing sway" (#45) · "never gimbal-smooth, never tripod" (#49) ·
"clean crisp polished image (high clarity, sharp, fine subtle grain)" (#11) ·
"rock-video × K-pop-MV vibe: edgy, punchy, glossy, stylish" (#11).

**Light** — "motivated natural light, one soft key" (#17) · "flat overcast daylight diffused through heavy fog,
single soft sky key" (#45) · "half her face in shadow" (#16) · "dim cold overcast daylight, no direct sun" (#17).

**Skin / realism** — "pore-level realism — visible pores, fine vellus hair, natural asymmetry, no smoothing"
(#16, #17, #45) — the same clause in all three dialects.

**Acting** — "the work is in the eyes" · "Natural blinking and active brow; no mask-face, no dead eyes" (#16) ·
"Keep every smile SMALL and natural; NO wide toothy grin, never Joker-like" (#16) ·
"FOREHEAD AND EYEBROW MOVEMENT MUST PRECISELY MATCH THE EMOTION OF EACH LINE" (#17).

**Sound** — "Audio: environmental SFX only … No music. No subtitles. No on-screen text or watermarks." (#16) ·
"diegetic singing ONLY. The DnB track itself is NOT audible/NOT present in the mix" (#17) — a track that is
referenced (`{{ref 1}}`) but explicitly muted.

## 5. Structure & story
- 307.861 s in **no scene taxonomy at all** — the snapshot is `ZEPHYR Special FINAL` root + `regenerations`.
  Structure lives *inside* the prompts: every prompt declares `N shots / ~Ns total` (#45: 3 shots/~10 s;
  #16: 4 hard cuts ~3 s each ~12 s; #32: 6 segments ~10 s).
- This episode is a **"special"** (a guest-character episode inside a series): brief calls it an episode of
  ZEPHYR and references a prior episode's cast; the publication's `featured_episode_slug` is
  `zephyr-special/full-film`, so one episode = the whole 5-minute cut.
- Stated story rule: build around a set piece — "design a standout scene and build the surrounding edit toward
  that culmination" (`brief_text.txt:609`); the brief is organised around three "impossible shots"
  ("We planned several 'impossible shots' and ultimately brought them to life", `brief_text.txt:416`).
- Editing method: "we simply edited together the most cinematic cuts" from consistent takes
  (`brief_text.txt:586`) — i.e. **generate variants, choose in the edit**, which explains the 22 first-attempts.

## 6. Per-case hard rules
- **Change the input before you lengthen the prompt** — bake physics into the asset (inverted character sheet),
  bake the lens into the plate (`brief_text.txt:164`; same doctrine as oneiric, `brief_text.txt` there).
- **Declare the shot budget in the prompt header**: `N shots · ~Ns total · <resolution>` (#45, #28, #16, #32).
- **One `LENS LOCK` per segment, in degrees, and no focal drift inside a segment** (#32).
- **Quantify colour**: `~70/20/10` (or 68/18/8/6) shares instead of adjectives (#16, #49).
- **Name the reference twice**: `{{uuid}}` plus a human alias `@tag`, and keep the loader order (#45, #49).
- **Always include the anti-slop clause**: "NOT a 3D render, NOT a game engine, NOT game-cutscene aesthetic,
  NOT a cartoon" (30/36 rows).
- **Skin clause on every character beat**: "pore-level realism — visible pores, fine vellus hair, natural
  asymmetry, no smoothing" (#16, #17, #45).
- **Privacy/cleanliness tag on the end of a shot**: "markers never generated" (#45, #46, #47) — i.e. never
  emit a watermark.
- **Forbid the model's default framing**: "off-centre, non-symmetrical compositions" (#17), "spontaneous
  documentary framing" (#17/#45).
- **If it must be inaudible, say so explicitly**: "the DnB track is NOT audible … No music in the audio" (#17).

## 7. Numbers
- Runtime 307.861 s = 5:08; 4,837 generations; 766 likes / 132,876 views (`stats.json`).
- Prompt rows 50 → **48 distinct** (34 video + 14 image); only 1 duplicate group (3 identical video prompts).
- Video chars: min 1,822 / median **5,754** / p90 13,930 / max **19,890**. Image chars: min 17 / median **566** / max 3,408.
- Refs per video prompt: min 0 / median **20** / max **66**; 729 `{{…}}` handles total (26 image handles, 3 audio).
- Shots per video prompt (`1 + HARD CUT`): 1 ×18 rows, 2 ×3, 3 ×3, 4 ×3, 5 ×1, 6 ×3, 7 ×4, 8 ×1
  → **104 internal shots over 36 prompts (avg 2.89)**.
- Timing: `~3s` ×31, `~4s` ×19, `~5s` ×18 (per-shot); 91 clock ranges over 20 rows; 18 `LENS LOCK` lines;
  degree tokens 180 ×27 (shutter), 84 ×15, 34 ×12, 29 ×7, 47 ×6.
- Colour budget tokens: 20% ×30, 70% ×27, 10% ×27, plus 72/68/18/35/38/30/40% one-offs.
- Regeneration pass: 25 shots, attempts 1 ×22 / 2 ×2 / 3 ×1; 1 manifest hash for all 25.
- Aspect: 21:9 ×36 rows (72%); assets up to 5,504×3,072; shots at 4032×1728 or 2016×864.
- Credits/min: UNKNOWN (no `credits_spent` in `stats.json`).

## 8. Failure modes named in this case
- **"Impossible shots" fail on prompt alone** — "At first, we tried tackling this purely through precise
  prompting, but the results fell short. Eventually… change the input" (`brief_text.txt:447-461`).
- **Position scrambling across movements** — "helping the model maintain full continuity across all movements
  without scrambling object positions" (`brief_text.txt:531`).
- **Mech sliding / physics absurdity** — "we didn't want it to feel absurd, taking into account the mech's
  scale and mass" (`brief_text.txt:507`).
- **Waxy / CG skin** — "Skin matte, no plastic sheen. Soft natural shadows on faces … NOT
  waxy/airbrushed/CGI/doll" (#11); "no smoothing, no retouching" (#16, #17, #45).
- **Joker grin / mask face** — "Keep every smile SMALL and natural; NO wide toothy grin, never Joker-like.
  Different emotions in the eyes. Natural blinking and active brow; no mask-face, no dead eyes" (#16).
- **Wrong lens regime** — "NOT wide-angle, NOT large-format, NOT a 65mm IMAX/large-format look" (#17) and
  conversely "NOT wide-angle, no fisheye, no deep focus" (same). Focal length is a hard constraint both ways.
- **Row/line-up staging** — "#17 `what_we_do_not_show`: NO standing in a row/line; NO hugging; NO looking into
  the camera/lens".
- **Music where none belongs** — "NO music in the audio" (#17), "No music, no subtitles, no on-screen text or watermarks" (#16).
- **On-screen markers** — "markers never generated" (#45).

## 9. Anything weird / low quality
- **The `regenerations` folder holds the 2.5 pass, not retries** — easy to mis-read as duplicates. Its
  `job_set_client_meta` points at `target_folder_id b8fc9265…`, which is **missing from `folder_tree.json`**;
  `subfolders_count: 2` but only 1 child is listed, so the snapshot is missing a folder.
- **All 25 `source_job_id`s are unresolvable** (0/25 found among the other rows' `job_id`), so the 2.0→2.5
  comparison cannot be reconstructed from this harvest.
- **Dialect 1 is a formatting bug preserved as a template**: 7 prompts have block headers glued onto the ends
  of sentences ("…NOT 3D/game/cartoon.CAMERA (cool operator moves):"), because newlines were lost.
- **Russian one-liner rows** with no grammatical subject: "удали один кенжал" ("delete one dagger", #9, 17 chars),
  "убери пену и конденсат" (#3, 71 chars) — edit deltas, useless as film prompts.
- **The `LOCKS` block is machine-duplicated text**: rows #32, #42, #50 are byte-identical (8,404 chars) — the same
  prompt harvested three times from the same `regenerations` folder.
- Duplicate image prompts (#1 and #10 are both character sheets); rows #17/#19/#21/#31/#43 all open with `{`
  (four conform to the `style_prefix` JSON schema, one does not).
- The brief is a **marketing essay, not a spec**: it names three techniques but ships **no block dictionary and
  no `.skill` files** — which is exactly why this case's prompt template is the least stable of the four.
  Treat its absence of a schema as a finding, not a gap in the harvest.
- `publication.json` text is double-encoded (`[mojibake: “—”]`); quotes repaired here.

---

## 10. Cross-case note — how much does the template vary with runtime?

ZEPHYR (5:08) sits between oneiric (19:49) and kok-boru (20 s), and its template is **not** in between — it is
the *least* standardised of all four. The correlation is not with runtime but with **whether the brief ships a
block dictionary**: oneiric ships CINEDANCE + `tig-*` skills and gets one stable 12-block order in 12 rows;
trigger ships `tig-acting-task`/`tig-blocking-map` and gets a stable content skeleton with a moving block order;
kok-boru ships a written "Style Prefix + Constraints" doctrine and gets one 8-block skeleton in 125/125 rows;
zephyr ships an essay and gets four dialects.

Same-IP / different-runtime control (from the lead's `kok-boru-film` harvest, 899 s, same project —
`featured_episode_slug kok-boru/full-film`): the 20 s carousel prompt is
`Style: → DIRECTOR'S NOTES: → CHARACTER TAGS: → Cinematography → Lighting: → Atmosphere: → Color: → VOICE →
SHOT n → Audio → Constraints:` (mirrored in), while the 899 s film's prompts begin `【风格＝绝对最高优先】`
("style = absolute top priority") and carry **no `SHOT n` list, no `HARD CUT`, no `Constraints:` block at all**.
So within one IP, the runtime/form change rewrites the template wholesale — the invariant is the *doctrine*
(style prefix first, physics on twos, no music), never the block list.

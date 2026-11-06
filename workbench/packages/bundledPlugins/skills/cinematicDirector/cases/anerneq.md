# ANERNEQ — case digest

## 0. Header

- **Title** ANERNEQ ("Anerneq — breath; soul", `skills/724f5ebf-…md:8`) · **type** `film` · **runtime** 1202 s (20:02) · **author** `higgsfield.studio`
- **publication_id** `561e15d4-57aa-4c99-bccc-97045495008a` · **snapshot_folder_id** `fa8b6914-8748-4a83-8551-ad7a2704407c` · **featured_episode_slug** `anerneq/full-film`
- **generations_count** 11,961 (`stats.json` → `publication.stats.generations_count`; also the root folder `count`) · likes 120 · views 27,839 (`stats.json`)
- flags: `type=film`, `is_ongoing=true`, `has_changes_since_publish=false`, `show_prompts=true`, `show_canvas=true`, `categories=[]`, `tags=[]`, cover 3840×2160, gallery video 3840×2160/1202 s
- **Provenance** (`_summary.json`, `brief_assets.json`): `/fnf/project-publications/higgsfield.studio/anerneq` → `publication_id`; `/fnf/folders/{snapshot_folder_id}` + `/children` → `folder_tree.json`; `/fnf/folders/{id}/items/v2?include_subfolders=true` → `prompts.jsonl` (150 rows, 1,213,274 B per `prompts_meta.json`); `https://dam-editor-worker.higgsfield.ai/brief/{snapshot_folder_id}/snapshot` → `brief.bin` → `brief_text.txt`; one `.md` asset from `d2ol7oe51mr4n9.cloudfront.net/user_3Bu87bnbVF6vTjFAF0NsctDxqwO/724f5ebf-b29e-4090-86ba-f40853d6450b.md` → `skills/` (filename in brief: `ANERNEQ_SKILL_v6_EN.md`, `brief_text.txt:132`)
- **Premise** (`publication.json.description`): *"An Arctic drama about love, sacrifice and the cost of letting go. Exiled with her father, whose fading mind mistakes her for his dead wife, a young huntress leads him across the frozen wilderness of 1920s Chukotka to the sacred Whale Bone Alley. She believes her own life is the price of saving him—but the journey demands a sacrifice she never imagined."* — the mojibake `[mojibake: “—”]` is a UTF-8 dash mis-decoded in the harvest, not part of the text.
- The project's **own SKILL file** (`skills/724f5ebf-…md`, 546 lines) is the most instructive artefact in this corpus: it is the *specification* this corpus is the *execution* of. Where spec and execution disagree, both are recorded below.

## 1. Production shape

- **Folder taxonomy is scene-ordinal, not act-based**: `1st scene` … `10th scene` (typo `8 thscene`, `9th scene`), plus `ASSETS`, `road`, `final-v1`, `final-v2` (`folder_tree.json` → `children.root`). The skill's own story division is three acts (`skills/724f5ebf-…md:386-392`) — the *folders* never use it. Execution tracks scene numbers; only the finished cut is thought in acts.
- **Root**: 11,961 items, `subfolders_count: 15`; `folder_tree.json` enumerates **14** root children (one folder missing from the harvested tree — see §9).
- Folder sizes (items): `ASSETS` 2,583 · `8 thscene` 2,195 · `final-v1` 1,879 · `final-v2` 1,748 · `6th scene` 1,363 · `road` 525 · `4th scene` 458 · `9th scene` 432 · `7th scene` 233 · `2nd scene` 184 · `1st scene` 148 · `10th scene` 127 · `5th scene` 80 · `3rd scene` 4.
- **Two finished passes exist side by side**: `final-v1` (1,879) and `final-v2` (1,748) — re-generation of the whole cut as a versioned folder, not in-place replacement. `road` (525) is the only narrative bucket created outside the scene numbering — it matches the skill's note that "the road scenes compress into short inserts" (`skills/724f5ebf-…md:543`).
- **Shot-level subfolders only where a scene was hard**: `1st scene` (1st/2nd/3rd shot), `2nd scene` (6 shots), `4th scene` (6 shots + a `regen` folder of 46), `5th scene` (4 shots). 6th–10th scenes have none — those were run as whole scenes, not per shot. `5th_shot` of `4th scene` holds 217 items against `6th_shot`'s 10: **the cost is per-shot and wildly uneven**, and the tree records where it went.
- **`job_set_type`** (`prompts.jsonl`, 150 sampled rows): `seedance_2_5` 121 (all video + speech), `soul_cinematic` 11, `nano_banana_2` 11, `gpt_image_2` 6, `text2image_soul_v2` 1. Matches the skill's tool statement: "**Seedance** — all video and all speech. **Claude + this skill** — every prompt. **Blender** — geometry, previz, blocking" (`skills/724f5ebf-…md:24`).
- **Resolution / aspect**: 2016×864 (108 rows, 72.0%, = 2.333 → **21:9**) · 1344×576 (13, 21:9 at draft size) · 2528×1088 (11, 21:9) · 6336×2688 (11, 21:9 master) · 3840×1648 (6, 21:9) · 2048×1152 (1, 16:9, 0.7% — a single outlier). **98.7% of the corpus is 21:9.** The skill's hard rule: "Aspect ratio **21:9**" (`skills/724f5ebf-…md:10`).
- **`job_set_client_meta` is `null` in 150/150 rows.** The studio staging metadata described in `HARVEST.md:48` was not captured for this case — **UNKNOWN**, no attempt to reconstruct it from folder names (though folder names *are* the staging metadata here, see §5).
- **Harvest design, not corpus size**: `_folder_tag` is exactly 25 rows × 6 folders (`ROOT`, `ASSETS`, `8 thscene`, `final-v1`, `final-v2`, `6th scene`). Everything below is over **150 sampled rows**, which collapse to **69 distinct prompts** (§9). Frequency claims are stated over distinct prompts wherever duplication would distort them.
- **Prompt params present but values not harvested**: `duration` in 121 rows' `_param_keys`, `aspect_ratio` in 138, `generate_audio` in 121 — no values in the jsonl. Only `width`/`height` survive. So the prompt-side duration statements cannot be cross-checked against the UI (§2, §7).

## 2. Prompt anatomy — the actual grammar

### 2.1 The canonical order the skill prescribes

```
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
(`skills/724f5ebf-…md:36-47`; "Added as needed: **THE SITUATION**, **FRAME MATCH**, **WHO IS WHO**. Use **LIVING MOMENT** instead of LIVING FACE/EYES for an animal or a physical process." `:49`)

### 2.2 The order that was actually used — two grammars coexist

**Grammar A — the 20-block order (13 rows, `r125-134,147-149`).** Observed sequence exactly:
`TAGS → STYLE PREFIX → Style → NO SUBTITLES → COMPOSITION → THE SHOT → SPOKEN LINE → CAMERA → LIVING → ANTI-AI-TELL → LIGHT → NO LENS FLARES → HARD ANAMORPHIC → HYPER-REAL → PHYSICS → ACTING → AUDIO → NEGATIVE` (no `TOTAL RUNTIME`/`GEOMETRY ANCHOR` in these rows; runtime is folded into `THE SHOT` as "~9s, ONE CONTINUOUS TAKE"). `r4,6,14,19,24` are a 5-row variant of the same family that puts `PHYSICS` and `ANTI-AI-TELL` before `AUDIO` and drops `LIGHT`/`NO LENS FLARES`/`HYPER-REAL` into a single `LIGHT —` opener.

**Grammar B — the FILM-LOOK-first production order (dominant).** Exact observed sequences, from the order census over 150 rows (block label → number of rows sharing that exact order):

| observed sequence | rows |
|---|---|
| `FILM LOOK → LIGHT → CAST → VOICES → CAMERA → KEEP THE LOGIC → NEGATIVE` | 12 (`r135-146`) |
| `LIGHT → FILM LOOK → CAST → AUDIO → KEEP THE LOGIC → NEGATIVE` | 7 (`r10,11,15,16,17,20,23`) |
| `FILM LOOK → LOCATION → CAST → VOICES → AUDIO → CAMERA → KEEP THE LOGIC → NEGATIVE` | 7 (`r57,61-66`) |
| `FILM LOOK → SKY → LIGHT → CAST → VOICES → AUDIO → CAMERA → KEEP THE LOGIC → NEGATIVE` | 7 (`r79,82,83,87,91,95,99`) |
| `LIGHT → FILM LOOK → CAST → THE SHOT → AUDIO → KEEP THE LOGIC → NEGATIVE` | 6 (`r2,3,7,8,18,22`) |
| `FILM LOOK → LIGHT → CAST → THE SHOT → VOICES → AUDIO → CAMERA → KEEP THE LOGIC → NEGATIVE` | 5 (`r71-74,84`) |
| `FILM LOOK → LIGHT → CAST → VOICES → AUDIO → CAMERA → KEEP THE LOGIC → NEGATIVE` | 5 (`r76,90,92,94,98`) |
| **B3 (late, 17–19 Sep)** `SKY → FRAMING → EYELINE AXIS → HOW HE IS COVERED → HOW HE GETS OUT → CAMERA → FILM LOOK → LIGHT → SUBJECT → THE SHOT → VOICES → AUDIO → KEEP THE LOGIC → NEGATIVE` | 9 (`r100,101,102,104,109,111,112,116,119`) |

The constant across every one of these: **`NEGATIVE` last, `KEEP THE LOGIC` immediately before it, `FILM LOOK` early (first or after `LIGHT`/`SKY`), and `CAMERA` late.** Those four positions are the actual invariant; the middle blocks shuffle per shot. Where a second `FILM LOOK` is needed it is re-issued as `FILM LOOK REPRISE` after `KEEP THE LOGIC` (56 rows) so the look brackets the whole prompt.

Block presence over 150 rows: `NEGATIVE` 122 · `AUDIO` 107 · `CAMERA` 104 · `FILM LOOK` 100 · `LIGHT` 98 · `KEEP THE LOGIC` 94 · `VOICES` 75 · `CAST` 71 · `FILM LOOK REPRISE` 56 · `THE SHOT` 54 · `SKY` 34 · `COMPOSITION` 32 · `LOCATION` 25 · `TAGS` 18 · `SPOKEN LINE` 18 · `PHYSICS` 18 · `CHARACTER ACTING` 13 · `HYPER-REAL CAPTURE` 13 · `NO LENS FLARES` 13 · `GEOMETRY ANCHOR` 13 · `TOTAL RUNTIME` 17 · `SUBJECT` 15 · `STRICT CONSISTENCY` 9 · `END` 7.

**Read this as a chronology, not a menu.** The SKILL's 20-block order is the *late formalisation* of what the production dialect was already doing: the look opens the prompt, the geometry/eyeline locks are added as the shot needs them, `KEEP THE LOGIC` states the invariants, `NEGATIVE` closes. B3 (17–19 Sep, the last week of work in the sample) is the most evolved: geometry and eyeline come first and the look moves into the middle. The skill's single most important structural sentence explains why any order works: "**Every prompt is an island.** The model has no memory. Light, optics, wardrobe, props, voice and geometry are re-specified from scratch in every shot" (`skills/724f5ebf-…md:51`).

### 2.3 The slug / header line

There is **no slugline** in the ANERNEQ dialect — no `EXT./INT.` line anywhere (0/150). The scene identity lives in the `STYLE PREFIX —` slot as a compressed one-liner:

> `STYLE PREFIX — SCENE AN-07 / AFTER THE WATER — TYNE, SOAKED AND FREEZING, DRAGS HER NEAR-LIMP FATHER ACROSS THE ICE IN FULL POLAR NIGHT … (ONE SHOT ~9s) — ANAMORPHIC "REVENANT" / IÑÁRRITU / LUBEZKI, ANTI-AI-TELLS, NO SUBTITLES.` (`prompts.jsonl#4`)

Slots: `SCENE <code>` · `<beat title>` · `<WHO> <STATE> <VERB> <OBJECT> <WHERE> <CONDITION>` · `(ONE SHOT ~9s)` · `<film-look reference chain>` · `<standing directives>`. This single line is the film's *slugline substitute* and is the second thing read after the light block.

### 2.4 How references are tagged

Three layers, and **the layers do not match**:

1. **`{{uuid}}` — the machine layer.** 196 occurrences across 150 rows, but only **1 distinct uuid**: `{{e66c0d10-cacb-4e1b-aa71-4bbe612ee8ab}}` = the daughter's face anchor. Median **1 uuid ref per prompt**, max 5. Labelled inline: `CAST: {{uuid}} — 18, hood up, soaked through and glazing with ice…` (49 rows), `SUBJECT: {{uuid}} — …` (6), `VOICES — conlang only…: {{uuid}} — …` (r86), `EYELINE AXIS: {{uuid}} is off-frame to the LEFT` (5), `SCREEN DIRECTION LOCK` (2). The label always states *the role in this shot*, never just the name.
2. **`@TAG` — the human layer.** Skill: "One element, one name — identical in the asset, in the prompt and in the table. A change of state gets a **new tag** (`@OMRYN_WET`, `@TYNE_FROSTBITE`), never an overwrite" (`skills/724f5ebf-…md:61`). In the prompts only **8 distinct tags** appear in 150 rows: `@OMRYN` 97 · `@NARTY` 43 · `@DOG` 33 · `@SNOW_GOGGLES` 13 · `@TYNE` 7 · `@loc_ICE` 5 · `@prop_FAT` 4 · `@omryn` 2. The skill's registry of ~30 tags (`@KNIFE @FIRESET @ZHIRNIK @AMULET @KHOREI @BURDYUK` …) is **not** used in the prompts — those objects are written in prose ("her KNIFE in its worn leather sheath, bone handle", `prompts.jsonl#86`). The two-layer split is stable across the corpus: **@tags and uuids are bookkeeping; prose is the prompt.**
3. **`{{ref 1}}` — the frame-argument layer.** 49 occurrences in 12 rows, used for attached reference frames: `SKY — COPY THE ATTACHED REFERENCE FRAME'S SKY EXACTLY` (`prompts.jsonl#100`).

---

## 3. What this case does that the others may not

**1. The prompt is structured around a 74-item NEGATIVE tail and a 51-variant "KEEP THE LOGIC" block — the two devices that neither sibling case in this batch uses.**
`NEGATIVE` closes 122/150 rows. Median **74** comma-separated prohibitions per prompt, max **188**, 4,684 total across 63 distinct prompts. It ends on format/behaviour, not on story:
> `NEGATIVE: centred, symmetrical, level horizon, … no zoom, no push-in, no cut, no dissolve, no montage, subtitles, text, watermark, music.` (`prompts.jsonl#86`)

The counterpart is `KEEP THE LOGIC` — 94/150 rows, **51 distinct variants**, and it is not a negative list but a *statement of the shot's invariants*: what must not change, what has already happened pre-frame-1, and the fixed order of beats:
> `KEEP THE LOGIC: the arc is SLEEPY CALM → SILENCE → ALARM → PANIC, in that order` (`prompts.jsonl`, KEEP-variant census; 1 row)
> `KEEP THE LOGIC: HE IS ALREADY UNDRESSED — no clothing is removed, handled, pulled or torn` (same census, 1 row)
> `KEEP THE LOGIC — RESTRAINT IS LAW: the cut is ONE slow deliberate ritual motion, controlled, practiced — not frantic, not repeated slashing` (`prompts.jsonl#86`)
None of the other cases has this block (vengeance has named `THE X LOCK`s; hell-grind has `HARD LOCK` tags). ANERNEQ's version is *narrative-causal*: it tells the model the order of cause, not just the position of objects.

**2. The prompt argues by prohibition, not by counting.** Median **49** negation tokens (`no`/`NOT`/`never`) per distinct prompt, max 187 — against **0.58** `EXACTLY`/`ZERO` counters. vengeance-inverts this (4.44 counters/prompt, zero NEGATIVE blocks). ANERNEQ is the corpus's purest example of the "subtract" school: "Realism is what you subtract, not what you add" (`skills/724f5ebf-…md:141`), and `NEGATIVE` is where the subtraction is enumerated.

**3. A constructed language, in Cyrillic, inside an English prompt — with the mouth physics specified.**
90/150 rows contain Cyrillic. `VOICES` (75 rows) is a standing block, and it always carries the same three locks: no translation, lip-sync, no dub:
> `VOICES — conlang only, no translation spoken or shown, lips match sound, no dub: {{uuid}} — the ritual line measured and low, ceremony cadence, hoarse` (`prompts.jsonl#86`)
> `Hard flat "ы" and "э", deep throat "ӄ".` (`prompts.jsonl#86`)
The skill states the reason as a *mechanism*, not a style: "A line written in Latin script is read by the engine as English words, and it lays English phonetics on top — soft vowels, an English 'r', an English rhythm. Cyrillic forces a different articulation" (`skills/724f5ebf-…md:178`). The brief calls it "The cheapest and most effective trick of the whole project" (`brief_text.txt:19624`). **This is the single highest-leverage idea in the corpus and it is unique to this case.**

**4. Identity is carried by exactly one uuid — the face — and nothing else.** 196 `{{uuid}}` occurrences, **1 distinct uuid** for the whole film. The face anchor is generated once and then *masked*, never re-run through a model: "The face is generated once, in close-up, and becomes the anchor. **The base portrait never runs through a model again** — every state (frostbite, frost, dirt, a wound) is built with masks around it" (`skills/724f5ebf-…md:541`). Contrast hell-grind (49 distinct uuids, 191 refs in one prompt) and vengeance (24 uuids, 10 per prompt). ANERNEQ spends its prompt budget on *behaviour* instead of on pointing at assets.

**5. Stillness is specified as a mechanical fact, with the alternatives named.**
> `CAMERA: raw living handheld, LOW, just above the fire, looking up at her — slow breathing drift, micro-corrections a beat late … No zoom, no push-in, no cut, no stabilisation, no gimbal, no drone, no tripod.` (`prompts.jsonl#86`)
> `the camera DOES NOT TRAVEL — it stays in one place and breathes` (`skills/724f5ebf-…md:263`, ref prompt) — the skill makes this a rule: "Separate 'the camera TRAVELS' from 'the camera STAYS PUT' — state it explicitly" (`:146`).

**6. Duration and shot-count are declared as a budget line, not implied.** `TOTAL RUNTIME` 17 rows; single-take statements in 49 rows; the skill's model is `TOTAL RUNTIME ~9 seconds. Shots: 1. Cuts: 0.` (`skills/724f5ebf-…md:333`). Where they went multi-shot they wrote the arithmetic out: `MULTISHOT — APPROXIMATELY 28 SECONDS TOTAL / HARD CUTS ONLY / NO DISSOLVES / NO MONTAGE / NO SLOW MOTION / SHOT 1 — 7–8 SECONDS` (`prompts.jsonl#77`). **0/150 rows use `SEG1/SEG2`; 63/69 distinct prompts contain no timecode range at all.** Time is budgeted per shot, never keyframed inside one.

**7. The acting method is named, and then deliberately reduced to one line.** The skill specifies the full ladder — "super-objective → the scene's event → motive → the goal of this moment → the obstacle → the tactic" (`skills/724f5ebf-…md:482`) — but the prompt emits only the tactic, and says so:
> `CHARACTER ACTING (Tigran method — tactic, not emotion): her tactic — move the load one metre at a time and spend as little as possible per metre` (`prompts.jsonl#125`)
`GOAL:`/`OBSTACLE:`/`TACTIC:` labels appear in **0/150** rows; `CHARACTER ACTING` in 13. This is a *gap between spec and execution* — see the contradiction note in §9.

**8. A whole block exists for one thing: the sky.** `SKY —` opens 34 rows (9 of them as the *first* line of the prompt) and is a pure "copy the reference exactly, here is what it is NOT" block:
> `SKY — COPY THE ATTACHED REFERENCE FRAME'S SKY EXACTLY: a FLAT, COOL, DESATURATED SLATE-BLUE … NOT navy, NOT royal blue, NOT black, NOT teal, NOT purple, NOT bright.` (`prompts.jsonl#100`)
Nothing comparable exists in hell-grind or vengeance; it is a response to a specific, repeatable failure (sky drifting per shot in a 21:9 film whose top third is sky).

---

## 4. Recurring phrasing bank

Frequencies = number of the 150 sampled rows containing the phrase (dedup not applied unless marked "distinct").

### Camera / optics
- `real 65mm ANAMORPHIC film` — 117 rows · `65mm anamorphic` in 1.52 places/prompt (distinct) — the corpus's most repeated technical claim.
- `NOT a render, NOT 3D, NOT AI-CGI, NOT digital-clean` — 54 rows (distinct-prompt 4-gram `not a render, not 3D` = 54/69).
- `oval bokeh, lens breathing` — 34 rows · `anamorphic breathing, heavy organic film grain, halation, slight softness` (`#4`).
- `no zoom, no push-in` — 35 rows · `no stabilisation, no gimbal` — 36 · `static tripod frame, stabilised, gimbal` (inside NEGATIVE) — 29.
- `Even exposure, no vignette` — 44 rows (4-gram `even exposure no vignette`).
- `highlights bloom and roll off, shadows lifted, no crushed blacks` — 35 rows.
- `ONE CONTINUOUS TAKE` — 49 rows · `NO CUTS` — 44 · `MULTISHOT` — 53 · `HARD CUT` — 78.
- `raw living handheld` / `living handheld` — `#4, #86`; `micro-corrections a beat late` (`#86`).
- `heavy MOVING grain` / `MOVE grain` — `skills/724f5ebf-…md:99`.

### Light
- `NATURAL LIGHT ONLY` + `DIM & COLD (KEY)` — the skill template, pasted verbatim (`skills/724f5ebf-…md:75`); `LIGHT —` opens 98 rows.
- `no sun, no moon, no aurora` — 35 rows · `No sun. No fire.` / `No moon. No stars.` stacked one-per-line (`prompts.jsonl#77`).
- `The flame lights the UNDERSIDE of their faces only and dies within a metre` (`skills/724f5ebf-…md:288`).
- `deep shadow, real falloff, strong chiaroscuro, low-key, underexposed` (`skills/724f5ebf-…md:288`).
- `NOTHING IS LIT … the WET SURFACES RETURN A FAINT COLD SHEEN` (`prompts.jsonl#4`) — a full night-interior lighting rig written as a list of absent sources.
- `No lens flares, no light streaks, no floating bokeh orbs, no glow overlays.` — 13 rows, its own block by design: "gets its own block, because folded into anything else the engine keeps adding them" (`brief_text.txt:10109`).

### Motion / physics
- `everything beyond two metres falls into darkness` (`prompts.jsonl#4`).
- `nothing floats, nothing loops, no two steps identical` (`prompts.jsonl#125`).
- `real gravity, nothing floating, nothing looping` (`prompts.jsonl#4`).
- `frozen hide creaking and cracking as it bends` / `the grip failing because her fingers will not close` (`prompts.jsonl#4`).
- `Snow moves across the ice low and horizontal. Hide and fur have real coarse weight and settle after they move.` (`skills/724f5ebf-…md:314-315`).
- `Material resists before it gives` — rule 20 (`skills/724f5ebf-…md:162`).
- `the slowness is the truth of the shot` (`prompts.jsonl#125`).

### Sound
- `no music, no score` — 61 rows (distinct-prompts: 58/69) · `no music no score no` 3-gram in 41 rows.
- `NATURAL SOUND ONLY … NO music, NO score, NO ambient bed, NO drone, NO swell, NO reverb, NO echo` (`skills/724f5ebf-…md:328-331`).
- `the small SHARP HISSES of drops meeting flame — the loudest thing in the scene` (`prompts.jsonl#86`).
- `Silence is an instrument: the heaviest moments get more silence, not more sound` (`skills/724f5ebf-…md:531`).
- `NO dialogue. NO music, NO score.` (`prompts.jsonl#125`) — silence is written even when absent.

### Acting / face
- `her eyes stay on his and do the work` (`skills/724f5ebf-…md:274-275`).
- `a single sharp intake of breath through the teeth, the eyes staying on the bones` (`prompts.jsonl#86`).
- `lips barely moving, weak dying breath` — the substitution for "whisper" (`skills/724f5ebf-…md:158`).
- `Blink cadence uneven and late. Brows, cheeks and mouth work independently; slight asymmetry.` (`skills/724f5ebf-…md:271-272`).
- `she does NOT play grief. She plays holding still. The grief shows only because holding still costs her so much.` (`skills/724f5ebf-…md:324-325`) — the *pattern* for a tactic line.

### Style / negative spine
- `a real photographed frame of 65mm anamorphic FILM … indistinguishable from a still lifted out of a modern photochemical arthouse feature` (`skills/724f5ebf-…md:67-69`); the in-production variant names the film: `indistinguishable from a still lifted out of The Revenant` (`prompts.jsonl#4`).
- `"The Revenant"` — 56 rows; `Lubezki` — 71 rows; `Iñárritu` — 15. The look is anchored to **a named film and a named DoP**, not to adjectives.
- `KODAK VISION3 500T` — 50 rows · `push-processed one stop, printed to a faded release print` (`prompts.jsonl#86`).
- `Never soft. Never smeared. Never mushy. Never plastic. Never AI-smooth.` (`prompts.jsonl#77`) — one-word-per-line negation stack.
- `MEGA-REAL` — 36 rows.

---

## 5. Structure & story

- **Three blocks** (`skills/724f5ebf-…md:386-392`): (1) **THE EXILE** — Tyne kills an arctic fox; Omryn burns his belongings and the camp; the shaman sentences him: "take him to the Whale Bone Alley, **a breath for a breath**"; then the road, the halts, the daily work, the first misidentification, the ice cave. (2) **THE ICE HOLE** — he walks off to find his dead wife, goes through the ice; she pulls him out and goes under herself; **the dog pulls her out and dies doing it**. (3) **THE WHALE BONE ALLEY** — the ritual, "it does not work the way she expected. She finishes it herself", the last vapour, the aurora, and a fox comes to the body.
- **Runtime budget**: hard ceiling 20 minutes (1202 s published). "The road scenes compress into short inserts. The fire, the ice hole, the cave and the bones are not cut" (`skills/724f5ebf-…md:543`). Per-shot budget observed: modal stated durations in distinct prompts are 4 s (34), 5 s (27), 8 s (18), 30 s (15), 9 s (13), 12 s (11), 7 s (11), 10 s (10); the 30 s entries are the four "one continuous take, ZERO CUTS, 30 SECONDS" rows.
- **The loop** is the film's only stated structural rule: "The film opens on a fox and closes on a fox … The debt is paid three times: **the fox, the dog, the father.** 'A breath for a breath' is said once, by the shaman. After that the film does it three times and explains nothing" (`skills/724f5ebf-…md:396`).
- **The motif is physical, not thematic**: breath-vapour as the soul, plus "one physical gesture — the knife at the base of the neck — in the first scene and the last. A rhyme with no words in it" (`skills/724f5ebf-…md:535`).
- **Story rules stated as law**: "A new word is coined once and then used everywhere without variants — **this language has no synonyms**" (`skills/724f5ebf-…md:497`); "Three lines carry the film … Not one word changed" (`:511`); "no synonyms in the language, no duplicates in the naming, no variants in the templates" (`brief_text.txt:19647`); "'A breath for a breath' is said once … explains nothing" (`:396`).
- **Dialogue discipline**: conlang only, Cyrillic, never translated on screen; the full script with translations is in the skill (`skills/724f5ebf-…md:398-458`). The one lucid moment is placed and labelled: "The one time in the film he is in his right mind, and the one time he says her name" (`:436`).
- `type=film`, single featured episode `anerneq/full-film` — not a series; `is_ongoing=true` but `has_changes_since_publish=false`.

## 6. Per-case hard rules (only what this case evidences)

1. **Write the header before the prompt.** "Write the plain-language header first — what happens, what is said, and how long each beat runs. Four lines. Not for the model: for the director. If the shot can't be written there, it isn't designed yet." (`skills/724f5ebf-…md:16`)
2. **Twenty blocks, always the same order** — "twenty blocks, always in the same order" (`brief_text.txt:19944`; canonical list `skills/724f5ebf-…md:36-47`).
3. **Prompt in English, conlang in Cyrillic, never romanised.** "the prompt is in English; the conlang line inside it stays in Cyrillic and is never translated, transliterated or romanised" (`skills/724f5ebf-…md:20`).
4. **Every prompt is an island.** "Light, optics, wardrobe, props, voice and geometry are re-specified from scratch in every shot. 'Same as the previous shot' is an instruction to something with no *before*" (`:51`).
5. **Repeat what matters in every block.** "Distance, darkness and scale are repeated in EVERY block at once, plus a matching negative. One mention is not enough" (`skills/724f5ebf-…md:166`); and "say it once and the engine loses it; say it in four blocks and it holds" (`brief_text.txt:19716`, headed "Repeat what matters in every block" `:19709`).
6. **Templates are pasted, never rewritten.** "Style, LIGHT, HARD ANAMORPHIC LOOK and HYPER-REAL CAPTURE are never rewritten. They are pasted from the skill word for word, and that is what holds the picture together across twenty minutes" (`brief_text.txt:10450`).
7. **One name per element; a new state is a new tag** — `@OMRYN_WET`, `@TYNE_FROSTBITE`, never an overwrite (`skills/724f5ebf-…md:61`).
8. **The face is generated once and never regenerated**; states are masked onto it (`:541`).
9. **The light can only come from something a person could have built** — "natural light only — fire, stars, snow as a bounce, no source that couldn't exist in this world" (`:523`).
10. **Camera: no gimbal, no drone, no orbit.** "No gimbal moves, no drone passes" (`:523`); "No orbiting camera in the madness scenes: the camera shakes and jumps but stays put" (`:525`).
11. **Tilted horizon only for lost control.** "Tilted horizon **only** in moments of lost control, madness and fear, never in the quiet warm scenes" (`:525`).
12. **Do not generate before everything is locked**: "not one shot until every character, location and prop is named and locked. The face is generated once in close-up and never regenerated" (`brief_text.txt:19670`).
13. **Order of work on a shot**: "Event and tactic → geometry in Blender → prompt in the 20 blocks → generate → check against §2 → regenerate, or fix the one block that failed" (`skills/724f5ebf-…md:545`).

## 7. Numbers

| metric | value |
|---|---|
| rows harvested | 150 = 6 folders × 25 |
| distinct prompts | **69** (108 rows are duplicates within batch groups) |
| jobs per row group | up to ×18 for one asset prompt (resolution bake-off, §9) |
| generations_count (published) | 11,961 for 1202 s ⇒ ≈10 generated items per second of finished film |
| prompt chars (all rows) | min 1,313 · median 6,440 · mean 8,088 · max 24,585 |
| prompt chars (distinct / video only) | 3,311 · 7,132 · 24,585 |
| prompt words (distinct / video only) | 565 · 1,184 · 3,977 |
| prompt lines | min 1 · median 81 · max 901 |
| NEGATIVE items per prompt | min 0 · **median 74** · max 188 · total 4,684 / 63 prompts |
| negation tokens (`no`/`NOT`/`never`) per distinct prompt | median 49 · mean 61.2 · max 187 |
| `EXACTLY`/`ZERO` counters per distinct prompt | mean 0.58 · max 4 · 47/69 prompts have none |
| uuid refs | 196 occurrences · **1 distinct uuid** · median 1/prompt · max 5 |
| `{{ref N}}` refs | 49 occurrences / 12 rows |
| @-tags in prompts | 8 distinct · 103 rows use at least one |
| shots per prompt | 0 labelled shots 38/69 · 2 shots 11 · 3 shots 12 · 4 shots 5 · 5–7 shots 4/69 |
| timecode ranges per prompt | 0 in 63/69 · max 7 |
| cuts stated | `Cuts: 0` 4 rows; `NO CUTS` 44 rows; `HARD CUT` 78 rows |
| `24 fps` | 1 row — frame rate is *not* specified in this corpus |
| aspect stated in prompt | 80 rows (`21:9` 131 occurrences, `2.39:1` 5) |
| UI aspect (width/height) | 21:9 in 148/150 rows (98.7%); one 16:9 outlier |
| UI duration param | **UNKNOWN** — key present, value not harvested |
| `job_set_client_meta` | **UNKNOWN** — `null` in 150/150 rows |
| folder items where the money went | `4th scene/5th_shot` 217 vs `4th scene/6th_shot` 10; `4th scene/regen` 46 |

**Duplication flag**: the aspect ratio is stated *twice* — inside the prompt as text (`21:9`, 80 rows) and in the generation params (`width`/`height`, 148 rows). The shared **LIRA** rule 4 says "Aspect ratio & resolution = platform parameters" and that they should be set in the UI, never in prompt text (`skills/3ced8f5e-…md`, "4. Aspect ratio & resolution = platform parameters"). ANERNEQ **breaks that rule deliberately** and states it as a look instruction (`HARD ANAMORPHIC LENS (KEY): true 65mm ANAMORPHIC — 21:9 aspect ratio`, `skills/724f5ebf-…md:90`), because the squeeze is part of the film-stock simulation, not a delivery setting. Duration, by contrast, is *only* in the prompt.

## 8. Failure modes named in this case

- **The glassy stare** — "Glassy eyes are a FROZEN PUPIL, not a highlight … Fix with movement: pupils drifting, uneven blinking, brows, cheeks and mouth working independently, slight asymmetry" (`skills/724f5ebf-…md:144`).
- **Flat crowds of sharp faces** — "Kill flat crowds of sharp faces by pushing background people into darkness and out of focus" (`:148`); spears: "far away, in the dark, out of focus, roughly a metre apart, six people maximum" (`:149`).
- **Two similar men fighting is a known weak spot** — "Fixes: two separate clips and a cut; radically different characters; an explicit pose from the first frame. WHO IS WHO is mandatory" (`:157`).
- **Blood** — "dark, near-black, viscous, and it WELLS — never bright red. For a killing: 'one short press, NO blood, NO gore'" (`:159`); "Blood on the lens: 'a real dark droplet, NOT a CGI overlay'" (`:160`).
- **The word "whisper"** — "mouth physics — 'lips barely moving, weak dying breath' — never the word 'whisper'" (`:158`).
- **Asking for a hidden face without demanding it** — "A hidden face needs an explicit 'FACE NOT SHOWN, hand / body part only' — **in every block**" (`:163`).
- **Artifact cleanup** — "remove 'gate weave' and 'chromatic aberration' together, keep grain moderate, add `NO digital artifacts, NO compression trails, NO ghosting streaks`" (`:165`); skill also notes "If the engine produces strange banding or artifacts, remove 'gate weave' and 'chromatic aberration' together and keep grain moderate" (`:95`).
- **The engine smears speech** — "It smears ӄ and consonant clusters. Re-generate the same shot with the same line but a different description of the delivery; for critical lines, simplify the Cyrillic spelling slightly toward what the engine can produce" (`:151`).
- **The word *bone* pulls toward a cartoon chew bone** — "Do not name the object — describe the geometry: *a single long smooth continuous shaft sweeping up out of the snow in a shallow arc … no knob, no ball, no joint*" (`:380`).
- **i2v vs t2v** — "for a new angle, drop the anchor image and go pure t2v. For a wide derived from a close reference, build the wide still first, then animate" (`:150`).
- **Prompt bloat** — "Shorter prompt, fewer subjects in frame — less slop" (`:143`).
- **The engine's default light** — "the model's default instinct is to flood the scene with even, bright light" (`brief_text.txt:7065`).
- **Lens flares must have their own block** — "gets its own block, because folded into anything else the engine keeps adding them" (`brief_text.txt:10109`).
- Scene-specific negative libraries exist **by scene type** — face close-up / night-and-fire / violence / crowd / animals / ice-and-water / whale-bone-alley / camera-and-motion (`skills/724f5ebf-…md:364-378`), plus six reusable scene-type handlers A–F (`:347-356`).

## 9. Anything weird / low quality

- **This is a 150-row sample of 11,961 items**, not the corpus. Any `0/N` below means "absent from the sample", never "absent from the project".
- **Duplication dominates**: 150 rows → **69 distinct prompts**; 27 duplicate groups, the largest ×18 (`r26-47`: the *same* whale-bone-graveyard asset prompt run at 3840×1648, 2528×1088 and 6336×2688 — a **resolution bake-off**, and the reason the width/height census shows five different "21:9" pixel sizes).
- **11 distinct Russian-language prompts** (`r50-56`, `r67-70`) among English ones. They are not translations: they are the *working* prompts for two shots whose English versions were being rebuilt — "**Что происходит.** То же самое, свет пересобран жёстко: НИКАКИХ фонарей, прожекторов, лучей" ("What happens. The same, with the light rebuilt hard: NO lamps, NO projectors, NO beams", `prompts.jsonl#50`). The project's prompt language was not fixed; the skill later fixes it ("the prompt is in English", `:20`).
- **9 rows open with a markdown fence** (`` ``` ``, `r58-60,125-127,147-149`) — the prompt was pasted out of a code block and the paste captured the fence. First line is literally `` ``` ``.
- **2 rows have an empty first line** (`r108`, `r114`).
- **Reference-tag holes**: in 10/69 distinct prompts a token was stripped out, leaving a double space where the tag should be — `the camera walks a few metres behind  and @DOG at hip height` (`prompts.jsonl#125`) and `  = ТЫНЭ, 18 — …` (`prompts.jsonl#4`, the `@TYNE` tag lost entirely). 19 such gaps total. Do not treat these prompts as byte-authentic.
- **En-dash loss in one dialect**: `SHOT 1 — 7 8 SECONDS` in the header census is `SHOT 1 — 7–8 SECONDS` in the raw text (`prompts.jsonl#77`); the range separator survives but is unreliable across rows.
- **Label hygiene is inconsistent**: a block label may be a bare line (`NEGATIVE`), an inline prefix (`AUDIO: …`), or bracketed (`[TOTAL RUNTIME ~7 seconds …`, `prompts.jsonl#125`). 191 distinct "header-like" ALL-CAPS strings were detected across 150 rows, most of them inline emphasis, not block labels — do not count them as structure.
- **`folder_tree.json` root claims 15 subfolders but lists 14**, and `3rd scene` has 4 items and no subs (`children["3rd scene"]` is `[]` while other scene folders have shot subs). A folder is missing from the harvest.
- **Name drift**: `@omryn` (2 rows) vs `@OMRYN` (97); `4th scene/5th_shot` vs `5th scene/1st shot` (underscore vs space). The brief's own "no duplicates in the naming" rule is violated in the tree.
- **The skill and the prompts disagree on the block list.** The skill prescribes `CHARACTER ACTING` with a GOAL/OBSTACLE/TACTIC ladder; the prompts contain `GOAL:`/`OBSTACLE:`/`TACTIC:` in **0/150** rows. The skill prescribes 20 blocks; the dominant production grammar is the 11-block FILM-LOOK-first order. The skill represents the *final* state of the system; the corpus is the *history* of arriving at it. This digest reports both, but a distillation must not claim the 20-block order is what the corpus demonstrates — it isn't, at 13/150 rows.
- **`publication.json` string is mojibake** (`—but`) — UTF-8 em-dash decoded as CP-something in the harvest. Other cases show the same (`hell-grind` description, `vengeance` folder name `city-walks (source folder name is byte-corrupted)`).
- **Cross-case contradiction worth carrying forward**: LIRA rule 4 (aspect ratio belongs in platform params, not prompt text) is **broken here on purpose** (80 rows state `21:9` inline) and **obeyed** in vengeance only partially (132 rows state `4:3` inline). Both films duplicate aspect into prompt text; neither leaves it to the UI. The distilled skill should say the parameter is *also* stated in the prompt for these cases — but must say **why** (the anamorphic squeeze / the 4:3 gate are look properties, not delivery settings).

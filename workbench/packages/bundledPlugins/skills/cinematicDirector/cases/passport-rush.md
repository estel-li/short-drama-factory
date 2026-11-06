# CASE DIGEST — PASSPORT RUSH

## 0. Header

- **Title**: `Passport Rush` · **type**: `film` · **runtime**: `287.541667 s` (4:47.5) · `publication.json`
- **Author**: `@higgsfield.studio` (`user_3GNcyaSCltezE7ot4WtRdn0jfo0`) · **publication_id**: `5faf8c98-ab7b-4195-bfb6-073a6e985785` · **snapshot_folder_id**: `cc812686-3e0a-4334-aa24-f50eba31f56d` · `publication.json`
- **generations_count**: `14,608` (`publication.json.stats`); `stats.json`: likes `203`, views `33,023`, votes `0`
- **tags/categories**: `[]` / `[]` (not in any curated shelf) · `show_prompts: true`, `is_featured: true`, `featured_episode_slug: passport-rush/full-film`
- **Folder name**: `PASSPORT_RUSH_ANIM` (`folder_tree.json`), workspace `Amina Team`
- **Provenance** (`_summary.json` absent for this case → reconstructed from siblings' pattern + HOST map): `/fnf/project-publications/higgsfield.studio/passport-rush`; `/fnf-community/entities/project_publication/{id}/stats`; `/fnf/folders/{snapshot_folder_id}` + `/children`; `/fnf/folders/{id}/items/v2` → `prompts.jsonl`; `https://dam-editor-worker.higgsfield.ai/brief/{snapshot_folder_id}/snapshot` → `brief.bin` → `brief_text.txt`. `brief_assets.json` lists 2 `.pdf` docs; only one is on disk (`skills/f19c5d2e-….pdf`, 37.7 MB — a storyboard PDF; text not extracted → **UNKNOWN** contents).
- **Premise** (`publication.json.description`, quoted in full): "Minutes from boarding, a young woman realizes her passport is across town. Ahead: a mad dash through an absurd apocalypse to make her flight."
  Brief's own logline (`brief_text.txt:1509`): "Check-in counter. A girl who forgot her passport at home on the day of her flight races through explosions and crazy races on the highway, acrobatic battles against ninjas, marathon cyclists, and an ancient chariot to make her flight on time."

## 1. Production shape

- **Two-stage taxonomy, stated by the brief itself** (`brief_text.txt:284`): "two main stages: art direction and video generation. Art direction covers generating all the assets… characters, backgrounds, and props… as well as early tests to check for AI slop."
- **Root children** (6 present, `subfolders_count: 7` — discrepancy, see §9):

| folder | count | subs | reading |
|---|---|---|---|
| `Art_direction/Assets` | 5,855 | 4 | plate lane: `1_Characters` 966, `2_Locations` 840, `3_Props` 2,681, `4_Vid_Slop_Check` 1,368 |
| `Seq1_Aeroport` | 1,250 | 7 | shot-range buckets `1`, `1-13`, `1-14`, `14-25`, `18,20,25` |
| `Seq2_TaxiDriver` | 2,127 | 12 | scene buckets `sc1…sc18` (proof-of-concept sequence) |
| `Seq3_Cop` | 899 | 5 | ranges + `regen` |
| `Seq4_Ninja` | 3,700 | 8 | ranges `1-18…45-55` + `regen` + `regen 2` |
| `Seq5_Home/Aeroport` | 356 | 5 | ranges only |

- **Source of truth**: `Art_direction/Assets/1_Characters` + `2_Locations` + `3_Props` (the reference registry). `4_Vid_Slop_Check` (1,368 items) is a *dedicated rejection bin* — the pipeline has a named stage for AI-slop triage.
- Sub-folder naming tells the whole edit history: numeric shot ranges (`1-18`, `19-25`, `34-50`), `scN` scene numbers, `regen` / `regen 2`, and `18,20,25`-style lists — i.e. **the folder tree is the shot list**, and regenerated shots get a new numbered folder. Brief: "we first assembled a full cut of the film, then regenerated individual scenes" (`brief_text.txt:415`).
- **Folder accounting drift**: the brief's own tally (`brief_text.txt:30-66`) says Characters 1,229 / Locations 844 / Props 2,694 / Video checks 1,545 = 6,312 art assets and Seq totals 1,269 / 2,203 / 913 / 3,776 / 368; the snapshot tree shows 5,855 art items and 1,250 / 2,127 / 899 / 3,700 / 356. The brief was written mid-project; the tree is the published snapshot. Brief also computes "Ninja = 44.3% of the story-sequence archive" and "Ninja + Taxi = 70.1%" (`brief_text.txt:183-198`).
- **`job_set_type`**: `seedance_2_5` **103** (all video), `text2image_soul_v2` 18, `seedream_v5_pro` 4. One video model for the entire film.
- **Resolution/aspect**: video `1920x1080` ×100, `1080x1440` (3:4 vertical) ×3. Plates: `2048x1152` ×13, `2720x1536` ×4, `1536x2048` ×3, `2048x2048` ×2.
- **`job_set_client_meta`**: **null in all 125 rows**. There is no JSON staging metadata; the studio encodes staging in *folder names* and in the prompt body only. Anything claiming "acts/scenes/attempts in meta" is unsupported here.
- Time span: `created_at` 2026-08-20 → 2026-09-24 (Aug 22 rows, Sep 103 rows).

## 2. Prompt anatomy — the actual grammar

**37 distinct block signatures across the 125 rows; ~11 recurring template families.** There is no single template — there is a *family of templates by sequence and by author-shift*. Observed block headers, by frequency (occurrences across the 103 video prompts):

- `CAMERA` 54, `AUDIO` 57, `STYLE` 60, `ACTION TIMING` 44, `FORMAT MODE` 40, `PHYSICS` 38, `QUALITY` 37, `LIGHTING` 36, `FORMAT` 34, `SCENE CONTEXT` 29, `COMPOSITION` 29, `ANIMATION` 28, `OPTICS` 24, `TIRE HARD-RULE (HIGHEST PRIORITY)` 21, `ANIMATION PRINCIPLES & PHYSICS` 21, `POSITIVE CONSTRAINTS (LOCKS)` 21, `LOCATION MAP` 20, `POSITIVE CONSTRAINTS` 20, `ACTIVE REFERENCES` 19 (x variant), `POSITIVE LOCKS` 19, `HARD CUT` 18, `FINAL CONSTRAINTS` 18, `ACTION — WHAT MOVES` 13, `FIRST FRAME AND SPATIAL BLOCKING` 12, `CAMERA CONTRAST` 12, `SHOT 1 — 00:00.00–00:05.00` 12, `INPUT REFERENCES` 11, `CAST LOCK` 7, `GLOBAL ACTIVE REFERENCES` 5, `SEQUENCE WIDE LOCK` 2, `TASK - VIDEO EDIT` 2.
- **Canonical order in the dominant (mid-project) family**: `SCENE CONTEXT → ACTIVE REFERENCES → LOCATION MAP → FIRST FRAME AND SPATIAL BLOCKING → FORMAT MODE → OPTICS → CAMERA → ACTION TIMING → PHYSICS → LIGHTING → AUDIO → STYLE → QUALITY → POSITIVE CONSTRAINTS` (rows 19,33,38,48). The *earlier* family starts with a hard-rule block: `TIRE HARD-RULE (HIGHEST PRIORITY) → FORMAT MODE → ACTION TIMING → ANIMATION PRINCIPLES & PHYSICS → STYLE → QUALITY → POSITIVE CONSTRAINTS (LOCKS)` (rows 1-11). The *later* family (rows 42-49, 94-109) becomes shot-numbered: `FORMAT → ACTIVE REFERENCE(S) → STYLE → CAMERA → COMPOSITION → ACTION — WHAT MOVES → ANIMATION → PHYSICS → LIGHTING → AUDIO → POSITIVE LOCKS`, with explicit `SHOT n — HH:MM.SS–HH:MM.SS` headers and `HARD CUT AT 00:0X.00.`
- **Unique to this case**: `TIRE HARD-RULE (HIGHEST PRIORITY)`, `ANIMATION PRINCIPLES & PHYSICS`, `FIRST FRAME AND SPATIAL BLOCKING`, `SEQUENCE WIDE LOCK`, `CAMERA CONTRAST`, `CAST LOCK`, `4_Vid_Slop_Check`-style `QUALITY` block.
- **Slug/header line** (first line of every long-form prompt, e.g. `prompts.jsonl#0`): `STYLIZED 3D ANIMATED-FILM SEQUENCE from "PASSPORT RUSH" — police-chase slapstick. … TOTAL 9s: SHOT 1 = 3s, HARD CUT, SHOT 2 = 3s, HARD CUT, SHOT 3 = 3s; each one continuous take, real-time speed (NO slow motion), animation ON TWOS (each key drawing held 2 frames, output 24fps). 16:9.` Slots: `[style tag] from "[FILM]" — [comic register]` + `TOTAL duration : shot budgets : cuts : speed rule : cadence rule : aspect`.
- A second, textual slug appears on some prompts: `STYLIZED 3D ANIMATED-FILM SHOT from "PASSPORT RUSH" (Scene 13) — playful…` (`prompts.jsonl#12,13,43`); and one shot is labelled `(Catr 21)` (`prompts.jsonl#48`, typo in source).
- **Reference tagging — three eras**:
  1. raw media UUIDs: `{{29d7d6aa-62fc-425b-a085-7b6449c7ae9d}}` (`prompts.jsonl#64,67,69,70,77,78`),
  2. positional aliases: `{{ref 1}}`, `{{ref 2}}`, `{{ref 3}}` (`prompts.jsonl#40,48`；最后一个在语料里是独立的视频 token),
  3. `@Video1`-style mentions in the repair jobs (`prompts.jsonl#93`).
- **Order rule is stated, not implied**: `ACTIVE REFERENCES (in this exact order, all 100% match)` ×21; `ACTIVE REFERENCES (in this exact order)` ×11; `ONLY TWO ACTIVE REFERENCES` (`prompts.jsonl#42`).
- **Reference *scope* is the core device** (see §3): each reference carries an explicit "controls only X" clause.
- **Segment/cut/timing syntax actually used**: `TOTAL 9s`, `SHOT 1 = 3s`, `HARD CUT`, `0.0–1.2s` / `2.1–3.0s` (action timeline), and in the shot-numbered family `SHOT 1 — 00:00.00–00:05.00` + `00:00.00–00:02.50:` + `HARD CUT AT 00:05.00.` (centisecond precision, 2 decimals). Chinese short-form instead uses `0.0至0.5秒` (`prompts.jsonl#64`).
- **Duplication between prompt and UI params — confirmed and deliberate**: aspect is *always* also written in the prompt (`16:9`, `9:16`, `1080x1440` prompts) although `params.width/height` also carry it; total duration is stated in prompt (`TOTAL 9s`) although `duration` is a UI param. The Chinese short-form comments on this practice explicitly: `{{ref 1}} 是6.4秒的低模动画预演（含四次硬切，约40%参考）` — i.e. the reference's own runtime and "~40% reference strength" are declared in text (`prompts.jsonl#119`).

## 3. What this case does that the others may not

1. **A Blender blockout video is fed as a reference that is allowed to control ONLY composition.** Verbatim: "`{{ref 1}}` — blocking layout: controls FULL COMPOSITION only. Reproduce exactly its static high diagonal bird's-eye camera, geometry and screen layout… The layout is static and does not control style. Ignore the low-poly placeholder look." (`prompts.jsonl#48`). This is the single most transferable device in the case: a 3D previs clip becomes the camera/geometry truth source while explicitly forfeiting all styling rights.
2. **The blockout is allowed to contain BLACK placeholder segments that the text then fills in** — "SHOT 1 (0–2 s) is a BLACK placeholder — its content is defined by the text below. SHOT 2 (2–6 s) is THE BLOCKOUT … PLACEHOLDERS ONLY — they mark positions and building heights, never appearance" (`prompts.jsonl#10`). Partial previs is explicitly sanctioned; no re-render needed.
3. **Physics hard-rules named after the single most failure-prone object.** 21 prompts open with `TIRE HARD-RULE (HIGHEST PRIORITY)`: "All four tyres stay fully inflated, firm and perfectly ROUND at all times … Only a tiny contact patch at the ground with very slight elastic compression (no more than 10% of tyre height) … do NOT apply exaggerated squash & stretch to the tyres" (`prompts.jsonl#1`). The rule is scoped: squash & stretch is permitted on suspension and characters, forbidden on tyres.
4. **Weight-transfer is specified as a causal chain, not as a look**: "on hard braking the car's momentum pitches forward — the NOSE dives DOWN and the TAIL heaves UP (classic brake dive) … BRAKING happens on the FRONT wheels — the skid marks and tyre-smoke come from under the FRONT tyres; because the tail lifts, the REAR wheels come OFF the ground and therefore lay NO skid mark and make NO smoke behind them." (`prompts.jsonl#1`). The comedy beat (cop launched forward) is derived from the physics, not added on top.
5. **Animation cadence is declared in the prompt as a technical spec**: "animation ON TWOS (each key drawing held 2 frames, output 24fps)" (`prompts.jsonl#0`) and "FULL 12 PRINCIPLES applied (squash & stretch, anticipation, staging, pose-to-pose, follow-through & overlap, ease in-out, arcs, secondary action, timing, exaggeration, solid drawing, appeal)" (`prompts.jsonl#40`). A 3D render is *told to behave like 2D limited animation*. Brief: "the physics should still follow the principles of animation" (`brief_text.txt:1354`).
6. **Reference-role hierarchy is enumerated inside one prompt**: layout video (positions) → `image_11` "MASTER SCENE REFERENCE … defines the LOOK, the ELEMENT PLACEMENT, the CROWD DENSITY and the SCALE RELATIONSHIPS of the final frame" → `image_1–4` designs → `image_9` construction building "must look exactly like this" (`prompts.jsonl#48`). Five reference classes, five different privileges.
7. **A compact Chinese template runs in parallel with the long English one** — 8 prompts, all in Seq2/Seq3, 2.5-4.0 K chars vs 10-28 K in English (`prompts.jsonl#64,67,69,70,77,78,119,121`). Same film, two prompt dialects, roughly 5–7× length difference.
8. **Surgical repair jobs are part of the shot list.** Two `TASK - VIDEO EDIT` prompts take an existing clip and change one thing: "Modify only the girl's suitcase-handle gripping arm/hand in @Video1 so that the suitcase is held by her LEFT hand (not the right), with the arm traveling BEHIND the existing olive backpack…" + "uniformly reduced to 88% of its current linear size" (`prompts.jsonl#93`, `#117`). The prompt starts with a caption-preservation clause: "Preserve every caption, subtitle, and other untargeted on-screen text element from @Video1 exactly as it appears".

## 4. Recurring phrasing bank

Counts = occurrences of the n-gram across the 103 video prompts (case-insensitive).

**Style / global**
- `on twos` 133 · `no slow motion` 123 · `golden-hour sunset` 98 · `one continuous` 95 · `animation on twos (each key drawing held 2 frames` 31 · `NO slow motion` also as `speed no slow motion animation on twos` 31
- `matches the reference` 81 · `the same direction` 38 · `in the same direction` 38 · `stylized 3D` (≈141; the n-gram splits at the digit) · `soft cel shading thin sketchy` 36

**Camera / optics**
- `the camera` 259 · `the frame` 288 · `of the frame` 103 · `low angle` 83 · `a low` 83 · `handheld` (with `tremor`/`micro-shake`) — see §3 quotes · `~35mm-ish`/`~40mm`/`50mm` lens declarations per prompt · `the whole shot` 87/80 · `for the whole shot` 36 · `the center` 87

**Light**
- `single cinematic light source` 32 · `sun raking across the frame from one consistent side held` 32 · `from one consistent side held` 32 · `lighting locked chat base` 32

**Motion / physics**
- `under the front wheels` 64 · `the rear wheels leave the ground` 32 · `the rear wheels leave` 32 · `rear wheels leave the` 49 · `lifting off the ground` 32 · `the nose dives down` 34 · `the tail heaves up` 34 · `skid marks and tyre-smoke` 32 · `no skid mark and` 32 · `tail heaves` 34

**Quality / negative**
- `no text no logos` 51 · `text no logos no` 41 · `no glasses` (character lock) · `do not` 158 · `not a` 164 · `clean holds on twos` 33 · `for the whole shot` 36 · `no broken glass` 35 · `no guardrail kerb gantry` 34

**Cast / identity**
- `the thin cop image` 71 · `the fat cop image` 54 · `always the thin cop` 34 · `is always the thin cop image` 34 · `white helmet with red` / `helmet with red beacon` 35 · `white headphones around her neck` 32 · `headphones around her neck` 41

## 5. Structure & story

- **Five parts, named in the brief** (`brief_text.txt:301-399`): 1 Airport ("The opening, which sets the story in motion"), 2 Taxi ("The proof of concept sequence"), 3 Police ("The police chase"), 4 Ninjas ("The chase with ninjas in pursuit"), 5 Home ("The heroine picks up her passport and returns to the airport").
- **Runtime budget**: 287.5 s / 5 sequences ≈ 57 s per sequence; the heaviest generation load is concentrated in one sequence (Ninja 44.3% of sequence assets) — i.e. action sequences cost 3–4× the asset count of the frame story.
- **Clip unit**: the film is cut from 3–10 s single-take clips, each with 1–5 internal hard cuts (`SHOT 1 = 3s, HARD CUT, SHOT 2 = 3s…`). Measured: median **1** cut marker per prompt, p75 3, max 8; **51 of 103** video prompts contain no cut at all (pure one-take shots).
- **"Proof of concept" is a named story unit**: Seq2 (Taxi Driver) was made first as the PoC. Brief: "For this project, we wanted to test how 3D previs and AI could work together in an action scene" (`brief_text.txt:480`), and `brief_text.txt:1135` "we wanted to create highly dynamic scenes and test how AI could work alongside Blender… we created a traditional storyboard."
- No episodes/series relation: `type: film`, single `featured_episode_slug: passport-rush/full-film`.

## 6. Per-case hard rules

- **Tyre rule (highest priority, 21 prompts)**: tyres always fully inflated and perfectly round; never flatten/sag/deflate/puncture/wrinkle; contact patch ≤10% of tyre height; no squash & stretch on tyres.
- **Squash & stretch is licensed only on suspension and characters** — never on hard props ("do NOT apply exaggerated squash & stretch to the tyres… squash & stretch is only for the car's suspension/body and for the characters", `prompts.jsonl#1`).
- **Real-time only**: "real-time speed (NO slow motion)" — 123 occurrences of `no slow motion`; the film never uses slow-mo as a crutch.
- **Continuity by stated seat/limb locks**: "driver and girl stay in their own seats the whole time; the girl has no seatbelt and both hands grip the two front headrests" (`prompts.jsonl#1`); "ANATOMY LOCK: limbs move expressively but never detach/stretch/dislocate/fly off".
- **Never invent text**: "no text, no logos, no subtitles" (51 & 41 occurrences); captions only exist in repair jobs where they must be preserved.
- **Never change the look of a placeholder**: "none of their look may survive in the final render" (`prompts.jsonl#10`).
- **Reference order is mandatory**: "ACTIVE REFERENCES (in this exact order, all 100% match)".
- **Watercolour belongs to the world, not to moving props**: "Use cleaner, more 3D-looking designs for important moving props, and keep the richer watercolor treatment in the surrounding world." (`brief_text.txt:625`).
- **Every recurring character must be in the inputs**: "Every recurring character that should appear in a shot needs to be represented clearly in the inputs." (`brief_text.txt:744`).
- **Do not change the lighting recipe per shot**: "the team reused the same lighting direction throughout production instead of describing the lighting differently for every shot" (`brief_text.txt:858`).

## 7. Numbers

| metric | value |
|---|---|
| runtime | 287.542 s |
| prompt rows | 125 (video 103, image 22) |
| unique prompts | 68 all / **51 unique video** |
| exactly-duplicated rows | 80 of 125 (largest cluster 8×; histogram 1×45, 2×6, 3×8, 4×4, 5×4, 8×1) |
| prompt chars (video) | min 1,479 · median **10,351** · max 28,441 |
| prompt chars, English long-form | median ~16,400 (rows 0-14,40-60,87-124) |
| prompt chars, Chinese short-form | 2,553–4,007 (8 rows) |
| refs per prompt | min 0 · median **13** · max 67 (`prompts.jsonl#40`); unique refs max 13 |
| hard cuts per prompt (`HARD CUT`/`硬切` markers) | median **1** · p75 3 · max 8 · zero in 51 of 103 |
| stated clip durations | 3,4,5,6,7,8,9,10,14 s; the 9 s / 3×3 s and 10 s / 2×5 s patterns dominate |
| aspect | 16:9 ×100, 3:4 vertical ×3 (`1080x1440`) |
| plates | 22 image jobs (18 `text2image_soul_v2`, 4 `seedream_v5_pro`) |
| generations per finished second | 14,608 gens / 287.5 s ≈ **50.8 generations per second of film** (whole project incl. failed attempts and plates) |
| attempts per shot (visible) | mode 1; clusters of 4 and 8 are batch re-runs of a byte-identical prompt (no prompt change ⇒ a pure luck-roll) |

## 8. Failure modes named in this case

From the brief (these are the studio's own post-mortems):
- **Watercolour breaks in motion**: "Heavy watercolor textures did not hold up well during video generation… The watercolor surface started to look like a flat image stretched over 3D geometry." (`brief_text.txt:609`); "almost as if a flat PNG had been stretched over the geometry" (`:1018`).
- **Assets that pass as stills fail in motion**: "Assets that looked good as still images did not necessarily work once animated." (`:668`); "A finished-looking image is not enough to validate an asset. It needs to be tested in video, under the same conditions in which it will appear in the film." (`:685`).
- **Empty references get filled with invented content**: "Some early tests were made before the character sheets were ready, so the taxi was empty in the references. The model responded by generating random passengers inside the car." (`:728`); "The model may invent missing information." (`:744`).
- **Flat light kills a painted world**: "Midday lighting made the watercolor locations look flat and dull." (`:788`) → replaced by the golden-hour formula.
- In-prompt guards (negative constraints, counted): `no ghosting, no flicker, no frame-skip stutter`; `no melting faces, no identity drift`; `no detached/stretched/warped limbs or hands`; `no floaty` (via `no floating`); `no blowout, explosion, fire, rollover or injury` (`prompts.jsonl#1`); `no sun disc`; `never a second source, never overcast`.
- **"AI slop" is an explicit, folder-level QC stage**: `4_Vid_Slop_Check` (1,368 items) (`folder_tree.json`).

## 9. Anything weird / low quality

- **No `_summary.json`** for this case (the other three have one) → provenance had to be reconstructed; `l1` folder list unavailable from summary.
- `folder_tree.json`: `root.subfolders_count` = **7** but only **6** children are present; `root.count` 14,361 vs 14,187 in the six children → 174 root-level items (the `ROOT`-tagged prompt rows).
- **Massive literal duplication**: 80/125 rows repeat an earlier prompt byte-for-byte (e.g. rows `99,100,102,103,104,105,110,111` are one prompt). Only 51 distinct video prompts for a 4:47 film — the corpus is much thinner than 125 suggests.
- **Language forks within one shot**: the same taxi beat exists as English `prompts.jsonl#63` and Chinese `#64/67/69/70/77/78`; the Chinese rows still address references by raw UUID, the English by `image_N` → two authoring tools/sessions.
- Brief typos inherited in the data: `"PASPORT RUSH"` (`brief_text.txt:1440`), `(Catr 21)` (`prompts.jsonl#48`), `Aeroport` (folder name).
- `prompts.jsonl#10` declares "SHOT 1 (0–2 s) is a BLACK placeholder" — a *deliberate* hole inside the reference video; do not mistake it for harvest corruption.
- `brief_text.txt` is msgpack run-extracted: prose is interleaved with `__type/__detail` scaffolding and asset URLs (71 usable prose lines out of 1,820). Quotes above are verbatim from those retained lines.
- The 37 MB storyboard PDF in `skills/` was **not** text-extracted → its content is UNKNOWN to this digest.

## 10. Cross-case note — does the prompt template change with genre?

Against my other three cases (romance 282 s / 4:3, drama 376 s / 2.4:1, noir 136 s / 16:9): **the skeleton is genre-invariant, the block vocabulary is not.**
- Constant across all four: `context → references (role-scoped) → camera/optics → timing timeline → physics → light → sound → positive locks`. Every film states its totality of constraints; only the labels change.
- Genre-specific *physics block*: passport-rush is the only case with a **named-object hard rule** (`TIRE HARD-RULE`) — action comedy needs per-prop physics locks because the joke *is* the physics. Red-flag does the same for doors/locks (门/锁具), romance replaces physics with **drawing-count rules** ("three drawings and only three"), adiliada replaces it with **acting-logic** blocks.
- Genre-specific *cadence*: ON TWOS + 12 principles are animation-genre artifacts; romance encodes the same idea as "the pose holds completely still for a long beat"; red-flag bans slow motion by name because fight choreography is the plot.
- Runtime does **not** predict template weight here: the shortest film (red-flag, 136 s) has the *leanest* prompts (median 2,950 chars) and the *most* dialogue; the longest (adiliada, 376 s) has the fewest video prompts but the heaviest plate lane. Template weight tracks **whether the film's information lives in motion (action) or in performance/plates (drama)**.
- Language is a studio-workflow variable, not a genre one: red-flag is 100 % Chinese, passport-rush is English with an 8-prompt Chinese dialect, romance/adiliada are English-only.

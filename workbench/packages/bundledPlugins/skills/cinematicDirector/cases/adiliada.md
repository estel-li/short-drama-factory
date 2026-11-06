# CASE DIGEST — ADILIADA

## 0. Header

- **Title**: `Adiliada` · **type**: `film` · **runtime**: `376.490667 s` (6:16) — the longest of my four cases · `publication.json`
- **Author**: `@higgsfield.studio` · **publication_id**: `bbe6a216-bdde-46eb-a56a-a6b182521ba4` · **snapshot_folder_id**: `9ad8b194-ff6c-48be-ab8d-2599a5f2c5f2`
- **generations_count**: `11,023`; `stats.json`: likes `475`, views `75,253`
- **categories**: `["banner","open-sourced-by-higgsfield"]` — this is one of the projects Higgsfield flagged as open-sourced, so its plate lane may be the most reproducible of the corpus. `is_featured: true`
- **Provenance**: `/fnf/project-publications/…`, `…/stats`, `/fnf/folders/{snapshot_folder_id}` (+`/children`), `/fnf/folders/{id}/items/v2` → `prompts.jsonl`; brief snapshot → `brief.bin`/`brief_text.txt`. `_summary.json` gives `l1 = ["1. COLD OPEN: \"The Crow Hunt\"", "2. MAIN TITLE SEQUENCE", "3. SPACE SCENES", "4. MEETING THE VILIAN"]` (note the typo "VILIAN" is in the source). `brief_assets.json` empty → no doc/skill assets harvested.
- **Premise** (`publication.json.description`): "A pitch-black sci-fi comedy about love, betrayal, and, above all, death. A guy named Adil accidentally stumbles into an impossible superpower: every time he dies, he's reborn in a new universe, as an alternate version of himself. Now he's doomed to hop from world to world, trying to stop the end of them all."
- Brief's own format statement: "ADILIADA is a photoreal AI short film, roughly six minutes, built in the format of a series opening. Every frame is generated: no filming, no sets, no camera crew." (`brief_text.txt:213`)

## 1. Production shape

- **Root children** (4 present; `subfolders_count: 5` — discrepancy, §9). Unlike my other cases, the top-level folders are **narrative units, not sequence numbers**:

| folder | count | subs | notable children |
|---|---|---|---|
| `1. COLD OPEN: "The Crow Hunt"` | 1,451 | 12 | 10 beat folders (`1.1 Window Takeoff`… `1.10 "Again"`), `ASSETS` 595, `LOCATIONS` 200 |
| `2. MAIN TITLE SEQUENCE` | 4,637 | 15 | `2.13 Easter Eggs` **2,041**, `2.6 DNA Helix and Mars` 355, `2.11 Deaths Montage` 291, `ASSETS` 808 |
| `3. SPACE SCENES` | 2,296 | 11 | `3.2 The 小ockpit` 519 (sic), `3.4 Adil's Revival` 329, `ASSETS` 171, `LOCATIONS` 150 |
| `4. MEETING THE VILIAN` | 2,363 | 13 | `4.3 Threat and Lore` 481, `4.5 Remembering the Trauma` 228, `ASSETS` 286, `LOCATIONS` 345 |

- **Reading the taxonomy**: the film is built as a **pilot episode opening**, so folders are titled as *title-sequence beads* (`2.4 Distracted Driver`, `2.8 Pirate Ship`, `2.9 Prehistoric Era`, `2.10 Sparta`), each with its own `ASSETS`/`LOCATIONS` sub-bins. Every folder carries its own asset subfolder ⇒ plates are produced **per beat**, not once for the film (contrast passport-rush's single global `Art_direction/Assets`).
- **`2.13 Easter Eggs` (2,041 items)** is the single largest beat folder — the pop-culture gag reel is where the most iteration happened.
- **No `regen` folders** (unlike passport-rush) and no `test` folders (unlike red-flag): exploration is filed under the beat it belongs to.
- **`job_set_type` — 8 models across two lanes (25 video / 93 image)**:
  - **VIDEO lane (25)**: `seedance_2_0` 25 only — at `4032x1728` (16), `896x384` (5), `2016x864` (4). Aspect ≈ 2.33:1 (anamorphic scope).
  - **IMAGE / plate lane (93)**: `soul_cinematic` 28, `soul_cinema_studio` 28, `nano_banana_2` 23, `gpt_image_2` 6, `seedream_v5_pro` 6, `cinematic_studio_image` 1, `seedream_v4_5` 1.
  - Plate resolutions are wide and varied: `2528x1088` 34, `2048x1152` 20, `4032x1728` 16, `2048x2048` 7, `6336x2688` 6, `5056x3392` 6, `3120x1328` 5, `896x384` 5, `2528x1696` 4 …
- **`job_set_client_meta`**: **null in all 118 rows**; `_param_keys` still exposes the tool surface — the plate lane uses `input_images`/`input_image`/`application`/`surface` (24/23/23/23 rows) and single rows carry `camera_model`, `camera_lens`, `camera_focal_length`, `camera_aperture` (the cinematic-studio camera pickers).
- Time span: 2026-06-30 → 2026-08-11 (Jun 3, Jul 89, Aug 26 rows).
- **All 25 video rows share one timestamp: `2026-08-11T10:47`** — a single bulk export/re-submission session, not a shooting schedule.

## 2. Prompt anatomy — the actual grammar

**Two completely different grammars, because there are two lanes.** Only 5 distinct header signatures in the whole case.

### 2a. VIDEO lane (25 rows, 8 unique prompts) — inline `LABEL:` blocks

- Signature: **`ACTIVE REFERENCES` / `CAMERA POSITION AND FRAME LAYOUT` / `THE DRIVER'S REACHING HAND (CRITICAL)` / `ACTION TIMING`** (2 rows), **`WORKFLOW METADATA` → `PATCH LOG` → `FINAL PROMPT`** (7 rows), **`FINAL PROMPT`** (3 rows), `ACTIVE REFERENCES` alone (11 rows).
- Real structure is **sentence-initial labels inside one paragraph**, not standalone header lines:
  `SCENE CONTEXT: … PRIMARY FRAMING LOCK: … ACTIVE REFERENCES: … STATE LOCK: … BLOCKING: …` then `0:00-0:04 … 0:04-0:05 … 0:05-0:08 …` then `Optics: … Physics: … Lighting: … Audio: …` (`prompts.jsonl#25,29`).
- **References are addressed by ordinal position, never by tag**: "The wounded passenger (first reference person, 100% matching that face)", "The driver (second reference person)", "Interior and environment (third reference)". Zero `{{…}}` tokens in all 25 video rows (`refs/prompt` median 0, max 0).
- **Timing syntax**: `0:00-0:04`, `0:04-0:05`, `0:05-0:08` — colon-style ranges, no "HARD CUT" tokens; the shot is declared un-cuttable ("ONE UNBROKEN CONTINUOUS HANDHELD SHOT, no cuts, shaky and breathing").
- **Model/UI split is declared in the prompt itself**: "UI settings handled outside prompt: duration, aspect, R2V mode — omitted from prompt body." (`prompts.jsonl#25`).
- Aspect: not stated in the video prompts at all — it lives in `params` (4032×1728 / 896×384 / 2016×864 are the same 2.33:1 framing at three resolutions, i.e. **draft → preview → final renders of one shot**).

### 2b. IMAGE / plate lane (93 rows, 51 unique prompts) — operation-first grammar

- **Four plate sub-grammars**, all unique to this lane:
  1. **Sheet** (panel spec): "COLUMN 1 (largest, leftmost): chest-up portrait, front view… — COLUMN 2: full-body front view, standing relaxed neutral A-pose… — COLUMN 3 (rightmost): full-body back view, same standing pose mirrored" (`prompts.jsonl#7`); variants "PANEL 1 (left)… PANEL 2 (middle)… PANEL 3 (right)" (`prompts.jsonl#3,15`) and 4-panel studio grids (`#0`).
  2. **Identity lock header**: "ABSOLUTE TOP PRIORITY — DO NOT CHANGE THE FACE: … treat the face as a locked, untouchable region — do not restyle, beautify, reshape, re-age, slim, smooth, relight or re-render the face" (`prompts.jsonl#0`).
  3. **Surgical edit**: operation named in the first clause, then `ONLY` scope, then a PRESERVE list, then the pixel-identical clause — see §3.
  4. **Studio product shot** ("Studio product photograph of a portable translucent see-through cassette Walkman…" `prompts.jsonl#1`; "product asset photograph of a vehicle-mount two-way radio transceiver" `prompts.jsonl#81`).
- **Technical tail** appended to sheets: "shot on full-frame camera with an 85mm lens look, shallow yet controlled depth of field, crisp tack-sharp detail, high dynamic range, 8k." (`prompts.jsonl#7`); plate backdrops are given as hex: "pure clean deep neutral grey (#3a3a3c)".
- **Midjourney flag tail leaks into 2 plots** — `--ar 21:9 --style raw --stylize 50 --v 8.1 --no people, animals, plinth, signboard, text` (`prompts.jsonl#19,93`). The studio clearly writes in an MJ-trained idiom and pastes it into a non-MJ engine.
- **Colour budgeting appears as percentages**: "Muted palette of 60% cool grey-blue slate, 30% chalky bone-white plaster and linen, 10% weathered oak brown." (`prompts.jsonl#93`).
- **Non-English**: 2 image prompts open with a **Russian working note** before the English prompt body — "Вот исправленная версия второго промта — 3 панели и clean-shaven сохранены…" (`prompts.jsonl#3`) and "Добавил инструкцию убрать щетину — вставил её в описание лица (крупный план)…" (`prompts.jsonl#15`). This is chat residue from a Russian-speaking operator, pasted into the prompt field. One prompt is literally `upscale` (`prompts.jsonl#10`, 7 chars).

## 3. What this case does that the others may not

### 3.1 The plate lane is a real production line: sheet → plate → edit

1. **Two-pass character construction, declared as policy** (brief): "A character is built in two passes with two models. Soul Cinema makes the face: always generated in close-up… That close-up face is the anchor every following asset of the character is checked against. Soul 2.0 then builds the looks: full-figure images with the wardrobe, costume, materials, silhouette, all fitted to the locked face." (`brief_text.txt:634`) — and the base is never touched again: "the original close-up portrait stays untouched. It never runs through a model again; the assembly happens in editing tools around it" (`:649`). The corpus shows exactly this split: `soul_cinematic` (28) face/look passes, then `nano_banana_2` (23) / `seedream_v5_pro` (6) / `gpt_image_2` (6) sheet assemblies.
2. **Every asset is a text+image pair, and the text half is reused verbatim**: "An asset is a pair: text plus image. The text descriptor goes into every prompt word for word" (`brief_text.txt:603`). Observable: the character descriptor strings repeat 25× across video prompts ("black curly hair, thin mustache, gold hoop earrings" etc., §4).
3. **The edit grammar: CHANGE / PRESERVE / pixel-identical.** Canonical shape, first clause names the single allowed operation:
   - "Edit ONLY the hair in this existing four-panel studio image and keep every other element 100% identical and untouched" (`prompts.jsonl#17`);
   - then the PRESERVE enumeration (framing, layout, backdrop, exposure, grade, grain, light direction);
   - then the forbidden-touch list (face, identity, bone structure, scar, stubble, moustache, goatee);
   - then the wardrobe enumeration *verbatim* (navy-teal trench with brass buttons, brocade waistcoat, turtleneck, bracers, crimson scarf, steampunk goggles) so that "don't change the costume" is checkable;
   - **closing identity clause**: "Everything else stays pixel-identical" (`prompts.jsonl#4`) / "KEEP EVERYTHING ELSE IDENTICAL:" (`prompts.jsonl#61`).
   - Removal variant: "Remove ONLY these items: (1) the ID badge with lanyard clip…; (2) the thin silver neck chain…; (3) the small tattoos on his right hand…" then the repair instruction "The uniform fabric must continue cleanly where the badge was — same dark teal double-breasted jacket with two button rows, same buttons, same folds." (`prompts.jsonl#4`).
   - Substitution variant with material lock: "Change ONLY the statue's face. Re-carve the statue's face so it depicts the man from the SECOND image… all rendered as a solid carved sculpture… The face must be carved stone, matte and monolithic, NOT living skin" (`prompts.jsonl#61`).
4. **Identity is a bounded pixel region**, not a description: "his face is 100% that reference face, but the reference controls FACE IDENTITY ONLY — the reference photo's beard, loose hair and casual clothing are NOT inherited" (`prompts.jsonl#25`).
5. **Staging diagrams and depth maps are separate reference classes** (brief): "The skill turns a frame into a schematic color-coded diagram, and Seedance reads exact positions, poses and facing directions off it. Being a colored circle with an arrow is humbling. Works every time." (`brief_text.txt:486`); "A depth map is a black-and-white image where the light areas mean near objects and the dark ones mean far. The model reads it as the depth skeleton of the scene" (`:510`). This is the only one of my four cases that names a **depth map** as a prompt input.

### 3.2 The iteration log: a defect→fix ledger kept *inside the prompt field*

Seven rows (`prompts.jsonl#25,27,31,33,43,46,49`) are the studio's working document. **Important factual correction:** those 7 rows are **byte-identical** (full SHA1 prefix `2b728e1d`, FINAL PROMPT body `e4576877`, 6,289 chars each, all at 4032×1728) — i.e. **one** iteration log submitted 7 times, not 7 different logs. The document has exactly this skeleton:

```
CINEDANCE WORKING PROMPT — backseat bleeding scene
WORKFLOW METADATA
  User goal: …  Platform: Higgsfield Seedance 2.0, R2V multi-reference (2 face refs + 1 interior ref).
  UI settings handled outside prompt: duration, aspect, R2V mode — omitted from prompt body.
  Current status: patched v4 — maximum-speed pass (parallax, strobing shadows, wind, vibration, overtaking the train).
FAILURE NOTES (internal, not for final prompt)
  v2 defect N: <symptom>. Fix: <exact fix>
  Standing note: <latent trap>
PATCH LOG
  <SECTION>: <what changed>
  …
  All other sections preserved unchanged.
FINAL PROMPT
  <the clean prompt body → pasted into generation>
```

**The defect→fix ledger (verbatim, complete — the ledger is 2 defects + 1 standing note, not 7):**

| # | defect symptom (verbatim) | root cause as the studio states it | the fix (verbatim) |
|---|---|---|---|
| v2-1 | "driver's hand described as 'blood-covered' BEFORE the grip" | state causality: the description pre-empts an event that has not happened yet | "driver fully clean until contact; blood transfers from passenger's palm at the grip" |
| v2-2 | "driver reference photo shows beard, wavy loose hair, tan t-shirt — model inherited the reference look" | an identity reference silently carries grooming/wardrobe and overrides the shot's spec | "hard appearance override — reference controls FACE IDENTITY ONLY; in-shot look = clean-shaven, grey hair slicked straight back, black suit jacket unbuttoned/hanging open over white dress shirt, dark tie (mirrors the passenger's black-and-white look)" |
| standing | "passenger reference photo has Ray-Bans on forehead — keep hard no-glasses lock" | small props in a reference are inherited even when unmentioned | a persistent negation lock in the reference block ("NO glasses and NO sunglasses, bare forehead with nothing on his head") |

**PATCH LOG = patch by section, everything else frozen.** Verbatim entries: "ACTIVE REFERENCES / driver block: rewritten with reference-controls-face-only lock + full appearance spec." · "FIRST FRAME: added 'driver's hands completely clean, no blood anywhere on the driver' state lock." · "ACTION TIMING 0:04–0:05: 'blood-covered hand' → 'CLEAN bare hand'; blood transfer happens at contact." · "PHYSICS: added contact-transfer rule for blood." · closing rule: **"All other sections preserved unchanged."**

**Why this matters as a method** (generic, model-agnostic):
- the prompt is versioned in place (`Current status: patched v4`) with a **change surface** (PATCH LOG) so a fix never silently rewrites unrelated behaviour;
- the working document explicitly separates **internal notes** ("FAILURE NOTES (internal, not for final prompt)") from the **generation payload** (`FINAL PROMPT` block) — the operator pastes only the tail;
- **UI-level settings are stripped from the prompt body by convention** (duration, aspect, R2V mode), so a prompt is portable across aspect/duration re-renders.

### 3.3 Other distinctive decisions

- **Long-take economics**: 8 unique video prompts for a 6:16 film — this is the *fewest prompts per minute* of my four cases (≈1.3 unique video prompts per finished minute vs ≈22 for red-flag, ≈10.6 for passport-rush, ≈7.9 for the romance case). The film is told in a handful of extremely specified takes.
- **Draft/preview/final ladder encoded in resolution**: the same shot exists at `896x384` (5 rows), `2016x864` (4 rows) and `4032x1728` (16 rows) — cheap geometry tests at 1/4 area before the money render.
- **Pop-culture register stated in the brief, not in the prompt**: the brief names the format ("a main-title reel built the way sitcoms and cartoon shows of the 2000s built them", `brief_text.txt:272`), while the prompts stay strictly descriptive. Brand/IP references are not carried into prompt text (contrast the romance case, which explicitly dropped a "well-known animated series" trigger to avoid IP).
- **Every prompt is an island — by policy**: "Seedance only sees the text in front of it, so every prompt is an island: positions, poses, wardrobe, props, optics, light, all spelled out from scratch, every single time. 'Same as the previous shot' is an instruction to a model that has no 'before'." (`brief_text.txt:1092`).

## 4. Recurring phrasing bank

Counts are n-gram occurrences across all 118 prompts (the video family dominates the high counts because 25 rows reuse 8 bodies).

**Video — camera/performance**
- `on the rear bench` 70 · `the front passenger seat` 60 · `directly behind the driver` 41 · `the rear bench directly behind the` 33 · `back over his own shoulder` 31 · `from the front passenger seat` 29 · `before the whip pan` 28 · `one continuous` / `no cuts shaky and breathing` 25

**Video — emotion/physical**
- `tears about to spill` 50 · `glassy and brimming with welling tears` 25 · `face crumpling jaw trembling barely holding himself` 25 · `drenched and dripping with sweat` 25 · `heavily soaked dark red across the whole belly` 25 · `no blood on it` 34 · `blood transfers ONLY by contact` (per-row) · `streaks past in motion blur` 27

**Video — identity descriptors (reused verbatim as the "asset text")**
- `black curly hair thin mustache gold hoop` 25 · `no glasses no sunglasses` 26 · `the wounded passenger first reference person` 25 · `the driver second reference person` 25 · `1980s American luxury sedan` 38 · `chrome trim woodgrain dash` 32

**Plate lane — craft**
- `character reference sheet` · `100% identical` · `pixel-identical` · `seamless neutral mid-gray seamless backdrop` · `treat the face as a locked, untouchable region` · `shot on full-frame camera with an 85mm lens look` · `pure clean deep neutral grey` · `--ar … --style raw --stylize … --v … --no …`

## 5. Structure & story

- **Format = pilot-episode opening in three parts** (`brief_text.txt:228-296`): (1) cold open that "gives you no context at all and only multiplies the questions… yes, I die thirty seconds in"; (2) main-title reel "packed with pop-culture references and rides on a driving, banging track that plays off the name itself: ADILIADA"; (3) titles roll straight into "what looks like the rest of the episode" and cuts off at the best possible moment "so you'll be sure the rest exists".
- **Runtime budget**: 376.5 s over 4 top-level units (cold open ≈1,451 items, main title 4,637, space 2,296, villain 2,363). The main-title reel is the heaviest unit (41 % of assets) — the opposite allocation from a conventional film, where act 1 is light.
- **The killer structural joke**: the title sequence is where the *series lore* is delivered (`2.6 DNA Helix and Mars`, `2.7 DNA Variants`, `2.8 Pirate Ship`, `2.9 Prehistoric Era`, `2.10 Sparta`, `2.11 Deaths Montage`, `2.12 Meeting the Family`) — an exposition montage disguised as credits.
- **Narrative rule the brief states** (`brief_text.txt:327`): "any alternate version of me still has to read as me. And that's exactly where the whole difficulty of the project lives, somewhere between 'make him different' and 'make him the same'" → policy: "A new universe is a new look, not a new person. The base is never touched." (`:1300`).
- Pipeline stages named in the brief: scene dramaturgy argued before generation (`:541`) → step-by-step storyboard (`:556`) → assembly / rough cut / **generation supervision** / fine cut / picture lock / cleanup-colour-sound (`:1137-1217`). "Generation supervision. A quality-control pass after the rough cut: regenerating broken shots, clearing out AI slop" (`:1169`).
- Single `film`, not a series — the "already existing series" is fiction.

## 6. Per-case hard rules

- **Nothing gets shot before the assets are locked**: "Not a single shot until every character, location and prop is built, named and locked." (`brief_text.txt:1254`)
- **The model has no memory — restate everything**: "Descriptors, location maps and staging go into every prompt word for word." (`:1277`)
- **A universe changes the look, never the face**: "A new universe is a new look, not a new person. The base is never touched." (`:1300`)
- **Say what you want, not what you avoid**: "The words you write are the words you summon, including the ones sitting inside a 'no'." (`:1323`) — and yet the case's own prompts are full of negations (`NO glasses`, `do not restyle`, `NOT living skin`), so treat this as the brief's aspiration, not as observed practice.
- **Direct, don't describe**: "The scene event, the motive, the goal, the obstacle, the tactic. Directing is the one part the model still won't invent for you." (`:1346`)
- **Reference scope must be capped per reference**: "reference controls FACE IDENTITY ONLY"; "This reference controls ONLY the cabin geometry… The reference photo's OWN camera position and framing are NOT inherited" (`prompts.jsonl#29`).
- **Working document discipline**: keep FAILURE NOTES out of the shipped body; patch by section; "All other sections preserved unchanged."
- **UI settings never go in the prompt body**: duration, aspect, R2V mode.
- **Identity region is untouchable in edits**: "treat the face as a locked, untouchable region"; every edit prompt ends with a pixel-identical clause.

## 7. Numbers

| metric | value |
|---|---|
| runtime | 376.491 s |
| prompt rows | 118 — **video 25, image 93** |
| unique prompts | 59 all · **8 unique video** · 51 unique image |
| duplicated rows | largest clusters: 25× one image prompt (`#93-117`), 7× the working prompt (`#25,27,31,33,43,46,49`), 7× one beat (`#29,32,35,36,38,41,42`), 6×, 5×, 4×… |
| prompt chars (video) | min 4,392 · median **7,985** · max 11,835 |
| prompt chars (image) | min **7** (`upscale`) · median ~1,245 · max 4,890 |
| refs per prompt (video) | 0 tags — references addressed by ordinal words instead |
| hard cuts per prompt | 0 (all one-take) |
| aspect (video) | 2.33:1 at three resolutions: 4032×1728 (16), 2016×864 (4), 896×384 (5) |
| aspect (plates) | wide, varying: 2528×1088 (2.32:1) ×34, 2048×1152 ×20, 2048×2048 ×7, 6336×2688 (2.36:1) ×6 |
| generations per finished second | 11,023 / 376.5 ≈ **29.3** |
| working-doc size | metadata block ≈1,700 chars + FINAL PROMPT 6,289 chars |
| attempts per shot | 7 identical submissions of the same working prompt at the same resolution/time; 25 identical submissions of one plate |

## 8. Failure modes named in this case

**From the in-prompt ledger (§3.2)** — the only case in my set where failures are written down as data:
1. **Event-state inversion** — describing blood before the causal contact made the model show blood from frame 1. Fix: a *first-frame state lock* + a *contact-transfer rule* in PHYSICS.
2. **Reference over-reach** — an identity photo's beard/hair/t-shirt were inherited into a shot that needed a clean-shaven driver. Fix: "reference controls FACE IDENTITY ONLY" + a full explicit appearance spec that contradicts the photo.
3. **Prop inheritance from a reference** — sunglasses/glasses on the reference's forehead kept appearing. Fix: a permanent negation lock.
4. **Reference framing inheritance** — the interior reference "was shot from the rear of the cabin, but this prompt's camera does NOT sit there — camera position comes only from the CAMERA sections below" (`prompts.jsonl#29`). Same class as #2, different attribute.

**From the brief**:
- **"Every frame must be generated" breaks when staging isn't materialised**: "In shots with several of us in frame, text alone won't hold the staging" (`brief_text.txt:486`) — hence colour-coded diagrams + depth maps.
- **Depth ambiguity**: "Without it the space drifts, and you'd be watching me fight a bird in a city that rearranges itself every three seconds." (`:510`)
- **Weak scenes are discovered too late**: "On an AI film a weak scene costs real money: you find out it doesn't work only after you've generated it." (`:541`)
- **Prompt self-containment**: "'Same as the previous shot' is an instruction to a model that has no 'before'." (`:1092`)
- **Damage to the identity base**: "The base image stays the same pixels" (`:649`) — every state change (scar, haircut, dirt, wound) is masked in, never re-generated.
- **Generation supervision** is a named QC gate for "AI slop" (`:1169`).

## 9. Anything weird / low quality

- `folder_tree.json`: `subfolders_count` = **5** but **4** children present; `root.count` 11,319 vs 10,747 in children → 572 root-level items (matches the 25 `ROOT` rows).
- Typos in the source preserved: `3.2 The 小ockpit` (a stray Chinese character in an English folder name), `4. MEETING THE VILIAN` ("VILLAIN"), `2.1 \tAbstract Opening` (literal tab in the name).
- **One prompt body is the word `upscale`** (7 chars, `prompts.jsonl#10`) — an operator using the prompt field as a UI command.
- **Russian chat residue inside two prompts** (`#3`, `#15`): the *note about the edit* precedes the prompt itself, so the model receives a Russian editorial comment as part of the prompt.
- **7 byte-identical working-prompt rows** — a report of "7 iteration logs" would overstate the evidence; the corpus contains **one** log rendered 7×.
- **25 byte-identical plate rows** (`#93-117`, `soul_cinema_studio`, 2528×1088) — a 25× batch of one prompt; either a seed sweep or a stuck retry loop. Results are not in the harvest, so which one it was is **UNKNOWN**.
- **All video rows share one `created_at` minute** — timestamps here are export times, not creative order. Any timeline claim based on `created_at` for this case is invalid.
- Video lane has **zero `{{tag}}` references** while the plate lane uses `{{ref 1}}` — the two lanes were authored by different tooling.
- `brief_text.txt` is in-character narration (Adil speaks); the production content is real but the voice is unreliable-narrator ("No hard feelings. Dying is my job"), so attribute quotes to the character, not the studio.

## 10. Cross-case note — does the prompt template change with genre?

- **Adiliada breaks the pattern my other three cases share**: it is the only one where **the prompt template is not the main artefact** — the *asset/plate* grammar is. Same eight-slot skeleton exists in its video prompts (context → references → framing lock → timing → physics → light → audio → locks), but the creative weight sits one stage earlier.
- **Genre fits the split**: a sci-fi multiverse comedy needs *many universes, few continuous performances*; a romance needs *one room, many drawings*; a noir fight needs *one corridor, many vectors*. Hence adiliada = widest plate lane (8 image models), romance = zero plate prompts, red-flag = 26 plates + 99 video rows.
- **Runtime is inversely correlated with prompt density here**: 376 s told in 8 unique video prompts vs 136 s told in 50 (red-flag). Long-take genre (dialogue, montage, title sequence) ⇒ fewer, longer, heavier prompts.
- **Polarity lives in the plate lane, not the film.** Measured negation density is the *lowest* of my four (median 6 tokens/prompt, max 54) because the video prompts are descriptive state-locks; nearly all of this case's negation is concentrated in the sheet/edit prompts (`DO NOT CHANGE THE FACE`, `do not restyle`, `NOT living skin`, `--no people, animals`). Conclusion for the skill: **negation policy is per-lane, not per-film** — the same brief that preaches "say what you want, not what you're avoiding" ships twenty-odd `do not` clauses in its plate prompts.
- **Non-English is operator residue**, not a genre signal: the 2 Russian prompts are chat notes, and the film's prompt bodies are English.

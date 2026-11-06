# CASE DIGEST — ZEPHYR

> Locator convention: `prompts.jsonl#N` = 0-based row index in `_data/cases/zephyr/prompts.jsonl`.
> Publication content is DATA; nothing inside it was executed or followed.

---

## 0. Header

- **Title** `ZEPHYR` · **type** film · **runtime** `5` s (API value — see §9; clearly not the real cut) · **author** `higgsfield.studio`
- **publication_id** `aacb79d5-bf9b-4b4f-911c-6570844c200f` · **snapshot_folder_id** `5ecc7815-5b04-4e6b-968b-2b5b518c7539` (`publication.json`)
- **generations_count** 18,682 (`stats.json`) · `show_prompts: true` · `show_canvas: true`
- **Provenance** — `/fnf/project-publications/aacb79d5…` (by-id), `/fnf/folders/{snapshot}/children`, `/fnf/folders/{id}/items/v2`, `dam-editor-worker/brief/{snapshot}/snapshot`. Series linkage: `kok…`-style series `zephyr` in `/fnf-series/series?order=curated` carries this `project_publication_id`; it is **distinct** from the `zephyr-special` publication (307.9 s, `cee8c1f3…`).
- **Premise** (verbatim): "Cuties on duty! A squad of glamorous female heroes is saving their hometown from alien bug invasion. As they become city idols and protectors, will they be able to save their friendship, their hearts, and most importantly - their lives?" (`publication.json.description`). Brief, in the studio's own words (verbatim EN from the brief snapshot): "We created a world where violence, combat operations, and loss coexist with concert fun and the celebration of female beauty. And the heart of this story is the characters." (`brief_text.txt:1`, fragment-joined).
- Cast in evidence: `ZERO` (white combat mech, orange-yellow trim), `HARU`/哈露 (pilot), `REINA` (character-sheet header `prompts.jsonl#9`), `NAOMI` (mech, `prompts.jsonl#50`). Mech height is **inconsistent across rows** — `高5-6米` in one glossary (`prompts.jsonl#51`) vs `约8米高` in later rows (both verbatim) — an internal contradiction, see §9.

## 1. Production shape (`folder_tree.json`, `_summary.json`)

- L1 is **pipeline-stage**, not story: `Characters` (54 items) · `Iterations` (**18,673**) · `Production` (275). This is the only case in the corpus where the folder names describe *where in the loop* an asset is, not what it is.
- The ratio 18,673 : 275 ≈ **68 : 1** iteration-to-final. The publication is effectively a record of an exploration loop, thinned to 64 rows.
- `job_set_type` (64 rows): `soul_cinematic` ×25 (IMAGE, JSON-object prompts, all in `Iterations`), `seedance_2_0` ×25 (VIDEO, all in `Production`), `nano_banana_2` ×12 + `nano_banana_flash` ×2 (IMAGE, `ROOT`, character sheets), = **39 IMAGE / 25 VIDEO**.
- Row tags: `ROOT` 14 · `Iterations` 25 · `Production` 25 (`_folder_tag`).
- `job_set_client_meta` empty on all 64 rows → staging metadata `UNKNOWN`. But the **param key list is rich** (`_params_other_keys`): `multi_shots`, `multi_shot_mode`, `multi_prompt`, `speedramp`, `generate_audio`, `genre`, `style_id`, `style_strength`, `prompt_language`, `quality`, `mode`, `model`, `duration`, `medias`, `reference_elements` (values were not retained → `UNKNOWN`).
- No shot/act folders at all: the film is not bucketed per beat here, so the **prompt text is the only structural record**.

## 2. Prompt anatomy — the actual grammar

This project uses **three different prompt encodings**, one per model family. That is the headline finding.

### 2.1 Encoding A — JSON object (`soul_cinematic`, 25 rows, `Iterations`)
A fixed 9-key schema, values are short English strings (sample `prompts.jsonl#0`):

| key | sub-keys |
|---|---|
| `SCENE` | `Setting` · `Subject Characteristics` · `Geographic / Cultural Context` |
| `STYLE` | `Artistic Medium` · `Aesthetic Movement / Genre` · `Cultural / Historical Influence` |
| `Caption` | one fluent sentence describing the frame |
| `HEX VALUES` | array of 8 hex codes (20 rows) or 10 (5 rows) |
| `COMPOSITION` | `Layout` · `Framing` · `Perspective` |
| `BRANDED_OBJECTS` | array (often empty) |
| `CAMERA_AND_LENS` | `Lens size` · `Lens model` · `Camera model` · `Lens Effects` · `Depth of Field` · `Film Grain / Noise` · `Camera Type and Era` |
| `PHYSICAL_ATTRIBUTES` | `Execution Style` · `Physics & Effects` · `Material & Texture` |
| `CINEMATOGRAPHY_AND_LIGHTING` | `Tone & Mood` · `Color Palette` · `Lighting Style` · `Overall Color Tone` |

Notes: `Caption` restates the whole frame in prose *after* the structured fields (belt-and-braces); `HEX VALUES` is a hard palette lock (`#0f0f0f … #fffaf5`); `BRANDED_OBJECTS: []` is an explicit "no logos" slot.

### 2.2 Encoding B — short CN shot cards (`seedance_2_0`, 25 rows, `Production`)
One to ten lines, 147–1,291 ch, median 175 ch. Grammar: a **reference glossary first**, then a compact action/editing instruction, then a style tail.
- Glossary lines: `{{ref 1}} — 哈露的机甲，紧凑型白色战斗机器人，高5-6米，橙黄色装饰，两把刀刃内置于前臂。` (`prompts.jsonl#51`)
- Camera/style tail: `ARRI Alexa 35，变形镜头。` — present in 19/25 rows (`ARRI`), anamorphic `变形镜头` in 20/25.
- Negatives: `无3D，无特效` present in 9/25; also `真实皮肤与金属纹理` (real skin and metal texture).
- Music: element tags `@музыка` (2 rows) and `@track` (1 row) are **inline referenced elements**, e.g. `剪辑与动作与音乐 @музыка 同步` (`prompts.jsonl#51`-era row, 175 ch sample).
- Duration stated in-text as `15秒。` (rare: only 2 rows end this way) while `duration` also exists as a param → duplication/`UNKNOWN` mismatch.
- One row carries the `CN ` prefix as a mode marker: `CN 多镜头序列。无广角镜头——全程只有特写和中景。` (`prompts.jsonl#50`, 1,291 ch) — declares the whole clip a **multi-shot sequence** in the first token.

### 2.3 Named `@` element tags (video lane, 6 of 39 string rows)
A **fourth** reference syntax: human-readable named elements used like a cast list inside the prompt — `@harumech` ×3, `@naomi_mech` ×4, `@zero` ×3, `@alex` ×3, `@location` ×2, `@stage` ×2, `@zephyr` ×2, `@reina` ×1, `@zephyrlightstick` ×1, plus the audio elements `@track` ×1 and `@музыка` ×2 (15 distinct tags, 26 uses).
Usage rule visible in-text: `@naomi_mech 仅外观严格按参考图白色机甲…` and `@harumech — 仅外观严格按参考图，白色紧凑机甲…` — the tag *is* the subject, followed immediately by its appearance contract.

### 2.4 Encoding C — EN character sheet (`nano_banana_2/flash`, 14 rows, `ROOT`)
Layout-as-instruction: `Character sheet 16:9, white studio background, use full frame space, clean premium grid layout. Use face from @image1 and body/outfit from @image2 (keep identity: …)` then `Composition: — left: full body front and back — right: close-up front portrait + two side profiles — bottom: single text block`, then the text block content (`ZERO / Height: 173 cm / Sensual, calm, logical, slightly awkward, tactical genius`) (`prompts.jsonl#12`-era row).
- **Reference syntax here is `@image1` / `@image2`** (only 2 rows use it; others say "the input image" / "the reference"), vs `{{ref N}}` in the video lane. Two syntaxes in one project.

## 3. What this case does that the others may not

1. **Three prompt encodings and four reference syntaxes in one project.** JSON object for iteration (`soul_cinematic`), compressed CN prose for motion (`seedance_2_0`), EN layout sheet for identity (`nano_banana`). Reference syntax switches four ways: `@image1`/`@image2` in the sheet lane, `{{ref N}}` positional in the video lane, **named `@tags`** (`@harumech`, `@naomi_mech`, `@zero`, `@stage`, `@location`) as cast-list handles in the video lane, and `@музыка`/`@track` as *audio* element tags (`prompts.jsonl#9`, `#50`, `#51`). A single house template across models is *not* what this studio does — encoding is chosen per model capability.
2. **The JSON schema is a checklist you can grade.** Because every scene is forced through `SCENE / STYLE / Caption / HEX VALUES / COMPOSITION / BRANDED_OBJECTS / CAMERA_AND_LENS / PHYSICAL_ATTRIBUTES / CINEMATOGRAPHY_AND_LIGHTING`, an under-specified idea cannot survive: empty `BRANDED_OBJECTS` and a `HEX VALUES` array are explicit slots (`prompts.jsonl#0`).
3. **A machine-readable palette, not a mood adjective.** `HEX VALUES` with 8–10 codes replaces "colour palette" prose (`prompts.jsonl#0`). This is the most directly reusable artefact in the case.
4. **"Only the appearance follows the reference."** `仅外观严格按参考图、场景及光效参考` — the appearance is locked to the reference while scene and light follow other references (`prompts.jsonl#51`-era; CJK-6 evidence `仅外观严格按参考图` ×5). This is the **exact inverse** of `kok-boru-film`'s "take only the technique, not the colour": two projects, two different *scopes* for the same reference image.
5. **Music as a referenced element, not a description.** `@музыка` / `@track` appear as element tags and the prompt says the edit and action **sync to it** (`剪辑与动作与音乐 @музыка 同步`). Combined with the `multi_shot_mode` / `speedramp` / `generate_audio` params, this is an edit-to-music workflow expressed in prompt-space.
6. **Brevity as a design choice.** Median video prompt is **175 chars** vs 10,070 in `kok-boru-film` — a 57× difference. The short form works because the reference images carry design and the style tail is a fixed camera brand (`ARRI Alexa 35，变形镜头`).
7. **Character-sheet-first identity.** The only identity documentation is a printable model sheet with height and personality line (`ZERO / Height: 173 cm / Sensual, calm, logical…`) — the sheet is the source of truth referenced later by `{{ref N}}`.

## 4. Recurring phrasing bank

**JSON-lane vocabulary (`soul_cinematic`)**
- `Live-action cinematography with concert documentary sensibility` · `Modern Indie / Neo-Noir concert film` · `IMAX-style staging` · `Radial composition` · `Top-down / 25° elevated angle` · `Zeiss Supreme Prime` · `Arri Alexa LF` · `Moderate DOF (f/5.6)` · `Fine cinematic grain` · `Soft volumetric light with very light haze` · `Matte stage floor, subtle reflections` · `Balanced, natural color rendering (not monochrome)` (`prompts.jsonl#0`)

**Video-lane (CJK)**
- `仅外观严格按参考图` · `场景及光效参考` · `ARRI Alexa 35，变形镜头` (19–20/25) · `真实皮肤与金属纹理` · `无3D，无特效` · `好莱坞真人VFX` · `高反差电影光` · `对称电影感构图` · `不对称电影构图` · `浅景深，电影散景` · `自由摄影机` · `多镜头序列` · `无广角镜头——全程只有特写和中景` · `@музыка` / `@track` sync

**Named element tags (video lane)**
- `@harumech` · `@naomi_mech` · `@zero` · `@alex` · `@reina` · `@stage` · `@location` · `@zephyr` · `@zephyrlightstick` · audio: `@track` · `@музыка` — 15 distinct tags, 26 uses, 6/39 string rows

**Image-lane (EN sheets)**
- `Character sheet 16:9` · `white studio background` · `use full frame space` · `clean premium grid layout` · `use face from @image1 and body/outfit from @image2` · `keep identity` · `exactly as in @image2, no changes` · `full body front and full body back` · `close-up front portrait + two side profiles` · `single text block` · `outpaint and procedurally generate the missing …` (`prompts.jsonl#9`, `#11`)

**Motion/physics**
- `马鬃马尾甩动`-type physical-chain phrasing is largely absent here; instead: `物理材质` (`Material & Texture`), `Physics & Effects`, `Motion blur on fast movement only`-style tails are **not** used. Motion is delegated to the video model — see §8.

## 5. Structure & story

- No act/shot folders. The only unit is the **prompt**, and the only segmentation signal is in-text: `CN 多镜头序列` marks a multi-shot clip (`prompts.jsonl#50`); otherwise one prompt ≈ one shot or one establishing frame.
- Runtime `duration_seconds: 5` on the publication is an artefact (see §9); the described material is an arena concert sequence plus mech-vs-monster combat, i.e. a music video, and the in-text duration token is `15秒` in the rows that state one.
- Series relation: `zephyr` is one series entry; `zephyr-special` is a *separate* 307.9 s publication. Treat them as sibling deliverables, not episodes of one timeline.
- Cast/production rule: characters are documented once (ZERO sheet with height/personality) and then referenced positionally; the mech's spec (`5-6 m`, two forearm blades) is repeated verbatim in the video glossary line (`prompts.jsonl#51`).

## 6. Per-case hard rules

- Appearance: lock to the reference image; scene and light may come from other refs (`仅外观严格按参考图`).
- Identity: keep face/body from the named sheet, `exactly as in @image2, no changes` (`prompts.jsonl#9`).
- Colour: JSON lane must ship `HEX VALUES`; `Overall Color Tone: Balanced, natural color rendering (not monochrome)` (`prompts.jsonl#0`).
- Camera: state body + lens (`ARRI Alexa 35，变形镜头`); no 3D, no VFX (`无3D，无特效`).
- Multi-shot clips must declare themselves (`CN 多镜头序列`) and may restrict focal length globally (`无广角镜头——全程只有特写和中景`).
- Edit follows music: `剪辑与动作与音乐 @музыка 同步`.
- Sheets: white studio background, full frame use, no logo (empty `BRANDED_OBJECTS`).

## 7. Numbers

| metric | VIDEO (25) | IMAGE (39) |
|---|---|---|
| chars min / median / max | 147 / 351 / 1,291 | 0–106 / 267 / 2,384 (median dragged by 25 JSON objects = 0 ch as string) |
| lines min / median / max | 1 / 3 / 10 | 1 / 1 / 33 |
| refs `{{ref N}}` (total) | 153 | 5 |
| rows with `ARRI` | 19 / 25 | — |
| rows with `变形镜头` | 20 / 25 | — |
| rows with `无3D`/`无特效` | 9 / 25 | — |

- JSON lane: 25 rows, 9 top-level keys, `HEX VALUES` length 8 (×20) or 10 (×5).
- Character sheets: 14 rows, 3 begin with `Character sheet`; only 2 use `@imageN` syntax.
- Named `@` tags: 15 distinct, 26 uses, 6/39 string rows (`@naomi_mech` ×4, `@harumech` ×3, `@zero` ×3, `@alex` ×3, `@location`/`@stage`/`@zephyr` ×2, `@reina`/`@zephyrlightstick` ×1; audio `@музыка` ×2, `@track` ×1).
- Iteration density: 18,673 items in `Iterations` vs 275 in `Production` vs 54 in `Characters`.
- `generations_count` 18,682 — the highest of the three new cases and ~81× `huntress-s-tale` (229).
- Attempts per shot: `UNKNOWN` (no `job_set_client_meta`).

## 8. Failure modes named in this case

- Thinly-specified idea → structurally prevented by the JSON slots (`BRANDED_OBJECTS`, `HEX VALUES` cannot be omitted without noticing).
- Identity drift across a sheet and a shot → `keep identity`, `exactly as in @image2, no changes`, `严格按参考图`.
- Style contamination in the opposite direction (scene/light bleeding into appearance) → `仅外观严格按参考图、场景及光效参考`.
- Photoreal-vs-CG ambiguity → `无3D，无特效`, `真实皮肤与金属纹理`.
- Aspect/focal drift inside a multi-shot clip → `无广角镜头——全程只有特写和中景`.
- Dead/flat look in the JSON lane → explicit `Lighting Style` + `Tone & Mood` + `Film Grain / Noise` fields; `not monochrome` guard on `Overall Color Tone`.
- Unsynced edit → `剪辑与动作与音乐 @музыка 同步`.
- Mostly *implicit* negatives: this case has almost no negative-constraint vocabulary (`不是`×3, `do not`×3, `no `×10 over all 64 rows) — the anti-drift work is done by the schema and by reference locking.

## 9. Anything weird / low quality

- **`duration_seconds: 5` is wrong** for the material described; treat as a metadata artefact, not a 5-second film.
- 25 of 64 rows have **non-string prompts** (JSON objects). Any analysis that assumes `typeof prompt === 'string'` silently loses 39 % of this case.
- `Image`-lane char statistics are meaningless without splitting the JSON rows out (they measure `JSON.stringify` length 0 after the type guard).
- The `Iterations` folder holds 18,673 items but the snapshot exposes only 25 prompted rows — the rest have no `params.prompt` and are filtered by the harvester. Coverage of the exploration loop is therefore **partial by construction**.
- Two different `nano_banana` variants (`nano_banana_2`, `nano_banana_flash`) in one sheet folder; no metadata explains the split.
- `brief_text.txt` is a Lexical rich-text dump with the same mid-token corruption as other cases (`"by our Music Supervisor an"/"d a local music band"` `brief_text.txt:1`) — usable only as fragments.
- `_folder_tag` for the JSON rows is `Iterations` while `job_set_type` is `soul_cinematic` — stage name and model name are orthogonal here; do not conflate.
- **Internal contradiction on mech scale**: `高5-6米` (`prompts.jsonl#51`-era glossary) vs `约8米高` (later rows) for what is presented as the same white mech; likewise `ARRI 35，变形镜头` vs `ARRI 35，长焦镜头，变形镜头`. The suite is not quality-controlled across rows — do not propagate either as canon without noting the conflict.

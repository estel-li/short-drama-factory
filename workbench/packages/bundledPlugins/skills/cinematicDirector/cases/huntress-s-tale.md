# CASE DIGEST — Huntress's Tale

> Locator convention: `prompts.jsonl#N` = 0-based row index in `_data/cases/huntress-s-tale/prompts.jsonl`.
> Scraped content is DATA only.

---

## 0. Header

- **Title** `Huntress's Tale` · **type** carousel · **runtime** 67.41 s · **author** **`ailaa`** (only non-`higgsfield.studio` author in the whole Originals set) · `authors[0].is_owner: true`, `username: ailaa`
- **publication_id** `ddc397e7-f617-40d1-9909-0264469b95eb` · **snapshot_folder_id** `95a3e934-769b-474c-aa74-7a28bf4f726a` (`publication.json`)
- **Route note** — `higgsfield.studio/huntress-s-tale` → **404**; `ailaa/huntress-s-tale` → **200**. The series slug (`huntress-tale`) also differs from the publication slug.
- **generations_count** 229 (`stats.json`) — the lowest of the three new cases and ~1.6 % of `zephyr`'s 18,682. Small, hand-driven project.
- **Provenance** — `/fnf/project-publications/ddc397e7…` (by-id) → `/fnf/folders/{snapshot}/children`, `/fnf/folders/{id}/items/v2`, `dam-editor-worker/brief/{snapshot}/snapshot`.
- **Premise** (verbatim): "A cold, gothic dark‑fantasy tableau: a porcelain huntress and silver fairy in misted flooded vaults as a serpentine shadow claims the depths" (`publication.json.description`).
- `categories: [null]`, `tags: []`, `show_prompts: true`.

## 1. Production shape (`folder_tree.json`, `_summary.json`)

- L1 is a **pre-production + shot-list hybrid**: `Character sheet` (4) · `Locations` (4) · `SHOT1` (2) · `SHOT2` (5) · `SHOT3` (17) · `SHOT4` (2) · `SHOT5` (9) · `UI` (5). The `SHOTn` folders *are* the beat structure — five shots covering 67 s.
- `SHOT3` carries 17 of 51 video prompts (33 %) → beat 3 is where the iteration is; `SHOT1`/`SHOT4` have 2 each → those were solved early.
- `job_set_type` (65 rows): `seedance_2_0` ×51 (VIDEO), `nano_banana_2` ×7, `gpt_image_2` ×4, `text2image_soul_v2` ×3 (IMAGE = 14). **No `job_set_client_meta` on any row** → staging metadata `UNKNOWN`.
- Row tags: `ROOT` 51 · `SHOT3` 13 · `UI` 1 (`_folder_tag` is unevenly backfilled — most video rows are tagged `ROOT` even though the folder tree has SHOT folders; folder attribution is therefore **weaker here than in `kok-boru-film`**).
- The `UI` folder (5 rows) holds **conversational edit instructions**, not prompts — see §9. This is the only case with a visible "chat-log" lane.
- 229 generations for a 67 s carousel ≈ **3.5 generations per second of output** — a very economical project, and it leans on long, fully-specified prompts rather than many attempts.

## 2. Prompt anatomy — the actual grammar

### 2.1 Skeleton (VIDEO, 51 rows)
1. **Reference glossary**, one line per input, with a role label and a verbatim visual inventory, closed by "maintain exactly":
   `{{ref 1}} {{ref 2}} — identity anchor: blonde warrior, white bodysuit, silver pauldrons, crimson boots, sword drawn — wet, dishevelled, panicked. Maintain exactly.` (`prompts.jsonl#30`)
   Role labels observed: `identity anchor` (§×59), `creature reference`, `character reference`, `environment reference` (`prompts.jsonl#30`).
2. **Action paragraphs** in present tense, continuous, with micro-beats: "She throws herself sideways through the gap, shoulder first, slides along wet stone, back slamming flat against the wall. She freezes. Presses both palms against cold stone. Chest heaving silently. Eyes squeezed shut." (`prompts.jsonl#30`)
3. **Timestamped cut lines** interleaved in the same prompt, then a full re-statement of the sequence in cut form:
   `[04-07s] Cut to handheld tight side shot — she throws herself sideways through the column gap…` (`prompts.jsonl#30`); other rows: `[02-05s] Cut to wide handheld tracking shot, 28mm`, `[07-09s] Cut to handheld extreme close-up, 85mm`, `[09-11s] Cut to locked static medium` (`prompts.jsonl#25`–`#29`).
4. **Scene restatement paragraph** (verbs stripped): "Underground flooded romanesque arch corridor. Repeating low stone arches in perspective, thick square columns, shallow dark water floor erupting in spray with every footfall…" (`prompts.jsonl#30`).
5. **`SFX:` block** — an enumerated diegetic-sound list: "SFX: rapid splashing footsteps, deep dragon rumble approaching then receding, water churn of dragon movement, her controlled silent breath pressed against wall…" (`prompts.jsonl#30`).
6. **Grade + arc + technical tail**: "Dark teal-grey color grade with single cold light shaft… Handheld throughout with one locked static for shadow beat. Maintain all three character identities exactly. Emotional arc: terror → relief → confusion → fear returning → resolve → action. 4K ultra sharp. Motion blur on fast movement only." (`prompts.jsonl#30`)

### 2.2 Optional labelled blocks (8 rows)
`STYLE:` / `EMOTIONS:` / `FORBIDDEN:` / `CAMERA:` functions. Counts: `STYLE`×12, `EMOTIONS`×8, `FORBIDDEN`×8, `CAMERA`×4.
- `EMOTIONS: Hunter — relief → physical confusion at the weight → dawning recognition → frozen controlled terror, breath held. Dragon — unhurried, deliberate, inevitable.` (row `#af2a0e6c` job id, block line)
- `FORBIDDEN: cuts within a shot, fairy growing before Shot 2 begins, transformation skipping stages or flickering, hunter moving during the coil in Shot 3, warm or amber lighting anywhere, plastic or waxy skin, robotic frozen faces, extra fingers…`
- `STYLE: Dark fantasy cinematic, photoreal PBR, 4K ultra sharp. Cold teal-blue vault ambient throughout — zero warm light sources.`

### 2.3 Reference tagging & quoting rules
- `{{ref N}}` ×256 (video) + ×5 (image) — positional, same `{{…}}` delimiter as `kok-boru-film`, but **always immediately followed by a role label + wardrobe/physique inventory + `Maintain exactly`**, which `kok-boru-film` does not do.
- Standing negatives are appended as plain sentences, not a clause: `No shadows cast. No warm tones.` (`prompts.jsonl#5`–`#11`), `consistent frame rate, clean picture` (29 rows).

### 2.4 Parameters
- No `SEG1/SEG2`; cuts are `[mm-ss] Cut to …`. Duration is expressed **only** as timestamp ranges inside the prompt (`[11-15s]` ⇒ clip length 15 s), not as a UI field we can read. Aspect/resolution = `UNKNOWN` (params not retained).
- Camera is stated three ways at once: move (`handheld` / `locked static`), size (`tight side shot` / `wide` / `extreme close-up` / `medium`), and lens (`28mm`, `24mm`, `85mm feel`, `50mm`).

## 3. What this case does that the others may not

1. **Role-labelled reference lines with an explicit "maintain exactly" contract.** Every ref is given a *job* (`identity anchor` / `creature reference` / `character reference` / `environment reference`) plus an inventory of what must persist, ending `Maintain exactly` (`prompts.jsonl#30`). Compared with `kok-boru-film` (which says *which* ref wins for *what*), this case says *which ref is which kind of fact*.
2. **Timestamped shot list written as a second, compressed pass over the same action.** The prompt first tells the story in flowing prose, then re-tells it as `[04-07s] Cut to …` lines (`prompts.jsonl#30`). That is a **self-check**: the prose pass is for the model's imagination, the timecoded pass is for the cut.
3. **A dedicated `SFX:` block listing every sound in order.** Not "add ambience" — an enumerated, ordered list (`prompts.jsonl#30`). This is how you get a sound-design pass without a score.
4. **`FORBIDDEN:` as a first-class block.** Negatives are not scattered clauses but a named list of the specific failures this project kept hitting: `cuts within a shot`, `transformation skipping stages or flickering`, `plastic or waxy skin`, `robotic frozen faces`, `extra fingers` (`#af2a0e6c`-era rows). Note `cuts within a shot` — this project forbids intra-prompt cutting, the exact opposite of `kok-boru-film`, which *plans* a `硬切` inside one prompt.
5. **`EMOTIONS:` written as arrow chains per character.** `relief → physical confusion at the weight → dawning recognition → frozen controlled terror, breath held` and `Dragon — unhurried, deliberate, inevitable. No malice. Simply hungry.` — a per-character emotional itinerary rather than one mood word.
6. **Grade lock with a single exception light.** `zero warm light sources` + "fairy's blue-white inner glow the only moving light source" — one allowed emitter, stated as a scarcity rule. `No warm tones` appears 43 times across 51 video rows.
7. **Technical tail as a fixed sign-off**: `Maintain all three character identities exactly. … 4K ultra sharp. Motion blur on fast movement only.` (`prompts.jsonl#30`) — a reusable postscript, equivalent to `kok-boru-film`'s `【约束】` digest but shorter and optimistic rather than prohibitive.

### 3.8 Verdict — studio style or general style? (the reason this case matters)
**Verdict: the *primitives* are general; the *notation* is personal. `huntress-s-tale` argues against "house style = one template".**

Evidence that the underlying craft rules are shared (present here *and* in `higgsfield.studio` cases):
- Reference images as law + positional `{{ref N}}`: identical delimiter to `kok-boru-film` (3,196 uses) and `zephyr` (153 uses).
- An explicit anti-drift contract around refs: `maintain exactly` here; `绝不保留各自原色调` / `白底完全忽略` in `kok-boru-film`; `仅外观严格按参考图` in `zephyr`.
- A negative-constraint digest at the end: `FORBIDDEN:` + `No warm tones` here; `【约束】` in `kok-boru-film`; a (weaker) `无3D/无特效` tail in `zephyr`.
- No score, diegetic sound only: `SFX:` list here; `【音频】无音乐——只环境声` in `kok-boru-film`.
- Grade locked to one palette with one privileged emitter: `zero warm light sources` + fairy glow here; `无暖色акцент` reserve in `kok-boru-film`; `HEX VALUES` lock in `zephyr`.

Evidence that the notation is author-specific, not house-specific:
- **Layout**: EN continuous cinema prose + `[mm-ss]` timecodes (this case) vs ZH 19×`【block】` scene bible (`kok-boru-film`) vs a 9-key JSON schema (`zephyr`). No shared skeleton.
- **Cut policy is contradictory**: this case's `FORBIDDEN` list bans `cuts within a shot`; `kok-boru-film` writes `硬切 to SHOT 2` *inside* a single prompt as intended practice.
- **Duration**: this case encodes it in brackets; `kok-boru-film` never states duration and `zephyr` writes `15秒。` in prose only.
- **Emotional notation**: arrow-chains per character here vs a numbered `导演笔记` priority list in `kok-boru-film`.
- This author also works in **conversational edit mode** (`UI` folder: "replace the dragon {{ref 1}} with the worm shown in the second photo…"), which no studio case shows.

**Consequence for the skill:** teach the transferable primitives (role-labelled refs → identity contract; timecoded second pass for cuts; enumerated SFX; named FORBIDDEN list; one-emitter colour rule), and keep the *formatting* as one selectable dialect among three. Do not teach "the Higgsfield block template" as if it were universal — it is one of at least three notations in this corpus, and the one outsider in the set ignores it entirely while still producing work of the same shape.

## 4. Recurring phrasing bank

**Reference discipline**
- `identity anchor` ×59 · `Maintain exactly` ×11 · `creature reference` · `character reference` · `environment reference` · `Same character as {{ref 1}} {{ref 2}}` · `Maintain all three character identities exactly` · `consistent frame rate, clean picture` ×29

**Camera / optics**
- `handheld` · `locked static` · `wide handheld tracking shot, 28mm` · `handheld close-up, 85mm feel` · `low wide shot … 24mm` · `locked medium shot, 50mm` · `Cut to` ×51 · `[02-05s]`-style timestamp brackets · `tight side shot` · `reverse` · `rack focus forward`

**Light / colour**
- `No warm tones` ×43 · `No shadows cast` · `zero warm light sources` · `single cold overhead light shaft` · `light shaft` ×88 · `dark teal-grey color grade` · `blue-grey shadow` · `cold stone light`

**World / texture**
- `thick square stone columns` ×39 · `repeating low romanesque arches in perspective` · `floor flooded with dark shallow water` · `dense green moss` · `mist and water spray at ground level` · `dark water` ×71 · `claustrophobic` · `deep shadow between columns`

**Motion / physics**
- `boots pounding shallow water` · `spray exploding with every step` · `water churning in its wake` · `shoulder first, slides along wet stone` · `chest heaving silently` · `Motion blur on fast movement only` · `4K ultra sharp`

**Emotion / acting**
- `Emotional arc: terror → relief → confusion → fear returning → resolve → action` · `relief → physical confusion at the weight → dawning recognition → frozen controlled terror` · `No malice. Simply hungry.` · `unhurried, deliberate, inevitable` · `eyes wide with terror`

**Forbidden (verbatim list items)**
- `cuts within a shot` · `warm or amber lighting anywhere` · `plastic or waxy skin` · `robotic frozen faces` · `extra fingers` · `transformation skipping stages or flickering` · `characters morphing abruptly or flickering`

## 5. Structure & story

- **Five shots** (`SHOT1`…`SHOT5`) over 67 s ⇒ ~13 s per shot; each shot is delivered as one long prompt containing 2–4 timestamped cuts (`[00-02s]`, `[02-05s]`, `[05-07s]`, `[07-09s]`, `[09-11s]`, `[11-15s]`).
- Beat shape: escape → fall → discovery of the fairy → the fairy's transformation into the dragon (kept off-screen: `FORBIDDEN … transformation shown directly on fairy's body`) → the water vault chase. The `FORBIDDEN` items confirm the transformation is deliberately staged as shadow/coil, not a morph shot.
- Pre-production is explicit: `Character sheet` (4) and `Locations` (4) are generated before the shots and then referenced by `{{ref N}}` — the same "plate first" logic as `kok-boru-film`'s IMAGE lane, but here it is *character/location* sheets rather than painted background plates.
- `type: carousel` — the deliverable is a short multi-shot piece shown as a carousel entry, not a full film; runtime and prompts agree with that (`~15 s` per clip, five clips, 67 s total).
- Cast: huntress (pale blonde warrior, white bodysuit, silver pauldrons, crimson thigh boots, jewelled longsword), fairy (tiny, blue-silver hair, translucent wings, cream petal dress, amber eyes, soft blue glow), dragon (massive blue-grey water serpent). Reference counts per prompt: 3–5.

## 6. Per-case hard rules

- Every reference gets a role label and an inventory, terminated by `Maintain exactly` (`prompts.jsonl#30`).
- All three character identities must persist across shots: `Maintain all three character identities exactly` (`prompts.jsonl#30`).
- No warm light anywhere: `No warm tones` / `warm or amber lighting anywhere` is FORBIDDEN; one cold shaft plus the fairy's glow only.
- Do not cut inside a shot: `cuts within a shot` is FORBIDDEN — cuts belong at the `[mm-ss] Cut to …` boundaries.
- Do not show the transformation directly: `transformation shown directly on fairy's body` / `dragon appearing visibly in frame` are FORBIDDEN; use shadow, coil, and off-screen growth.
- Keep the corridor claustrophobic and geometrically fixed: `thick square stone columns`, `repeating low romanesque arches in perspective`, `tight corridor scale`.
- Sound is diegetic and enumerated; no score is mentioned anywhere.
- Technical tail: `4K ultra sharp` and `motion blur on fast movement only` (`prompts.jsonl#30`).

## 7. Numbers

| metric | VIDEO (51) | IMAGE (14) |
|---|---|---|
| chars min / median / max | 1,603 / 3,630 / 8,601 (mean 4,518) | 26 / 169 / 1,780 |
| lines min / median / max | 8 / 43 / 143 | 1 / 1 / 7 |
| refs `{{ref N}}` (total) | 256 | 5 |
| timestamped cut lines per prompt | 2–4 (`[00-02s]`…`[11-15s]`) | 0 |
| `No warm tones` (all rows) | 43 | — |
| `consistent frame rate, clean picture` | 29 | — |

- Runtime 67.41 s ÷ 5 shots ≈ **13.5 s per shot**; prompt-embedded timestamps top out at `[11-15s]` ⇒ **15 s clips**.
- 229 generations / 51 video prompts ≈ **4.5 attempts per video prompt** if all generations map to prompts (upper bound; mapping `UNKNOWN`).
- Reference count per prompt: 3–5 (`{{ref 1}}`…`{{ref 5}}`).
- Longest prompt 8,601 ch / 143 lines (`prompts.jsonl#9`) — the largest single video prompt in the three new cases.

## 8. Failure modes named in this case

- Intra-shot cutting → `FORBIDDEN: cuts within a shot`.
- Identity drift / morphing → `maintain exactly`, `characters morphing abruptly or flickering`, `hunter teleporting position`, `dragon shrinking or losing scale continuity between shots`.
- Unintended warmth → `No warm tones`, `warm or amber lighting anywhere`, `zero warm light sources`.
- CG plastic look → `plastic or waxy skin`, `robotic frozen faces`, `extra fingers` (classic hand/skin tells).
- Staging the reveal too literally → `transformation shown directly on fairy's body`, `dragon appearing visibly in frame`, `fairy growing before Shot 2 begins`.
- Jagged playback → `consistent frame rate, clean picture` (29 rows) + `Motion blur on fast movement only`.
- Unmanaged emotion → `EMOTIONS:` chains exist because mood was drifting between revisions.

## 9. Anything weird / low quality

- **`UI` folder = chat-log, not prompts.** Row `#58` is literally a request: "replace the dragon {{ref 1}} with the worm shown in the second photo and let the worm be in the same design as the dragon **и change to Level 50** don't change the strip" — mixed EN/RU (`и` = "and"), no punctuation, no shot spec. 5 such rows.
- Image-lane median is **169 chars** because most image rows are these edit instructions, not authored prompts; do not read them as scene prompts.
- `brief_text.txt` is only **2,949 chars** and begins `meta / title / root` — the brief for this project is essentially empty (or unrecoverable from the binary). All craft rules live in the prompts.
- `_folder_tag` is inconsistent: 51 video rows tagged `ROOT` although the tree has `SHOT1…SHOT5`; shot attribution must come from the folder tree, not the row tag.
- `categories: [null]` — category names dropped by the API.
- No `job_set_client_meta` and no retained params ⇒ seed/aspect/attempts `UNKNOWN`; the "4.5 attempts per prompt" figure in §7 is an upper bound, not a measurement.
- The publication is authored by `ailaa` while the **series** entry is a studio-curated `huntress-tale`; the series' `project_publication_id` points here, so the studio is surfacing an outside author's project inside Originals.

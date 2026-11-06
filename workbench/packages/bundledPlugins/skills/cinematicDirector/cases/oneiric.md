# CASE DIGEST — ONEIRIC

> Locator convention: `prompts.jsonl#N` = 1-based row (JSONL line) in `_data/cases/oneiric/prompts.jsonl`;
> `brief_text.txt:N` = line number after splitting the file on `/\r?\n/`;
> `publication.json` / `folder_tree.json` / `stats.json` / `_summary.json` = case-level files.
> **Harvest caveat:** `_folder_tag` is capped at 25 rows per folder (oneiric: 25/25/25/25/25/22), so folder
> counts below are a *sample of 25 per folder*, not the production distribution.

---

## 0. Header
- **Title** ONEIRIC · **type** `film` · **runtime** 1188.958 s (19:49) · **author** `higgsfield.studio`
  · **publication_id** `dfa3c067-3f17-47cc-bc0d-65cc82fb11f0` · **snapshot_folder_id** `85a0f627-285b-4c8a-ac20-bcfd309d54c5` (`publication.json`)
- **generations_count** 41,096 (`stats.json` → `publication.json.stats`); community: 931 likes / 161,310 views (`stats.json`)
- **featured_episode_slug** `oneiric/full-film`; categories `["banner","open-sourced-by-higgsfield"]` (`publication.json`)
- **Provenance**: `/fnf/project-publications/higgsfield.studio/oneiric`; `/fnf/folders/85a0f627…/children`;
  `/fnf/folders/{id}/items/v2?include_subfolders=true`; brief snapshot `dam-editor-worker.higgsfield.ai/brief/85a0f627…/snapshot` (`_summary.json`). Harvest = 147 prompt rows; prompt bytes 1,241,074 (`prompts_meta.json`).
- **Premise** (quoted, `publication.json.description`): "ONEIRIC - a short film. Four college students in a dorm discuss the news: Oneiric's technology can plug your brain into any time and place. Each fantasizes about where he'd spend one day: Bob — the Trojan War, to see Helen with his own eyes; Sam — a deep-space future as a galactic pirate; Rudy — a fairy-tale world as a mage on a griffin. Each fantasy plays out as its own genre vignette."
- Creator account is `user_3GNcyaSCltezE7ot4WtRdn0jfo0` (studio publishing account) but every brief asset URL
  belongs to `user_3CJPreqcNMXMgR5BsQfXBILXuTo` — the actual maker (`brief_text.txt`, 12 cloudfront refs).

## 1. Production shape

**Folder taxonomy = (assets | regenerations | SCENE n — SET) then (shot n) inside each scene.**
Root: 41,159 items, `subfolders_count: 20` (`folder_tree.json`).

| L1 folder | items | subs |
|---|---|---|
| ASSETS | 22,960 | 6 (ANIMALS 1041 / CHARACTERS 5458 / EXTRAS 3485 / LOCATIONS 10753 / PROPS 1589 / TITLE SEQUENCE 634) |
| regenerations | 292 | 0 |
| SCENE 1 – KITCHEN | 303 | 3 (shot 1–3) |
| SCENE 2 – LIVINGROOM | 1326 | 11 (shot 1…8, 5A, 7A, 7.1) |
| SCENE 3 – TROY | 1665 | 0 |
| SCENE 3B – LIVINGROOM | 52 | 0 |
| SCENE 4 – LIVINGROOM | 862 | 7 (shot 1–7) |
| SCENE 5 – COSMOS | 5397 | 4 (Re-Gen, Shot 5, Shot 6, transition s5-s6) |
| SCENE 6 – LIVING ROOM | 912 | 2 |
| SCENE 7 – FAIRYTALE | 1819 | 3 |
| SCENE 8 – LIVINGROOM | 186 | 3 |
| SCENE 9 – FAIRY TALE | 3743 | 0 |
| SCENE 9A – LIVINGROOM | 64 | 0 |
| SCENE 10 – LIVING ROOM | 747 | 0 |
| SCENE 11 – LAB | 116 | 0 |
| SCENE 12 – TITLE SEQUENCE | 418 | 0 |

What the naming tells us: the pipeline is **assets → scene → shot**, and the *scene* is the unit of
continuity, the *shot* is the unit of generation. Source-of-truth folder is `ASSETS` (56% of all items:
22,960 of 41,159) — they generated 5.5k character stills and 10.7k location stills before/while shooting.
The fantasy vignettes (TROY 1665, COSMOS 5397, FAIRY TALE 3743+1819=5562) dominate the generation spend;
the dorm "frame" scenes are cheap (52–186 items each) — i.e. expensive iteration went into the genre
vignettes, the return-to-dorm beats were solved once and reused.
`SCENE 3B`, `9A`, `SCENE 5/shot 5A`, `shot 7.1` are insert scenes added later — evidence of a resequenced edit.

**Models / resolution** (`mine2.mjs stats`):
`seedance_2_0` 99 (all video), `soul_cinematic` 28, `gpt_image_2` 12, `text2image_soul_v2` 4,
`seedream_v4_5` 2, `nano_banana_2` 1, `seedream_v5_pro` 1.
Aspect: **21:9 dominates (137/147)** — 4032×1728 ×94, 2528×1088 ×27, 2688×1152 ×8, 2016×864 ×5, 3840×1648 ×3;
16:9 ×8 (2048×1152, 5120×2880, 2720×1536); one 1:1 (2880×2880) and one 6336×2688.
So video generation ran at **4032×1728 (21:9, 7:3)** — a wider-than-2.39:1 canvas, not standard 4K DCI.

**`job_set_client_meta`: 0/147 rows non-null.** No staging metadata in this snapshot — the studio's
staging lives in the *folder names* and in the prompt text itself (see §2).

**Iteration intensity**: 147 rows → **107 distinct prompt texts** (84 video, 23 image); 40 duplicate rows in
21 duplicate groups — 1 prompt re-run 5×, 5 re-run 4×, 6 re-run 3×, 9 re-run 2×. Median 9,027 chars per video
prompt (min 126, max 35,672).

## 2. Prompt anatomy — the actual grammar

There are **two lanes and two video dialects**. Merging them yields a wrong template.

### 2.0 Lanes
- **IMAGE lane** (48 rows: `gpt_image_2`, `soul_cinematic`, `text2image_soul_v2`, `seedream_v4_5/v5_pro`, `nano_banana_2`):
  no labelled blocks at all. 1–6 paragraphs of dense art-direction prose, median 1,972 chars, and the
  **aspect ratio is written into the prose** (37/48 rows). Example opener: "Luminous photoreal cinematic film
  still, wide establishing shot of a clearly magical fairy-tale realm" (`prompts.jsonl#2`).
- **VIDEO lane** (99 rows, all `seedance_2_0`): labelled ALL-CAPS blocks. 67/99 state the aspect ratio and the
  shot duration in-prompt; 67/99 say "100% match(es)"; 76/99 say "no music".

### 2.1 Video dialect A — the structured shot-spec (SCENE 3, 3B, 5; also 2 of the 4 SCENE 5 "Re-Gen" rows)
Observed order — 12 rows in exactly this order; 6 more with a leading `GLOBAL AUDIO LOCK` paragraph and
`CHARACTERS`/`CAMERA` omitted, 5 more with the leading audio lock but `CHARACTERS` present (`c2_order.mjs`):
```
SCENE CONTEXT → OUTPUT SETTINGS → ACTIVE REFERENCES → CHARACTERS → LOCATION MAP
→ FIRST FRAME AND SPATIAL BLOCKING → [SEGMENT 1/2/3 — label] → OPTICS → CAMERA
→ ACTION TIMING → PHYSICS → LIGHTING → [DIALOGUE] → AUDIO → POSITIVE LOCKS
```
Counts over 99 video rows (`count2.mjs`): LIGHTING 75 · OPTICS 71 · PHYSICS 71 · SCENE CONTEXT 70 ·
ACTIVE REFERENCES 70 · POSITIVE LOCKS 70 · AUDIO 69 · OUTPUT SETTINGS 65 · ACTION TIMING 65 ·
LOCATION MAP 62 · CHARACTERS 56 · FIRST FRAME AND SPATIAL BLOCKING 54 · CAMERA 43 · DIALOGUE 20 ·
`SEGMENT n — <TITLE>` 25 occurrences / 9 rows · `HARD CUT` 147 occurrences / 26 rows.

### 2.2 Video dialect B — the locks-first patch ledger (SCENE 7, 9)
Observed order (18 rows, plus 6 with a leading `— GLOBAL LOCKS —` and 9 with a trailing `— ASSETS / LINKING —`):
```
[GLOBAL <X> LOCK ×N]  →  — REFERENCE DEFINITIONS —  →  — TECHNICAL BLOCK —  →  — PROMPT —
→  ACTING TASK — <NAME>  →  — ASSETS / LINKING —
```
- `GLOBAL … LOCK` headers: **188 occurrences, 45 distinct names**, over 33 rows. Top:
  `GLOBAL LOOK LOCK` 33 · `GLOBAL AUDIO LOCK` 24 · `GLOBAL GRIFFON TAIL LOCK` 19 · `GLOBAL RUDY LOCK` 16 ·
  `GLOBAL BASILISK LOCK` 15 · `GLOBAL BASILISK WINGS LOCK` 12 · `GLOBAL NO ON-SCREEN TEXT / NO WATERMARK LOCK` 9 ·
  `GLOBAL MAX ANAMORPHIC LOCK` 7 · `GLOBAL RUDY HOOD-OFF / BARE-HEAD LOCK` 5.
  Locks-per-prompt is bimodal: **7 locks ×8 rows, 1 lock ×8 rows, 6 ×6, 9 ×3** (max 20).
- Some prompts open *before* the scene: `AUDIO > SCENE CONTEXT > …` in 6+5 rows, i.e. a `GLOBAL AUDIO LOCK — SFX ONLY`
  paragraph is literally line 1 (`prompts.jsonl#75, #79, #82, #84, #90, #93, #100, #104, #112, #120`).
- `— TECHNICAL BLOCK —` is the delivery-spec block: "Cinematic photoreal, live-action. 21:9. 9s. SFX only,
  no music." (`prompts.jsonl#73`). `— PROMPT —` is the actual description, i.e. **spec first, story last**.
- `ACTING TASK — KING` / `— JACK` style blocks: given-circumstances → tactic → moment-to-moment beat list
  (`prompts.jsonl#73`).

### 2.3 The slug/header line
**There is none.** Unlike CULLY HILL's `88 — CLIP 07 (…) — World: X, Variant A — ~8s, 21:9 — INT. …` header line,
ONEIRIC starts straight at `SCENE CONTEXT` or at a lock. Production identity lives in the *folder*
(`SCENE 9 - FAIRY TALE/shot 7`) + the reference UUIDs, never in a prompt title. `INT./EXT.` sluglines are
**absent** (0 occurrences of `EXT.`/`INT.`); location is prose in `LOCATION MAP`.

### 2.4 Reference tagging
- `{{uuid}}` for every asset (99/99 video rows; **1,623 refs total**, median 15 per prompt, min 2, max 69).
- `{{ref 1}}`、`{{ref 2}}` 用于临时/UI 附件（31 与 2 行；语料第二个用的是独立的视频 token，此处统一为 `{{ref N}}`）。 `@TAG` appears in 1 row only.
- Ordering rule stated in the CHARACTERS block: each entry is `{{uuid}}: <anatomy> — … Action-critical: … Face 100% matches <…>`
  (`prompts.jsonl#50`). The dialect-B equivalent is `— ASSETS / LINKING —` which is a one-line-per-uuid
  `= what it controls` table (`prompts.jsonl#73`).
- Continuation prompts exist in Russian: "продолжи кадр `{{ref 1}}`" ("continue the shot") (`prompts.jsonl#110`, 126 chars).

### 2.5 Segment / cut / timing syntax — clock-based
- Dialect A: `SEGMENT 1 — RUN OUT AND LEAP (no stopping)` then a standalone `HARD CUT` line, repeated
  (`prompts.jsonl#126`).
- `ACTION TIMING` uses **absolute seconds per segment**: "0.0-1.6s (SEG 1): … HARD CUT. 1.7-2.6s (SEG 2): …" (`prompts.jsonl#50`).
  235 clock ranges over 73 rows. Durations also stated as `~8s`, `~11s`, `9s.`, `10s.` (dialect-B technical block).
- Dialogue is timecoded in its own block: `SAM  @0.5s–1.6s: "Guys, we gotta jump!"` (`prompts.jsonl#50`) —
  184 quoted lines over 60 rows.

### 2.6 Aspect ratio / duration *inside* the prompt — duplication is deliberate
67/99 video prompts write `21:9`, 41 write `2.39:1`, 18 write `16:9`; 17 prompts write an explicit shot
duration (`12s` ×7, `10s` ×6, `9s` ×4, `8s` ×4). Meanwhile the UI params carry `aspect_ratio` (115 rows) and
`duration` (99 rows). So the number exists **twice**. In dialect B the technical block also restates the
no-music rule that the UI's `generate_audio` param implies. The brief explains why the optics half of this
duplication exists (§3).

## 3. What this case does that the others may not

1. **It bakes the lens into the assets instead of the prompt.** "Seedance doesn't reliably hold anamorphic
   optics asked for in a video prompt… The fix is to move the lens one step earlier in the pipeline:
   generate the location image with the anamorphic effect already in it" — "the plate itself becomes the lens"
   (`brief_text.txt:8197-8227`). So 21:9/anamorphic still appears in every prompt, but as a *maintainer*, not a request.
2. **"Naming them summons them" — negative words are banned from video prompts.** "In video prompts those
   words never appear at all even as bans (see the iron rules: naming them summons them)" (`brief_text.txt:8482-8483`).
   Verifiable consequence: only 2/99 video rows contain any anti-slop negative ("NOT 3D / no CGI"), versus
   30/36 in zephyr and 33/98 in trigger. ONEIRIC controls by positive locks (`POSITIVE LOCKS`, `GLOBAL … LOCK`),
   not by `FORBIDDEN` lists — `POSITIVE LOCKS` appears in 70 rows; the word FORBIDDEN appears in only 2 rows,
   both as a bullet *inside* a lock ("• FORBIDDEN: he must NOT grip the two ends and pull them APART left-and-right", `prompts.jsonl#73`),
   and 0 rows carry a negative block header.
3. **The prompt is a patch ledger, and the patches are labelled as such.** "VERTICAL-UNROLL LOCK — MECHANICS,
   READ CAREFULLY (**this keeps coming out wrong**): the scroll must open VERTICALLY, TOP-TO-BOTTOM, NOT sideways"
   (`prompts.jsonl#73`). Same pattern: "GLOBAL RUDY HOOD-OFF / BARE-HEAD LOCK — HIGHEST PRIORITY, READ FIRST,
   ABSOLUTE" (`prompts.jsonl#78`), "`#1 TOP PRIORITY — THE GRIFFON'S WINGS ARE FOLDED SHUT (read first)`"
   (`prompts.jsonl#105`). Each failed generation leaves a named scar in the template.
4. **Hard rules are emitted as standalone one-line bullets in caps**, not as prose: `NO SLOW MOTION.` ·
   `NO PAUSE.` · `NO GORE.` · `SFX ONLY.` · `FULL-BLEED.` · `EXACTLY FOUR SECONDS.` · `ONE CONTINUOUS TAKE.`
   (`prompts.jsonl#85`). This is the one place negatives *are* allowed: as enumerated absolutes, never as
   "avoid/no X" phrasing.
5. **A Voice Bible pinned verbatim across clips.** "a voice here is a written block — register, timbre, tempo,
   manner — decided once, stored in the Voice Bible, and pasted into every generation verbatim, never even a
   synonym changed" (`brief_text.txt:8643-8666`). In the corpus this is the `AUDIO` block's
   `SAM's voice: bright, high-set American male voice with a reedy, nasal, hard edge…` (`prompts.jsonl#50`), 184 occurrences of the pattern.
6. **Diagrams are a separate input class, not a picture.** "make the AI treat a reference not as a picture to
   copy, but as a system of spatial data" (`brief_text.txt:7811-7818`), and positions are then written as
   `x 50%, y 55%` in the prompt (29 rows carry `x N%`; e.g. `prompts.jsonl#126`).
7. **Asset states are separate assets, per a naming convention the whole team follows.** "A character has as
   many assets as states he goes through: Alfie in the common room and Alfred in the lab bed are different
   assets of the same man" (`brief_text.txt:34-74`). Hence 45 distinct `GLOBAL … LOCK` names all
   pointing at different uuid states of the same objects.
8. **The writer is a skill file, and the block order is a contract.** "Every shot is written by the CINEDANCE
   skill in the same blocks, in the same order" (`brief_text.txt:9022`). The brief ships four `.skill`
   attachments: `tig-scene-engine.skill`, `tig-acting-task.skill`, `tig-diagram.skill`,
   `CINEDANCE HIGGSFIELD SKILL.skill` (`brief_text.txt:7866, 9489-9490, 10555, 11344`).

## 4. Recurring phrasing bank

**Control / lock phrases** (counts over 99 video rows, `mine2.mjs countmarkers`/`c2_facts`):
`100% match` 69 rows · `GLOBAL … LOCK` 188 tokens · `HARD CUT` 147 tokens / 26 rows ·
`no subtitles` 79 rows · `no music` 76 rows (155 tokens) · `NON-IP` 26 rows · `x N%` coords 29 rows ·
`~Ns` duration 14 rows.
Boilerplate sentences reused verbatim: "no subtitles, no music" · "SFX only, no music, no subtitles" ·
"Clean modern glass — no horizontal light streaks, no blue flare lines, no lens flare" ·
"100% matches the reference" · "(words only in DIALOGUE)".

**Camera / optics** — "Shot on a 35mm ANAMORPHIC lens — natural, non-distorting rendering — wide open at the
fastest aperture" (#50) · "VERY HEAVY background blur" · "big oval/elliptical bokeh, marked horizontal stretch,
heavy edge-blur and falloff" (#50) · "HARD handheld SHAKE throughout" (#50) · "vintage 2x anamorphic lens,
de-squeezed widescreen" (#73) · "tall vertical OVAL / cat-eye" (#73) · "pronounced anamorphic focus breathing" (#73).

**Light** — "Cool deep sci-fi interior glow" (#50) · "Warm golden hazy day … soft god-rays and floating motes" (#98)
· "No flat front light" (#50) · "Faces readable" (#50) · "exposure stays perfectly even edge to edge" (#98) ·
"GLOBAL LOOK LOCK — NO VIGNETTE, EVER" (#101 first line).

**Motion / physics** — "Real weight and momentum over the vast drop" (#50) · "Real-time, grounded, no floaty
motion" (#50) · "Believable jump arcs" (#50) · "wings FOLDED TIGHT against its body, streamlined like a stooping
falcon" (#98) · "robots/creatures do not slide" appears as "their feet NEVER slide on the floor: no skidding,
no drifting" (#48 technical block).

**Sound** — "SFX only, no music" · "diegetic sound effects only" · "NO music, NO score, NO soundtrack, NO singing" (#75)
· long enumerated foley strings: "the soft shuffle of the court's collective step forward, the dry flick of the
twine threads brushed away…" (#73).

**Acting** — "ACTING TASK — KING (invested; the work is in his eyes; ALIVE and involuntary, not performed)" (#73)
· "GIVEN CIRCUMSTANCES / TACTIC / moment to moment (real reactions, no mugging)" (#73)
· "(Safety: the king's gaze stays engaged and searching — never a frozen, glassy stare; natural blink cadence.)" (#73)
· "When not speaking, lips stay closed" (#50).

## 5. Structure & story
- 1,188.958 s in 12 numbered scenes + 3 lettered inserts = **16 top-level units**. Frame narrative:
  dorm living-room scenes (2,4,6,8,10, 3B, 9A) alternate with the three fantasies — **TROY (3), COSMOS (5), FAIRY TALE (7 + 9)** —
  plus **KITCHEN (1)**, **LAB (11)**, **TITLE SEQUENCE (12)**.
- Beat budget: the insert scenes are tiny (52–186 items), the fantasies huge — the film is 3 vignettes
  bridged by cheap returning-to-the-couch beats. Each vignette is internally shot-numbered 1…8, so a vignette
  ≈ 6–8 generated clips.
- Story rules stated: the brief carries the V.O./dialogue discipline in the `DIALOGUE` + `AUDIO` blocks
  ("SAM speaks ONLY this line, only within his time slot. No added, changed, improvised or mumbled words.
  When not speaking, lips stays closed." — `prompts.jsonl#50`), i.e. **one line per character per shot, timecoded**.
- `type` is `film`, `featured_episode_slug: oneiric/full-film` → one episode = the whole film. No series relation.

## 6. Per-case hard rules
- **Never write the lens as a request.** Bake anamorphic into the location plate; in video prompts only
  maintain it (`brief_text.txt:8197-8227`).
- **Never name what you don't want in a video prompt** — "naming them summons them" (`brief_text.txt:8483`).
  Use `POSITIVE LOCKS` / `GLOBAL … LOCK` instead.
- **Every prompt restates the identity of every on-screen asset as a uuid + `Face 100% matches`** (#50).
- **One spoken line per character per shot, with an explicit time window**, and "no other words from anyone" (#50).
- **Locks go first, and repeat at the end**: dialect B opens with the patch list and closes with
  `— ASSETS / LINKING —` (a re-statement of what each uuid controls) (#73).
- **State the aspect ratio and the duration inside the prompt** even though the UI owns them (67/99 rows).
- **Cut type must be named** (`HARD CUT`), and no other transition word is used (0 `DISSOLVE`, 0 `WIPE`, 3 `CUT TO`).
- **Asset naming = `element + scene suffix + version suffix`; a changed state is a new asset, never an overwrite**
  (`brief_text.txt:59-74`).
- **Never let the model invent the number of segments**: `OUTPUT SETTINGS` fixes it — "Three-segment sequence
  with a HARD CUT between each (two hard cuts total)" (#50).

## 7. Numbers
- Runtime 1,188.958 s = 19:49 (`publication.json`); 41,096 generations; 931 likes / 161,310 views (`stats.json`).
- Prompt rows 147 → **107 distinct** (84 video + 23 image). Video chars: min 126 / median **9,027** / p90 21,611 / max **35,672**.
  Image chars: min 21 / median 1,972 / max 2,675.
- Refs per video prompt: min 2 / median **15** / max **69**; total 1,623 `{{…}}` handles.
- Shots per video prompt (`1 + HARD CUT`): 1 ×71 rows, 3 ×4, 4 ×3, 5 ×3, 6 ×5, 7 ×1, 8 ×1, 9 ×1, 12 ×2, 13 ×6, 15 ×2
  → **296 internal shots declared across 99 prompts (avg 2.99)**; 10 rows declare ≥12 internal cuts.
- Cuts: 147 `HARD CUT` tokens; 235 clock-ranges; 184 timecoded/attributed dialogue lines over 60 rows.
- Aspect: 21:9 in 137/147 rows (93%); video canvas 4032×1728 ×94.
- Iteration: 40 of 147 rows are exact re-runs, in 21 duplicate groups (largest group 5).
- Credits/min: UNKNOWN (no `credits_spent` field in this case's `stats.json`).

## 8. Failure modes named in this case
- **Anamorphic drift** — the reason optics were moved to the asset stage: "ask Seedance for that look in a prompt
  and it won't hold it reliably, the optics drift from shot to shot" (`brief_text.txt:8197-8212`).
- **Vignette** — "GLOBAL LOOK LOCK — NO VIGNETTE, EVER: absolutely NO vignette anywhere, in any frame" (#101).
- **Naming the artefact** — "no horizontal light streaks, no blue flare lines, no lens flare" is only allowed at
  the image stage; in video prompts those words "never appear at all" (`brief_text.txt:8482-8483`).
- **Floaty motion** — "Real-time, grounded, no floaty motion" (#50); "their feet NEVER slide on the floor:
  no skidding, no drifting" (#48).
- **Flat front light** — "No flat front light" (#50); "Faces readable… no crushed silhouette" (#126).
- **Dead eyes / mugging** — "never a frozen, glassy stare; natural blink cadence" (#73); "real reactions, no mugging" (#73).
- **Scroll opening sideways** — "FORBIDDEN: he must NOT grip the two ends and pull them APART left-and-right" (#73).
- **Wrong cast on screen** — "GLOBAL ON-SCREEN CAST LOCK — ONLY RUDY IS EVER SHOWN, SAM & BOB NEVER APPEAR (fix,
  HIGHEST PRIORITY, READ FIRST)" (#111, #122).
- **Gore / music** — "NO GORE." (#85), "SFX ONLY." (#85).

## 9. Anything weird / low quality
- **The harvest is 25-per-folder, not proportional**: TROY (1,665 items) and the 52-item insert folder each
  contribute ≤25 rows. Do not read §1's folder table as effort distribution.
- 40 of 147 rows are byte-identical re-runs (21 duplicate groups).
- Junk rows: `prompts.jsonl#11` is a single Russian noun phrase "откусаный кусок пиццы" (21 chars, `nano_banana_2`) —
  an asset iteration, not a film prompt. One prompt (#110) is a 126-char Russian continuation.
- Truncation: the harvester's `.log` of `POSITIVE LOCKS` in some rows ends mid-word ("…clearly reads as su" in #98);
  the JSONL itself is not truncated, but this digest quotes the file as-is.
- `job_set_client_meta` is null for all 147 rows — no attempts/staging metadata recoverable here.
- Scene names are inconsistently spelled: `SCENE 7 - FAIRYTALE` vs `SCENE 9 - FAIRY TALE`, `LOCATION MAP` vs
  `LIVINGROOM` vs `LIVING ROOM`, `SCENE 3  - TROY` (double space). Folder names are the unreliable key.
- `publication.json` text is double-encoded (em-dashes render as `[mojibake: “—”]`); quotes in §0 were repaired.
- Brief and prompt disagree on nothing observable, but the brief's own prose is mojibake-prefixed per line
  (`w\t`, `wq`, `%`) — line numbers in `brief_text.txt` are approximate anchors, not clean citations.

---

## 10. Cross-case note — how much does the template vary with runtime?

Same studio, same method doc lineage (this brief and `trigger`'s ship the same `.skill` family and the same
"iron rules" doctrine), but **runtime and form change the template's shape, not its vocabulary**:

| | oneiric (19:49) | zephyr (5:08) | trigger (8:36) | kok-boru (20 s carousel) |
|---|---|---|---|---|
| labelled blocks per video prompt | 12–15 | 0–14 (2 monolith dialects) | 6–11 | 8–11, rigid |
| shots per prompt (avg) | 2.99 | 2.89 | 1.24 | 3.88 |
| median video prompt chars | 9,027 | 5,754 | 6,101 | 9,238 |
| clock timecodes inside prompt | 235 ranges / 73 rows | 91 / 20 rows | 471 / 77 rows | **0** |
| negative/`FORBIDDEN` block | 0 rows | 0 rows | 43 rows | 50 rows |
| prompt→UI duplication | restates AR + duration | almost none | restates 2.39:1 | **none** |

The long-form cases buy continuity with **volume and re-statement** (15 refs/prompt, 188 named locks, a
Voice Bible pasted verbatim); the short carousel buys it with **a fixed 8-block skeleton reprinted every shot**
(§kok-boru). ONEIRIC never uses a negative block; TRIGGER/KOK-BORU build the whole control surface out of one.
That is not a runtime effect — it is a *studio-doctrine* split, and it is the single most important thing to
get right when distilling a template: **oneiric's template is a positive-lock spec, trigger's is a negative
contract.** Both are in the same workspace (`Maliksfield`, `folder_tree.json`), so this is a genuine A/B.

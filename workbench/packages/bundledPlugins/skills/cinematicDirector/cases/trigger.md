# CASE DIGEST — THE TRIGGER

> Locator convention: `prompts.jsonl#N` = 1-based row (JSONL line) in `_data/cases/trigger/prompts.jsonl`;
> `brief_text.txt:N` = line number after splitting on `/\r?\n/`; `publication.json` / `folder_tree.json` / `stats.json`.
> **Harvest caveat:** `_folder_tag` is capped at 25 rows per folder (ROOT 25, and 25 for each of four scenes),
> so folder counts are a sample, not the production distribution.

---

## 0. Header
- **Title** The Trigger · **type** `film` · **runtime** 515.903 s (8:36) · **author** `higgsfield.studio`
  · **publication_id** `0967df6b-0216-459b-91a4-48495ce4bea3` · **snapshot_folder_id** `6f964d46-3365-4089-9eeb-d7a1471eac98` (`publication.json`)
- **generations_count** 5,429 (`stats.json` → `publication.json.stats`); 1,086 likes / 135,080 views (`stats.json`).
- **featured_episode_slug** `the-trigger/full-film`; categories `["open-sourced-by-higgsfield","spotlight"]`
- **Provenance**: `/fnf/project-publications/higgsfield.studio/trigger`; `/fnf/folders/6f964d46…/children`;
  `/fnf/folders/{id}/items/v2?include_subfolders=true`; brief snapshot `…/brief/6f964d46…/snapshot` (`_summary.json`).
  125 prompt rows, 607,886 prompt bytes (`prompts_meta.json`).
- **Premise** (quoted, `publication.json.description`): "An ageing hitman takes his orders in a diner, printed under the price of coffee and apple pie. When the new order names the soldier who once dragged him off a roof in Afghanistan, he has to decide which of his two lives he is still living in."
- Workspace **`Maliksfield`** (`82746fbc-d749-42fa-b4cc-d83c8f131f07`) — the same workspace as `oneiric`.
- Assets and two `.skill` attachments live under `user_3GVcpTp7fHMxCVPhBelWo5SScmg` (5 refs) plus 2 under
  `user_3CJPreqcNMXMgR5BsQfXBILXuTo` (also oneiric's creator) — 3 distinct cloudfront hosts in one brief (`c2_urls.mjs`).

## 1. Production shape

**Folder taxonomy = `ASSETS` (+ Characters/Costume/Locations/Props) | 6 numbered scenes.** Root: 5,431 items,
`subfolders_count: 8`; 7 L1 children are listed (one folder is missing from the snapshot).

| L1 folder | items | subs |
|---|---|---|
| ASSETS | 2,495 | 4 — Characters 941 / Costume 226 / Locations 987 / Props 341 |
| SCENE 01 – KILLER'S WORK | 443 | 1 (`GUEST CHECK` 52) |
| SCENE 02 – CAR ARRIVES | 32 | 0 |
| SCENE 03 – SNIPER WATCHING | 818 | 0 |
| SCENE 04 – SNIPER'S REACTION | 291 | 0 |
| SCENE 05 – CREDITS | 341 | 0 |
| SCENE 06 – WAR FLASHBACK | 879 | 4 (`AFGHAN BOY` 105, `AMERICAN BASE` 12, `APACHE` 25, `CORNER HOUSE` 95) |

What the naming tells us: **the scene name is the unit of continuity and the sub-folder is the sub-unit**
(`SCENE 01/GUEST CHECK` = the diner-table prop set; `SCENE 06/CORNER HOUSE`, `/APACHE`, `/AFGHAN BOY` = the
flashback's locations). Unlike oneiric, **there are no `shot n` folders** — 443 items sit directly in
`SCENE 01`. So the shot list is not folder-encoded here; it is encoded **inside the prompt header**
(`SHOT — TERRENCE AT THE WINDOW, 10 SECONDS`) and in the prompt count per scene. The tiny
`SCENE 02 – CAR ARRIVES` (32 items) marks a one-beat transition solved in a single generation.
Distribution of the *sampled* prompts: ROOT 25, SCENE 06 25, SCENE 03 25, SCENE 01 25, SCENE 05 25 — but
distinct texts per folder are 3 / 6 / 11 / 11 / 8, i.e. the same prompt was re-rolled in batches.

**Model / resolution** (`mine2.mjs stats`): `seedance_2_5` 98 (all video), `seedream_v5_pro` 26 (all props/
stills), `cinematic_studio_3_0` 1 (a Chinese 5-second shot, #55).
Aspect: **21:9 ×91** (2016×864 ×64, 1344×576 ×27) · 16:9 ×33 (2720×1536 ×12, 1360×768 ×13, 1920×1080 ×7,
1280×720 ×1) · 4:3 ×1. Two working resolutions coexist: **2016×864 for hero shots** and **1344×576 for the
sniper-window sequence** (lower res for a heavy VFX/scope-POV shot).

**`job_set_client_meta`: 0/125 rows non-null.** No staging metadata.

**Iteration intensity**: 125 rows → **39 distinct prompts** (35 video + 4 image). 86 duplicate rows; one prop
reference is duplicated **13×** and one flashback shot prompt **6×**. Median 6,101 chars per video prompt
(min 689, max 9,134 — the tightest length band of all four cases, 1.5 decades vs 2+ elsewhere).

**The bilingual corpus**: 28 of 98 video rows are **Chinese rewrites of the identical prompt** (same references,
same beats, same shot list; e.g. the diner scene `prompts.jsonl#76` is the CN twin of the EN set, 22.5 s /
7 shots). Language is a *render variant*, not a content variant — the block skeleton survives translation
(`场景背景 / 【…rule…】 / 风格 / 光线 / 摄影机与镜头 / 激活参考 / 空间调度 / 格式模式 / 动作时间轴 / 表演任务 / 物理 / 声音 / 禁止`).

## 2. Prompt anatomy — the actual grammar

### 2.0 Lanes
- **IMAGE lane** (26 `seedream_v5_pro` + 1 `cinematic_studio_3_0`). No blocks; **one paragraph, median 1,159 chars**
  (min 698, max 1,597), all beginning `Prop reference, one single photograph on a smooth matte dark charcoal-grey
  background, soft diffused overcast-style lighting…` (#1–#25). 25/26 say "no text/watermark". Aspect ratio is
  stated in only 1 of 27 image prompts — assets were generated square/plate-first, cropped later.
- **VIDEO lane** (98 rows, all `seedance_2_5`). Two EN dialects + one CN dialect; `【…】` bracket headers in 78 rows.

### 2.1 Dialect A — the EN "film-style + identity" spec (3 rows: #26, #27, #28)
```
FILM STYLE — <scene>, fixed for the whole film.
IDENTITY (top priority): … → CAMERA: … → GRADE: … → KIT LOCK (mandatory, taken from the references): …
→ THE OTHER TWO SOLDIERS / 【<SCENE-SPECIFIC LAW>】 → ACTING: … → REFERENCES: … → SCENE: …
→ ACTION (10s): … → CAMERA: … → ACTING TASK: … → SOUND: … → FORBIDDEN: …
```
Counts over 98 video rows: `IDENTITY` 3 · `KIT LOCK` 8 · `SCENE:` 3 · `ACTION (Ns):` 3 · `REFERENCES:` 3 ·
`ACTING` 35 · `GRADE:` 34 · `CAMERA:` 25 · `SOUND:` 32 · `FORBIDDEN` 60 rows total (43 as a `【FORBIDDEN】` block,
17 as a bare `FORBIDDEN:` header).

### 2.2 Dialect B — the EN bracketed spec (the dominant form, ~43 rows)
```
[Duration: Ns. <SLUGLINE — ONE SHOT ONLY/SINGLE CONTINUOUS SHOT>]
→ 【REFERENCES — ranked】 / 【REFERENCES — RANKED】 → GRADE: → LENS: → CAMERA: → GEOGRAPHY / 【THE SHOT】 /
  【KIT LOCK — EVERY MAN, EVERY FRAME】 → 【TIMELINE — Ns】 or 【BEATS】 → ACTING / ACTING TASK →
  SOUND: → 【FORBIDDEN】
```
`c2_order.mjs`: 29 rows reduce to `【REFERENCES】 > 【TIMELINE/BEATS】 > 【FORBIDDEN】`; 12 to
`【REFERENCES】 > GRADE: > CAMERA: > ACTING > SOUND: > FORBIDDEN`; 5 each to two 9-block variants.
**41 distinct `【…】` labels, 479 occurrences** (`c2_probe cjkheaders`). Top:
`【FORBIDDEN】` 43 · `【音色:同上】` ("voice timbre: as above") 35 · `【TIMELINE】` 24 ·
`【REFERENCES — ONE PLATE PER PAGE】` 20 · `【REFERENCES — ranked】` 17 · `【THE SHOT — ONE SET-UP FOR ALL THIRTY SECONDS】` 17 ·
`【THE OPENING】` 17 · `【HOW EACH PAGE ARRIVES AND LEAVES】` 17 · `【GRADE, CAMERA, LENS】` 17 ·
`【PLATE LOCK — THE PRINT IS PHOTOGRAPHED, NOT WRITTEN】` 13 · `【女服务员的手:必须是女性的手】` 11 ·
`【苹果派:完整,不掉渣】` ("the apple pie: whole, no crumbs") 11 · `【EYE LAW — HIGHEST PRIORITY】` 9 · `【LIGHT】` 9 ·
`【SILHOUETTE LAW — SECOND PRIORITY】` 6. Small-caps is *not* used — the label system is CJK brackets even in English.

### 2.3 Dialect C — the Chinese full rewrite (28 rows)
Same skeleton, Chinese labels, and the only place **multi-shot prompts with clock timelines** appear in this
case: `七个镜头,共22.5秒` ("seven shots, 22.5 s total") with `镜头1——0.0至2.5秒——…` and `2.5秒切` ("cut") between
them (`prompts.jsonl#76`). CN shot counts per prompt: 7 ×7, 12 ×7, 15 ×3, 9 ×2, 8 ×2, 10 ×1; totals
20 s ×12, 22.5 s ×7, 23.7 s ×3 (`c2_probe`). The CN `禁止` ("forbidden") block can be longer than the body:
"音乐相关(反复强调,必须全部成立):整段视频无音乐;店内不放音乐;no music, no score, … no radio, no jukebox, no speakers,
no singing, no humming, no whistling" (#76).

### 2.4 The slug/header line — this case has one
Two header forms, both carrying the duration:
- `SHOT — TERRENCE AT THE WINDOW, 10 SECONDS` (#51, #53, #56, #64, #67, #69, #71, #72, #75 — "5 SECONDS" and
  "10 SECONDS" variants; 9 rows).
- `Duration: 5s. AFGHANISTAN, KABUL, DAY — ONE SHOT ONLY: three men on the roof, firing.` (#36, #38, #39, #40,
  #42, #44, #46, #47, #48, #50 — 34 rows) — i.e. **duration → INT./EXT.-style slugline → shot-count manifesto**.
`END CREDITS — THE GUEST CHECK BOOK. 30s.` (#101–#108, #110–#125) is a third variant.
Slugline vocabulary is deliberately tiny: `AFGHANISTAN, KABUL, DAY` · `NEW YORK, NIGHT` · `a New York brownstone
street` · `a diner` — no scene numbers inside the prompt (scene number lives in the folder).

### 2.5 Reference tagging — **explicitly ranked**
`【REFERENCES — ranked】` then numbered:
```
1: {{36b8fb78-…}} = JACK.
2: {{d0095f26-…}} = TERRENCE.
Faces, kit and weapons decided by their own assets alone.
3: {{ref 5}} = THE HOUSE — …
No other reference is used.
```
(`prompts.jsonl#29`; `【REFERENCES — RANKED】` used at #51+). Rank order is a **precedence contract**, and it is
stated twice — at the top as a list (51 rows) and inside the `FORBIDDEN` as "no invented face". `{{uuid}}` in
57 rows, `{{ref N}}` in 70 rows (props/locations), `@TAG` in 22 rows (`@loc_SNP_diner.png`, #76).
The credits sequence goes further: one plate per page, 7 plates, each used "in beat N only" (#101).

### 2.6 Segment / cut / timing syntax — clock, and a language split in cut density
- **`HARD CUT` occurs 0 times in 98 video prompts.** Only 3 `CUT TO`/`MATCH CUT` tokens. The EN prompts are
  written as single takes and the film's cuts happen in the edit: **47 of 71 EN prompts declare exactly one shot**,
  24 declare two (`1.34` shots/prompt).
- The **CN rewrites are the opposite**: they enumerate shots explicitly with `镜头1——0.0至2.5秒` and `2.5秒切`
  ("cut"), averaging **8.14 shots/prompt** (7 ×7 rows, 12 ×7, 15 ×3, 9 ×2, 8 ×2, 10 ×1). Same scenes, a much
  denser cut list — the CN pass re-cut the material on paper.
- Timing is written as pipe/tilde clock ranges: `0–2.5s | Ground floor, bare mud walls…` (#26);
  `0.0–1.5s — He stands at the glass…` (#51); `Around 1.0s Terrence breaks a shot` (#29).
  **471 clock ranges across 77 rows** — the densest timing grammar in the set.
- `【TIMELINE — 5s】` sections give the whole beat map before the description (#36).
- Chinese rows use `0-2秒：` and `2.5秒切` (#55, #76).

### 2.7 Aspect ratio / duration inside the prompt — stated, and stated twice
56/98 video rows write `2.39:1` (all as `LENS: anamorphic 2.39:1` or `IDENTITY (top priority): 2.39:1`), while
`aspect_ratio` is also set in the UI params (125/125 rows). Duration is stated in the header (`Duration: 5s.`,
`…, 10 SECONDS`) **and** in the `duration` param (99/125 rows). Resolution is never stated in-prompt.
The duplication is a deliberate belt-and-braces: the brief's own doctrine says the prompt is the only thing the
model reads, while the brief also admits the UI owns the value — see §8.

## 3. What this case does that the other cases may not

1. **It writes the control surface as a terminal `【FORBIDDEN】` block, and the block is 11.8% of all prompt
   characters** (71,963 of 609,844 chars over 60 rows, `c2_probe forbiddenlen`). Example: "no machine gun, no
   machine gunner, no belt-fed weapon, no ammunition belts. No fourth man on the roof." (#36). This is the
   opposite of oneiric's positive-lock doctrine and it is the same studio.
2. **It writes a precedence rule that tells the model which instruction to *drop* on conflict.** "IDENTITY (top
   priority): 2.39:1, true human proportions, faces exactly match the reference images… **If any instruction
   pulls a face off the reference, drop the instruction and keep the face.**" (`prompts.jsonl#26`). No other case
   states a conflict-resolution order.
3. **It repeats a hard fact three times, in three registers, to defeat a named recurring bug.**
   "THREE MEN ON THE ROOF **AND NO MACHINE GUN**: … **THERE IS NO MACHINE GUN AND NO MACHINE GUNNER ANYWHERE IN
   THIS SCENE.**" (#29) — and again in `【FORBIDDEN】` (#36). Same for goggles: "INCLUDING WHILE BOTH MEN ARE
   BEHIND THEIR RIFLE SCOPES. Nobody is bare-headed, nobody pushes the goggles up" (#29).
4. **It renders on-screen text from photographic plates, not from a text prompt.**
   "【PLATE LOCK — THE PRINT IS PHOTOGRAPHED, NOT WRITTEN】 Each reference is the finished photograph of that
   page. The print on it is already there and is copied exactly: letter for letter, dot for dot" (#101).
   The whole credits sequence is one set-up for 30 seconds with page-tears as the only action.
5. **It writes acting as an ordered, numbered eye-program with a silences-and-exceptions list.**
   "【EYE LAW — HIGHEST PRIORITY】 HE IS WIDE AWAKE… 1. HE SEES. 2. HE MEASURES IT. 3. HE KNOWS. 4. IT IS NOT HIS
   OWN LIFE." then "The mouth, brows, jaw and nostrils stay out of it… The FACE is quiet — the EYES are loud." (#51).
6. **It uses a stated "iron rules" doctrine that bans negatives — while shipping enormous negative blocks.**
   The brief: "Say what is there, not what you avoid. The word 'American' put a flag on a sleeve; writing 'no
   flag' put it back. Describe plain bare fabric instead and it disappears." (`brief_text.txt:2474-2481`).
   The prompts' answer is visible in #26: the uniform is specified positively ("Every surface of the uniform is
   PLAIN BARE FABRIC") *and* negated in the same sentence ("— no patches, no insignia, no emblems, no writing").
   This is the corpus's clearest example of a doctrine the working prompts did not fully obey.
7. **It budgets shots by wall-clock, not by shot count**: 30 s in one prompt (#52, #66, #101), 22.5 s / 7 shots in
   another (#76), 5 s in another (#36). Duration is chosen first and the content is fitted to it.
8. **Every scene is broken down before a single generation, and the breakdown is what the prompt is written from.**
   "On an AI film a weak scene costs real money — you find out it doesn't work only after you have generated it.
   So every scene is broken down before a single generation: what the scene is, what each character's motive,
   goal, obstacle and tactic are, and what the one physical action is that carries it" (`brief_text.txt:431-460`);
   "That work produces the director's read for each scene, and the read is what the prompts are then written from.
   The camera language, the grade and the sound follow it; they never lead it" (`brief_text.txt:564-578`).
   The prompt is the *output* of a pre-production document, which is why `ACTING TASK` arrives as
   `motive / Goal / Tactic` triads (#26, #51) and why the script is written "for a model with no memory"
   (`brief_text.txt:416`).

## 4. Recurring phrasing bank

**Control / contract phrases** — `【FORBIDDEN】` 43 rows · `【REFERENCES — ranked】` 51 · `100% match` 3 rows
(trigger barely uses it — identity is enforced by rank + "face law" instead) · `NON-IP` 0 rows ·
`anti-slop` 33 rows: "Not anime, not animated, not a video game, no CGI look." (#51); "no anime, no illustration,
no game CG, no plastic skin" (#36); "Anime, manga, speed lines, smear frames, illustration, game CG, plastic
skin, over-sharp HDR; face-swap or generic AI faces" (#26) — a **fixed anti-slop string** reused verbatim.

**Camera / optics** — "RED, custom Leica lenses, vintage 2x anamorphic — vertical oval bokeh, cat-eye edges,
out-of-focus highlights smeared horizontally, subtle chromatic aberration, soft vignette. Clean coating: no flares,
no light streaks, no starbursts." (#26) · "violently unsteady and handheld — the frame lurches, the horizon rolls
and never levels, focus is hunted by hand, impacts punch the image, grit on the glass" (#29) ·
"Locked off, or a slow mechanical push; the camera physically travels, never zooms" (brief) ·
"Fight Club / Fincher–Cronenweth grade: cold teal exterior, crushed blacks, fine 35mm grain" (#51).

**Light** — "GRADE: warm golden Afghan memory — honey-and-sand palette, creamy gold sunlight, dusty tan and khaki,
16mm texture, fine grain, gentle halation. Low saturation." (#26) · "Two-temperature Titans/Fight Club grade:
teal-green shadows, dirty amber-yellow paper, no clean whites, murky crushed blacks" (#98) ·
"One faint cold catchlight in each eye so the eyes stay alive and readable — that is the only highlight allowed
on him" (#51).

**Motion / physics** — "NORMAL SPEED throughout, no slow motion, no speed ramps, no zooms" (#29) ·
"The rifle is SHOULDERED, stock into the pocket, cheek near the stock, eyes over the sights. The muzzle leads
wherever the man is looking" (#26) · "They move in bounds, not in a continuous stream: one man moves while the
others hold and cover" (#26).

**Sound** — "SOUND: controlled breathing, boots rolling on mud steps, plate carriers and leather, gear knocking
once and being stilled, grit falling, the muffled hollow of the stairwell… No music." (#26) ·
"one hard scrape of shoes on floorboards, the lamp going over, the flat click of the switch… No music, no
stinger, no whoosh." (#51).

**Acting** — "ACTING: don't play emotion, play the execution of tactics; the work is in the eyes. Safety line:
gaze always engaged, natural blinking." (#26) · "motive: … / Goal: … / Tactic: …" triads in `ACTING TASK` (#26, #51) ·
"underplay everything. Faces slack from the eyebrows down, no scowls, no widened eyes, no gasps" (`brief_text.txt:4091-4098`).

**Story / continuity** — "This film's rule: two timelines that never share a look" (`brief_text.txt:251`) ·
"Jack in the diner and Jack on the Kabul roof are different assets of the same man" (`brief_text.txt:884`).

## 5. Structure & story
- 515.903 s over **6 scenes**, two interleaved timelines:
  present-day diner (`SCENE 01 KILLER'S WORK` 443 items, `02 CAR ARRIVES` 32, `03 SNIPER WATCHING` 818,
  `04 SNIPER'S REACTION` 291) and the Afghanistan flashback (`SCENE 06 WAR FLASHBACK` 879), plus
  `SCENE 05 CREDITS` 341 as a *story* scene (the guest-check book is the ending).
- Runtime budget: 8:36 over 6 scenes ≈ 86 s/scene, but the scene item counts show where the work went —
  SNIPER WATCHING + WAR FLASHBACK = 1,697 of 2,804 scene items (61%).
- **An episode is the whole film** (`featured_episode_slug: the-trigger/full-film`); no series relation is exposed.
- Stated story rules: the brief frames the film as two timelines that never share a look (`brief_text.txt:251`);
  the read comes first — "the read is what the prompts are then written from. The camera language, the grade and
  the sound follow it; they never lead it" (`brief_text.txt:578`).
- The ending is designed as a **typographic scene**: 8 pages, 7 torn away, 1 left, one 30-second set-up (#101).

## 6. Per-case hard rules
- **Rank the references and say what each one owns**: `1: … = JACK. 2: … = TERRENCE. Faces, kit and weapons
  decided by their own assets alone. … No other reference is used.` (#29).
- **State the precedence rule**: "If any instruction pulls a face off the reference, drop the instruction and
  keep the face." (#26).
- **Duration first**: every prompt opens with `Duration: Ns.` or `SHOT — <NAME>, N SECONDS` (34 + 9 rows).
- **One shot per prompt unless a cut is explicitly written** — 0 `HARD CUT` tokens in 98 prompts; the edit happens outside.
- **Bind geometry to the frame, not to the object**: "'The left side of the gun' is read as frame-left… Rewritten
  as 'the near side facing camera', it behaved." (`brief_text.txt:2497-2504`).
- **One reaction per beat**: "React, glance away, react again is the default the model reaches for, and it kills
  the moment. State the reaction once, then movement." (`brief_text.txt:2520-2527`).
- **Scale by cues, not measurements**: "Car roofs seen from above, the tops of stoop steps, foreshortened
  figures — that is how altitude reads. Metres do nothing." (`brief_text.txt:2543-2551`).
- **Countable events need proof**: "One flash equals one rocket, with the emptied tubes visible; otherwise the
  model fires nine rockets from four tubes." (`brief_text.txt:2567-2574`).
- **Physics beat sequences, not state lists**: "A man hit reads dead only if he falls as dead weight — head
  first, asymmetric shoulders, a knee folding inward, a glove dragging. A list of states reads as a robot."
  (`brief_text.txt:2590-2598`).
- **Vary size and angle every shot**, and **never repeat a set-up** (`brief_text.txt:2614`; the credits prompt
  asserts "ONE SET-UP FOR ALL THIRTY SECONDS" as the deliberate exception, #101).
- **Always write the anti-slop string** ("no anime, no illustration, no game CG, no plastic skin") — 33 rows.
- **No music, ever, in this film** — 51 rows; and the diner is diegetically music-free by店规 (#76: "这家店不放音乐").

## 7. Numbers
- Runtime 515.903 s = 8:36; 5,429 generations; 1,086 likes / 135,080 views (`stats.json`).
- Prompt rows 125 → **39 distinct** (35 video + 4 image). 86 duplicate rows; largest batch 13 identical rows.
- Video chars: min 689 / median **6,101** / p90 9,134 / max **9,134**. Image chars: min 1,109 / median 1,159 / max 1,597.
- Refs per video prompt: min 0 / median **5** / max **14**; 610 `{{…}}` handles (lowest per-prompt ref count of
  the four cases — this film leans on rank + prose, not on a large reference board).
- Shots per video prompt: **EN 71 rows — 1 shot ×47, 2 shots ×24 (avg 1.34); CN 28 rows — avg 8.14
  (7–15 shots each); overall 323 shots over 99 prompts (avg 3.26)**. The EN half is the single-take corpus,
  the CN half is the on-paper re-cut.
- Timing: **471 clock ranges / 77 rows**; 34 `Duration: Ns.` + 9 `SHOT — …, N SECONDS` headers;
  stated values 5 s ×26, 30 s ×8 (+ 10 s ×6, 5 s ×3 from headers); CN totals 20 s ×12, 22.5 s ×7, 23.7 s ×3.
- Cuts: 0 `HARD CUT`, 3 `CUT TO`, 0 `SEG1/SEG2`.
- Language split: 70 EN video rows (median 6,576 chars) vs 28 CN video rows (7–15 shots each).
- `FORBIDDEN` share: 71,963 chars over 60 rows = **11.8%** of all prompt characters.
- Aspect: 2.39:1 stated in 56 rows; UI aspect param on 125/125.
- Credits/min: UNKNOWN (`stats.json` carries no `credits_spent`).

## 8. Failure modes named in this case
- **The named-failure doctrine** — the brief's rules are introduced as scars: "The iron rules of this film…
  **These were all learned by generating the wrong thing first.**" (`brief_text.txt:2430-2445`).
- **Naming a negative summons it**: "The word 'American' put a flag on a sleeve; writing 'no flag' put it back."
  (`brief_text.txt:2481`).
- **Frame-relative ambiguity**: "the ammunition belt appeared on both sides twice" until rewritten as
  "the near side facing camera" (`brief_text.txt:2504`).
- **Reaction stacking**: "React, glance away, react again… kills the moment" (`brief_text.txt:2527`).
- **Metric measurements don't read**: "Metres do nothing" (`brief_text.txt:2551`).
- **Unproven countable events**: nine rockets from four tubes (`brief_text.txt:2574`).
- **State lists read as robots**: "A list of states reads as a robot" (`brief_text.txt:2598`).
- **Machine-gun confabulation** — the single most repeated guard in the corpus:
  "NO MACHINE GUN AND NO MACHINE GUNNER, no belt-fed weapon, no ammunition belts" (#29, #36).
- **Goggles pushed up / bare-headed soldiers** — a whole paragraph of guards (#29), plus `FORBIDDEN` restatement (#36).
- **Reloading that shouldn't happen** — "Jack or Terrence cycling the bolt, working the action, reloading,
  changing magazines, lifting their heads, coming off the scope… at any point — they fire once each and stay
  exactly as they are" (#29).
- **AI-face / anime drift** — the anti-slop string (33 rows) plus "face-swap or generic AI faces" (#26).
- **Sleepy eyes** — "No sleepy eyes, no heavy or drooping eyelids… no slow blinking, no glazed or unfocused stare,
  no thousand-yard stare" (#51).
- **Re-typeset text** — "Do not re-typeset, re-render, re-letter, re-space, re-spell, re-size, re-align, translate,
  correct, tidy or restyle any of that text" (#101).

## 9. Anything weird / low quality
- **86 of 125 rows are exact duplicates** — the "125 prompts" is really 39 texts; e.g. one prop reference appears
  13× (#1,2,3,17–21) and one flashback prompt 6× (#35,37,41,43,45,49). Read §7's distinct counts, not row counts.
- **Folder tree is inconsistent**: `subfolders_count: 8` but 7 L1 children are listed; `SCENE 01` lists 1 sub
  folder while the collection is flat otherwise.
- **`#55` is a `cinematic_studio_3_0` row (698 chars, Chinese, 1280×720)** — a one-off UI path inside an otherwise
  pure `seedance_2_5` film; it is the same 5-second shot as #54/#56 in a different model/language.
- **Rows reference `{{ref 7}}` while the prompt only ranks `image_1`–`image_6`** in the credits prompt (#101
  line "` {{ref 7}}= PAGE 4" — note the leading space and missing space before `=`), a copy-paste artefact.
- **Brief line numbering is unstable**: `brief_text.txt` is a raw Lexical dump; lone `\r` bytes mean a plain
  editor may split lines differently from `/\r?\n/`. Quote + line number together when citing.
- `publication.json` text is double-encoded (`[mojibake: “—”]`); quotes repaired here.
- **The doctrine and the artefact disagree**: the brief says don't write what you avoid, the prompts carry the
  largest negative blocks in the corpus. Reported as observed; not reconciled by any file in the harvest.

---

## 10. Cross-case note — how much does the template vary with runtime?

TRIGGER (8:36) splits its own corpus: the **EN prompts are the single-take case** (1.34 shots/prompt, 0
`HARD CUT`, 471 clock ranges) while the **CN rewrites of the same scenes average 8.14 shots/prompt**. It buys
coverage by generating 5/10/22.5/30-second whole takes and cutting them in the edit; oneiric (2.99 shots/prompt)
and kok-boru (3.88) build the cuts *inside* the prompt. So the runtime→template relation is not "longer film =
longer prompt" (trigger's median 6,101 chars is *below* both oneiric's 9,027 and kok-boru's 9,238) — it is
**"where does the edit live?"**. Trigger's EN lane answers: outside the prompt. Its CN lane answers: inside,
as a 7–15 item shot list. Kok-boru, at 20 s, answers: inside, in a rigid 8-block skeleton. Oneiric answers:
inside, in 12–15 blocks with per-segment timecodes.

What stays constant across a 20-second carousel and a 20-minute film, from the same studio family: a
**style/identity block first**, **references with an explicit precedence order**, **duration stated up front**,
and **one block that enumerates the colour palette numerically or as an accent doctrine**. What changes is
(a) whether the cut lives in the prompt, (b) whether the control surface is positive (oneiric/zephyr) or
negative (trigger/kok-boru), and (c) whether the shot list is ordinal (`SHOT 1…n`, kok-boru) or clocked
(`0.0–1.5s`, trigger). Note the oddity worth flagging to the skill: trigger is the most *negative* prompt
template in the corpus produced by the studio that wrote "say what is there, not what you avoid".

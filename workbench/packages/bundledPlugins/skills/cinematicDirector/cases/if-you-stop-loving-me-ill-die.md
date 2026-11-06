# CASE DIGEST — IF YOU STOP LOVING ME, I'LL DIE

## 0. Header

- **Title**: `If you stop loving me, I'll die — I don't like dying, but for our love I'm ready to go that far` · **type**: `film` · **runtime**: `281.833333 s` (4:42) · `publication.json`
- **Author**: `@higgsfield.studio` · **publication_id**: `7df43eb6-fae6-4c0d-8f8d-f5b2245e602b` · **snapshot_folder_id**: `14e56656-a977-44c6-bc55-0eecd3fb26bc`
- **generations_count**: `4,202`; `stats.json`: likes `607`, views `80,351` (highest like-rate of my four cases)
- **categories**: `["banner","spotlight"]`; `is_featured: true`
- **Working title / folder name**: `Tonic Immobility` (`folder_tree.json`) — the film is published under a different name. Brief: "Inside the project and across all assets the film goes by a shorter name" (`brief_text.txt:4922`).
- **Provenance**: `/fnf/project-publications/…`, `…/stats`, `/fnf/folders/{snapshot_folder_id}` (+`/children`), `/fnf/folders/{id}/items/v2` → `prompts.jsonl`; brief snapshot → `brief.bin`/`brief_text.txt`. `_summary.json` confirms `l1 = ["Development","PT-1","PT-2","PT-3"]`. `brief_assets.json` has **no** doc URLs (unlike passport-rush) — no PDF/skill assets harvested.
- **Premise** (`publication.json.description`): "If You Stop Loving Me I'll Die…: A deadpan silent animated comedy about love, blackmail and, above all, death. Tolik has exactly one talent: dying. Any refusal, however small, kills him on the spot — and he revives the moment he gets his way. His wife has been resurrecting him for years, until one morning she packs a suitcase and walks out. Now it's just him, a dripping tap nobody's going to fix, and a neighbour knocking at the door."
- Format facts the brief states: "**4:3 frame**. In Higgsfield's 4K mode our clips came out at **3326 × 2494 px**, with no upscaling on our side. The animation runs **on twos**: each phase is held for two frames… This is done in post, not requested from the model." (`brief_text.txt:5023-5038`). "Not a single line of dialogue: everything rests on action, rhythm and sound." (`:5000`). "three parts, five scenes, around twenty-five shots, including the title card" (`:5060`).

## 1. Production shape

- **Root children** (4 present; `subfolders_count: 7` — discrepancy, §9):

| folder | count | subs | content (from prompts) |
|---|---|---|---|
| `Development` | 1,627 | 6 | `Animation_test` 212, `Characters_test` 289, `Locations_test` 680, `Props` 132, `Scenes_Test` 226, `Stills_test` 88 — pure R&D lane |
| `PT-1` | 1,842 | 4 | `sc0 - title` 24, `sc1` 909, `sc2` 775, `sc3` 134 → the wife + the dripping tap |
| `PT-2` | 224 | 4 | `4-1`, `4-2`, `4-3 (cooking)`, `4-4` → Tolik alone with the soup |
| `PT-3` | 335 | 9 | `5-1…5-9b` → the neighbour hauls the dead man up |

  `PT-*` — the meaning of the prefix is **not stated anywhere in the harvest (UNKNOWN)**; content-wise the folders are keyed to *scene numbers* (`sc1`, `4-3 (cooking)`, `5-9b`), so read `PT` as "part/passthrough" only as a hypothesis. The tree also carries sibling letter variants (`5-9` vs `5-9b`) and one non-ASCII folder name `5-5邪` ("evil") — editorial intent lives in the folder names, not in metadata.
- **Source of truth**: `Development/*_test` (the look was *decided* there) + the `sc`-numbered folders (shot identity). The `Development` folder holds 39 % of all items but contributes exactly **1** prompt row — i.e. asset exploration dwarfs shot rendering here.
- **`job_set_type`**: `seedance_2_0` **64**, `minimax_h3` **34**, `seedance_2_5` 2. This is a *three-engine* film — and the split is by technical job, not by sequence:
  - `seedance_2_0` = main engine, 2880×2160 (55) and 1440×1080 (9);
  - `minimax_h3` = 2048×1536, used where Seedance pushed flat characters into volume;
  - `seedance_2_5` = 960×720, 2 rows only (long-take experimentation, `prompts.jsonl#13,18`).
- **Resolution/aspect**: 4:3 in every single row — `2880x2160` 55, `2048x1536` 34, `1440x1080` 9, `960x720` 2. Not one 16:9 row except three prompts whose *text* says 16:9 (§9).
- **`job_set_client_meta`**: **null in all 100 rows**. No staging metadata; the batch structure is visible only via duplicate clusters.
- Time span: 2026-07-21 → 2026-08-19. The July rows (ROOT, 07-21…08-10) are a **conventional 3D "Poor Soviet-era kitchen"** concept; the August rows (PT-1/2/3, 08-18/19) are the final **hand-painted 2D over 3D** look. The brief documents the switch; the prompts show it as a hard break.

## 2. Prompt anatomy — the actual grammar

**23 distinct block signatures / 100 rows, two dialects, one of them narrative.**

**Dialect A — "engine order" template** (early, 2.0): `SCENE CONTEXT → ACTIVE REFERENCES → FORMAT MODE → OPTICS → FIRST FRAME / BLOCKING → ACTION TIMING → LAYERS → LIGHTING → AUDIO → POSITIVE LOCKS → STYLE` (17 rows; e.g. `prompts.jsonl#0-8`). This matches the brief's stated canonical layer order (`brief_text.txt:1156`): "style → context → location → first frame → optics → camera → timing → overlaps → lighting → audio → locks".

**Dialect B — narrative/painterly template** (late, MiniMax + 2.0 mixed-media): `THE IMAGES → WHAT WE SEE OF HER → THE WIGGLE — THREE DRAWINGS → HER SHADOW ON THE FLOOR → HOW THE WATER IS MADE → WHAT HAPPENS → SHE IS A PAINTING ON GLASS → WHAT HOLDS → HOW IT MOVES → SOUND` (rows 28-49). **These headers are unique to this case in the whole corpus** and are sentences, not labels:
- `THE IMAGES` 35 · `WHAT HAPPENS` 35 · `HOW IT MOVES` 35 · `WHAT HOLDS` 33 · `THE WIGGLE — THREE DRAWINGS` 19 · `WHAT WE SEE OF HER` 19 · `SHE IS A PAINTING ON GLASS` 22 · `HER SHADOW ON THE FLOOR` 13 · `HOW THE WATER IS MADE` 18 · `WHAT SHE IS DOING AND WHY` 12 · `HOW SHE MOVES` 12 · `HOW HE LIES` 6 · `THE NEIGHBOUR` 6 · `THE PUSH IN` 3 · `HOW HE HANGS` 3.
- Conventional blocks still present where needed: `STYLE` 51, `ACTIVE REFERENCES` 38, `SOUND` 38, `AUDIO` 35, `POSITIVE LOCKS` 35, `LIGHTING` 34, `SCENE CONTEXT` 26, `FIRST FRAME / BLOCKING` 25, `FORMAT MODE` 23, `ACTION TIMING` 23, `OPTICS` 22, `LAYERS` 20, `TIMING` 20.
- **Third micro-dialect**: markdown headings — `## MASTER INTENT`, `# ACTIVE REFERENCES`, `# FAILURE PREVENTION / NEGATIVE CONSTRAINTS`, `# MASTER POSITIVE LOCKS` — in one 16,211-char prompt duplicated twice (`prompts.jsonl#41,42`). This is the only prompt in my four cases with a `# FAILURE PREVENTION` block.
- **No slug line.** Prompts open with the *style sentence*, not a title: "Hand-drawn limited 2D animation over a stylized 3D-rendered kitchen, in the mixed-media manner of flat hand-painted 2D characters composited over a stylized 3D-rendered set: … 4:3, one continuous take, no cuts, locked camera." (`prompts.jsonl#28`).
- **Reference tagging**: `{{ref 1}}`-style aliases plus prose role assignment ("The first image is the exact opening frame and the whole set… The second image gives her paint and her build, not her pose… The third image gives one thing only — how tall she stands against this kitchen" `prompts.jsonl#28`). References are addressed as **ordinals in words** ("first/second/third image"); the median prompt uses 3 refs, max 12.
- **Segment/timing syntax**: no hard cuts anywhere (0 occurrences of `HARD CUT` in 100 rows). Timing is **beat-based and relative**: "1,1.7,2.9,3.6" style second markers (`prompts.jsonl#0`), "for a long beat then" (60), "from the first frame to the last" (96). The brief states the reason (`brief_text.txt:1223`): "second-by-second timecodes didn't hold on it" (for 2.0).
- **Aspect/duration inside the prompt**: 4:3 stated in nearly every prompt *as well as* in `params.width/height`; duration is almost never stated in the prompt (it lives in the UI — see §6), which is the opposite of passport-rush. Only `prompts.jsonl#41` states a hard duration ("12s KITCHEN LEAK ONER").

## 3. What this case does that the others may not

1. **Two optically contradictory materials in one generation, declared as such**: "Two materials share one frame and never mix optically: the background lives with its own light and shadows, the characters are stickers laid on top of the picture, their paint baked into the artwork." (`brief_text.txt:5113`). The whole pipeline exists to stop the model from unifying them: "In our tests the engines consistently leaned towards a volumetric reading of a character" (`:5196`).
2. **Performance is specified as a finite set of drawings, not as movement**: "HER HEAD HAS THREE DRAWINGS, AND THEY CARRY THE WHOLE PERFORMANCE … Her head is only ever one of three flat drawings, each held completely still and each replaced by the next in a single step." (`prompts.jsonl#28`). Plus a *body* set: "There are three drawings of her body and only three." and an irregular loop order — "one, three, one, two, three, one, three, two — coming back to the two side drawings more often than to the middle one" (`prompts.jsonl#28`). This is animation direction written as a pose deck.
3. **Body mechanics are deliberately NOT described** — the single most counter-intuitive rule in my four cases: "on this film we stopped describing body mechanics in prompts altogether: movement is set by a logline, the model works out the rest itself, and its default turned out to be closer to what we wanted than our micro-direction." (`brief_text.txt:2743`).
4. **Negative phrasing is banned by policy; every prohibition is rewritten as a positive**: "the forbidden thing turned up in frame about as often as it disappeared. Everything is translated into the positive" (`brief_text.txt:2780`). Observed practice is **not** literally negation-free: with one consistent regex over all four of my cases (case-insensitive `no|not|never|without|do not|绝对禁止|禁止|绝不|不要`) this case sits mid-pack — median **14** tokens per prompt, max 105 — below passport-rush (26 / 110), above red-flag (12 / 36) and adiliada (6 / 54). The rule therefore governs *semantics* ("state what holds") rather than the count of negating words: `no zoom no pan` coexists with the affirmative lock style.
5. **References outrank words, and the fix is a new picture, not a new sentence**: "a visual reference almost always turned out to be stronger than a text instruction contradicting it: a conflict between picture and description was resolved by replacing the picture, not by adding words." (`brief_text.txt:3313`).
6. **Sound is a required prompt block with no music allowed**: "the engine reads it as 'soundtrack at my discretion' and once produced a dramatic accompaniment nobody asked for. So every prompt names a specific diegetic sound explicitly, and no room is left for music." (`brief_text.txt:4572`). `SOUND`/`AUDIO` appears in 73 of 100 prompts.
7. **Per-shot engine assignment is a craft decision**: 2.0 for the bulk; 2.5 "for complex micro-movements and long takes: it holds them far more reliably, but tends to complicate the action and add movement of its own" (MiniMax's niche: "where Seedance consistently pushed a flat character into volume, MiniMax handled it better", `brief_text.txt:5261-5283`).
8. **Grip discipline for anatomy**: "Gripping a hand or a forearm produces a stretched silhouette, a broken shoulder line and extra hands at the point of contact. Grip only a massive part: a collar, an ankle in a slipper, a trouser leg at the thigh." (`brief_text.txt:3291`).

## 4. Recurring phrasing bank

Counts = occurrences across 100 video prompts.

**Style / material**
- `flat hand-painted 2D characters composited over a stylized 3D-rendered set` **100** · `limited 2D animation on twos` 67 · `in the mixed-media manner of flat hand-painted 2D characters` 51 · `like flat hand-painted 2D characters composited` 46 · `flat hand-painted 2D gouache` 55 · `a stylized 3D-rendered kitchen` 52

**Camera**
- `camera holds one fixed position` 51 · `no zoom no pan` 47 · `one continuous take no cuts` 49 · `the flat plane of the picture` 59 · `movement stays inside the flat plane of the picture` 44

**Light**
- `daylight from the window on the right` 50/71 · `the window on the right` 71 · `on glass in front of` 44 · `lighting` block in 34 prompts

**Motion / staging**
- `from the first frame to the last` 96 · `for the whole shot` 94 · `for a long beat` 88 · `the pose holds completely still` 54 · `still for a long beat` 52 · `head is only ever` 52 · `in the same places` 56 · `at the same size` 55 · `come from the blocking below` 45

**Performance / story**
- `the back of her head` 49 · `with her back to` 50 · `at the kitchen table` 49 · `away from the camera` 47

**Audio (from the SOUND/AUDIO blocks)**: diegetic-only lists naming the tap drip, the radio, the spoon in borscht, the suitcase zip — e.g. the standing rule "no music" plus one named sound per beat.

## 5. Structure & story

- **Three acts, five scenes, ~25 shots** (`brief_text.txt:5060`); acts named "Breakfast", "Alone", "The Neighbour"; four characters — "the wife, the husband, the neighbour and the Tap which in this film is a character in its own right" (`:5166`).
- **Runtime budget methodology is explicit**: "Running time at 24 fps, beat lengths in multiples of two frames. The first scene is laid out as **fifteen beats totalling 41 seconds**, and the same table shows the budget: **about seventy seconds of generation for forty-one seconds of screen time, a ratio of 1.7**" (`brief_text.txt:3063`).
- **Rhythm is written before the prompts**: "Rhythm is written before the prompts… The first cycle with the yolk runs slowly — this is where the film's rule is established; the second, with the beer, is half as long, because there is nothing left to explain. Then the metronome stops" (`brief_text.txt:3091-3099`).
- **Duration honesty**: "Extended clips consistently came out about 0.5 s shorter than requested, so the duration is set about half a second longer or an extra tail is left for the edit." (`:3151`).
- **Continuation chain** is the edit's gluing device: "the last frame of the previous one becomes the first frame of the next" (`:3479`), and the joins are then matched in the timeline (`:3532, 3547`).
- No dialogue, no subtitles; single `film` (not a series).

## 6. Per-case hard rules

- **Duration must be set in the UI to what the shot needs** — never left at default: "with six seconds planned and fifteen set in the interface, it improvises for nine seconds with no script and that is exactly where the deformations appear" (`brief_text.txt:3040-3041`).
- **Every prompt carries four things**: "the style line, references, action, sound" (`brief_text.txt:277`).
- **One locked camera per long take; every object present from the first frame; mandatory take selection** (`brief_text.txt:1269`).
- **No negative phrasing** — translate to positive (`:2780`).
- **Don't describe body mechanics** — set movement with a logline (`:2743`).
- **Grip only massive parts** (`:3291`).
- **Don't add seconds to fix a broken run**: "If the action goes wrong in two takes out of three, the prompt is not rewritten — the run is split in half. Adding seconds is pointless" (`brief_text.txt:3501-3502`).
- **Flatness must be held inside one generation** — "The whole frame comes out of Seedance in a single pass: characters and background are not assembled in layers." (`:5151`).
- **Ban volume in words and in staging** — "Phrases like 'zero 3D, no volume, no CGI shading' produced volumetric figures with a gouache texture. What worked was different: a frame where the flat characters already stand inside that very set." (`:5367-5382`).
- **Sound: name one specific diegetic sound; leave no room for music** (`:4572`).

## 7. Numbers

| metric | value |
|---|---|
| runtime | 281.833 s |
| prompt rows | 100 — **all video** (no plate lane in this harvest) |
| unique prompts | **37** (2.7 rows per prompt on average) |
| duplicated rows | 91 of 100; clusters up to **12×** (`prompts.jsonl#28,29,30,31,32,33,36,37,38,44,47,48` byte-identical) |
| prompt chars | min 1,398 · median **6,885** · max 16,211 |
| refs per prompt | median **3** · max 12 |
| hard cuts per prompt | **0** (one-take film) |
| aspect | 4:3 ×100 (`2880x2160` 55, `2048x1536` 34, `1440x1080` 9, `960x720` 2) |
| clip length | implicitly 4–12 s; the only explicit durations are internal beat markers and one "12s KITCHEN LEAK ONER" (`prompts.jsonl#41`) |
| generation budget (stated) | 70 s of generation per 41 s of screen, **ratio 1.7** |
| generations per finished second | 4,202 / 281.8 ≈ **14.9** (whole project) |
| shots | ~25 including title card; 5 scenes; 3 acts |
| attempts per shot | 3–12 visible re-runs of the identical prompt (batch size 4 pattern: 4× clusters recur 7 times) |

## 8. Failure modes named in this case

- **Volumetric drift on turns and body mechanics** — the central enemy (`brief_text.txt:5196-5197`); "almost always coincided with the character sliding into volumetric movement, and the flatness was lost" (`:2743`).
- **Negative prompts backfire** — "were unreliable: the forbidden thing turned up in frame about as often as it disappeared" (`:2780`).
- **Grip deformations** — stretched silhouette, broken shoulder line, extra hands (`:3291`).
- **Pose-reference background leaks into the shot** — "The background from a pose reference leaks into the shot." (`:4398`); "any detail left on the grey backing leaks into the shot" (`:4873`).
- **Detail binds to frame position instead of the body** — "Socks drawn differently on each leg bound themselves not to the leg but to its position in the frame, and jumped every time the step changed. Fixed by redrawing the sheet, not by prompting." (`:3904`).
- **Master-shot presentation leak** — the engine draws "from inside the maquette", with air instead of the fourth wall (`:3991`).
- **Model invents a score** when sound is unspecified (`:4572`).
- **"Flat and matte" produces paper** when describing water (`:4668`); **underwater reflections appear without a direct prohibition** (`:4690`).
- **Extra seconds get improvised** → deformations (`:3040-3041`).
- **Prompt length is not a lever**: "prompt length does not improve the result, it redistributes the risks" (`:270`).
- **Nothing works first try**: "across the whole film not a single prompt worked on the first try, so what gets reused is the frame and the specific locks that once closed a specific failure" (`:248`).

## 9. Anything weird / low quality

- `folder_tree.json`: `subfolders_count` = **7** but **4** children present; `root.count` 4,203 vs 4,028 in children → 175 root-level items (matches the 24 `ROOT`-tagged rows).
- **Aspect contradiction**: three prompts (`prompts.jsonl#22,23,49`, byte-identical, 1440×1080 = 4:3) contain the string `16:9`. The engine output stayed 4:3. Text-vs-params drift.
- **Massive duplication**: 37 unique prompts for 100 rows; the 12× cluster is one sheet rendered 12 times with no prompt change.
- **`Development` folder has 1,627 items and 1 prompt row** — the harvest sampled per folder, so the R&D lane is almost invisible in `prompts.jsonl`.
- Folder `5-5邪` (non-ASCII, "evil") and `5-9` vs `5-9b` siblings — editorial naming, harmless but noisy.
- The brief is a machine-translated Russian production article: artifacts like `EPrompt length`, `8Two different kinds of volume`, `_8Extended clips`, `Ss. In a still prompt…`; sentence fragments split across msgpack runs. All quotes above are from retained complete runs.
- Naming mismatch: published title contains a subtitle; folder is `Tonic Immobility`; brief calls the film "our animated short" (`:4922`).
- No skill `.md`/`.pdf` assets were harvested (`brief_assets.json` empty) even though the brief repeatedly describes internal SKILL files ("a skill here means a set of rules and methods that Claude loads into its work", `:5336`) → skill text itself: **UNKNOWN**.

## 10. Cross-case note — does the prompt template change with genre?

- **Skeleton holds, vocabulary mutates.** The same eight slots (context → references → camera → timing → materials/physics → light → sound → locks) appear in all four of my cases, but this one renames almost every slot into a narrative clause (`WHAT HOLDS`, `HOW IT MOVES`, `SHE IS A PAINTING ON GLASS`). Romance/performance genre ⇒ **the block names become the acting direction**.
- **Not a polarity outlier by measurement — an outlier by *structure*.** This case has **no separate ban block at all**: every constraint lives inside the descriptive blocks, and there is no `POSITIVE LOCKS`-only stop-list, no film-wide forbidden section. Structure across my four cases: passport-rush = inline `POSITIVE CONSTRAINTS (LOCKS)` mega-paragraphs; red-flag = film-wide `■ 全片禁止` **plus** per-segment `【FORBIDDEN】`; adiliada = one `# FAILURE PREVENTION / NEGATIVE CONSTRAINTS` heading plus `do not` clauses in the plate lane; this film = prohibitions invisible (folded into prose). Measured negation density is mid-pack (median 14 tokens/prompt), so the genre marker is *where the prohibitions live*, not how many there are.
- **Physics slot is replaced, not deleted**: passport-rush writes tyre/weight-transfer physics; red-flag writes door-hinge/lock physics; this film writes *drawing counts* ("three drawings and only three"). The slot's function — make the model's free parameters countable — is constant.
- **Runtime is not the driver.** 282 s here vs 288 s in passport-rush: same length, but this film runs 0 hard cuts and ~6.9 K-char prompts, passport-rush runs 2 cuts/prompt and ~10.4 K-char prompts. The difference is genre (deadpan one-take comedy vs slapstick chase), not duration.
- **Language**: English-only, but with a translation gloss — the only case whose prompt style is explicitly reasoned about in prose ("we wrote X and got Y").

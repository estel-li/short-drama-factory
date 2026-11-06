# CASE — `cully-hill-boys` · THE CULLY HILL BOYS (Higgsfield Studio, 2026)

**The flagship case: a 115-minute feature generated entirely in Seedance.** Full detail lives in
`_analysis/B_cully_brief.md` (the studio's own methodology, from the brief) and
`_analysis/C_cully_prompt_grammar.md` (the prompt anatomy, from 350 real prompts). This file is the
digest; every non-obvious claim below carries the locator used in those two documents.

---

## 0. Header

| field | value |
| --- | --- |
| Title | The Cully Hill Boys (`name` "Cully Hill Boys") |
| Type | `film`, featured, single publication |
| Runtime | **1:54:49** (`duration_seconds` 6888.896); brief says "1 hour 54 minutes" (`brief_text.txt:527`) |
| Author | `@higgsfield.studio` / "Higgsfield Studio" |
| `publication_id` | `0efa70c1-07ec-410a-813b-8629502a7de3` (= `project_id`) |
| `snapshot_folder_id` | `b619c13c-83ba-4ea3-b85c-de9be41bd01b` |
| `generations_count` | **473,214** (`stats.json`; folder-tree subsets sum to 473,039) |
| Views / likes | 323,369 / 1,390 (`stats.json`) |
| Published | 2026-08-10; premiere New York 2026-08-05 (`brief_text.txt:527`) |
| Provenance | `/fnf/project-publications/higgsfield.studio/cully-hill-boys`; `/fnf/folders/…` (items v2, 50/folder cap); `dam-editor-worker…/brief/{folder}/snapshot` → `brief.bin` → `brief_text.txt`; 3× `.md` skills from cloudfront |
| Premise (quote) | *"The Cully Hill Boys is an action-comedy that follows three underachieving London rappers who, in an attempt to make a name for themselves, accidentally get caught in a messy drug war. A fast, funny, beat-driven crime movie about loyalty, friendship, and refusing to stay invisible."* (`publication.json.description`) |
| Setting | South-East London, **2011**, late September (`brief_text.txt:700`) |
| Cast | real, likeness-licensed: Cal = Matt Kiatipis, Oli = Israel Adesanya, Horace = N3on 1, Tobin = Quinton "Rampage" Jackson (`brief_text.txt:740`) |

**The one-sentence thesis of this case:** it is not a film made of lucky generations — it is a film made
of *locked assets + a frozen prompt grammar + a version log*, and the numbers prove the discipline
(473k generations, 137 scenes, ~600 approved assets, 1 re-shoot bucket of 562).

---

## 1. Production shape

**Folder taxonomy** (`folder_tree.json`) — 7 top-level folders, generations in brackets:

```
Cully Hill Boys (root)
├ 0 Regenerations                [   562]  the deliberate re-shoot bucket
├ 1 ACT (1-49)                   [146,471]  36 scene subfolders ("05 scene", "18 scene" …)
├ 2 ACT (50-93)                  [140,693]  28 subfolders, often paired ("56-57 scene")
├ 3 ACT (93-120)                 [125,007]  14 subfolders ("98-99-100", "103-108")
├ 4ACT_Epilogue (121-137)        [ 25,918]  13 subfolders + an "assets" folder
└ PRE  PROD                      [ 34,388]  10 subfolders: ASSETS 12,021 · Costumes 5,960 ·
                                             Character Test 611 · CLEAN UP 187 · Test_scene16 68 ·
                                             Test_v1 375 · Test_v2 149 · Test_v3 3,667 ·
                                             Test_v4 7,257 · Test_v5 3,416
```

What the naming tells us:

- **Act folders are keyed to the film's own scene numbering** ("1 ACT (1-49)") — the folder *is* the
  shotlist, in film order. This is the brief's rule: *"Work runs in scene blocks, in the order of the
  film, each block in its own shotlist file."* (`brief_text.txt:13487`)
- **`PRE  PROD` holds the entire asset economy** and, crucially, **five sequential test rounds**
  `Test_v1 → Test_v5`. Test_v5 (3,416) is the survivor; v2 (149) is a dead end. The stress-test rule in
  the brief ("ten generations, recognisable in ten out of ten") is visible here as 5 versions.
- **`0 Regenerations` is separate and tiny (562)** — re-shoots were treated as an exception with their
  own bucket, not smeared into the acts.
- "assets" appears as a folder even inside the Epilogue (869) — assets were built per-need, not only up
  front, but always as assets, never as one-off prompts.

**Source of truth = the canvas**, stated: *"The canvas is the source of truth on the project: if an
asset is not there, it is not in a shot either."* (`brief_text.txt:473`)

**Models / parameters observed** (`prompts.jsonl`, 350 rows sampled at 50 per folder):

| `job_set_type` | rows | role |
| --- | --- | --- |
| `seedance_2_0` | 200 | production video |
| `seedance_2_5` | 100 | controlled model-comparison pass: 53 distinct scenes re-run from their saved 2.0 prompts (`job_set_client_meta.seedance25_comparison`) |
| `seedream_v4_5` | 36 | image: location plates / sheets |
| `gpt_image_2` | 8 | image edit (some instructions in **Russian**) |
| `nano_banana_2` | 6 | image edit / upres |

`aspect_ratio`: **21:9 = 314/350**, 16:9 16, 3:4 12, 1:1 6, 4:3 2. Rasters: 2016×864 (224) → 6048×2592
(12). `resolution`: 1080p 145 · 720p 100 · 4k 69. `duration`: 15 s (130) · 8 s (32) · 12 s (27) · 14 s
(24) · 10 s (22) … **`multi_shots: false` in all 300 video rows** — every multi-cut prompt is a *single*
generation with internal hard cuts. `generate_audio: true` in 297. `prompt_language: "en"` in all 300 —
**including the 90 Chinese prompts**, so that field is unreliable.

**`job_set_client_meta` decoded** — 250/350 rows are `{}`; the 100 `seedance_2_5` rows carry
`seedance25_comparison:{act, scene, attempt, source_job_id, source_job_set_id,
source_manifest_sha256, execution_run_id, target_folder_id}`. This is a **reproducibility harness**, not
creative metadata: same prompt, new model, with source job + prompt-set hash + run id
(`cully-seedance25-clean-folder-20260807T0915Z`) recorded so the comparison is auditable.

---

## 2. Prompt anatomy — the actual grammar

**Block headers, observed order** (avg position in the prompt that use them, English video, n=210;
counts = prompts using the block out of 300 video prompts):

`REFERENCE MAPPING` (50) → `SCENE CONTEXT` (250) → `ACTIVE REFERENCES` (123) / `REFERENCES` (24) →
`LOCATION MAP` (129) → `FIRST FRAME AND SPATIAL BLOCKING` (112) → `FORMAT MODE` (136) →
`OPTICS` (138) → `CAMERA` (142) → `STYLE` (153) → `ACTION TIMING` (169) → `PHYSICS` (147) →
`LIGHTING` (184) → `AUDIO` (261) → `QUALITY` (122) → `POSITIVE CONSTRAINTS` (52) /
`POSITIVE LOCKS` (83).

Rare/scene-specific blocks worth knowing: `DEEP-NIGHT EXPOSURE LOCK`, `CROWD AND PERIOD LIFE`,
`FINAL FRAME`, `CONTINUITY LOCKS`, `CHARACTER ACTING`, `PERFORMANCE / PHYSICS`, `THE UNINTERRUPTED TAKE`,
`GEOGRAPHY`, `LENS LOCK`, `THE BREACH`. 99 distinct strings in total.

- **`AUDIO` (87 %) is the only near-universal block** — more common than `SCENE CONTEXT` (83 %). The one
  thing never omitted is the sound directive.
- The order matches the attached CINEDANCE skill's 12-section architecture
  (`skills/7a900bd1-…md:163–176`) with `STYLE` + `QUALITY` inserted between `PHYSICS` and `AUDIO`.
  Adjacency is near-deterministic: `OPTICS→CAMERA` 135, `LIGHTING→AUDIO` 144, `STYLE→QUALITY` 122,
  `FORMAT MODE→OPTICS` 115.

**Header/slug line — three formats, and the famous one is a minority:**

1. **Banner dialect** (3 full instances; the `HARVEST.md` example is this family):
   `CULLY HILL — SCENE 19A — CLIP 05  (v3 · systemnik v5)` / quoted director's note /
   `World: THE BOYS (Friends) · WARM PUB INTERIOR · Variant A · v5` / `Format: MULTISHOT · 4 cuts ·
   15s total` / `── STYLE PREFIX (Boys · Variant A · v5) ──` (`prompts.jsonl#82`).
   **`CULLY HILL — <number>` occurs 0 times in this sample** — do not build on it.
2. **No header at all** — the house default, **170/300** prompts open with the literal string
   `SCENE CONTEXT`; the scene id / INT-EXT / time of day live inside the first sentence:
   `Scene 123, INT. NIGHT — Alison's grand cream living room, the aftermath: … FOUR shots, HARD CUTS at
   0.5s / 3.5s / 6.5s, ~9.5 seconds total.` (`prompts.jsonl#0`)
3. **Slugline first** — 15/300: `INT. THE COMMONS GARAGE — DEEP NIGHT`, then `STYLE` in slot 1.

**Reference tagging** — `{{uuid}}`:

- **298/300 video prompts use tags**; median **11** per prompt, mean 13.4, p90 26, max 89 (`#80`).
  Chinese prompts carry *more* (median 13) than English (median 8) — density replaces block count.
- **Location is tagged FIRST**: `{{L}} — the LOCATION (tagged FIRST, controls all geometry, furniture,
  materials and practical light): … Camera angles are NOT inherited — the plate supplies the SET only.`
  (`#12`; 21 rows say "tagged FIRST" literally, 60 state the ownership in some form).
- **Location refs carry an explicit ban on inheritance** — geometry/materials/light yes, framing never:
  `Controls geography, materials and daylight only; not camera angle or story identity. 100% matches
  the reference.` (`#45`); `NOT framing or angle — LOCATION reference only, never a frame/composition
  reference: do not copy its …` (`#21`).
- **Characters carry an ownership sentence**: `100% matches the reference — THE REFERENCE OWNS THE FACE
  at every scale.` (170 rows use `100% match(es) the reference`; 21 add the face line; `#281` sharpens
  it: `…and the FACE ONLY: the reference does NOT set the camera`).
- **Acting is its own ref**, paired to the character ref: `{{C}} — CHARACTER ACTING: OFF-FRAME (in
  front, behind the camera) — never seen; only his deep, slow, weary, final voice delivering the
  order.` (`#45`)
- **Element names ride alongside**: `@char_CB_Tobin_v1_v1`, `@loc_CB_railway_tracks_s111_v5`,
  `@prop_CB_gunTobin_s26_v2` — the brief's naming format (`brief_text.txt:1542`), 5 rows.
- **Order**: location → leads in frame order → props → vehicles → interiors → off-frame/voice refs.
- Image prompts use placeholders instead: `{{ref 1}}` / `{{ref 2}}` (25/50 image prompts).

**Segment / cut / timing syntax actually used:**

| device | example | volume |
| --- | --- | --- |
| `N shots, HARD CUTS at a / b / c, ~Ts total` | `FOUR shots, HARD CUTS at 0.5s / 3.5s / 6.5s, ~9.5 seconds total` | `N shots` 85 (28 %); any `HARD CUT` 112 (37 %) |
| `SHOT n (~Xs): …` headlines in `SCENE CONTEXT` | `SHOT 1 (~0.5s): the same HIGH WIDE placement anchor…` | 29 (10 %); numbered `SHOT n`≥107 |
| `ACTION TIMING` absolute-second rows | `0.0–4.0s — INTERIOR REVERSE (35° / 35mm). … [BG: {{…}}]` | **173 (57.7 %)** |
| `BEAT n — TITLE` sections | `BEAT 1 — EMPTY ENTRANCE PATH` | 14 (4.7 %) |
| `SEG n` / `SEG1/SEG2` | `SEG 1 — TWO HALF-SECOND ESTABLISHES (0.0–1.0s)` | only 9 (3 %) — **legacy** |
| Chinese `段1/段2` + `（踩动作硬切）` | `0.0–5.0s 段1【纵深建立·蠕动缓推·微荷兰角】：…` | 90 zh prompts |

**Aspect / duration inside the prompt vs UI params:** aspect ratio is **never** in the prompt (0 rows),
duration *is* (as `~9.5 seconds`) and is also a UI param → **duplication, and it is intentional**: the
prompt paces the cut list, the UI enforces the cap. Flag for the skill: state the duration in the prompt
whenever there is more than one shot.

---

## 3. What this case does that the others do not

1. **Fifteen blocks, and literally no negative block.** The grammar has no `NEGATIVE` section at all —
   **0/300 prompts contain a `NEGATIVE …` line**, and the word "negative" appears only as the lighting
   term `true negative fill` (18/300). Every prohibition is rewritten as a positive inside the section
   that owns it: *"There is no negative block. A prohibition is written as the desired outcome inside the
   relevant section, because 'does NOT fall on his back' reads to the model as an invitation to think
   about falling on his back. Write 'falls on his stomach'."* (`brief_text.txt:2564`).
2. **A named style prefix per world, prepended to every shot.** Five worlds, each with a fixed
   `OPTICS → CAMERA → LIGHTING → STYLE → QUALITY` head: `STYLE PREFIX — WORLD OF DMITRY (Variant A ·
   Balabanov × Scorsese)` (`#51`), `VERNON CREW / British crime (Guy Ritchie × Refn)` (`#40`),
   `THE BOYS (Friends) · WARM PUB INTERIOR · Variant A · v5` (`#82`), `THE COMMONS · COLD DUSK GARAGE ·
   v5` (`#38`), `COMMONS-BACKSTAGE (v5 · cool-fluorescent variant)` (`#64`). This is the single most
   reusable structure in the corpus.
3. **Optics in degrees, off a named ladder, with outcome stacks.** `Optics is written in degrees, not
   millimeters, off a ladder of ten anchors: 180 / 135 / 107 … The native zone, 29, comes out reliably;
   past it the risk starts.` (`brief_text.txt:9892`). The skill bank supplies 107/84/47/29/18/8 with
   distances and requires "at least 4 observable phrases" for telephoto, "at least 3" for wide, because
   *"content decides the lens"* (`brief_text.txt:9911`). In practice: 47° used 101×, 29° 57×, 84° 44×.
4. **`ACTION TIMING` as an absolute-second table with sub-beats inside a row.** One row per shot, and
   inside the row `0.5–1.5s … 1.5–2.7s … 2.7–3.6s` beats — so a 6.5 s shot carries a three-beat
   performance inside a single generation (`#12`). `[BG: {{…}}]` re-invokes the plate per row.
5. **`60:30:10` executed as a physical object, not a grade.** *"The accent is not graded in — it is found
   as an object with a real source in the frame: a green door, a sodium lamp, an orange tent, the glow of
   a monitor."* (`brief_text.txt:2475`); 87/300 prompts write `60:30:10 — dominant / secondary / accent.`
   and then spell the three bands out in words.
6. **The ALIVE RULE** — the whole acting system compiled into one paste-ready paragraph: *"each person
   blinks naturally about once every 3–4 seconds of their screen time, at random unposed moments, never
   in sync with each other and never on a beat; everyone BREATHES visibly, intensity per state …"*
   (`#12`, `#45`, `#282`; 19/300). Together with *"the words nostalgic, jealous and sad appear nowhere
   in the prompt"* this is the case's acting doctrine.
7. **Music scenes built the other way round.** *"A video model will not perform your song."* → record the
   track first, cut it into ~12 s blocks on breaths, generate a black-picture video carrying the vocal,
   **switch the model's audio off** so the copyright check cannot block the take, lock the mouth to the
   waveform, lay the track under in the edit (`brief_text.txt:11877–11932`).
8. **A version log as a production artefact.** *"Every iteration was surgical: one line changes, the rest
   stays word for word. Everything goes into the log — version, what changed, verdict — 137 entries in
   our case"* (`brief_text.txt:13502`). The log is why "regenerate from the saved final prompt with one
   line changed" works (`brief_text.txt:13882`).

---

## 4. Recurring phrasing bank

**Exact repeated sentences** (video prompts; the corpus is a few dozen pinned blocks re-used 20–162×):

| freq | sentence |
| --- | --- |
| 162 | `100% matches the reference.` |
| 119 | `FIRST FRAME AND SPATIAL BLOCKING` *(block label used as a sentence boundary)* |
| 53 | `ARRI Alexa, vintage spherical primes, subtle anamorphic.` |
| 51 | `60:30:10 — dominant / secondary / accent.` |
| 50 | `THE COMMONS — RIVERSIDE SOUTH-EAST LONDON — BLUE HOUR, 2011.` |
| 50 | `Dark, atmospheric, socially alive and filmic.` |
| 50 | `ACTIVE REFERENCES（只放本镜实际用到的）` *(CN: "only what this shot actually uses")* |
| 44 | `{{ref}} controls location identity, architecture, geography, materials, lighting motivation and colour balance.` |
| 43 | `This prompt controls pose and performance.` |
| 42 | `100% matches the reference — THE REFERENCE OWNS THE FACE at every scale.` |
| 37 | `{{ref}} is the exclusive location reference for this shot.` |
| 37 | `Preserve the venue name THE COMMONS exactly as it appears on the existing facade signs — the only readable text; do not add, redesign or multiply signage.` |
| 37 | `One lens, no optical drift.` · `Vehicles unbranded and period-appropriate.` · `The blue-hour state from {{ref}} is locked.` |

**Camera / optics:** `locked off on sticks`, `tripod weight, no drift`, `SETTLE — controlled handheld
easing into a slow hold`, `calm breathing handheld`, `breath-level micro-sway only`, `restrained
shoulder-handheld breathing sway and natural operator corrections`, `one continuous face-side orbit`,
`a single motivated push-in`, `slow lateral pan at street level`, `rack focus`, `natural 180-degree
shutter`, `No cuts, no slow-motion`, `camera stays`, `never crosses behind him`, `One lens locked per
shot.`, `Lens locked.`, `85/107° wide rectilinear … straight lines stay straight, no fisheye`.

**Light:** `one motivated source per frame`, `true negative fill`, `never flat front light`, `tight cool
booklight wrap … fast falloff into deep shadow`, `practical light`, `cold fluorescent spill`, `sodium haze`,
`deep blue-hour blacks, controlled warm practicals`, `60:30:10`.

**Motion / physics:** `Honest scene mechanics`, `real weapon weight`, `real spring resistance`, `the
fabric reacts with weight and delayed swing`, `no ghosting, no duplicated limbs`, `no morphing`,
`no slow motion`, `real-time`, `one visible micro-event every one or two seconds`.

**Sound:** `Diegetic sound only, in this exact order:` + `- …;` bullet list, `No music.`,
`NO music score, NO slow-motion; diegetic sound only.`, `SFX only`, `low room tone`, `no subtitles`,
`VOICE ({{C}}, verbatim): "A 45-year-old English man. Deep, gravelly baritone with an East London
accent; slow, deliberate, and quietly authoritative delivery…"`.

**Acting:** `ALIVE RULE (everyone, every shot):`, `100% matches the reference — THE REFERENCE OWNS THE
FACE`, `his register:`, `eyes fixed`, `a slow unimpressed blink`, `never mirrored`, `a tired headshake and
the ghost of a fond smirk`, `behaviour rather than display`, `unspoken, never voiced, never subtitled`.

---

## 5. Structure & story

- **Acts keyed to scene numbers, not minutes**: Act 1 = scenes 1–49, Act 2 = 50–93, Act 3 = 93–120,
  Epilogue = 121–137 (`folder_tree.json`). 137 scenes in 115 minutes ≈ **50 s of screen time per scene**,
  which matches the generative limit: clips are ≤15 s and always cut internally.
- **Generation budget by act** (folder counts): Act1 146k · Act2 141k · Act3 125k · Epilogue 26k ·
  pre-prod 34k. The Epilogue is ~18 % of Act 1's spend — the film front-loads its action.
- **Story rules stated**: one bad day structure ending in a train; the epilogue is 17 scenes of
  aftermath (custody → national news) — the brief describes it as "two days later".
- Not a series/carousel — one `film` publication, no episodes (`publication.json`).

---

## 6. Per-case hard rules (only what this case evidences)

- **Assets first**: *"Not one shot until every character, location and prop is locked, named, versioned
  and stress-tested. This rule saves more money than everything else combined."* (`brief_text.txt:14010`)
- **An asset is text + image**, and the text goes into every prompt word for word (`brief_text.txt:1358`).
- **One asset per state**: clean Cal / wet Cal / bloodied Cal are three assets (`brief_text.txt:272`).
- **Empty hands on a character sheet** — every object is its own asset (`brief_text.txt:1492`).
- **No rim light / no "studio" / no "overhead key light"** on sheets — each bakes light into every later
  generation (`brief_text.txt:1492`).
- **A variant never overwrites**: new name, new version (`brief_text.txt:1525`).
- **Never test a hero before his location is ready** (`brief_text.txt:1793`).
- **Every tag exactly once, inside ACTIVE REFERENCES** — duplication is the top cause of a refused launch
  (`brief_text.txt:2579`).
- **Location refs own geometry, never framing** (`brief_text.txt:2579`).
- **One lens per shot; FOV changes only on the hard cuts** (`brief_text.txt:9911`).
- **Positions come from what is visible in the plate** — metres and "to the left of the hero" are
  meaningless; use landmarks + frame-left/right + which line the camera never crosses
  (`brief_text.txt:10818`).
- **Describe everything, every time — the model has no memory** (`brief_text.txt:14033`).
- **Change one thing at a time; one line per iteration; log it** (`brief_text.txt:14056`).
- **After 15–20 generations, change the shot, not the sentence** (`brief_text.txt:13552`).
- **Give the model less freedom**: a corner not a room, a landmark not open space, a map not guesswork
  (`brief_text.txt:14079`).
- **"SFX only. No music." is mandatory in every prompt** (`brief_text.txt:13938`).
- **Nothing in frame is newer than 2011**, repeated in every plate and prompt (`brief_text.txt:715`).
- **A rule becomes a law when it has a name, a visible proof in the frame, and a sentence stating what
  counts as a broken shot** — ~150 named locks, ~80 ending "= failed take" (`brief_text.txt:13689`).

---

## 7. Numbers

| metric | value |
| --- | --- |
| Runtime / scenes / assets / generations | 1:54:49 · 137 · ~600 · 473,214 |
| Generation spend by act | 146k / 141k / 125k / 26k (+34k pre-prod, 562 regen) |
| Video prompt length | median **9,748 chars / 1,472 words**; English median 11,153; p90 16,525; max 37,078 |
| Chinese prompt length | median 5,339 chars / 305 words |
| Image prompt length | median 1,273 chars |
| Blocks per prompt | median 10 (EN 13, CN 4) |
| Refs per prompt | median **11**, mean 13.4, max 89 |
| Cuts per prompt | 57.7 % use a timed cut table; `N shots` declared in 28 %; up to 6 cuts in one 15 s clip |
| Duration | 15 s cap, mode 15 s (130/300), median 14 s; music blocks ~12 s |
| Ref budget per generation | 9 images · 3 videos · 3 audio |
| Attempts per shot | a "give-up at 15–20" rule; log shows worst offenders v15 / v10 / v9; only 137 log entries for 137 scenes |
| Credits per minute | **UNKNOWN** — no cost/credit figure is stated anywhere in the harvest |
| Prompt size discipline | 8–12 KB is the working range; <3 KB rows are simple/legacy generations |

---

## 8. Failure modes this case names (→ negative constraints)

From the prompts (literal guards, counts of the 300 video prompts): `no modern tech beyond 2011` (50),
duplication guards — `duplicat*` (71), `ghosting` (56), `morphing` (12) — `no slow motion` (90),
`no subtitles` (59), `no music` (111), `the only readable text` (137 — signage must not multiply),
`never looks at the camera` (9), `never crosses behind him` (2), `the camera never compensates for
darkness` (3), `never passes through …` (51).

From the brief (34 named failures with fixes — the full table is in `B_cully_brief.md` §8): hero identity
drift · voices drifting between clips · heroes teleporting / camera jumping sides · face stable only while
calm · invented teeth on the first laugh · studio key light baked into every shot · edge glow dragging
light into every scene · props that cannot be dropped because they were born in the sheet · the model
dragging every shot toward the present day · near-copy of the location plate · duplicate tags refusing the
launch · prohibitions backfiring · lens sliding to a middle FOV · adjectives giving shallow acting ·
frozen frame on "nobody moves" · dead listener · wrong end of the pitch attacked from memory · door-break
frozen mid-timing · crowds collapsing past 15 people · duplicated props in motion · single-word emotions
arriving as caricature · scale drift · full prompt rewrites losing what worked · slop surviving to screen.

---

## 9. Anything weird / low quality

- **The corpus is a 50-per-folder sample, not the library.** 350 rows of a 473k-generation project. Any
  "this appears N times" statement is bounded by that cap — one scene family can own 50 identical
  sentences. State frequencies as "of the sample".
- **90/300 video prompts are Chinese** (all of Act 2, 30/50 of the Epilogue) while `prompt_language` says
  `en` for all of them. Bilingual residue includes Russian (`размашисто`, `профиль`, `фокус не меняем`)
  and the image-edit prompts are partly Russian — the prompt chats were multilingual.
- **`brief_text.txt` is a damaged extraction**: 169 KB of ASCII printable runs from a binary container;
  non-ASCII glyphs are deleted and every run boundary is a lost character. Prose is only ~42 KB of it;
  the rest is msgpack scaffolding, 13 asset-embed URLs/uuids and 9 tokenised code blocks. Raw quotes may
  contain stray `%`, `)`, `#` glyphs at paragraph heads.
- **`prompts.jsonl` contains a few truncated prompts**: `#257` is 56 chars (`animated this character
  {{ref 1}} in emotional scene`) — a UI stub, not a shot prompt. `#7` (333 chars) is a bare
  `SETTING:` note. Don't count these as the grammar.
- **The "fifteen-block skeleton" is a reconstruction**: the brief's list is split across a run boundary
  (`brief_text.txt:2535`), and the live prompts show 12–16 blocks with per-scene inventions, so exact 15
  is a nominal figure. Trust the observed order, not the count.
- **UNKNOWN**: the five full style-prefix texts, the ten FOV anchors in full (only 180/135/107 + 29
  survive in the brief), the visual bible document, the 137-entry version log, cost/credit figures.

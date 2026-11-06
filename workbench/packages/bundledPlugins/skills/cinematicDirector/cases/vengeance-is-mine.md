# VENGEANCE IS MINE — case digest

## 0. Header

- **Title** `Vengeance is mine` · **type** `film` · **runtime** 1598.92 s (26:39) · **author** `higgsfield.studio` · **featured_episode_slug** `vengeance-is-mine/full-film`
- **publication_id** `03b49f80-d877-4800-8f60-2dd6bea917f1` · **snapshot_folder_id** `281d5e38-39ab-460b-a97b-4b3b7edac9fd`
- **generations_count** 37,335 (root `count` 37,428) · **likes 7 · views 634** (`stats.json`) — the least-promoted case in the batch
- flags: `type=film`, `is_ongoing=false`, **`has_changes_since_publish=true`**, `show_prompts=true`, `show_canvas=true`, `categories=["spotlight"]`, `tags=[]`, `is_discoverable=false`, cover 1920×1080, gallery video 1664×1248/1598.9 s
- **Provenance** (`_summary.json`, `brief_assets.json`): `/fnf/project-publications/higgsfield.studio/vengeance-is-mine`; `/fnf/folders/281d5e38…` (+ `/children`); `/fnf/folders/{id}/items/v2` → `prompts.jsonl` (150 rows, 2,269,187 B per `prompts_meta.json`); `dam-editor-worker.higgsfield.ai/brief/281d5e38…/snapshot` → `brief.bin` → `brief_text.txt`; four `.md` assets from cloudfront → `skills/`, of which **`skills/a7ff619c-9740-4245-b518-e8349511ae20.md` is the project's own 106-line rulebook** (`name: vengeance-is-mine-rules`, "the director's hard rules — followed exactly, every prompt, every time") and the other three are the shared **CINEDANCE** (`2963a200…`, 1329 lines), **ACTING SYSTEM** (`713754be…`, 442 lines) and **LIRA** (`a6a56fe4…`, 612 lines).
- **Premise** (`publication.json.description`): *"A sleepy Texas town in the nineteenth century. A stranger walks in and starts killing, calmly and without a word of explanation. Bullets pass through him and he keeps walking. The sheriff and his deputies do what men with guns do, and it changes nothing. Nobody knows what he wants, and nobody knows what he is avenging."*
- **The brief's own frame**: "VENGEANCE IS MINE is a **26-minute black-and-white AI short film in Academy 4:3**. Every frame is generated: there is no filmed footage, no sets, no camera crew and no real people behind the faces… He is **WI, the demon of vengeance**, and he has come for every sin ever spilled in this town. WI was born entirely from our imagination — no actor, no likeness, no rights to clear — and he came out in one pass: no casting round, no alternates kept." (`brief_text.txt:14021`, `:14022`)

## 1. Production shape

- **Folder taxonomy is scene-iteration, not scene-list.** 22 root folders (root claims 23) and the *same scene appears under five different names*: `First Scene` (3,219) · `First scene saloon` (179) · `s1salun` (3,681) · `Saloon/SceneWBarman` (3,341) · `Saloon/AssetW/PoliceDep` (1,739); likewise `s2 Sheriff's house` (394) · `Sheriff house and policeDep` (57) · `s4-5 Walkthrough and Sheriff's House` (2,630), and `First Scene/Police Department after Wi` (2,464) · `Wi on police DEP1` (235) · `Wi on police Dep2` (2,691) · `Searching Wi` (215). **Flat folders with `/` in the name** are flattened subfolders: the harvest lost the nesting, the arithmetic survived.
- Sizes: `1/2 ACT assets and test` 3,710 · `s1salun` 3,681 · `Saloon/SceneWBarman` 3,341 · `First Scene` 3,219 · `Scene #3` 2,728 · `Wi on police Dep2` 2,691 · `s4-5 Walkthrough…` 2,630 · `assets` 2,569 · `First Scene/Police Department after Wi` 2,464 · `Saloon/AssetW/PoliceDep` 1,739 · `city-walks (source folder name is byte-corrupted)` 715 · `s3 Police Station  p2` 705 · `s2 Sheriff's house` 394 · `Assets test` 348 · `Wi on police DEP1` 235 · `Searching Wi` 215 · `First scene saloon` 179 · `Assets/daughter and mom/turtle` 121 · `tests` 117 · `Sheriff house and policeDep` 57 · `final` 19 · `Poster` 0.
- **"The source of truth" is `final` (19 items)** — a tiny folder for a 26-minute film, 0.05% of the root. Everything else is working material. Compare anerneq, which keeps two full `final-v1`/`final-v2` passes (3,627 items). Here the finished cut was not stored in the folder tree beyond 19 items.
- **`job_set_type`**: `seedance_2_0` 117 (all video + speech), `seedream_v5_pro` 33 (image plates, edits, diagrams). Two models only — the narrowest toolchain in the batch.
- **Aspect**: **1440×1080 = 4:3** in 113/150 rows (75.3%) — the delivered format; 2720×1536 in 33 (the `seedream_v5_pro` image size, 1.77:1); 1920×1080 in 4 (an early test, `r25-28`, Jul 14). The 4:3 is a *look decision*, stated in the prompt as often as it is set in the UI (132 rows).
- **`job_set_client_meta` is `null` in 150/150 rows** → the studio staging metadata is **UNKNOWN** for this case. Do not reconstruct it.
- **Harvest design**: 25 rows × 6 folders (`ROOT`, `1/2 ACT assets and test`, `s1salun`, `Saloon/SceneWBarman`, `First Scene`, `Scene #3`). The 150 rows collapse to **36 distinct prompts** — the heaviest duplication in the batch (§9).
- **Iteration is visible as a chat log, not as folder versions.** Many rows are *the director's note plus the prompt*: `Собрал под новую плиту. Дерево в центр, весь блокинг перенесён на колею` ("Rebuilt for the new plate. Tree to centre, all blocking moved onto the rut", `prompts.jsonl#100`), `Нашёл и вычистил: в промте было ~45 отрицаний` ("Found and cleaned: the prompt had ~45 negations", `prompts.jsonl#105`). The edit history is *inside* the prompts file.

## 2. Prompt anatomy — the actual grammar

### 2.1 The prescribed order (rule 0 of the project skill)

> `SCENE CONTEXT → OUTPUT SETTINGS (story-critical) → ACTIVE REFERENCES → ACTING TASK (our block, right after the references) → LOCATION MAP → FIRST FRAME AND SPATIAL BLOCKING → FORMAT MODE → OPTICS → CAMERA → ACTION TIMING → PHYSICS → LIGHTING → AUDIO → POSITIVE LOCKS. Sections a shot does not need are dropped; the order never changes. A standalone NEGATIVE CONSTRAINTS block is forbidden.` (`skills/a7ff619c-…md:12`)

This is **CINEDANCE's architecture plus two deliberate modifications**: `ACTING TASK` is inserted immediately after `ACTIVE REFERENCES` ("our block"), and `POSITIVE CONSTRAINTS` is renamed **`POSITIVE LOCKS`**. CINEDANCE's own list is `SCENE CONTEXT / ACTIVE REFERENCES / LOCATION MAP / FIRST FRAME AND SPATIAL BLOCKING / FORMAT MODE / OPTICS / CAMERA / ACTION TIMING / PHYSICS / LIGHTING / AUDIO / POSITIVE CONSTRAINTS` with `OUTPUT SETTINGS` and `NEGATIVE CONSTRAINTS` optional (`skills/2963a200…md`, "Final prompt architecture"). Compare and the derivation is exact.

### 2.2 The order that was actually used

Measured by locating every section header in each row and sorting by byte offset:

- **44 rows carry the full 13-section structure.** Two sub-forms:
  - **25 rows** — `SCENE CONTEXT → OUTPUT SETTINGS → ACTIVE REFERENCES → ACTING TASK → LOCATION MAP → FORMAT MODE → OPTICS → CAMERA → ACTION TIMING → PHYSICS → LIGHTING → AUDIO → POSITIVE LOCKS` (i.e. rule 0 exactly, `r75-99`);
  - **19 rows** — identical minus `ACTING TASK` (`r2-24`). The block is present only when a living character has a beat — consistent with rule 19: "**ACTING TASK** … for every living character with a beat; the director's external beats go into ACTION TIMING" (`skills/a7ff619c-…md:68`).
  - **0 rows contain any block outside rule 0's order.** No row reorders, no row adds a section.
- Section presence over 150 rows: `CAMERA` 107 · `ACTIVE REFERENCES` 69 · `AUDIO` 49 · `PHYSICS` 49 · `ACTION TIMING` 48 · `POSITIVE LOCKS` 45 · `SCENE CONTEXT` 44 · `OUTPUT SETTINGS` 44 · `LOCATION MAP` 44 · `FORMAT MODE` 44 · `OPTICS` 44 · `LIGHTING AND EXPOSURE` 44 · `ACTING TASK` 25.
- **A second, later dialect (25 rows, `r100-124`)** does not use the CINEDANCE section names at all. It is a *layered proof* format: `SHOT — EXT. {{loc}} — DAY — WIDE…` → `ONE SINGLE CONTINUOUS SHOT` → `STYLE` → `ACTIVE REFERENCES` → `[WHAT THE BUNDLE IS — AN OBJECT, PURE FREIGHT — THIS BLOCK OUTRANKS EVERYTHING BELOW IT]` → `LOCATION — {{loc}}, EXACTLY THIS PLATE` → per-object blocks (`THE DEAD TREE IS THE CENTRE OF THE PICTURE`, `THE STRAP`, `THE SAGUAROS`, `THE SKY`, `TONALITY`) → argument blocks (`BECAUSE IT IS COMING TOWARD US IT GROWS`, `IT IS TOWED SIDEWAYS`, `THE FRAME STACKS UP, GROUND-HEAVY`) → `POSITIVE LOCKS`. This is the newest material in the sample (12 Sep) and is the most sophisticated writing in the entire corpus: it does not *describe* the frame, it *derives* it.
- **A third, earliest dialect (5 rows, `r0,1,7,11,13`, 13–14 Aug)** — `SCENE` / `LOCKS` only, 5–6 KB, no references section beyond bare uuids.
- **Two `seedream` rows use quoted-dict keys** (`'Caption'`, `'BLOCKING (@block_door_closeup — from photo 2)'`, `r45,46`) — a different authoring tool, not a different grammar.

### 2.3 The slug / header line

The slugline exists and follows a fixed template:

> `SHOT — INT. {{f9b17e6a-…}} — DAY — LOW ANGLED` (`prompts.jsonl#54`, ×13 rows)
> `SHOT 68 — INT. {{4d6245fe-…}}` (`prompts.jsonl#137`, ×13 rows)
> `SHOT — EXT. {{b4507e08-…}} — DAY — WIDE, DISTANT HIGH-ANGLE VIEW` (`prompts.jsonl#105`)

Slots: `SHOT <n?> — <INT./EXT.> — {{location uuid}} — <DAY/NIGHT> — <FRAMING/ANGLE>`. **The location is named by uuid inside the slugline**, not by a name — a mechanical guarantee that exactly one location tag exists (§3.5). It also **inverts the CINEDANCE rule** "Do not include scene numbers" (`skills/2963a200…md`, "Scene context") — this project does include them (`SHOT 68`, `SHOT 07`).

### 2.4 How references are tagged

- **`{{uuid}}` is the only in-prompt reference mechanism.** 1,805 occurrences across 150 rows, **24 distinct uuids**, median **10 per video prompt**, max 43. Three roles only, always announced in `ACTIVE REFERENCES` or the slugline: **location**, **character**, **prop**.
- **Every reference is given its role in words, not just its uuid.** The mechanism is stated as a rule about *conflicts*, not about naming: "**a conflict of two location references = the model takes the wrong geometry** (the bar test that pulled in a façade with a rail and the whole hall) → exactly ONE location tag per prompt" (`skills/a7ff619c-…md:51`). In-prompt form:
  > `{{a69cb002-…}} — THE MARSHAL OFFICE — THE ONE AND ONLY LOCATION OF THE FILM, THE REFERENCE IS LAW IN EVERY DETAIL: the iron jail bars along the LEFT, the plank door in its frame LEFT OF CENTER with the THIN BRIGHT GAP OF DAYLIGHT UNDER ITS LEAF…` (`prompts.jsonl#2`)
- **`@TAG` is a registry layer that never reaches the prompt.** The rule file says tags are written "letter for letter; case matters" and live in `tag-registry.md` in the "Wi convention" (`@char_Wi_…`, `@loc_Wi_…`, `@prop_Wi_…`) (`skills/a7ff619c-…md:104-106`); the brief lists the registry — `@char_VM_bartender_v2_blood`, `@loc_VM_saloon_int_bar_s4`, `@prop_VM_winchester_bartender`, `@prop_VM_dummy_headless` — and notes "**a body double is a prop**" (`brief_text.txt:14613`). In the prompts: **1 @-tag in 150 rows** (`@block_door_closeup`, `r46`). Exactly as in anerneq, the tag layer is human bookkeeping; the uuid is the machine interface.
- **`{{ref 1}}`** appears in 20 rows — the image-model lane's "the attached image" handle.
- **In-prompt naming**: the demon is called **THE TALL MAN** in the reference descriptor (20 rows) and **WI** in the locks/rules (120 rows contain the string `WI`). The rule "The monster is always **WI**" (`skills/a7ff619c-…md:26`) is honoured at the *lock* level, and the references block still spells him out for the model.

### 2.5 Timing syntax

- **The zero frame + one cut is the standard shape**, stated to the tenth of a second:
  > `15 seconds. 0.0–0.5s: one physically locked ZERO FRAME. 0.5s: exactly ONE HARD CUT, the only cut in the film. 0.5–15.0s: one single unbroken take with one continuous, extremely slow physical push.` (`prompts.jsonl#2`)
  Rule 1: "**Frame 0 — always.** Every generation is a CONTROLLED MULTI-SHOT SEQUENCE: Shot 1 is a static establishing wide of 0.5 s (unless told otherwise), then a HARD CUT into the action. **Frame 0 is always static — it gives the model depth.**" (`skills/a7ff619c-…md:13`)
- **Timecode density is the highest in the batch**: 769 `a–b s` ranges across 19 distinct prompts (median 4.5 per distinct prompt, max 15). `ACTION TIMING` is not prose — it is a schedule: `0.5–4.0s — THE APPROACH IN THE GAP`, `4.0–6.5s — THE THREE BLOWS`, `7.0–13.0s — THE ENTRY, IMMEDIATELY`, `13.0–15.0s — THE STOP` (`prompts.jsonl#2`).
- `HARD CUT` in 50 rows, but **`MULTISHOT` in 0** and `CUT n` numbering in 0 — the cut is always described *as an event with a timecode*, never as a numbered shot list. Compare hell-grind (`CUT 1`, `CUT 2`, 198 occurrences).
- `24 fps` in 49 rows (15 distinct) and `Academy 4:3` in 132 rows — frame rate and gate are prompt text here, not UI settings (contradicting LIRA rule 4).
- Stated duration: **15 s is the modal length** (39 distinct prompts), then 6.5 s and 5.0 s (27 each), 15 s flagged again as `15s` (23). The film is cut from 15-second blocks — the model's maximum, not a dramatic unit.

### 2.6 Aspect / duration inside the prompt vs in the params

- Aspect is stated **twice**: as `Academy aspect ratio 4:3` in the canon STYLE block (132 rows) and as `width/height = 1440×1080` in the job (113 rows). Duplication is intentional — the 4:3 is part of the *photographic* claim ("Academy 4:3" is 1950s Hollywood), not only a delivery setting.
- Duration is stated **only** in the prompt (`15 seconds.`); the `duration` param key exists in 117 rows but **its value was not harvested → UNKNOWN**. The in-prompt numbers therefore cannot be cross-checked against the UI for this case.
- `fps` is in the prompt (`24 fps`), and `multi_shots` / `multi_shot_mode` / `generate_audio` keys exist but are unread. **UNKNOWN** whether the UI was set to match.

## 3. What this case does that the others may not

**1. It abolishes the negative block and replaces it with named positive LOCKS — and it says so, with a receipt.**
`0/150` rows contain a `NEGATIVE` block; `0/150` contain a line beginning `No `; `0/150` contain `⚠️` or `HARD LOCK`. Instead: **38 distinct named `THE X LOCK`s** and **7 named `THE X COUNTER`s**, each a positive statement with an observable proof. The rule:
> "**Positive key only.** A negative generates the forbidden thing ('no subtitles' → subtitles; 'free of tears' → tears). A local negative lock stands only next to its positive, against a known failure. **Trigger words never enter the prompt, not even in denial.**" (`skills/a7ff619c-…md:26`)

And the receipt is a director's note that quantifies the conversion:
> `Нашёл и вычистил: в промте было ~45 отрицаний, включая самые опасные — список «never sags, never bows, never curves, never dips» … «NOT a character» … «no bracing, no struggle» … Всё переведено в аффирмативы.` — "Found and cleaned: the prompt had ~45 negations, including the most dangerous — the list 'never sags, never bows, never curves, never dips', 'NOT a character', 'no bracing, no struggle'. All translated into affirmatives." (`prompts.jsonl#105`)

This is the **exact inverse of ANERNEQ**, whose median prompt carries 74 prohibitions in a `NEGATIVE` block. Both are "high-realism" films; they are built on opposite epistemologies of the negative. **Any distilled skill must present both and say which failure each answers** — negatives suppress a known artefact; positives avoid *summoning* one.

**2. Every "don't" is rewritten as a counter with a number and a proof.**
> `THE DUST COUNTER: exactly ONE burst of dust and dirt in the whole film — at the break (~6.5s), from the empty seat — rolling low, thinning, settling; zero dust before it, zero new bursts after it.` (`prompts.jsonl#2`)
> `THE BLOW COUNTERS: exactly THREE blows, all his — TWO that shake the leaf (~4.5s, ~5.5s, the second heavier) and THE THIRD that breaks it out (~6.5s)` (`prompts.jsonl#2`)
> `THE WALLS-SACRED LOCK: THE WALLS NEVER BREAK — no crack, no hole, no crumbling … the ONLY thing that breaks in the film is the door with its frame` (`prompts.jsonl#2`)
332 `EXACTLY` + 236 `ZERO` occurrences; mean **4.44 counters per distinct prompt** (max 15) vs anerneq's 0.58. Rule: "hard counters (exactly N shots / N−1 strokes / N−1 cases, the last round in the chamber); hit rate about 50–70%" (`skills/a7ff619c-…md:56`). Note the syntax: the counter is *named*, *numbered*, *placed in time*, and *closed in both directions* ("zero before it, zero after it").

**3. The camera is anchored in world coordinates, never in screen coordinates — because the model mirrors.**
> `The camera is INSIDE the marshal office, LOW AT FLOOR LEVEL — the lens a hand above the floorboards, a few metres from the door wall, on the reference's own axis, aimed at the door.` (`prompts.jsonl#2`)
> `THE PUSH LOCK: one continuous floor-level push of exactly 0.12 metres at one constant speed, 0.5s to 15.0s — the complete camera movement; the camera stays a hand above the boards the whole film.` (`prompts.jsonl#2`)
The rule states the mechanism, not the taste: "(a) at which world object the camera stands … (b) from which SIDE OF THE CHARACTER'S BODY it looks … (c) proof of the position in observable features in every shot … (d) a lock — 'the camera never crosses to the [X] side'. Screen terms … appear only AS CONSEQUENCES of world anchors, never on their own: **the model mirrors**" (`skills/a7ff619c-…md:17`). The push distance is given **in metres** (0.12 m over 14.5 s) — a number, not "slow".

**4. Exactly one location tag per prompt, with the reference declared supreme.**
> `{{a69cb002-…}} — THE MARSHAL OFFICE — THE ONE AND ONLY LOCATION OF THE FILM, THE REFERENCE IS LAW IN EVERY DETAIL`
> `THE ONE-LOCATION LOCK: the marshal office … is the ONLY location of the film — every frame is shot inside it, from one spot, on the reference's own axis` (`prompts.jsonl#2`)
The failure this answers is named: "**a conflict of two location references = the model takes the wrong geometry** (the bar test that pulled in a façade with a rail and the whole hall) → exactly ONE location tag per prompt; if the shared location reference is wider than the frame — write 'IN THIS SEQUENCE ONLY ITS [part] APPEARS IN FRAME'" (`skills/a7ff619c-…md:51`). Compare hell-grind, which routinely loads 5–8 location/character uuids per prompt.

**5. Props and characters are described exactly once, and the descriptor is copied verbatim into every prompt.**
> "each is its own asset, and **each is described exactly once in a prompt. Describe a prop twice and the model gives you two of them; the hat taught us that**." (`brief_text.txt:120`)
> "An asset is a pair: text + image. **The text descriptor goes into every prompt word for word**" (`brief_text.txt:14350`)
Rule 9: "A prop is described ONCE (the hat lesson)" (`skills/a7ff619c-…md:27`). This is a *duplication rule* the other two cases do not have: anerneq re-describes everything every time ("Every prompt is an island"), vengeance re-*points* at a fixed descriptor every time. Both avoid drift; they differ in what they spend tokens on.

**6. The film is written in a closed list of framings, and the closure is the style.**
> `FOUR WINDOWS, A CLOSED LIST: every frame of this video is one of exactly FOUR framings, and all four live CLOSE: (1) a low Dutch MEDIUM from the left, (2) a chest-up CLOSE Dutch from the right, (3) a floor-skimming Dutch DETAIL on the boots, (4) a tight three-quarter Dutch MEDIUM from the front-left.` (`brief_text.txt:2423`)
> `all handheld, all canted and never levelling, all holding WI LARGE in the frame, each keeping its own spot and its own scale for its whole shot` (`brief_text.txt:11938`)
The rule generalises to FOV arithmetic: "FOV in degrees + distance + observable result; LENS LOCK per segment; **a face close-up = 29° from about 4 m; the wide = 84°; 63° is the canon of the bar**" (`skills/a7ff619c-…md:88`). Measured: `63°` in 44 rows — the sample is almost entirely the bar interior, so only one of the three lenses is exercised.

**7. There is no subtitle clause anywhere, and no tears clause — the trigger words are absent, not forbidden.**
`subtitle` appears in **0/150** rows (anerneq: 124; hell-grind: 56). The positive substitute is rule 22: "Captions are handled positively: '**the photographic image fills the frame edge to edge**'" (`skills/a7ff619c-…md:78`) — and that sentence is in the prompt (`prompts.jsonl#2`). Similarly rule 15 removes the *word* "tears" from every prompt: "tears in any form = crying → the word is removed; the eyes are 'matte and dry'" (`skills/a7ff619c-…md:40`). This is the corpus's clearest demonstration that **a prohibition can be implemented as an absence**.

**8. It admits exactly one kind of negative: a local lock standing next to its positive.**
Despite rule 8, the most repeated phrase family in the corpus is a negative list:
> `no pan, no tilt, no zoom, no shake, no reframe` — `no pan` 105×, `no tilt` 97× (`prompts.jsonl#2` et al.)
It is legal under the rule's own exception — "A local negative lock stands only next to its positive, against a known failure" (`skills/a7ff619c-…md:26`) — because it sits immediately after the positive sentence that defines the whole move: `This push is the complete camera movement: no pan, no tilt, no zoom, no shake, no reframe`. **The distinction is positional, not semantic**: no negative block, but a negative clause is fine after its positive.

---

## 4. Recurring phrasing bank

### Style / canon (pasted verbatim into every prompt — rule 20)
- `BLACK & WHITE, 1880s American West, in the exact photographic style of HIGH NOON (1952, DoP Floyd Crosby): hard documentary realism, flat grey tonality, visible film grain, no diffusion, no gloss. Academy aspect ratio 4:3. … Total realism, no CGI look, no color anywhere.` — 117 rows contain `HIGH NOON`, 131 contain `Crosby`, 94 `BLACK & WHITE`.
- `Exact photographic language of HIGH NOON (1952), photographed by Floyd Crosby: hard chronicle-like western realism, pure neutral monochrome black-and-white, a flat grey tonal scale, hard undiffused daylight with crisp shadow edges, deep focus` (`prompts.jsonl#2`).
- `the same heavy 1950s grain and flat documentary grade` (`brief_text.txt:13257`).

### Light (canon, opens `LIGHTING AND EXPOSURE` — rule 20)
- `LIGHT: the light source stays outside the frame, only its hard window daylight visible, raking the room, the door, the man and the corpse; one single light temperature.` (`prompts.jsonl#2`; `one single light temperature` 88 rows, `source stays outside the frame` 50 rows)
- `EXPOSURE REMAINS STABLE THROUGH THE COMPLETE FILM — set once and held … nothing pumps, drifts or adapts when the doorway opens.` (`prompts.jsonl#2`)
- `the two windows … read BLOWN PURE WHITE with minimal gradation`; `THE UNDER-DOOR GAP burns as one thin bright strip at floor level` (`prompts.jsonl#2`)
- Banned inside this canon: `soft daylight`, `gentle bloom`, `soft toe`, `halation`, `newsreel realism with dread` (`skills/a7ff619c-…md:75`).

### Camera / optics
- `LENS LOCK: 63° diagonal field of view, constant throughout…` (`prompts.jsonl#2`) — 44 rows.
- `handheld through the operator's body: quiet breathing rise and fall, a micro-settle, small corrections, minimal / light controlled shake, a sympathetic sway or jolt on gunshots with a return` (`skills/a7ff619c-…md:89`).
- `the steps of a push-in "read as small absorbed sways"` (`skills/a7ff619c-…md:89`).
- `no pan, no tilt, no zoom, no shake, no reframe` (105/97).
- `framing tightens ONLY through the camera's physical advance` (`skills/a7ff619c-…md:88`).
- `identical angle every frame, held to the final frame` (`skills/a7ff619c-…md:54`, Dutch-angle rule).
- `to the last frame` / `from the first frame to the last` — 17 occurrences each as 5-grams; the corpus's most repeated ending.

### Motion / physics
- `EVERYTHING IN THE FILM OBEYS REAL ON-SET PHYSICS — NATURAL, ORGANIC, PHOTOGRAPHED, NEVER ANIMATED` (`prompts.jsonl#2`).
- `true weight, true momentum, natural starts and stops; zero mechanical motion, zero puppet motion, zero floating, zero sliding without cause` (`prompts.jsonl#2`, `THE NATURAL-MOTION LOCK`).
- `the stop of a heavy living man: the weight settles, the coat swings once and comes to rest` (`prompts.jsonl#2`).
- `The door takes the first two blows as real timber — jolting, flexing a hair, settling back` (`prompts.jsonl#2`).
- `a real living human body` underneath the stillness — always appended to `THE WI LOCK` (`prompts.jsonl#2`).

### Sound
- `Diegetic ambience and physical foley only. No voice anywhere.` (`prompts.jsonl#2`) — 117 rows contain `diegetic`.
- `a line gets ≥ 2 s before the cut; a scare lives inside one shot` (`skills/a7ff619c-…md:77`).
- `no music` in 42 rows; music is a *post* layer: "Music lives in post — generated in Suno and Seedance and laid under the picture in the edit" (`brief_text.txt:13540-13542`).
- `BLOW ONE: a heavy BOOM, the natural rattle of latch and hinges` — sound named as the thing that produced it (`prompts.jsonl#2`).

### Acting
- `ACTING TASK — {{uuid}}` then four labelled lines: `SCENE DIRECTION, UNSPOKEN:` / `MOTIVE:` / `GOAL:` / `OBSTACLE:` / `TACTIC:` (`prompts.jsonl#75`) — 25 rows, the only case in the batch that puts the acting method *in the prompt as a labelled block*.
- `MOTIVE: this bar is his whole life and now it is a trap he is locked inside.` (`prompts.jsonl#75`)
- `OBSTACLE: his own body — the hands shaking the rifle he needs steady, the breath too loud in the silence` (`prompts.jsonl#75`)
- `TACTIC: press into the counter; ration the panic into WATCHING — sweep in raids` (`prompts.jsonl#75`)
- `HE IS A LIVING MAN AND HE BLINKS` (block title, `prompts.jsonl#75`); `blinks` in 71 rows — "blinks are strong events (a timecode, 'clearly visible', lid travel about 1/3 s)" (`skills/a7ff619c-…md:66`).
- `the gaze holds its point BETWEEN blinks` (`skills/a7ff619c-…md:56`) — the anti-frozen-eyelid formula.
- WI's negative-acting spec, stated as positive mechanics: `moves like a walking tree (head, neck, spine, pelvis and shoulders one block; knees, elbows and wrists straight; the limbs levers from the shoulder and the hip); NEVER blinks; no breath, no sweat, no mimicry; a mask-smile; a gaze into emptiness` (`skills/a7ff619c-…md:67`); `mask-smile` in 25 rows, `walking tree` in 6, `never blinks` in 9.

### Dialogue / wit
- `Violence comes with humour.` / `The joke lives in the picture, never in mugging.` (`brief_text.txt:13629`, `:12330`)
- `No words from another language inside an English prompt` (`skills/a7ff619c-…md:28`) — and yet the *director's notes* in `prompts.jsonl` are Russian (39 rows contain Cyrillic). Rule 10 governs prompt text only; the annotation layer is bilingual by design ("The bilingual prompt library: every shot in English with its Russian translation", `brief_text.txt:13780`).

---

## 5. Structure & story

- **One 26-minute film in Academy 4:3**, not a series (`type=film`, one featured episode `vengeance-is-mine/full-film`).
- **Story units are named shots, and the folder tree is the shot list**: `Scene #3`, `s1salun`, `s2 Sheriff's house`, `s3 Police Station p2`, `s4-5 Walkthrough and Sheriff's House`, `First Scene/Police Department after Wi`, `Wi on police DEP1/2`, `Searching Wi`, `Poster`, `final`. Scene numbers exist only up to ~5 in the folders while the prompts contain `SHOT 68` — the folder numbering is not the edit order.
- **Stated story rules**: the premise must stay unexplained — "Nobody knows what he wants, and nobody knows what he is avenging" (`publication.json`); "A stranger walks in and starts killing, calmly and without a word of explanation"; "Bullets do not stop him" (`brief_text.txt:14021`). The demon's whole characterisation is a *lock*, not a backstory: `THE WI LOCK: the stiff proud manner — one rigid block, little arm swing, the fixed mask-smile, the wide-open eyes — zero blinks, zero visible breath, zero expression change, the whole film; and underneath it, always, a real living human body.` (`prompts.jsonl#2`)
- **The violence is staged as comedy and as practical effect**: "The demon waltzes a headless dummy through a gunfight and hurls it at the camera: fourteen seconds, four shots, three hard cuts, one continuous dance" (`brief_text.txt:765`); "Every effect reads as practical. Black paint, snapping cloth, a theatrical dummy — animatronics and practical work, never CGI" (`brief_text.txt:13597`, `:13605`).
- **Blood is a material, not a colour**: in B&W the rule is "Blood and liquid in black and white are '**neutral black**'; a glossy, paint-like black is allowed as a stylisation; contact between heads is hidden between the bodies; finished heads are '**dark indistinct ruined shapes**'" (`skills/a7ff619c-…md:80`). The prose calls it black paint and dots: "the black drops dotting time like a metronome" (`brief_text.txt:8777`).
- **Post is a separate, stated pass**: "Two things are laid over the picture in post: film grain, one stock for the whole film, and the type — the title card in the prologue and the end credits. Colour was a unification pass" (`brief_text.txt:13540-13541`). The edit went through three stages to picture lock.
- **Pre-production rule that governs all of it**: "The shotlist was made by hand. Every scene was blocked on paper first — who stands where, where the camera lives, what each shot has to carry — before a single prompt existed… **A shot that has no place on the paper plan does not get a prompt.**" (`brief_text.txt:199`ff)

## 6. Per-case hard rules (only what this case evidences)

1. **CINEDANCE order, always, no exceptions; no standalone negative block.** `skills/a7ff619c-…md:12`.
2. **Frame 0 is always static and always 0.5 s, then exactly one hard cut.** `:13`. "More shots only on the director's word; in a multi-shot, continuity locks after every cut: position, orientation, props, smoke."
3. **Every actor present in frame 0 is tagged in Shot 1's description, even a hidden one — the location too.** `:14`.
4. **Always 24 fps, Academy 4:3, pure neutral monochrome, real time.** `:15`.
5. **Actors anchored measurably, proved by a landmark behind them; orientation by the body in the world, never screen left/right.** "a bright object such as a lit doorway magnetises both the aim and the position" `:16`.
6. **Camera anchored by world object + side of body + observable proof + a never-cross lock.** `:17`.
7. **Positive key only; trigger words never enter the prompt, not even in denial.** `:26`.
8. **A prop is described once.** `:27` ("the hat lesson").
9. **No words from another language inside an English prompt** (platform reference tags excepted). `:28`.
10. **Blocking maps: plain white background, no grid, no furniture, one colour per figure+prop bundle, outlines only, staging reference attached last.** `:98-103`.
11. **Light and style are canon, verbatim, in every prompt; the light never changes on its own initiative.** `:72-76` — "A special lighting scheme … enters a prompt ONLY when the director asks for it directly."
12. **Diegetic sound only, no music; a line gets ≥ 2 s before the cut; a scare lives inside one shot.** `:77`.
13. **Captions handled positively.** `:78`.
14. **The horizon is level by default.** `:79`.
15. **Hard counters for anything countable; hit rate 50–70%, cured by regeneration.** `:56`.
16. **Re-check = two questions per piece: does it contradict itself; can the model read it two ways. "Ambiguity = an error, even when the text is internally logical."** `:93`.
17. **The director's anchors go in word for word; strict replacement; unclear → ask BEFORE assembling; every contradiction flagged.** `:32-35`.
18. **Before delivery, "confirm the director's edits to yourself point by point; re-check always."** `:62`.
19. **Anything that fails, simplify the shot, not the words** — *this is the shared hell-grind rule and this project's prompt lane obeys it in practice* (see §9).

## 7. Numbers

| metric | value |
|---|---|
| rows harvested | 150 = 6 folders × 25 |
| distinct prompts | **36** (143 rows are duplicates; 29 dup groups, largest ×13) |
| generations_count | 37,335 published / 37,428 items in root |
| prompt chars (all rows) | min 1,614 · median 11,468 · mean 15,128 · max 40,836 |
| prompt chars (video, distinct) | min 1,614 · median 17,354 · max 40,836 |
| prompt words (video, distinct) | min 236 · **median 3,128** · max 7,428 |
| uuid refs | 1,805 occurrences · **24 distinct** · median 10/video prompt · max 43 |
| `{{ref N}}` refs | 20 rows |
| @-tags in prompts | **1** (`@block_door_closeup`) |
| named `THE X LOCK`s | **38 distinct** (top: `THE ZERO-FRAME LOCK` 45, `THE SINGLE-TAKE LOCK`/`THE SITTING LOCK`/`THE DISTANCE LOCK`/`THE WALKWAY LOCK`/`THE SOLID-BODY LOCK`/`THE TREMOR LOCK`/`THE BREATH LOCK`/`THE NO-FIRE LOCK`/`THE OFF-FRAME WORLD LOCK` 25 each) |
| named `THE X COUNTER`s | **7 distinct** (`THE ACTION COUNTER` 45, `THE ONE-DOOR-EVER COUNTER` 11, `THE BLOW COUNTER` 9, `THE DUST COUNTER` 8, `THE SHAKE COUNTER` 4, `THE BREAK COUNTER` 4, `THE DOOR-SHAKE COUNTER` 3) |
| `EXACTLY` / `ZERO` | 332 / 236 occurrences · mean 4.44 per distinct prompt · max 15 |
| `NEVER` | 278 occurrences in 107 rows — but **all inside named locks**, never in a negative block |
| timecode ranges per distinct prompt | 0 in 12/36 · **median 4.5** · max 15 · 769 occurrences total |
| stated durations (distinct prompts) | 15 s (39) · 6.5 s (27) · 5.0 s (27) · 15 s again as `15s` (23) · 3.5 s (16) |
| `24 fps` | 49 rows / 15 distinct |
| `Academy 4:3` stated in prompt | 132 rows / 30 distinct |
| `63°` LENS LOCK | 44 rows (the bar canon; `84°`/`29°` appear 0 times — the sample never leaves the bar) |
| negative blocks | **0 / 150** |
| line-start `No ` prohibitions | **0 / 150** |
| word `subtitle` | **0 / 150** |
| local negative lists | `no pan` 105 · `no tilt` 97 occurrences, all immediately after the positive camera statement |
| `⚠️` / `HARD LOCK` | **0 / 0** |
| cuts per prompt | 1 hard cut (44-row family), 0 cuts (25-row family, "ONE SINGLE CONTINUOUS SHOT") |

**Duplication flag**: aspect ratio is stated in the prompt (`Academy 4:3`, 132 rows) *and* set in the job (`1440×1080`, 113 rows). Duration and fps are stated in the prompt and their parameter values are **UNKNOWN**.

## 8. Failure modes named in this case

The rule file's rule 15 is an explicit **trap list** — the single most valuable artefact in the batch for the negative-constraint library, because each trap names the *word* that causes it and the *rewrite* that cures it (`skills/a7ff619c-…md:36-61`):

| trigger | what the model does | the rewrite |
|---|---|---|
| "tears" in any form | crying | remove the word; eyes "matte and dry" |
| moisture on a cheek near the eyes | a tear | sweat only as STATIC wetness, all moisture above the eyes |
| "wet / moist eyes" in a close-up | crying | delete |
| "sights" next to an eye | an OPTIC on the eye | "aims along the top of the barrel"; "small steel notch and thin front post low on the barrel" |
| **"soft / softly / gentle / gently" in ANY section (camera, sound, foley)** | soft light, diffusion, soft shadows | quiet / low / small / faint; **the count of soft/gentle in a finished prompt = ZERO** |
| an aim "past the frame edge" as the character turns | the barrel BROADSIDE in profile | "points AT the lens, seen almost END-ON, muzzle a dark circle facing the camera" + "THE BARREL NEVER TURNS BROADSIDE" |
| weapon held at arm's length | the mount falls apart | MOUNT LOCK: "butt seated in the shoulder, cheek welded to the stock, both elbows bent and tucked" |
| a weapon "pressed to the body" with no hand named | the barrel STICKS TO the body | LIVE GRIP + "a SEPARATE SOLID OBJECT: air and cloth read between the barrel and his vest" |
| a hand out of frame | a one-handed grip | both hands visible + "both hands in every frame" |
| free hands near an object | the model hands them the object | name the empty hands |
| "slips / failing / searches for support" | he drops it | describe the recovery |
| "diving" | a literal jump | "ducking" |
| "over-the-shoulder" | the dialogue OTS prior | re-specify the shot |
| a full reference for an invisible character | he climbs into the frame | only a visible crop; "an unseen presence just past the camera" |
| an object "behind the camera" named by name (windows) | it enters the frame | "hard window daylight" with no source named |
| **two location references** | wrong geometry (pulled in a façade + a whole hall) | exactly ONE location tag; "IN THIS SEQUENCE ONLY ITS [part] APPEARS IN FRAME" |
| a bright landmark (a lit doorway) | a magnet for aim and position | orientation by the body; muzzle and doorway on opposite sides |
| colour names | a tint on the black and white | no colour words |
| "steep diagonal" | a random Dutch angle | deliberate PERMANENT tilt, degrees and side, identical every frame |
| "locked gaze" with no caveat | frozen eyelids | blinks as separate timecoded events; "gaze holds its point BETWEEN blinks" |
| long strings of shots | the model loses cycles and cases | hard counters (exactly N shots / N−1 strokes / N−1 cases) |
| "visible shafts / god rays" | glossy volumetric light | "shafts" removed; hard raking daylight + drifting smoke |
| **"glowing" vocabulary (glow / glowing / flare / burn / searing / shine / luminous / spark)** | lens flares, halation, halos | ban the whole family; only rim / etched / bright / hard glints / crisp edges; "the lens stays clean and dry, shielded as if under a deep matte box" |
| insects without a counter | a swarm | "EXACTLY TWO FLIES", one dispersal per event |
| hard raking on a close-up | the working eye drowns in shadow | lock "the aiming/working eye clearly readable" |
| shake intensifiers without limits | escalating wobble | always "lightly shaking", "light live shake", "visible but controlled" |

Plus the standing bans: `soft daylight`, `gentle bloom`, `soft toe`, `halation`, `newsreel realism with dread` (`:75`); "**the count of soft/gentle in a finished prompt = ZERO**" (`:41`).

## 9. Anything weird / low quality

- **150 rows → 36 distinct prompts.** 143 of 150 rows are duplicates; the largest group is **×13** (`r56-63,70-74` and `r101-104,116-124`), because one prompt was re-run 13 times in a batch. Any frequency claim over "rows" is a claim about *batching*, not about writing. This digest reports distinct-prompt numbers wherever it matters.
- **The prompts file is 50% a chat log.** 39 of 150 rows contain Cyrillic, and several of those are not prompts at all but **the director's notes pasted above the prompt**: `Дверь теперь сорвана с петель полностью и лежит плашмя на полу` ("The door is now completely torn off its hinges and lies flat on the floor", `prompts.jsonl#29`), `Потому что я слишком подробно расписал весь интерьер «за дверью»` ("Because I described the interior 'behind the door' in too much detail and said 'gaping open, revealing the room' — the model decided it had to show the whole room, and removed a piece of wall to do it", `prompts.jsonl#33`), `Изменил: центральная дверь ВЫБИТА` ("Changed: the central door is KNOCKED OUT", `prompts.jsonl#37`). **These notes are the case's real methodology text** — each one is a failure → fix pair, in the director's own words, and they corroborate the rule file independently.
- **The `seedream_v5_pro` lane is a different authoring style**: 33 rows of image prompts, 2–8 KB, some as Python-repr dicts (`'Caption': …`, `r8,29-40`), some as terse edits (`Edit this exterior frame — TWO changes`, `r133-136`), some Russian (`Добавил край окна справа от двери`, `r46`). They are not the video grammar and should not be counted as prompts.
- **Folder-name rot**: `city-walks (source folder name is byte-corrupted)` (mojibake for `city-walks`), `First Scene/Police Department after Wi` (the sentence is cut mid-word — "after Wi[?"), `s3 Police Station  p2` (double space), `Poster` with **0 items**, and five folders for scene 1. `folder_tree.json` root claims 23 subfolders and lists 22.
- **`has_changes_since_publish = true`** — the published film's folder was edited after publication; the snapshot is not the published cut's exact state. anerneq and hell-grind both report `false`.
- **No `Regenerations` folder** (hell-grind has one holding 12.6% of all items), so the retry cost is invisible here except through the duplicate counts in `prompts.jsonl` and the folder sizes.
- **One prompt is a full manual for another prompt's geometry**: `r105`/`r112` run to 40,836 chars (7,428 words) and begin with the negation audit quoted in §3.1. It is the longest and most self-aware document in the corpus.
- **Rule vs practice, honestly**: rule 8 ("positive key only") is honoured at the *structure* level (no negative block) and violated at the *clause* level (`no pan, no tilt, no zoom, no shake, no reframe`, 105 instances). Rule 10 ("no words from another language inside an English prompt") is honoured in prompt bodies and violated in the same file's annotation layer (39 rows with Cyrillic). Rule 0's order holds in 44/44 structured rows. `⚠️`/`HARD LOCK` are absent here and dominant in hell-grind — those labels are a *house style*, not a necessity.
- **Cross-case contradiction to carry forward**: on the role of the negative, this case and `anerneq` are **opposed and both successful**. ANERNEQ: 74-item `NEGATIVE` block, median 49 negation tokens per prompt, 0 counters. VENGEANCE: 0 negative blocks, 4.44 counters per prompt, 278 `NEVER`s confined to named locks. A distilled skill must not average them; it must state the trade — *enumerate the artefact and you also enumerate it to the model; name a lock and you must also state its positive proof*. Note also that the brief's own prose still says "Generate video without subtitles" (`brief_text.txt:13363`) while the rule file forbids the phrasing and the prompts contain it nowhere: **the doctrine outran the brief**.

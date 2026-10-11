---
name: ai-video-storyboard
description: Use when planning a multi-shot AI video (TikTok Reel, Instagram Ad, YouTube Shorts, product explainer) where the target duration exceeds what a single AI generation can produce (>15s), and you need a coordinated shot list with visually consistent prompts for each segment
---

# AI Video Storyboard Generator

## Overview

AI video generators produce 5–15 second clips. Real-world videos are longer: 30s TikToks, 60s ads, 90s explainers. This skill bridges that gap by producing a complete **shot-list storyboard** — a coordinated sequence of per-shot prompts with shared visual language, so the assembled final video looks like one intentional piece of work rather than six disconnected clips.

**Core insight:** Visual consistency across shots matters more than any single shot being perfect. A mediocre but consistent set of shots edits together; six gorgeous but mismatched shots do not.

## When to Use

- User wants a video longer than 15 seconds
- User wants a TikTok / Reel / Short / ad / explainer / B-roll sequence
- User says "help me make a video about X" and has no shot list
- User is about to generate multiple clips and needs a plan

**Do NOT use for:**
- Single-shot generation (just help with one prompt instead)
- Static image generation
- Video editing advice after clips are generated (that's a separate concern)

## Workflow

### Step 1 — Brief Intake

Ask the user these questions in a single message. Accept short answers:

1. **Goal platform and duration?** (TikTok 30s / Reel 15-60s / YouTube Short / Instagram Ad / explainer)
2. **What is the video about?** (subject, story, product)
3. **Brand vibe / tone?** (cozy, energetic, premium, minimalist, playful, cinematic, etc.)
4. **Call to action at the end?** (visit website, buy product, follow channel, etc.)
5. **Any hard constraints?** (must include logo, specific colors, locations, etc.)

If user already provided some of these, skip those questions and confirm the rest.

### Step 2 — Infer Structure

Based on duration and platform, divide the timeline into shots of ~5 seconds each (the sweet spot for AI video generators).

**Standard cadences:**

| Platform | Duration | Shots | Pacing |
|---|---|---|---|
| TikTok Hook | 15s | 3 | Fast cuts, single idea |
| TikTok Reel | 30s | 6 | Hook → Build → Payoff → CTA |
| Instagram Ad | 15s | 3 | Hook → Product → CTA |
| Instagram Ad | 30s | 6 | Hook → Problem → Product → Benefit → Social proof → CTA |
| YouTube Short | 60s | 12 | Hook → 3-act structure → CTA |
| Product Explainer | 90s | 18 | Problem → Solution → How it works → Results → CTA |
| Brand Story | 60s | 10-12 | Atmosphere-driven, longer shot holds |

### Step 3 — Establish Visual Consistency Layer

Before writing any shot, lock in the shared visual language. This is what makes shots edit together:

- **Color palette** (3-5 specific hex values or named colors)
- **Lighting style** (golden hour / neon / overcast / motivated / cinematic rim light)
- **Lens character** (shallow DOF / deep focus / wide angle distortion / macro)
- **Film look** (clean digital / 16mm grain / anamorphic / VHS / 35mm)
- **Motion language** (handheld / locked off / dolly only / gimbal smooth)

Write these as a **Visual Theme** block at the top of the output. Every shot's prompt must respect this block.

### Step 4 — Write Each Shot

For each shot, produce this structure:

```
## Shot N (START-ENDs) — [Purpose label: Hook / Setting / Action / Detail / Reveal / CTA]

**Composition:** [shot type + angle, e.g., "Extreme close-up, overhead"]
**Camera move:** [locked / slow dolly in / tracking / crane up / etc.]
**Lighting:** [from the Visual Theme, applied to this scene]
**Subject:** [what is in frame]
**Action:** [what is happening]

**Prompt to copy:**
> [Complete, cinematic-quality prompt, 40-80 words, including: subject + action + environment + camera + lighting + style + technical spec (duration, aspect ratio, resolution). Always ends with "cinematic 1080p, synchronized audio"]

**Audio direction:** [what the synchronized audio should sound like — ambient sounds, music beat position, voice-over line]
```

**Critical rules for shot prompts:**

1. **Always specify the shared visual language** in every prompt (color palette, lighting, lens character, film look). This is how you enforce consistency.
2. **Specify exact duration** (4s / 5s / 8s) and **aspect ratio** (9:16 for TikTok/Reels, 16:9 for YouTube landscape, 1:1 for feed posts).
3. **Always end with "cinematic 1080p, synchronized audio"** — this signals professional-grade quality and works with modern video models that support both.
4. **Use cinematography vocabulary**: ECU (extreme close-up), CU, MS (medium shot), WS (wide shot), OTS (over-the-shoulder), POV, Dutch angle, low angle, high angle, bird's eye, dolly in, dolly out, tracking, handheld, rack focus, etc. See `references/shot-types.md` for the full vocabulary.
5. **Don't write abstract prompts** — be concrete. "A woman" → "A barista in her late 20s with wavy auburn hair, wearing a denim apron".
6. **No model-specific hacks** — don't write prompts tuned to specific model quirks. Write model-agnostic cinematic prompts that work anywhere.

### Step 5 — Add Narrative Structure

The sequence of shots must have a **story arc**, not a random list. Use one of these patterns:

**Pattern A — Hook / Build / Payoff / CTA (TikTok default)**
- Shot 1: Visual hook (stop the scroll)
- Shot 2-3: Build context / intrigue
- Shot 4-5: Main content / payoff
- Shot 6: CTA

**Pattern B — Problem / Solution / Proof / CTA (Ad default)**
- Shots 1-2: Relatable problem
- Shot 3: Your product as solution
- Shots 4-5: Benefits / results
- Shot 6: CTA

**Pattern C — Atmosphere → Climax (Brand story)**
- Longer atmospheric shots
- Slow reveal
- Emotional climax
- Logo reveal

### Step 6 — Add Post-Production Checklist

Close with actionable post-production notes:

```
## Post-Production Checklist
- [ ] Generate all N shots with your preferred AI video tool
- [ ] Stitch in [CapCut / Descript / DaVinci Resolve / Premiere]
- [ ] Apply [specific LUT or color grade] for consistency
- [ ] Add [transition type and duration] between shots
- [ ] Layer BGM: [genre / BPM / mood]
- [ ] Add text overlays for [hook / CTA / captions]
- [ ] Export [platform spec: 9:16 1080x1920 30fps for TikTok, etc.]
```

### Step 7 — Explain Why It Works

Close with a "Why this works" block explaining the creative decisions. This educates the user and differentiates your output from generic prompt lists. Reference:

- The hook rule (first second determines watch-through)
- Pacing cadence (average scroll time)
- Story structure (why the shot order matters)
- Platform-specific conventions

## Output Format

The final output is a single Markdown document containing:

1. **Header** — Title, duration, shot count, aspect ratio
2. **Visual Theme** — Shared palette, lighting, lens, film look, motion
3. **Shot List** — N shots, each following the structure in Step 4
4. **Post-Production Checklist**
5. **Why This Works** — creative rationale

See `examples/` for four complete sample outputs:

- `tiktok-reel-30s-coffee.md` — Coffee shop opening TikTok
- (more examples to be added)

## References

- `references/shot-types.md` — Cinematography vocabulary (ECU, CU, MS, WS, OTS, POV, angles)
- `references/camera-moves.md` — Camera movement vocabulary (dolly, crane, pan, tilt, tracking)
- `references/lighting.md` — Lighting terminology (golden hour, rim, motivated, practical)
- `references/genre-templates.md` — Pre-built templates for common genres (food, fashion, tech, travel, SaaS)

## License

MIT — use freely, commercial or personal.

# v26-cinematic-camera - DRAFT

| | |
|---|---|
| Tag | `v26-cinematic-camera` |
| Date | 2026-10-05 |
| Built on | [v25-state-phase-timers](v25-state-phase-timers.md) |
| Groups | 1 shipped group(s) changed |
| Confidence | **DRAFT - fill this in** |

> **DRAFT.** Every other note on this page is written for a player: what this
> version changes over the last one, and what was discovered on the way. Rewrite
> this before the release PR merges - its merge is what publishes the release.

## What it changed

Shipped groups this version carries that the last release did not:

- `60FPS - cinematic camera`

The commits to `wip/working.pnach` it carries since v25-state-phase-timers:

- fix(patch): play cinematic camera clips at their real speed (ed92539)

## What was discovered

fix(patch): play cinematic camera clips at their real speed

This PR stops transformation cinematics' cameras from cutting ahead of the action, so Vegeta's Great Ape transformation keeps the camera on him as the energy ball goes up.

## Synopsis

During a cinematic, the render camera (`FUN_0023D510`) plays a camera clip and steps the clip's time by a bare 2.0 a tick, so at 60fps it ran through its shots in half the real time. The new group `[60FPS - cinematic camera]` changes that step to 1.0.

## What changed

| | v24 | This PR |
|---|---|---|
| `0023D6A4` | `lui $at, 0x4000` (2.0 a tick) | `lui $at, 0x3F80` (1.0 a tick) |
| Exported groups / patch lines | 33 / 557 | 34 / 558 |

## Test results

Vegeta (Scouter), `R3`, `drift.py --slot 9`, pixel drift against the 30fps arm:

| arm | mean | v28 | v42 | v98 | v300 |
|---|---|---|---|---|---|
| 30fps, second run | 0.00 | 0.0 | 0.0 | 0.0 | 0.0 |
| v24 | 24.72 | 34.1 | 30.9 | 33.9 | 14.3 |
| v24 + this group | 14.29 | 12.4 | 13.7 | 22.7 | 0.8 |

| check | result |
|---|---|
| Exact-vsync photos at v28 / 42 / 56 / 182 | the 30fps shot, one vsync ahead, including the camera on Vegeta raising the ball at v182 |
| Not fixed by this group | the first cut (v14) lands 3 vsyncs early; the energy ball's flash (v98) 12 early, #10 |
| Cell 1st Form's transformation drift | 8.85 -> 7.57 |
| `export.py` / `version.py status` | validated / `changed=60FPS - cinematic camera` |

Closes #21

🤖 Generated with [Claude Code](https://claude.com/claude-code)

> Seeded from one merge's body, which may describe only one of the changes
> listed above: #63.

## Get this version

Download `428113C2.pnach` from the
[v26-cinematic-camera release](https://github.com/Saupernova13/pcsx2-bt3-60fps/releases/tag/v26-cinematic-camera),
or:

    git show v26-cinematic-camera:patch/428113C2.pnach > 428113C2.pnach

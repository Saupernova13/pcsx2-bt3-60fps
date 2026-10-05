# v26-cinematic-camera - DRAFT

| | |
|---|---|
| Tag | `v26-cinematic-camera` |
| Date | 2026-10-05 |
| Built on | [v25-state-phase-timers](v25-state-phase-timers.md) |
| Groups | 5 shipped group(s) changed |
| Confidence | **DRAFT - fill this in** |

> **DRAFT.** Every other note on this page is written for a player: what this
> version changes over the last one, and what was discovered on the way. Rewrite
> this before the release PR merges - its merge is what publishes the release.

## What it changed

Shipped groups this version carries that the last release did not:

- `60FPS - cinematic camera`
- `60FPS - effect track clock`
- `60FPS - rushing Blast 2 time limit`
- `60FPS - transformation flash`
- `60FPS - transformation load`

The commits to `wip/working.pnach` it carries since v25-state-phase-timers:

- fix(patch): name the group after a rushing Blast 2, not a rush blast (fdd1677)
- fix(patch): give a rushing Blast 2 its real time limit (07dbf99)
- docs: record the two effect classes behind #10 and map the rest (bc1a7bd)
- fix(patch): run scripted effect tracks and the transformation flash at 30Hz (c647c20)
- fix(patch): poll the transformation loader at the game's 30Hz (ccfa135)
- fix(patch): play cinematic camera clips at their real speed (ed92539)

## What was discovered

(fill this in)

> Seeded from one merge's body, which may describe only one of the changes
> listed above: the merge that owed this version.

## Get this version

Download `428113C2.pnach` from the
[v26-cinematic-camera release](https://github.com/Saupernova13/pcsx2-bt3-60fps/releases/tag/v26-cinematic-camera),
or:

    git show v26-cinematic-camera:patch/428113C2.pnach > 428113C2.pnach

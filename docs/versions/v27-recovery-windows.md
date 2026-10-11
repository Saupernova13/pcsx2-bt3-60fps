# v27-recovery-windows - DRAFT

| | |
|---|---|
| Tag | `v27-recovery-windows` |
| Date | 2026-10-11 |
| Built on | [v26-cinematic-camera](v26-cinematic-camera.md) |
| Groups | 1 shipped group(s) changed |
| Confidence | **DRAFT - fill this in** |

> **DRAFT.** Every other note on this page is written for a player: what this
> version changes over the last one, and what was discovered on the way. Rewrite
> this before the release PR merges - its merge is what publishes the release.

## What it changed

Shipped groups this version carries that the last release did not:

- `60FPS - recovery windows`

The commits to `wip/working.pnach` it carries since v26-cinematic-camera:

- fix(patch): let launched and blown-away fighters recover after 9 frames (2aa5cff)
- refactor(patch): tighten comments in the working pnach (2f338a1)

## What was discovered

fix(patch): let launched and blown-away fighters recover after 9 frames

This PR makes a fighter who has been launched upward or blown away wait as long as at 30fps before they can recover; at 60fps they could recover in half the time.

**Confidence: 99%**
Both windows measured equal to 30fps in the rig, and the compares are the only gates in the decompiled handlers. Only your play test is left.

## What changed

| | Before | After |
|---|---|---|
| Launched (state 206), recovery allowed when `actionFrame` > (`001E8D00`) | 8 ticks | 17 ticks |
| Blown away (213 / 214 / 223), air recovery allowed when `actionFrame` > (`001E9994`) | 8 ticks | 17 ticks |

New group `[60FPS - recovery windows]`, two words.

## Test results

Rig slot 1, a breakpoint on the first instruction inside each window, counted from P2 entering the state (`recwin.py`):

| Window opens after | 30fps | Before | After |
|---|---|---|---|
| blow-away (charged smash) | 18 vsyncs | 9 | 18 |
| launched (Square x3, Up + Triangle) | 18 vsyncs | 9 | 18 |

| Check | Result |
|---|---|
| `export.py` | 39 groups, 552 patch lines, validated |

Closes #158

🤖 Generated with [Claude Code](https://claude.com/claude-code)

> Seeded from one merge's body, which may describe only one of the changes
> listed above: #159.

## Get this version

Download `428113C2.pnach` from the
[v27-recovery-windows release](https://github.com/Saupernova13/pcsx2-bt3-60fps/releases/tag/v27-recovery-windows),
or:

    git show v27-recovery-windows:patch/428113C2.pnach > 428113C2.pnach

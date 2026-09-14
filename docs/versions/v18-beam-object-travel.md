# v18 - beam object travel

| | |
|---|---|
| Tag | `v18-beam-object-travel` |
| Date | 2026-09-09 |
| Built on | [v17](v17-blast-object-travel.md) |
| Groups | 24 (277 patch lines) |
| Confidence | **CONFIRMED IN PLAY** 2026-09-09; inherits v12's flag |

## What it changed over v17

Added `[60FPS - beam object travel]`.

Buu's charged blast runs on a sibling of the rock class, with a different layout:
`position(+0x60) += delta(+0x80)`, step scalar at `[obj+0x04]`, and the same 37.037
per-tick delta, set once at launch and never rewritten. As with the rocks, two
paths converge on one `jal Vec3Add`, at `00156004`, and hooking that single call
covers both. (The fix commit names the function `FUN_00155EE8`; the containing
function actually starts at `FUN_00155C5C`.)

## What was discovered

- **Why it was slow to find: the beam is a particle pool.** Slots are recycled, so
  the net-displacement detector that found the rocks reported an address "moving
  656 units" when it was different particles occupying the slot in turn. Requiring
  the step vector to stay constant across three consecutive vsyncs filtered the
  pool out.
- **The decisive step was a data experiment, not a code one.** Poking the delta to
  half mid-flight dropped the advance from 37.037 to 18.519 a tick and moved the hit
  v59 -> v71, proving the mechanism before any instruction was patched.
- **An enumerated site is not a tested site.** `00155FE4` was in the candidate
  family the whole time and never fires for the beam, because the branch at
  `00155FB4` skips its block.
- **Three movers, one shape**: a projectile keeps a per-tick delta vector, and the
  fix is always to halve the advance at the one `Vec3Add` the update converges on,
  never the stored delta, which other code reads.

## Evidence

Impact by the opponent's state flip, as shipped from the pnach:

| gap | 30fps | 60fps without | 60fps with |
|---|---|---|---|
| 86 | 50 | 44 | 45 |
| 657 | 81 | 59 | 76 |

The travel component paces 18.42 units a vsync in both arms - an exact match. The
residual ~5 vsyncs is the pre-launch animation, a separate defect. Inert at idle,
for plain ki blasts and for Frieza's rocks, which re-measure at v124 unchanged.

## Confirmed in play

The user also confirms **Buu's breath attack** is fixed by this group - a move that
was never measured, and evidence the hook sits on the class rather than on the one
blast it was found through.

## Get this version

    git show v18-beam-object-travel:releases/v18-beam-object-travel/428113C2.pnach > 428113C2.pnach

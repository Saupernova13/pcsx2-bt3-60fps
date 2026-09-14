# v17 - spawned projectile flight

| | |
|---|---|
| Tag | `v17-blast-object-travel` |
| Date | 2026-09-09 |
| Built on | [v16](v16-projectile-travel.md) |
| Groups | 23 (269 patch lines) |
| Confidence | **MEASURED, NOT FELT IN PLAY\*** - the user felt no change, for measured reasons; inherits v12's flag |

## What it changed over v16

Added `[60FPS - blast object travel]`.

Frieza's summoned rocks - and everything else on the same object class - are moved
by `FUN_0015BFB8`: `position(+0x30) += direction * step`, with the step at
`[obj+0x58C]` and a per-tick delta at `[obj+0x50]` of 37.037 units, identical in
both arms. Two code paths reach the move and converge on one `Vec3Add` at
`0015C28C`; the trampoline there calls the fused scale-add instead, giving
`position + delta * 0.5`.

## What was discovered

- **Buu's charged blast is also exactly 2x, via a second mover** - not this one; it
  was found in v18.
- **Frieza's rocks travelled 1.77x too fast**, and v16's integrator never touches
  them.
- **Why the user feels nothing.** The move is `pre-launch + gap / speed`, and at
  30fps the summon phase alone is 103.2 vsyncs, with the rocks crossing at 18.75
  units a vsync:

| gap | travel share of the move | what the fix can move |
|---|---|---|
| 125 | 6.7 of 110 vsyncs - 6% | 4 vsyncs (67 ms) |
| 474 | 25.3 of 128 - 20% | 11 vsyncs |
| 628 | 33.5 of 137 - 24% | 17 vsyncs (0.28 s) |

At the range anyone actually fights at, the rocks are **94% summon animation**.
The measurement was sound, and so is the user's report.

## Evidence

Impact clocked by the opponent's state flip, as shipped from the pnach:

| gap | 30fps | 60fps stock | 60fps fixed |
|---|---|---|---|
| 125 | 110 | 103 | 106 |
| 474 | 128 | 112 | 124 |
| 628 | 137 | 118 | 134 |

Travel paces 17.96 units a vsync against 30fps's 18.63. The site never fires at
idle or for a plain ki blast, so it cannot double-compensate with
`[60FPS - projectile travel]`. (status.md quotes the stock arm as 102/113; this
table is the fix commit's own measurement.)

## Still wrong in this build

The summon phase itself: 98.3 vsyncs at 60fps against 103.2 at 30, about 5 vsyncs
fast and uncompensated - the part of this move a player can actually see.

## Get this version

    git show v17-blast-object-travel:releases/v17-blast-object-travel/428113C2.pnach > 428113C2.pnach

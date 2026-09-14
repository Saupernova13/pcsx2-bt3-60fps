# v05 - blast sequence rate (withdrawn)

| | |
|---|---|
| Tag | `v05-blast-sequence-rate` |
| Date | 2026-09-06 |
| Built on | [v04](v04-blast-effect-rate.md) |
| Groups | 16 (209 patch lines) |
| Confidence | **DO NOT USE** - withdrawn in v06, restored in v07, withdrawn for good in v08 |

## What it changed over v04

Added `[60FPS - blast sequence rate]`: gates the scene-graph walker's `vtable[0]`
call at `001AD188` for a single class - vtable `002C3940`, update `FUN_001587B8`,
an action controller with a per-tick counter at `+0x14`.

## What was discovered

- **v03 and v04 were developed against a move that does not show the bug.** A
  scripted Super Kamehameha lands 6 hits and 8520 damage at both rates. The case
  actually reported - the Angry Kamehameha from the user's own capture - shows it
  plainly: the camera cuts back to the fight at 2.1s at 30fps and 1.4s at 60fps,
  with the energy ball forming at double speed.
- The sequence is mixed - 0.85s of it already correctly compensated, about 49
  ticks not - so no whole-sequence constant could fix it, and none exists.
- **Found by bisecting code instead of constants**: gate a call on frame parity,
  ask whether the camera cut moved, descend. That led through `FUN_0012CB60` to
  `FUN_001AD150`, the scene-graph walker.

## Evidence

In real time with the game running free, the cut landed at 2.0s against the
30fps game's 2.1s. The normal-battle blast schedule was byte identical.

## Why it is withdrawn

The gated controller is what **spawns** the blast's effects. Cleared as innocent
in v07 on an uncharged tap, it turned out in v08 to kill a charged blast outright.

## Get this version

    git show v05-blast-sequence-rate:releases/v5-blast-sequence-rate/428113C2.pnach > 428113C2.pnach

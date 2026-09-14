# v19 - screen fade

| | |
|---|---|
| Tag | `v19-screen-fade` |
| Date | 2026-09-09 |
| Built on | [v18](v18-beam-object-travel.md) |
| Groups | 25 (279 patch lines) |
| Confidence | **CONFIRMED IN PLAY** 2026-09-09; inherits v12's flag |

## What it changed over v18

Added `[60FPS - screen fade]`, two words.

`FUN_00172810` is the game's fullscreen fade service - a colour, a fade-in, a hold
and a fade-out. Its init at `FUN_00172718` takes durations in **seconds** and
multiplies by a hard-coded 30.0: the same defect as the tween constructor. One word
makes it 60.0, which doubles all three phase counts and their divisors together,
so the blend curve is unchanged and only its rate halves. The 180-tick hold cap at
`001728C8` is a separate literal and is doubled on its own.

## What was discovered

- **It is the fade service, not the move.** An earlier pass the same day measured
  the Galick Cannon fade at 28 ticks either way, ruled out four leads, and mistook
  the plateau for the fade.
- **The callers speak seconds, read straight from the ELF**: the static descriptors
  at `002ECCC0` and `002ECCF0` hold 0.5/1.0/0.5 and 1.0/0/1.0 seconds. So this fixes
  every fade in the game at once, not one move's flash.
- A four-site variant that halved each per-tick step measured identically. The
  one-word constructor fix shipped because it inserts no instruction into the
  fade-out, whose 1.0 is both the step and the 1.0 in `blend = 1.0 - counter/duration`.

## Evidence

Vegeta (Scouter)'s Final Galick Cannon, save state 3, per vsync on mean luma:

| arm | full white | lifts at | scene behind it |
|---|---|---|---|
| 30fps | v446..v495 | v508 | mean 170 |
| 60fps before | v437..v460 | v476 | mean 90 - the animation, exposed |
| 60fps after | v443..v491 | v504 | mean 168 |

The fall is value-for-value the 30fps curve over the same 28 vsyncs. No regression:
the ultimate's eleven state transitions land on identical vsyncs with the group on
and off, and Frieza's rocks and Buu's charged blast construct no fade node at all.

## Get this version

    git show v19-screen-fade:releases/v19-screen-fade/428113C2.pnach > 428113C2.pnach

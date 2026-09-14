# v22 - beam clash

| | |
|---|---|
| Tag | `v22-beam-clash` |
| Date | 2026-09-12 |
| Built on | [v21](v21-rush-struggle.md) |
| Groups | 27 (313 patch lines) |
| Confidence | **DURATION CONFIRMED IN PLAY** 2026-09-12, outcome not yet\*; inherits v12's flag |

## What it changed over v21

Added `[60FPS - beam clash]`.

Two beams collide, both fighters enter state 304 (`FUN_001FB660`) and rotate their
sticks. Rotations count into `fighter+0xE4C` through condition 0x33 at `001FB9BC`,
and the contest is run by an event manager, **`FUN_001D8E50`**, dispatched once per
tick from `FUN_001D9900` for modes 1..5. The fix:

- doubles every phase length - 30 -> 60, 60 -> 120, 106 -> 212, 16 -> 32 - so each
  phase lasts its 30fps real time;
- leaves the tug moving one step a tick, so over twice the ticks it reaches twice the
  magnitude - and halves the clash point constant at `gp-0x6F40` (0.05 -> 0.025), so
  the point lands where 30fps puts it and updates every frame instead of in 30Hz
  steps; phase 4 runs to 142 instead of 71;
- gates the AI's rotation query to every other tick through the human/AI flag, on its
  own trampoline at `000F1540`, and starts counting rotations at tick 32 instead of 16.

## What was discovered

- **The whole contest is on a tick clock.** 30 ticks of one fighter's introduction,
  30 of the other's, 46 in which a tug at `[m+8]` moves one step a tick toward whoever
  leads on cumulative `+0xE4C`, 16 to show the result, then a few to drive the tug out.
  The sign of the tug names the winner. `pt = tug/(|tug|+20)`; its +/-0.64
  thresholds only choose a camera mode.
- **`+0xE4C` does not start at zero.** It is seeded from the move's power and the
  characters' attributes - a head start whose weight doubles if the clash is halved.
- **Rejected: running the manager on even ticks only.** It restored the duration
  exactly and **strobed the camera** - `FUN_001D8980` and `FUN_001D8B88` re-issue a
  camera request through `FUN_001C6E78` every tick, and a skipped tick leaves the
  previous frame's camera standing. Halve a clock; never skip a call that may render.
- **The AI gate is exact.** With the 60fps base patch alone the CPU's stepping is tick
  for tick the 30fps game's (0.492 a tick, +54), and the fix reproduces the 30fps
  result outright: 72-72 idle, 91-86 at 5 rotations a second.
- **Without `beam object travel`, the clash never happens** from this save state: the
  beams cross at double speed and miss each other.
- **The CPU's shortfall in the full build is not an AI defect.** Dropping any one of 24
  groups leaves its stepping bit identical; building up from the base patch shows
  `beam object travel` (0.492 -> 0.385) and `animation clock` (-> 0.377) changing where
  the clash forms, and the AI reacting to that. (The fix commit attributed this to the
  random stream; that explanation was disproved afterwards.)
- **The player's input is still read every tick, deliberately.** Rotations count one
  per quadrant crossing: below about 7.5 rotations a second both rates see every
  crossing and the counts are identical; above it the 30fps game aliases crossings
  away (119 against 128 at 8 rotations a second).

## Evidence

The user's own save state, both sticks at a true 5 rotations a second:

| arm | clash | player | CPU | winner |
|---|---|---|---|---|
| 30fps | 4.34s | 91 | 88 | player |
| 60fps before | 2.17s | 61 | 62 | CPU |
| 60fps with this | 4.30s | 91 | 74 | player |

Shipped build across hand speeds:

| rot/s | 30fps | 60fps with this |
|---|---|---|
| 0 | CPU 31-72 | CPU 31-59 |
| 2 | CPU 55-72 | CPU 55-60 |
| 3.5 | CPU 73-75 | P1 73-69 |
| 5 | P1 91-88 | P1 91-74 |
| 8 | P1 119-88 | P1 128-74 |

## Still wrong in this build

With every group enabled the CPU ends 10-18% low, so a near-tie the 30fps game gives
the CPU - 3.5 rotations a second - goes to the player. Every other speed tested picks
the 30fps winner.

## Get this version

    git show v22-beam-clash:releases/v22-beam-clash/428113C2.pnach > 428113C2.pnach

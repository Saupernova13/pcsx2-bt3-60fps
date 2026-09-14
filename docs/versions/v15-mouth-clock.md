# v15 - mouth clock

| | |
|---|---|
| Tag | `v15-mouth-clock` |
| Date | 2026-09-08 |
| Built on | [v14](v14-camera-pacing.md) |
| Groups | 20 (251 patch lines) |
| Confidence | **CONFIRMED IN PLAY** 2026-09-08, cut-in and pre-fight intro; inherits v12's flag |

## What it changed over v14

Added `[60FPS - mouth clock]`: two hooks, at `0024ED2C` and `0024F3D4`, halving the
per-tick rate of the game's **second** clip player.

A track object holds a keyframe array at `+0x28` whose key times are shorts, a key
index at `+0x40`, a key count at `+0x42`, and two float clocks - `+0x34`, stepped in
the jump-table case at `0024ED20`, and `+0x44`, stepped in `FUN_0024F264`. Both
advance by the track's rate at `+0x2C` once per tick, and that rate is 2.0. The fix
hooks the add rather than the rate load, because `0024F290` branches straight to
`0024F3D0`, past any hook on the load.

## What was discovered

- **Cut-in speech is not skeletal animation.** `[60FPS - animation clock]` already
  paced the `model+0xB40` controller correctly; a second clip player in the same
  module, keyed on a different struct, had never been looked at. At 60fps a track
  ran off the end of its keyframes in half the real time and held the last key - a
  mouth that stops mid-sentence.
- **The ini was silently ignoring the group.** PCSXROO reads its enable list from
  its own per-game ini at boot; a group missing there applies nothing and reports
  nothing. That cost an hour, and patchctl now warns about it.

## Evidence

Vegeta (Scouter)'s Final Galick Cannon, save state 3, per-vsync film aligned to
state 287:

| arm | transitions | first | last | span |
|---|---|---|---|---|
| 30fps | 10 | v43 | v163 | 2.00s |
| 60fps, v14 | 12 | v43 | v115 | 1.20s |
| 60fps, this build | 14 | v43 | v167 | 2.07s |

5.00 open/close transitions a second against 10.00 - exactly 2x - and with the
group every one of the 30fps arm's ten beats lands within two vsyncs.

No regression: `hitclock.py --baselines` is byte identical, and neither hook fires
in ordinary battle. It does change Goku's ultimate on 90 of 170 vsyncs - the second
track object drives that shot's radial speed-line effect, which was 2x for the same
reason - but that half is not independently verified as an improvement.

## Get this version

    git show v15-mouth-clock:releases/v15-mouth-clock/428113C2.pnach > 428113C2.pnach

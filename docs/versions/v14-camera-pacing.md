# v14 - camera pacing

| | |
|---|---|
| Tag | `v14-camera-pacing` |
| Date | 2026-09-08 |
| Built on | [v13](v13-pursuit-stomp.md) |
| Groups | 19 (235 patch lines) |
| Confidence | **CONFIRMED IN PLAY** 2026-09-08; inherits v12's flag |

## What it changed over v13

Added `[60FPS - camera pacing]`.

`FUN_001C69C8` updates every camera in the game: it builds a target for the tick
and lerps the camera's euler angles toward it. Both halves were per-tick and
neither was compensated:

- **the chase** - the blend rate `$f20`, exactly 0.20 a tick in both arms, applied
  twice as often at 60fps so the camera converged in half the real time and then
  sat still;
- **the target** - a scripted camera move counts `fighter+0x558` down once a tick
  from a length in `fighter+0x55C` authored in 30Hz frames (9 for Cell's Perfect
  Barrier, 30 for the move before it).

The blend is halved on the lerp path only, after the branch that chooses between
lerping and snapping, so a scripted cut still snaps. It covers the look
direction too, which is lerped with the same rate.

## What was discovered

- **It was never a Cell problem.** Both sites are shared by every camera and every
  scripted move in the game.
- **Neither half is a fix on its own**: halving the blend alone gives 12.84 degrees
  of error, gating the move alone 14.01, both together 1.52.
- **The test harness had been lying.** `movieshot.py` and `stomptest.py` reloaded the
  save state after applying a preset. Slot 4 had been captured while patched, so
  that reload put `[60FPS - battle]` back and the "30fps" arm ran at 60fps. Slot 9
  was captured unpatched, so v13's pursuit results stand.

## Evidence

Mean absolute camera orientation error against the 30fps arm, Cell's Perfect
Barrier, shot 1: **22.96 degrees -> 1.52**, peak 89.3 -> 4.2. The orbit stops at
vsync 66 against 30fps's 70, where unpatched 60fps stopped at 34. On Goku's
ultimate, which takes no input, mean error 5.00 -> 1.93 and peak 14.6 -> 0.7.

No regression: charge 99 and ultimate 161 unchanged, the pursuit stomp still
connects, and the ordinary battle camera improves from 3.71 to 2.88 degrees
rather than going sluggish.

## Get this version

    git show v14-camera-pacing:releases/v14-camera-pacing/428113C2.pnach > 428113C2.pnach

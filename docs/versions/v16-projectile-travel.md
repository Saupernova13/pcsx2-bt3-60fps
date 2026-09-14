# v16 - projectile travel

| | |
|---|---|
| Tag | `v16-projectile-travel` |
| Date | 2026-09-09 |
| Built on | [v15](v15-mouth-clock.md) |
| Groups | 22 (261 patch lines): 21 shipped, plus an optional widescreen group that is off |
| Confidence | **CONFIRMED IN PLAY** 2026-09-09; inherits v12's flag |

## What it changed over v15

- Added `[60FPS - projectile travel]`: one hook at `00176A2C`, the effect-node
  integrator, which steps `pos += vel * [class+0x20]` once a tick with no delta-time
  term. For a plain ki blast that step is 27.7778 units a tick in both arms.
- Added `[Widescreen 19.5:9 - S24 Ultra]`, **off by default**. PCSX2's stock 16:9
  patch for this game is three words, the third an instruction - `lui $at,0x3F40`
  becoming `0x3F10`, which is 1/aspect - and the model reproduces it bit for bit;
  19.5:9 needs a widen factor of 1.625. Verified at the arithmetic (`$f20`
  0.6495191 -> 0.3991836, ratio 0.61458 as predicted), **not verified on screen**. It
  conflicts with the stock widescreen patch, and a display preference is the user's
  call, so it ships installed but disabled.

## What was discovered

- **The first fix here that changes how the game plays** rather than how it looks:
  a blast at double speed halves the time you have to dodge it.
- **Travel was separated from wind-up by fitting across ranges**, flight = fixed +
  gap/speed: 30fps 28.4 vsyncs fixed + 14.02 units/vsync, 60fps 27.2 fixed + 28.05.
  The fixed part was already right; the travel term was exactly 2.000x. One range
  on its own would have hidden it.
- **The user's EmuDeck install had been running the working pnach with all 24
  groups enabled** since at least 2026-09-05 - quarter-speed animation, no beams,
  broken ground movement, the state 157 trap - while every test ran against
  PCSXROO. `deploy.py` now refuses the groups that must never ship.
- **Buu's Flame Shower Breath is not the blast bug.** First reported as running
  long, then measured properly as state 262 running 7% fast; two earlier
  measurements had measured the wrong move.

## Evidence

Flight time by the opponent's reaction, passive-CPU training scene:

| gap | 30fps | 60fps before | 60fps after |
|---|---|---|---|
| 420 | 58 vsyncs | 42 | 57 |
| 657 | 76 | 51 | 74 |
| 842 | 88 | 57 | 87 |

Every range within two vsyncs of the 30fps game, verified as shipped from the
pnach. A breakpoint on the site never fires in an idle battle.

## Still wrong in this build

Buu's charged `L2+Up+Triangle` uses a second mover this does not touch (found in
v18), and Frieza's "I might die this time" was untested (v17).

## Get this version

    git show v16-projectile-travel:releases/v16-projectile-travel/428113C2.pnach > 428113C2.pnach

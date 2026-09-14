# v06 - blast effect duration

| | |
|---|---|
| Tag | `v06-blast-effect-duration` |
| Date | 2026-09-06 |
| Built on | [v05](v05-blast-sequence-rate.md) |
| Groups | 15 (184 patch lines) |
| Confidence | Superseded by v07 and v08 |

## What it changed over v05

- Removed `[60FPS - blast effect rate]` and `[60FPS - blast sequence rate]`.
- Added `[60FPS - blast effect duration]`: halves all **nineteen** per-tick steps
  across the two blast effect classes instead of gating their updates, so the
  geometry is still rebuilt every frame and every coupled channel moves together.

Cut in the same commit as its sibling [v06b](v06b-withdraw-broken-blast-groups.md).

## What was discovered

- **Gating an update that constructs something deletes it.** The ki aura and
  particle gates work because those updates only advance state. The blast effect
  updates rebuild the beam's geometry every frame, so skipping one does not slow
  the beam - it leaves nothing to draw. That matched the user's report exactly: no
  charge ball, no output beam, a half-built effect stuck to the hands.
- Halving one channel in isolation does nothing, because the channels are
  compared against each other. Halving all nineteen together is the fix.
- A move can be timed in real time with the game running free, not only by frame
  stepping.

## Evidence

The Super Kamehameha's beam is on screen 0.6s..1.75s at 60fps unpatched,
0.6s..2.85s with this, against the 30fps game's 0.6s..3.0s. Damage and hit count
byte identical.

## Still wrong in this build

The ultimate's camera cut is early again, since the sequence gate is out.

## Get this version

    git show v06-blast-effect-duration:releases/v6-blast-effect-duration/428113C2.pnach > 428113C2.pnach

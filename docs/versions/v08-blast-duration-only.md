# v08 - blast duration only

| | |
|---|---|
| Tag | `v08-blast-duration-only` |
| Date | 2026-09-06 |
| Built on | [v07](v07-blasts-fixed.md) |
| Groups | 15 (184 patch lines) |
| Confidence | Fine; the ultimate's blast ends early. Same group list as v11 |

## What it changed over v07

Removed `[60FPS - blast sequence rate]` for good.

## What was discovered

- **A test input that does not exercise a code path proves nothing about it.**
  v07 cleared the gate with an uncharged tap. Charged - hold Triangle, BOOST!,
  release - the gate is catastrophic: 5 hits and 1520 damage against 6 and 13680,
  and nothing renders at all, while the move still shows its banner, firing pose,
  rumble and correct duration.
- The gated controller is what spawns the effects, so running it at half rate
  loses the spawn - the same failure as the effect-rate gate, which skipped the
  geometry rebuild. **Gating suits a system that only advances state; never one
  that constructs something every frame.**

## Evidence

Charged Super Kamehameha with this build: 6 hits, 13680 damage, beam on screen
0.3s..2.7s against the 30fps game's 0.3s..2.6s, the charge rendering in the hands
and nothing left stuck to them afterwards.

## Still wrong in this build

The ultimate's camera cut is early again, stated as known-not-fixed in the file's
own header.

## Get this version

    git show v08-blast-duration-only:releases/v8-blast-duration-only/428113C2.pnach > 428113C2.pnach

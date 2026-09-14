# v03 - blast hit cadence

| | |
|---|---|
| Tag | `v03-blast-hit-cadence` |
| Date | 2026-09-06 |
| Built on | [v02](v02-airborne-and-hover.md) |
| Groups | 14 (165 patch lines) |
| Confidence | Measured against the 30fps oracle; superseded |

## What it changed over v02

Added `[60FPS - blast hit cadence]`.

Every attack's hitbox carries a tick counter at `H[0x0A]`, where `H` is
`[obj+0x60]`. `FUN_001AFE70` advances it once a tick, and a hit lands when it
reaches an interval authored **in ticks** in the move's data record
(`D[0x0B]`, at `[[obj+0x64]+0x24]`). The same counter paces the attack's whole
life: it ends once the hits landed, `H[0x0B]`, exceed the maximum `D[0x0A]`.
`FUN_0012E7C8` is the only thing that increments it and `001AFE98` is its only
caller, so one frame-parity gate on that call fixes the cadence and the duration
together. The first hit is never delayed - the `blez` at `001AFF08` short-circuits
while no hits have landed - so single-hit melee is untouched.

## What was discovered

- The reported "ki blasts cut short, fewer hits" was a blast firing its hits twice
  as fast and spending its hit budget in half the real time.
- It took two passes to reproduce. Four first hypotheses were all wrong, one
  measurement was contaminated by its save state, and input had to be scripted in
  **ticks rather than vsyncs** before the defect showed as 28 vsyncs against 16.
  The beam is `FUN_00186250`.

## Evidence

Same save state and scripted input: hits every 8 vsyncs spanning 32, against 4
and 16 unpatched at 60fps. Damage and hit count identical either way. Confirmed
end to end through the cheat engine, not only by direct pokes.

## Still wrong in this build

The blast's launch flash still plays at double speed, stated in the file's own
header. This fix changes when damage lands, not what is drawn - which v04 found
the hard way.

## Get this version

    git show v03-blast-hit-cadence:releases/v3-blast-hit-cadence/428113C2.pnach > 428113C2.pnach

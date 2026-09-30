# v24 - the idle taunt, stage scenery and Solar Flare

| | |
|---|---|
| Tag | `v24-state-phase-timers` |
| Date | 2026-09-17 |
| Built on | [v23](v23-known-issues-refresh.md) |
| Groups | 33 (557 patch lines) |
| Confidence | **CONFIRMED IN PLAY** 2026-09-17 for the taunt, the stage, Solar Flare and Hercule's grenades; the state phase timers also carry a standing caveat below |

## What it changed over v23

Six groups, the largest batch since the early versions. Four are fixes the user
reported and then played; two are display options.

**The idle taunt, and 21 clocks behind it.** `[60FPS - state phase timers]`
returns to the shipping set, minus the one site that caused the state 157 trap.
`FUN_001EE968`, the idle handler, counts to `0x5B` - 91 frames authored at 30Hz -
then hands over to state 67, the taunt, so at 60fps an idle fighter taunted in
half the real time. The group also paces the 21 remaining per-tick counters
inside the fighter state machine: every attack, charge, block and recovery was
expiring in half its real time. Measured from a match-start state, counting took
180 vsyncs unpatched, ~90 on v23, and 180 again with the group.

| | Before | After |
|---|---|---|
| Idle fighter taunts after | ~1.5s | 3.0s, matching 30fps |
| Sites the group gates | - | 21 clocks (was 22, one was an index) |

**The stage's own scenery.** `[60FPS - stage animation]` halves one data word,
`001153C8`. A stage's moving props are a scene graph with keyframe tracks whose
time index advanced by a bare `2.0` a tick - 60 units a second at 30Hz, 120 at
60Hz. The World Tournament blimp and its banners were the visible symptom.

| World Tournament - Noon, 80 vsyncs | stage time |
|---|---|
| unpatched 30fps | 94 -> 172, **+78** |
| v23 | 122 -> 280, +158 |
| v24 | 92 -> 171, **+79** |

**Solar Flare.** `[60FPS - solar flare]` keeps the victim's blind timer
(`fighter+0x0FF8`) and its white flash on real time. The lock-off lasted 1.25s
at 60fps against 2.50s at 30fps.

**Hercule's grenades.** `[60FPS - thrown object rate]` runs both of Hercule's
ki-blast updates - tapped and charged - on even ticks. `[60FPS - projectile
travel]` never reached them; they are objects with their own update, and
everything in it is counted in ticks: flight, gravity, spin, debris, fuse and
explosion.

**Two display aspects.** `[Widescreen 16:10]` and `[Widescreen 21:9]` join the
existing 19.5:9 group, all switched off by default. "21:9" is a marketing name:
the group carries 64:27, which is what the format defines.

## What was discovered

- **The one site that made phase timers unsafe was an index, not a clock.**
  `001E6F40`, inside `FUN_001E6DC8` - which IS state 157 - walks a table at
  `sll i,1` / `addu s2` / `lh [+6]` and exits on `i >= N-1`. Gating an index made
  that state advance by nothing on odd ticks and never leave. Classifying all 22
  sites found 21 clocks and this one index. It is out.
- **Halving a step is not interchangeable with running on even ticks.** For
  thrown objects the half step sampled positions 30fps never visits, and
  collision is tested at the sampled positions: the charged blast's second bounce
  clipped a rock lip and came to rest 70 units off, 31 vsyncs late. Running the
  update at 30Hz reproduces the 30fps outcome; halving does not.
- **The stage evaluator never runs on Rocky Area at all**, so issue #11's Rocky
  Area wind is a different system and is untouched here.

## Known not fixed

Unchanged from v23, plus one new item from the same play-test:

- **A fighter can freeze mid-combo with its model strobing on alternate frames**
  (issue #39). Reported under this group set and not yet reproduced. The state
  157 trap was never triggered on demand either, so both need a bisect before
  the phase-timer group can be called settled.
- An ultimate's beam still lands its first hit about half a second early.
- Frieza's rocks and Buu's charged blast still have a ~5-frame pre-launch
  overshoot.
- Some pre-fight intro animations are paced wrong against the camera.
- In a beam clash the CPU ends a little weaker than at 30fps at a middling
  rotation speed.
- Death by a body-erasing attack: the camera has never been re-checked.

## Get this version

Download `428113C2.pnach` from the
[v24 release](https://github.com/Saupernova13/pcsx2-bt3-60fps/releases/tag/v24-state-phase-timers),
or:

    git show v24-state-phase-timers:patch/428113C2.pnach > 428113C2.pnach

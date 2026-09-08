# Build confidence ladder

Which build to trust, and why. Set by testing **in play**, not by measurement.
Newest at the top. `releases/latest/` currently holds **v15**.

| Build | Groups | Confidence | Ultimate's blast | Notes |
|---|---|---|---|---|
| `v15-mouth-clock` | 20 | **FIXED, NOT YET PLAY-TESTED** | correct | Adds `mouth clock`; inherits v12's flag and v14's star |
| `v14-camera-pacing` | 19 | **FIXED, NOT YET PLAY-TESTED** | correct | Adds `camera pacing`; inherits v12's flag. **Starred pending the user's own play-test** |
| `v13-pursuit-stomp` | 18 | **FIXED, NOT YET PLAY-TESTED** | correct | Adds the two pursuit groups; inherits v12's flag |
| `v12-restore-sequence-wait` | 16 | **FINE, FLAGGED** | correct | Carries the input-timing flag below |
| `v11-back-to-v8-set` | 15 | **DEFINITELY FINE** | **ends early** | The known-good baseline. Fall back here |
| `v10-withdraw-phase-timers` | 16 | superseded | correct | Identical group list to v12 |
| `v9-scripted-clocks` | 17 | **DO NOT USE** | correct | State 157 trap |
| `v8-blast-duration-only` | 15 | fine | ends early | Same group list as v11 |
| `v7-blasts-fixed` | 16 | superseded | - | Contained the withdrawn sequence-rate gate |
| `v5`, `v4` | 16, 15 | **DO NOT USE** | - | Withdrawn: gating deleted the beam |

## v11 - DEFINITELY FINE

The baseline. Confirmed in play: no state 157 trap.

**Its known tradeoff is accepted, not a defect.** The ultimate's blast ends
early, because `[60FPS - sequence wait]` is absent. Do not re-open that as a bug
against this build - it is the price of the build.

Fall back here if anything later misbehaves.

## v12 - FINE, WITH A STANDING FLAG

Confirmed in play: no trap, and the ultimate's cinematic and charge are correct
again. Differs from v11 by exactly one group, `[60FPS - sequence wait]`.

> **FLAG: POTENTIAL INPUT TIMING ISSUE.**
> This build and **every build from here forward** may carry an input timing
> problem. Reported by the user, currently unconfirmed and uncharacterised.
> Every later build inherits this flag until it is explicitly cleared by
> testing. If input feel is ever in question, compare against v11 first.

## v13 - the pursuit stomp

Adds `[60FPS - knockback flight]` and `[60FPS - pursuit timing]` to the v12 set.
Fixes the heavy smash into Circle pursuit stomp, which missed at 60fps and
landed every time at 30. Five separate durations authored in 30Hz frames, in one
chain; see findings.md for the derivation.

Verified by automated test, not yet by the user:

- Nine press delays from 5 to 45 vsyncs. Before: 0 of 9 connect. After: 9 of 9,
  within 1-3 vsyncs of the 30fps arm at every delay.
- Confirmed with the VM running free and the pad on the wall clock
  (`python tools/stomptest.py --presets off nopursuit full`), which is a
  different instrument from the frame-stepped sweep and agrees with it.
- The charge and ultimate oracles are unchanged to the vsync, so nothing that
  already worked moved.

`nopursuit` is the 16-group v12 set, kept as a named preset so this can be
switched off without editing anything.

**It inherits v12's input-timing flag** - nothing here clears it.

## v14 - camera pacing

One group, `[60FPS - camera pacing]`, and it is not a Cell fix - it is the
camera system. `FUN_001C69C8` updates every camera in the game and lerps its
euler angles toward a per-tick target; both the blend rate (`$f20`, a flat 0.20
a tick) and the scripted camera-move countdown (`fighter+0x558`, a length in
`fighter+0x55C` authored in 30Hz frames) are per-tick and were uncompensated.

Mean absolute camera orientation error against the 30fps arm, Cell's Perfect
Barrier, shot 1: **22.96 degrees -> 1.52**. Peak 89.3 -> 4.2. Halving the blend
alone gives 12.84 and gating the move alone 14.01, so **neither half is a fix on
its own** and `nocamera` (the 18-group v13 set) is kept as a named preset for
diffing.

Global, measured rather than assumed: on Goku's ultimate from save state 8,
which takes no input at all, mean error goes 5.00 -> 1.93 and peak 14.6 -> 0.7.

Confirmed by contact sheet at 0.12s on the wall clock: the fixed arm matches the
30fps arm tile for tile through the orbit, where unpatched 60fps is a beat ahead.

No regression - charge 99, ultimate 161, pursuit stomp still connects, and the
**ordinary** battle camera improves from 3.71 to 2.88 degrees rather than going
sluggish.

**It inherits v12's input-timing flag** - nothing here clears it.

Also in this build: `movieshot.py` and `stomptest.py` no longer reload the save
state after applying a preset. Save state 4 was captured while patched, so that
reload put `[60FPS - battle]` back and the "30fps" arm ran at 60fps. Slot 9 was
captured unpatched, so the v13 pursuit results are unaffected.

## v15 - mouth clock

Adds `[60FPS - mouth clock]`: two hooks, at `0024ED2C` and `0024F3D4`, halving
the per-tick rate of the game's **second** clip player. That player drives the
keyframe tracks a scripted cut-in uses - the mouth among them - and its rate is
2.0 a tick, so at 60fps a track burned its keyframe array in half the real time
and held the last key.

Measured per vsync on Vegeta (Scouter)'s Final Galick Cannon, save state 3, on a
frame-advance film aligned to the first vsync of state 287:

| arm | transitions | first | last | span |
|---|---|---|---|---|
| 30fps unpatched | 10 | v43 | v163 | 2.00s |
| 60fps, v14's 19 groups | 12 | v43 | v115 | 1.20s |
| 60fps, this build | 14 | v43 | v167 | 2.07s |

5.00 open/close transitions a second against 10.00 - exactly 2x - and with the
group the final phrase, which v14 skips entirely, plays again. Every one of the
unpatched arm's ten beats lands within two vsyncs.

No regression: `hitclock.py --baselines` is byte-identical with the group on,
neither hook fires at all in ordinary battle, and the whole-frame difference from
the 30fps reference over the Vegeta cut-in is unchanged at 3.46.

It does change Goku's ultimate, on 90 of 170 vsyncs: the second track object
drives that shot's radial speed-line effect, which was running at 2x for the same
reason. The hit counters land on identical vsyncs either way, so the schedule is
untouched - but this half is **not independently verified as an improvement**,
only as the same correction for the same cause. Worth a look in play.

**It inherits v12's input-timing flag and v14's unverified camera fix.**

## The state 157 trap

Goku parks in fighter state 157 (`FUN_001E6DC8`), an airborne dash/flight state,
with pending state `0xFFFFFFFF` - no queued transition - and no button held. The
game keeps ticking normally; only that fighter is trapped. A save-state reload
clears it.

Seen on v9 (17 groups). Not seen on v11 (15) or so far on v12 (16). The group
that differs and is out of both is `[60FPS - state phase timers]`, which is the
only group that gates counters **inside the fighter state machine** and whose 28
sites were all validated against two **grounded** oracles - a held charge and a
mashed rush. No airborne state was ever tested, and the trap is airborne.

That is a strong circumstantial case, not a proof. It was never reproduced under
controlled conditions.

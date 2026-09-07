# Build confidence ladder

Which build to trust, and why. Set by testing **in play**, not by measurement.
Newest at the top. `releases/latest/` currently holds **v13**.

| Build | Groups | Confidence | Ultimate's blast | Notes |
|---|---|---|---|---|
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

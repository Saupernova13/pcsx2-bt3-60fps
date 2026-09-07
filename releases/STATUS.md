# Build confidence ladder

Which build to trust, and why. Set by testing **in play**, not by measurement.
Newest at the top. `releases/latest/` currently holds **v12**.

| Build | Groups | Confidence | Ultimate's blast | Notes |
|---|---|---|---|---|
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

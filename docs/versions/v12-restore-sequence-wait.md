# v12 - sequence wait restored

| | |
|---|---|
| Tag | `v12-restore-sequence-wait` |
| Date | 2026-09-07 |
| Built on | [v11](v11-back-to-v8-set.md) |
| Groups | 16 (204 patch lines) |
| Confidence | **FINE, WITH A STANDING FLAG** - confirmed in play |

## What it changed over v11

Restored `[60FPS - sequence wait]`. The group list is identical to
[v10](v10-withdraw-phase-timers.md); `state phase timers` stays withdrawn.

The user confirmed v11 did not trap, but the ultimate's blast went back to
ending early - exactly what `sequence wait` fixes and what its removal predicted.

## What was discovered

- **The state 157 trap** was seen on v09 (17 groups) and not on v11 (15) or v12
  (16). The group out of both is `state phase timers`, the only one that gates
  counters inside the fighter state machine, validated only against grounded
  oracles while the trap is airborne. A strong circumstantial case, never proven.

## Evidence

Checked by exact comparison against the declared patch words rather than a
heuristic: all 20 of `sequence wait`'s words matched live RAM, including four that
are legitimately zero because they are nops in delay slots, and all 22
phase-timer sites still read the stock ELF word.

## Confidence

Confirmed in play: no trap, and the ultimate's cinematic and charge are correct
again.

> **FLAG: potential input timing issue.** Reported by the user, never confirmed
> and never characterised. This build and every build after it inherits the flag
> until testing clears it. If input feel is ever in question, compare against v11.

## Get this version

    git show v12-restore-sequence-wait:releases/v12-restore-sequence-wait/428113C2.pnach > 428113C2.pnach

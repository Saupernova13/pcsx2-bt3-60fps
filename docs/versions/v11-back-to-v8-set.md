# v11 - back to the v08 group set

| | |
|---|---|
| Tag | `v11-back-to-v8-set` |
| Date | 2026-09-07 |
| Built on | [v10](v10-withdraw-phase-timers.md) |
| Groups | 15 (184 patch lines) |
| Confidence | **DEFINITELY FINE** - the known-good baseline, confirmed in play |

## What it changed over v10

Removed `[60FPS - sequence wait]`. The group list is byte-identical to
[v08](v08-blast-duration-only.md).

A rollback at the user's call to isolate a fault, not a verdict on the group:
the state 157 trap had survived withdrawing `state phase timers`, and the two
integer-clock groups were what separated v09 from v08.

## What was discovered

- **Shrinking a live group leaves its dropped hooks patched in RAM**, because
  patchctl can only restore addresses the pnach still names. The hooks were
  restored by hand before the swap - `00158910` and `00158948` read the stock ELF
  word again and the `000F0AC0-0B04` trampoline was zeroed. Verified, not assumed.

## Confidence

Confirmed in play: no state 157 trap. Its known tradeoff is accepted, not a
defect: the ultimate's blast ends early, because `sequence wait` is absent. Fall
back to this build if anything later misbehaves.

## Get this version

    git show v11-back-to-v8-set:releases/v11-back-to-v8-set/428113C2.pnach > 428113C2.pnach

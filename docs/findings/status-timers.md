# Fighter status timers

The per-tick status timer block: paralysis, Solar Flare's lock-off, the combat timers.

## 2026-09-17 - issue #32, Solar Flare's lock-off: half its time

SuperCombo lists Solar Flare as "causes opponent to lock off, staggers
opponent" without a duration, so the 30fps game is the oracle. Krillin has it
and After Image Strike, so save state 3 is Krillin 66 units from a standing
Ultimate Gohan on Rocky Area - Evening
(`work/state-backups/rocky-krillin-vs-standing-gohan.p2s`). He is roster index 4,
eight `Up` from Babidi.

### Two timers, one of them wrong

`L2` + `Circle`. The stagger is Gohan's state 198, and it is 50 vsyncs at 30fps
and at 60fps - animation-paced and already right. Differencing Gohan's fighter
against a run that cast nothing finds the other one: `fighter+0x0FF8`, armed to
75 at `001C82F4` and falling one a tick, with `+0x0FFC` following it.

`FUN_001E1D20`, the same per-tick status block that holds paralysis (#28), sets
flags `0x93`, `0x137` and `0x96` while `+0x0FF8` is positive - the lock-off -
and moves `+0x0FFC`, the white flash, toward twice the timer by at most 15 a
tick through `FUN_001DC030`, its only caller.

| arm | timer runs | flash peaks | flash rise per 2 vsyncs |
|---|---|---|---|
| 30fps | 150 vsyncs, 2.50s | 132 at +18 | 15 |
| every shipped group | 75 vsyncs, 1.25s | 132 at +9 | 30 |

### The load is not on every path

The first hook replaced the load at `001E1F30` and changed nothing. A breakpoint
on the helper never fired: when the victim is not paralysed, `001E1EB0 blezl`
loads `+0x0FF8` in its delay slot at `001E1EB4` and jumps to `001E1F34`, past
the hook. `001E1F30` only runs while paralysed.

`[60FPS - solar flare]` hooks the decrement itself, `001E1F3C`, which every path
reaches after the `<= 0` test, so a finished timer never sees the helper. Its
delay slot, `li $a1, 0x93`, is left alone. The flash call at `001E1F74` goes
through a helper that zeroes the step on odd ticks and jumps to
`FUN_001DC030`.

| arm, from the pnach | timer runs | flash peaks | flash rise per 2 vsyncs |
|---|---|---|---|
| every shipped group + this | 150 vsyncs | 132 at +18 | 15 |

### After Image Strike is already #20

Krillin's other Blast 1, "Effect lasts 15 Seconds", arms `+0x0E08` and the
`+0x0F64` stat slots - the same `$s6` stores as the buffs. 15.00s at 30fps,
7.50s shipped, 15.00s with `[60FPS - buff duration]`. Recorded on PR #25.

### Checked and correct

- **Wizard Barrier** (Babidi, "Lasts 2.5 Seconds"): state 254 for 144 vsyncs,
  2.40s, at 30fps and at 60fps with every shipped group.

### Not established

- **Other Solar Flare users.** Only Krillin's was cast; the timer and flags are
  on the victim and shared.

## 2026-10-10 - issue #143: the freeze on guard counters and smash clashes

Found by reading BT3-Decompiled, not by a RAM diff. `BtlChars_UpdateFreeze`
(`src/battle/btl_char_mgr.c`, `FUN_001C0CB8`) runs once a tick:

- a pending freeze (`freezeNext`, `fighter+0x1324`) waits `freezeDelay`
  (`+0x1328`) ticks, then becomes the freeze (`freeze`, `+0x1320`);
- the freeze falls one a tick; while it is positive every phase skips the
  fighter (`BtlChar_IsFrozen`).

The pending values are set in ticks where a contact resolves
(`src/battle/btl_char_hit.c`, which calls the fields `stopLen` / `stopDelay`):

| Function | Case | Length, delay | Words |
|---|---|---|---|
| `BtlHit_ApplyGuard` | guard results 7 (push stop) and 8 (guard counter), attacker | 2, 1 | `001C7E08`, `001C7E0C` |
| `BtlHit_ApplyGuard` | result 7, defender | 3, 0 | `001C7F2C` |
| `BtlHit_ApplyGuard` | result 8, defender | 3, 0 | `001C7F3C` |
| `BtlHit_CheckClash` | two smashes of the same kind, both | 6, 0 | `001C9144` |
| `BtlHit_CheckClash` | mixed kinds, both | 2, 0 | `001C9190` |

The same function also freezes the other fighter for one tick per request
while a fighter holds flag `0x125` or `0x126` (cinematics, throws); that
freeze follows the flags and has no length of its own.

Rig slot 7, P2 holds Square 20 vsyncs, P1 presses Up + Square in the window
(a Z-Counter, result 8):

| | P1 `+0x1320` | P2 `+0x1320` | P1's counter (57, 43) |
|---|---|---|---|
| 30fps | 3 ticks, 6 vsyncs | 2 ticks after 1, 4 vsyncs after 2 | 14, 14 vsyncs |
| test build | 3 vsyncs | 2 after 1 | starts 3 vsyncs early |
| with `[60FPS - hit-stop]` | 6 vsyncs | 4 after 2 | 14, 13 vsyncs |

`[60FPS - hit-stop]` doubles the six values. A freeze of 3 ticks written
straight into P2 lasts 6 vsyncs at 30fps and 3 without the group
(`work/tools-scratch/specs/forcestop.json`).

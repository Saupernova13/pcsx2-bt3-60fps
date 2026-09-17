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

# Fighter status timers

The per-tick status timer block: paralysis, Solar Flare's lock-off, the combat timers.

## 2026-09-17 - issue #28, paralysis: half its published duration

SuperCombo lists 24 paralysis Blast 1s with a duration, "paralyzes opponent for
N seconds or less". Nothing in this project had ever measured one.

### The scene

Babidi has Demon Eye (4 seconds) and Wizard Barrier (2.5 seconds), so one
character tests two published timers. He is roster index 60, row 8 column 4,
five `Down` and one `Right` from Hercule. Save state 6 is Babidi against a
standing Ultimate Gohan on Rocky Area - Evening, drifted to 60 units apart
(`work/state-backups/rocky-babidi-vs-standing-gohan.p2s`). At the match-start
distance of 227 units Demon Eye fires and never arrives.

Demon Eye is `L2` + `Circle`. Babidi casts in state 253; Gohan is paralysed in
state 211 and recovers through 56.

### Measured

| arm | paralysed from | duration |
|---|---|---|
| 30fps | v56 | **240 vsyncs, 4.00s** |
| `60FPS - battle` only | v32 | 120 vsyncs, 2.00s |
| every shipped group but beam object travel | v33 | 120 vsyncs |
| the same plus `state phase timers` | v33 | 120 vsyncs |

The 30fps arm hits the published 4 seconds exactly. The phase-timer group does
not reach it.

### One decrement, several arming paths

Sampling Gohan's fighter every 20 vsyncs through the paralysis finds one word
falling by 10 each sample: `fighter+0x0FE0`, 119 to 0. A write watchpoint
finds the arming at `001CBC18` (from move data via `FUN_00212760`) and the
decrement at `001E1EE0`. `FUN_00204200` also adjusts it, so the arming value is
not one site; the decrement is.

```
001E1ED4  lw    $v0, 0xFE0($s1)
001E1EE0  addiu $v0, $v0, -1        once a tick while positive
001E1EE8  sw    $v0, 0xFE0($s1)
001E1F10  addiu $v0, $v0, -3        and 3 more when FUN_001D4D98(0x100000)
```

The `-3` is the "or less": mashing shortens it. It fires per press, so it is
left alone.

`[60FPS - paralysis]` replaces the load at `001E1ED4` with a call to a 6-word
helper at `000F1700` that adds the tick's parity to the loaded value, so the
`-1` nets to nothing on odd ticks. `$t0`, which it uses, appears nowhere in the
function.

| arm, from the pnach | duration |
|---|---|
| every shipped group but beam object travel, plus this | 239 vsyncs |
| `60FPS - battle` plus this | 240 vsyncs |

### The same function holds ten more countdowns

The decrement sits in the fighter's per-tick update (`FUN_001E1D20`, which
Ghidra calls `FUN_001e23d0`), after the state dispatch and the meter economy.
It is a block of status timers, every one per tick, none compensated:

| site | field | behaviour |
|---|---|---|
| `001E1E3C` | `+0x0D48` | -1 while positive |
| `001E1E98` | `+0x1036`, 50 bytes | +1 each, capped at 100 |
| `001E1F3C` | `+0x0FF8` | -1, sets flags 0x93, 0x137, 0x96 while positive |
| `001E1F88` | `+0x0FE8` | -1 |
| `001E1FAC` | `+0x0FE4` | -1, sets flag 0x96 |
| `001E1FD4` | `+0x0DE4` | -1 unless a state flag |
| `001E1FF8` | `+0x0E40` | -1 on a condition |
| `001E2008` | `+0x0FF0` | -1 while flag 0x13 |
| `001E21C4` | `+0x0D88` | +1 in states 0x89-0x8C |
| `001E2394` | `+0x1580` | -1 in one mode |
| `001E23AC` | `+0x0964` | +1, the ticks-in-state counter |

Which mechanic each one is has not been established. The 50-byte array climbing
to 100 is shaped like SuperCombo's "option anti-repetition system", which
remembers what a combo has already used. Each needs a move that arms it and a
30fps arm before it is touched.

### Not established

- **Mashing.** The COM does not mash, so the per-press subtraction was read,
  not measured.
- **Paralysing Smash Ki Blasts** share the decrement but were not cast.
- **Demon Eye misses entirely on v23**, because `[60FPS - beam object travel]`
  halves the beam's speed and not its life. That is #29.

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

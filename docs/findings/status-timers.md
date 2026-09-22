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

## 2026-09-17 - issue #34, the combat timers

Paralysis (#28) exposed a block of per-tick countdowns in the fighter update,
`FUN_001E1D20`. Mapping each timer's arming site back to the state table named
most of them, and exercising the moves SuperCombo describes armed five.

### Which move arms which timer

Save state 4 is Goku (Early) against a standing Ultimate Gohan
(`work/state-backups/rocky-goku-early-vs-standing-gohan.p2s`); a script dashes in
(`Up` + `Cross` until 20 units) and then plays an input. Goku's Rushing
Techniques are, in slot order, Heavy Finish, Kiai Cannon, Flying Kick and Heavy
Finish, so `Square` then `Triangle` is Heavy Finish.

| field | armed by | what it does |
|---|---|---|
| `+0x0D48` | every hit taken; states 250, 252 | combo timer, re-armed to ~32 per hit |
| `+0x1036`, 50 bytes | hits | a used option's byte drops to 0 and climbs 1 a tick, capped at 100 |
| `+0x0FF0` | the end of hitstun or stun (states 189-204) | 14 ticks |
| `+0x0DE4` | the attacker's Ground Slash (states 174-179) | 30 ticks, paused while a state flag holds |
| `+0x0E40` | the attacker after a Blast 2 cinematic (states 298-306, 313-315) | 59 ticks |

The byte array is the shape of SuperCombo's "option anti-repetition system":
options that cannot repeat within a combo, a combo being hits that do not drop
the hit counter.

### Measured

| timer | 30fps | shipped | shipped + `[60FPS - combat timers]` |
|---|---|---|---|
| combo `+0x0D48`, Heavy Finish | 204 | 167 | 198 |
| after hitstun `+0x0FF0`, Heavy Finish | 28 | 14 | 28 |
| repetition byte back to 100 | 198 | 99 | 199 |
| `+0x0DE4`, Ground Slash | 68 | 39 | 69 |
| `+0x0E40`, Frieza's I Might Die This Time rocks from save state 7 | 118 | 59 | 119 |

The combo timer's remaining 6 vsyncs is where the last hit lands: it is
re-armed per hit, and the stun before it is 116 vsyncs at 30fps and 114 at 60fps.

### Delay slots decide the hook shape

- `+0x0D48` and `+0x0E40`: `addiu` then `sw`. A `jal` on the `addiu` would
  store before the helper runs, so the helper stores and the `sw` becomes a
  `nop`.
- `+0x0FF0`: the decrement is in `blez`'s delay slot. The hook is on the next
  instruction, whose helper undoes the `-1` on odd ticks, stores, and replays
  the `dmove`.
- `+0x0DE4`: decrement and store are reached through a `blezl` and a `bnez`,
  both with the work in their delay slots, and every nearby instruction is a
  branch or a call. `001E1FC4`-`001E1FD8` is replayed in a trampoline.
- The repetition loop's helper sets `$ra` past the loop on odd ticks.

### Not established

- **`+0x0D88`**, +1 a tick in states 0x89-0x8C, and **`+0x1580`**, state 4 in one
  game mode, were not investigated.
- **In play.** Whether a combo that drops or connects at 30fps now does the same
  at 60fps was not scripted.

## 2026-09-22 - issue #34, the last two: a shrugged-off hit and the hurt face

`+0x0FE8` and `+0x0FE4` were left out above because nothing tried armed them.
Every load and store of either offset in the ELF sits in four functions, and
both timers turn out to be cosmetic.

| field | armed by | read by | what it does |
|---|---|---|---|
| `+0x0FE8` | `001C9FF4`, 3, in the hit resolver `FUN_001C9B50` on hit result 2 | `FUN_001DFE30` | the victim shakes sideways by 0.25 units, the sign flipping with the timer's low bit |
| `+0x0FE4` | `FUN_001CF220`, 30, on the victim at every step of damage dealt over time | the countdown itself | sets flag `0x96` each tick; `FUN_001D1808` puts the face (`model+0x1664`) in mode 5 while it is set |

**Hit result 2 is a hit shrugged off, not a guard.** A pad-2 guard blocked a
five-hit rush, a Rush Ki Blast, a held smash and a rush ending in `Triangle`
without any of them reaching the result. Result 2 is forced for ordinary hits
while the victim's `+0x0E18` is positive, and `+0x0E18` is a Blast 1 buff:
`FUN_002004C8` arms it from skill flag `0x400`. That is False Courage,
"cannot be stunned by Ki Blasts & Melee Attacks": Hercule's (`L2`+`Circle`,
state 253) armed it to 224 ticks against SuperCombo's 7.5 seconds. The same result also comes from a resistance
check (`+0x0E14`, a second buff, and state flags on both sides) that was not
exercised.

Flag `0x96` is one of the three flags Solar Flare's lock-off sets, and the
states after Drain Life's launch set it too. Through Drain Life the face was in
mode 5 on every tick the flag was set and never otherwise. The camera frames
Cell during the drain, so the face was not seen in a capture.

Both countdowns decrement shortly before a call, so the hook replaces the
decrement with a `jal` whose delay slot is the `move $a0, $s1` that follows.
The helper returns the decremented value with the odd tick added back and the
original store runs.

Save state 7, Cell (2nd Form) against a pad-2 Ultimate Gohan
(`rocky-vs2p-cell2-near-gohan.p2s`), from the pnach. The shake with `+0x0E18`
written on Gohan and one `Square`; the face after Drain Life's last drain step
(the move re-arms it five times at 30fps):

| | 30fps | v24 | v24 + `[60FPS - combat timers]` |
|---|---|---|---|
| `+0x0FE8` per vsync after the hit | 3, 3, 2, 2, 1, 1 | 3, 2, 1 | 3, 3, 2, 2, 1, 1 |
| `+0x0FE4` after Drain Life's last step | 60 vsyncs | 30 | 60 |

The victim stays in idle, state 11, through the shrugged-off hit in every arm.

### A rig trap found on the way

`Roo.input_release()` releases pad 2 as well. A script that holds a pad-2
guard with `input.set ... pad=1` and then releases pad 1 with `input_release()`
drops the guard on the same frame; `input_set()` with no buttons releases pad 1
alone.

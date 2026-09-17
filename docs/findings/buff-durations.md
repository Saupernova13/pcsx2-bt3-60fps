# Blast 1 buffs and timed status effects

The durations behind Blast 1 stat boosts and After Image Strike.

## 2026-09-16 - issue #20, the Blast 1 buffs: the wiki is the oracle

Every other fix in this project needed a 30fps arm to say what "right" is.
This one did not. SuperCombo publishes Blast 1 buff durations **in seconds**,
so the number to hit was known before the emulator started - and the 30fps game
reproduced it exactly, which is the check that the oracle is the right one.

### Getting to the move

Vegeta (Scouter) is already in save state 3, and his Saiyan Soul is published
at **1.9 seconds to cast, effects last 20 seconds**, for 3 Blast Stock.

**A Blast 1 is Circle tapped while L2 is held**, and the D-pad picks which one:

| input | state | cast |
|---|---|---|
| `L2` + `Circle` | 253 | 72 vsyncs - Explosive Wave, 1 stock |
| `L2` + `Up` + `Circle` | **254** | **112 vsyncs** - Saiyan Soul, 3 stock |

112 vsyncs is 1.87 seconds against a published 1.9. That is the confirmation
that `Up` selects the second Blast 1, before any of the rest was measured.

### Finding the timer without knowing what to look for

Sample the whole fighter (0x1600 bytes, 1408 words) every 40 vsyncs for 1440,
twice - once having cast the buff and once having pressed nothing - and keep
the words that fall monotonically in the first run and not in the second. Nine
words survive, and six of them are the same number:

| offset | start | rate |
|---|---|---|
| `+0x0E14`, `+0x0E1C` | 594 | 1 per 2 vsyncs |
| `+0x0F64`, `+0x0F7C`, `+0x0F94`, `+0x0FAC` | 594 | 1 per 2 vsyncs |
| `+0x0D80`, `+0x0E20` | 50000 | falls to 0 over the same window |

600 ticks at 30Hz is 20 seconds. The four at stride `0x18` are the stat slots -
Saiyan Soul boosts Attack, Super, and activates Brickwall.

**The control run is what makes this cheap.** A fighter is full of counters
that always run; differencing against a run that cast nothing leaves nine
candidates out of 1408, and the answer is visible without reading any of them.

### One register carries every duration

Write watchpoints land on two different decrement sites - `00200B00` for the
`+0xE14` pair and `001C32D0` for the `+0xF60` array - which looks like two
fixes. Following the *arming* write instead lands somewhere better:

```
00200558  jal  002123B0             the move's duration, in frames
0020055C  move $s6, $v0             <- the ONE place $s6 is set
00200620  sw   $s6, 0xE08($s1)
00200688  blez $s6, 002006C0
00200690  div  $zero, $s5, $s6      a per-tick amount = total / duration
002006A4  sw   $v0, 0xE10($s1)
00200754  sw   $s6, 0xE14($s1)
00200778  sw   $s6, 0xE18($s1)
00200860  move $t1, $s6             -> FUN_001C3410, the four stat slots
00200A08  sw   $s6, 0xE1C($s1)
00200A1C  sw   $s6, 0xE24($s1)
```

`FUN_00200408` is a 54-case jump table on the effect type (table at
`002F0FD0`), and `$s6` is the duration in every case. It is set once and read
only as a duration, so **doubling it where it is set doubles every buff timer
in the game at once**.

The `div` at `00200690` is what makes that safe rather than lucky. A
drain-over-time effect derives its per-tick amount from the duration, so
doubling the duration halves the step and the total is unchanged. The two
compensations that would otherwise have to be applied separately are one.

`move $s6, $v0` is an `addu` with `$zero`, and `sll $s6, $v0, 1` is the same
single word with the shift folded in. One data patch, no trampoline.

### Measured

Save state 3, Vegeta (Scouter), timer at `fighter+0x0E14` followed to zero:

| arm | armed with | ran | ticks | real time |
|---|---|---|---|---|
| 30fps (`off`) | 599 | 1200 vsyncs | 600 | **20.00s** |
| 60fps (`full`, 27 groups) | 599 | 600 vsyncs | 600 | **10.00s** |
| 60fps + this group | **1199** | 1200 vsyncs | 1200 | **20.00s** |

All six timers double together. The 30fps arm hitting the published 20 seconds
to two decimal places is what makes the other two rows readable at all.

**`[60FPS - meter economy]` (#16) does not fix this**, which #20 asked
explicitly: the `full` arm above carries it and still ends at 10 seconds. Buff
durations are not counted on `fighter+0x132C`.

### Confirmed on a second character, with two more published numbers

Hercule was located the same day (see the roster note in [`rig.md`](../rig.md)), and
both of his Blast 1s carry a published duration. He is `work/state-backups/rocky-hercule-vs-standing-gohan.p2s`,
also save slot 5.

His timers are at **different offsets** from Saiyan Soul's - `+0x0E18` and the
`+0x0F60 + i*0x18` slots rather than `+0x0E14` and `+0x0F64`. That is the inner
loop at `001C32C8`, which walks two entries per slot; a buff takes whichever
entry suits its effect. Same array, same decrement, same `$s6`.

| move | published | 30fps | 60fps | 60fps + this group |
|---|---|---|---|---|
| False Courage | 7.5s | 7.67s | 4.00s | 7.67s |
| Champion Style?! | 15s | **15.00s** | 7.67s | **15.00s** |
| Saiyan Soul (Vegeta Scouter) | 20s | **20.00s** | 10.00s | **20.00s** |

The armed values double exactly - False Courage 224 -> 449, Champion Style 449
-> 898 - and the two `7.67s` rows are the same number, not a near miss: the
sampling loop steps 20 vsyncs at a time, so a 450-vsync span reads 460 in both
arms. Champion Style and Saiyan Soul are long enough to land on the step
boundary and both read their published seconds exactly.

**Three moves, two characters, three different published durations, one word.**

### What this does not cover

- **After Image Strike (15s)** is on characters not yet loaded.
- **Teen Gohan SSJ2's Unforgivable** lasts until the Max Power gauge drains
  rather than a fixed time, so it is a different question.
- Explosive Wave, the other Blast 1 on the same character, arms no duration at
  all and is byte-for-byte unchanged with the group on: state 253 for 70 vsyncs
  either way. That is the only negative control this scene can provide.

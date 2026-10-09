# Scripted effect commands

Newest sections at the bottom.

## 2026-09-28 - issue #77: the effect-command ramps

Hercule's Dynamic Mess Em Up Punch (`L2` + `Triangle`, `rocky-hercule-vs-standing-gohan.p2s`)
throws a white flash on its first hit. With every open fix on, the flash at
60fps filled the screen for three vsyncs, where the 30fps flash is a medium
burst around the fist. Great Saiyaman 2's rush in his Ultimate does the same: a
yellow fireball fills the view at 60fps and is a small orange one at 30fps.

### Which effect draws it

Five effect classes run during Dynamic Mess Em Up Punch (the class map is in
`effect-classes.md`, added by PR #76). Making each class's draw return at once,
one at a time, and photographing the hit, the flash disappears only with the
scripted-effect-track class's draw (`FUN_0019DD38`, vtable `002C4278`). That
class's timers already match 30fps with `[60FPS - effect track clock]` (PR #76),
so the difference had to be something the timers do not cover.

### The field that differs

Dumping both of the class's live objects at the same track time in each arm
(30fps v117, 60fps v116), every field matched but a uniform scale at
`obj+0x30`..`+0x38`: -1.605 against -4.183 for the flash, 0.272 against 0.356
for the second effect. A write watch on it lands in `FUN_001AAF80` called from
`FUN_0019D868`, a setter the effect-command handler `FUN_0014EBD8` calls every
tick when its command's flag `0x40` is set (`0014EE30`). The value it passes is
`f12`, which is `f24` in the runner, `FUN_0014FF90`:

    f24 = slot[+0x160] * f26                 00150248

### The ramp

`FUN_0014FF90` runs a move's effect commands once a tick. For each command it
keeps a value at `slot+0x160` and a timer at `slot+0x200`, and animates the
value from the command's definition (`$s3`):

| field | meaning |
|---|---|
| `def+0x1C`, `+0x20`, `+0x24` | start, middle and end values |
| `def+0x28` | duration, in seconds |
| `def+0x2C` | where the middle falls, as a fraction |
| `def+0x30` | rate per tick, when there is no duration |

    timed (def+0x28 > 0):  total = def+0x28 * 30.0                  001509B4
                           timer += 1.0 a tick                        001509D0
                           value = start -> middle -> end, linear in the timer
    rate:                  value += def+0x30 a tick                   00150AA4
                           until it reaches the end value

Both count 30Hz ticks. A write watch on Dynamic Mess Em Up Punch's value reads 0.24, 0.29,
0.34 ... one step a tick at 60fps.

### The fix

The timer steps 0.5 (`001509D0`). The rate needs a multiply the function has no
room for, so the rate's load at `00150A98` becomes a jump to a wrapper at
`000F1A70` that loads it, halves it and jumps back to `00150AA0`. The `addu` in
the jump's delay slot is independent of the rate and still runs first; the
wrapper uses `$f0` as scratch, which `00150AA0` reloads.

The other `lui $at, 0x3f80` loads in the runner (`001502C8` to `00150538`)
build vectors - an up axis, a w of 1.0 - and the RNG calls near `00150564` pick
a random spray direction per emission. None of them is a clock.

### Measured, every open fix on

| Dynamic Mess Em Up Punch's flash | 30fps | before | after |
|---|---|---|---|
| scale step per 30Hz tick | -0.516 | -1.03 | -0.516 |
| scale when the flash ends, v119 | -2.12 | -5.73 | -2.64 |

The ramp starts two game ticks after its effect appears, in both arms. At 60fps
that is two vsyncs instead of four, so the ramp runs one 30Hz step longer before
the effect ends; that is the -2.64 against -2.12.

Best-match pixel difference against 30fps, within 4 vsyncs:

| mark | before | after |
|---|---|---|
| v112 | 37.9 | 21.6 |
| v116 | 68.0 | 25.9 |
| v120 | 46.4 | 33.2 |
| v124 | 4.6 | 7.7 |
| v200 | 19.2 | 9.6 |
| v250 | 26.0 | 11.3 |

The timed mode runs in Vegeta (Scouter)'s and Goten's transformations, where
its parameter changes nothing visible (the Vegeta scene scores identically with
and without the group). Traced in memory instead: its timer reads 0, 0.5, 1.0,
1.5 a tick against 0, 1, 2, 3 at 30fps.

### What is left

- Dynamic Mess Em Up Punch as a whole leads 30fps by about 3 vsyncs, measured on v24 back
  on 2026-09-22 (issue #8); nothing here moves that.
- The two-tick start of a ramp, above.

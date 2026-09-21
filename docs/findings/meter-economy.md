# The ki economy, meters and Blast Stock

Ki income and drain, Max Power Mode, and the game's per-second clock.

## 2026-09-16 - issue #4, the ki economy: BT3 does have a framerate constant

The report: *"Ki charges faster, ki also drains faster (notable best from max
power mode)"*. This is the first issue in the batch of ten to be reproduced,
root-caused and fixed in one pass, and the mechanism turns out to be a whole
subsystem rather than a rate.

### Finding the gauge, and two false trails on the way

`fighter+0x09F8` is total ki, in units of 100000 per HUD bar - Cell 1st Form
caps at 400000, Teen Gohan at 500000, which is exactly the 4 and the 5 the HUD
prints beside each portrait. Its meter object starts at `fighter+0x09E4` and
carries four gauges: `+0x00/+0x04`, `+0x0C/+0x10`, `+0x14/+0x18` (ki) and
`+0x1C`, each a current/max pair.

Two earlier attempts found nothing, and both failures are reusable:

- **Charging cannot be measured from a full gauge.** The first hunt held every
  button in turn from the match-start state and diffed the fighter struct. Ki
  was already at its cap, so the charge button moved nothing and looked like no
  button at all.
- **A wrapping counter sampled sparsely looks like a monotone drain.** The
  second hunt fired three blast moves 200 vsyncs apart and found `+0x132C`
  falling 27 -> 18 -> 9 -> 0, a perfect straight line. It is not a gauge. It is
  a counter that runs 0..29 and wraps, and sampling it every 200 vsyncs
  manufactured the slope. Traced at 20-vsync resolution it reads
  29, 18, 8, 28, 18, 8, 28 - the wrap is obvious and the "drain" disappears.

What did work was the opposite of a drain test: stand still and watch for words
that **climb and then flatten**, which is the shape of a gauge filling to a cap.
That found `+0x09F8` (to 400000), `+0x099C` and `+0x09F0` (both to 100000) and
`+0x0828` (to 100) in one pass.

### The measurement

From `work/state-backups`, slot 7, Cell on Rocky Area, both arms run the same
60 vsyncs with no input:

| arm | ticks | ki at 0 | ki at 60 vsyncs | gained |
|---|---|---|---|---|
| unpatched 30fps | 30 | 179163 | 284k | 105k |
| v23 + the 28 groups | 60 | 179163 | 389k | **210k** |

Exactly 2x, and the off arm ticked half, so the A/B is sound. Per tick both
gain the same 3500 - the gauge is a fixed amount of ki per tick, uncompensated.

### The mechanism, which is bigger than ki

A write watchpoint on `fighter+0x09F8` lands in `FUN_001CED18`, a generic
`Ki::add(obj, amount)`; gating that would also halve ki won from hits, so it is
the wrong place. A breakpoint on its entry names the callers by their amounts:

```
ra 001E1A90  amount +3333  x12      # once a tick, li a1, 0xD05
ra 001E1A5C  amount  +180  x6       # once a tick, computed
ra 001E1A5C  amount  +205  x6
```

Both live in `FUN_001E16C0`, which decompiles to **one tick of one fighter's
entire meter economy**: ki income by those two paths, income for the second and
third gauges, a `fighter+0xD80 -= 400` drain, and this:

```c
bVar1 = 0x1d < puVar10[0x4cb] + 1;      /* puVar10[0x4cb] is fighter+0x132C */
puVar10[0x4cb] = puVar10[0x4cb] + 1;
if (bVar1) puVar10[0x4cb] = 0;
...
if (bVar1) { /* the once-a-second blocks: 20000, 900, 600, 300 ... */ }
```

**`fighter+0x132C` is the game's second.** It counts 0..29 and everything
guarded by its wrap is a per-second effect. At 60fps it wraps every 30 *ticks*
and so fires twice a second. The old 2026-08-22 note listing `+0x132C` as "a
counter advancing +2 per frame, range 0..29" was looking straight at it.

The computed path is even more explicit. `FUN_0020EF20`:

```
0020EF3C  li   v1, 0x1E        # 30
0020EF4C  lw   v0, 0x44(a1)
0020EF50  div  v0, v1          # a per-second figure, divided into a per-frame share
```

The README says BT3 has no master framerate variable, and for motion that is
still true - every site hardcodes its stride. But **the meter economy does have
one**, twice: a literal 30 as a divisor, and a 0..29 counter used as a clock.

### The fix: one gate, not a dozen constants

`FUN_001E16C0` has exactly **one caller**, `001E2584`, at the tail of the
per-fighter update. Gating that call to even ticks puts income, drain and the
second itself back on real time together. Halving each constant instead would
have left the 0..29 second wrong, which is the part a player feels as
"everything happens twice as fast".

The trampoline is a `jal` so `ra` still points at `001E258C`, and takes the even
branch with a `j` rather than a `jal` so the economy returns straight into the
caller's epilogue.

| after 46 vsyncs from slot 7 | `+099C` | `+09F0` | ki | second |
|---|---|---|---|---|
| unpatched 30fps | 94498 | 95520 | 259962 | 14 |
| 28 groups, no gate | 100000 (capped) | 100000 (capped) | 340761 | 7 |
| **28 groups + the gate** | **94498** | **95520** | **259962** | **14** |

Value for value, at every sample, for both fighters. A scripted minute of rush,
jump, ki blasts, a blast move and a boost leaves the gated arm's second-counter
on the 30fps arm's value and the picture intact.

Spending ki on a move is **not** affected: that happens on the move's own code
path, not per tick, so the cost of a Kamehameha is still a Kamehameha.

### Max Power Mode: the drain was covered, the charge was not (2026-09-17)

The "not established" item below, measured. Save state 4 is Goku (Early) against
a standing Ultimate Gohan (`work/state-backups/rocky-goku-early-vs-standing-gohan.p2s`),
roster index 0. Holding `L2` at full Ki is state 55, and the blue overlay that
fills over the Ki bars is the meter object's fourth gauge, `fighter+0x0A00`,
capped at 30000. At the cap the game shows "MAX POWER!" and spends a Blast Stock.

| arm | fill to 30000 | drain from 30000 |
|---|---|---|
| 30fps | 112 vsyncs | ~1080 vsyncs |
| every shipped group | 56 vsyncs | ~480 vsyncs |
| shipped + meter economy | 56 vsyncs | ~1020 vsyncs, the 30fps slope |

The drain is `FUN_001CEE10`, inside the gated economy. The fill is not: the
charge state's handler adds to the gauge once a tick at `001EB90C`, and the
amount comes from `FUN_0020F000`, which spreads 30000 over a charge time in
seconds with a hard-coded 30.0 at `0020F028`. It has one caller.

`[60FPS - max power charge]` makes that 60.0. From the pnach, with the economy
gate: **113 vsyncs**, 265 a tick. Ki charging itself (`L2` below full Ki, Ki
poked to one bar) was already right with the economy gate: +35k per 20 vsyncs
in both arms.

### Not established

- **Max Power Mode in play.** The drain and the charge are measured above; the
  mode's own moves (Violent Rush, Hyper Smash) were not.

## 2026-09-21 - the economy also drains Momentum, which paces every charged attack

`FUN_001E16C0`'s `fighter+0xD80 -= 400` is **Momentum**, SuperCombo's hidden
value "filled up by attacking your opponent using Rush Attacks, and
automatically drained over time", which makes "all charged melee attacks ...
charge" faster. `FUN_001E3368` blends the smash charge rate between two
per-character values by `fighter+0xD80 / 100000`.

Rush hits add it per hit, not per tick, so only the drain was wrong. Save state 3,
Krillin against a standing Ultimate Gohan, the same three-hit rush in every arm:

| arm | Momentum added per hit | peak |
|---|---|---|
| 30fps | 8000, 7600, 8000 | 15600 |
| v24 | 8000, 7600, 8000 | 8800 |
| v24 + this group | 8000, 7600, 8000 | 16000 |

So this group is a dependency of `[60FPS - smash charge]` (#17): without it a
charge started from Momentum fills late, 22 vsyncs against 20 from half.

# Projectile, rock and beam travel

The three movers: effect-node projectiles, spawned objects and travelling beams.

## 2026-09-09 - projectile travel: found, measured at exactly 2x, and FIXED

The user's framing again: find the global system, not the single move. This one
delivered.

### The measurement that made it findable

Two things unlocked it, both the user's suggestions. **Training mode** so the
opponent does not retaliate, and **"get up high in the sky and far"** so the
projectile is in flight long enough to time. Three save states were built by
flying Buu back and up from the user's own passive-CPU scene:

    slot 7   gap 420      slot 6   gap 657      slot 2   gap 842

The clock is the opponent's reaction, and the gap is fixed, so flight time
against range separates the wind-up from the travel:

| arm | fit |
|---|---|
| 30fps | 28.4 vsyncs fixed + gap / **14.02** units-per-vsync |
| 60fps | 27.2 vsyncs fixed + gap / **28.05** units-per-vsync |

Fitted against measurements at three ranges, predicting 58/75/88 against an
actual 58/76/88. The fixed term is the wind-up before launch and is already
correctly paced. **The travel term is 2.000x.**

That ratio is the whole finding. A single-range measurement gives 1.49x and
looks like a partial bug; it is only 1.49 because a constant 28-vsync wind-up is
mixed in. Range-sweep, then fit - one distance would have hidden it.

### The system

`00176A2C`, inside the effect-node update:

    00176A2C  lwc1 $f12, 0x20($s2)   the node class's step, in units PER TICK
    00176A34  jal  Vec3Scale         temp = [node+0x30] (velocity) * $f12
    00176A44  jal  Vec3Add           [node+0x10] (position) += temp

`pos += vel * step` once a tick, no delta-time term. For a plain ki blast the
step is **27.7778 units a tick and identical in both arms** - which is exactly
why real-time speed doubles. `node+0x5B4` next door is a per-tick lifetime
countdown, so the blast also expires in half the real time; speed and lifetime
cancel and the blast covers its authored *distance*, which is why "does it
reach" tests could never see this and only *timing* could.

Finding it needed the position first. Three earlier scans failed because the
flight was short and slow; from slot 6 the projectile moves 28 units a vsync and
a constant-velocity scan finds it immediately. Its writers turned out to be
struct copies (`00176434`, `0012DFEC`) and then the VU0 vector library
(`00121ECC`, which capstone renders as garbage) - the integrator was only
reachable through the library caller's `$ra`, `00176A4C`.

### The fix, and what it covers

`[60FPS - projectile travel]`: one hook, halving `$f12`. Verified **as shipped
from the pnach**, not just as a live poke:

| gap | 30fps | 60fps without | 60fps with |
|---|---|---|---|
| 420 | 58 | 42 | **57** |
| 657 | 76 | 51 | **74** |
| 842 | 88 | 57 | **87** |

A breakpoint on the site never fires in an idle battle, so nothing outside a
live projectile is touched.

**It does NOT cover every blast.** Buu's charged `L2+Up+Triangle` (state 272)
launches a projectile that moves 37 units a vsync, and a breakpoint on
`00176A2C` gets **zero hits** during its flight - checked twice, at two
different times, with the launch confirmed by state. There is a second mover.
Chasing it stalled: the charged move's own firing window is fragile (70 ticks of
charge fires at 60fps but not 30; 95 and 110 fire at 30fps but not 60), and a
watchpoint on the best candidate landed on stack memory at `01FFE44C`, whose
writer at `001AC87C` is building vectors on `$sp`. Not found yet.

Frieza's "I might die this time" is untested - it needs a character-select trip.

## 2026-09-09 - the charged blast: also exactly 2x, and a SECOND mover

Buu's `L2+Up+Triangle` (state 272), measured the same way as the ki blast:
training scenes on the ground at three ranges, 60 ticks of charge - the one
charge that fires in both arms - and the opponent's reaction as the clock.

| gap | 30fps impact | 60fps impact | 30fps state 272 | 60fps state 272 |
|---|---|---|---|---|
| 86.5 | v64 | v44 | 124 vsyncs | 101 |
| 341.7 | v78 | v51 | 136 | 108 |
| 598.6 | v92 | v58 | 150 | 114 |

Fitting impact = pre-launch + gap/speed, and it fits to the vsync at all three:

| arm | pre-launch | travel |
|---|---|---|
| 30fps | 59.3 vsyncs | **18.29** units/vsync |
| 60fps | 41.6 vsyncs | **36.58** units/vsync |

**Travel is 2.000x, again.** So this is the same class of defect as the ki blast
and the global picture is now clear: *every* projectile motion path in this game
integrates position per tick with no delta-time term.

Two further findings:

- **The pre-launch phase is ALSO too fast** - 59.3 against 41.6 vsyncs, a ratio
  of 1.42. That is separate from travel and is not the wind-up seen on the ki
  blast, which matched between arms (28.4 vs 27.2). Unexplained.
- **`[60FPS - projectile travel]` does not touch this move.** Impact is v44/51/58
  with the group on and v44/51/58 with it off, identical. A breakpoint on
  `00176A2C` gets zero hits during the flight. **There is a second mover.**

### The second mover is not found, and three candidates are ruled out

1. **`00176A2C`**, the effect-node integrator that v16 fixes. Zero hits during
   this move's flight, checked at two different times with the launch confirmed
   by fighter state.
2. **`0018510C`** in `FUN_00184BD8`, which is a real per-tick advance -
   `[obj+0xB8] += $f20`, clamped at `[obj+0xC0]`, with the object's world
   position built as `direction([obj+0x90]) * that distance + origin([obj+0x80])`.
   It looked exactly right. Hooked and halved: the site **does** execute during
   the move, six times out of six, and impact stayed at v44/51/58. So that
   scalar is the beam's drawn length, not what carries the hit.
3. **Stack temporaries at `01FFExxx`**, which two scans landed on because render
   transforms rewrite them every frame with large deltas. Excluding the top of
   RAM removes them; it also removed every candidate, so the position is not a
   moving vec3 in the searched region.

Every writer found so far is a struct **copy** - `00176434`, `0012DFEC`,
`001555DC` - each reading its source from `[obj+0x38]`, and each feeding a
render node rather than owning the motion. The authoritative object is behind
that pointer and has not been walked.

Frieza's "I might die this time" is still untested and is the obvious next
subject: the user reports it as the most extreme case, and rocks that visibly
cross the screen are a better tracking target than a beam.

## 2026-09-09 - Final Form Frieza: rocks travel 1.77x too fast, and v16 misses them

Navigated to character select from a training save state (pause -> Return to
Character Select -> Yes), picked **Frieza, Final Form** - the form strip opens
with Cross on the character, then Cross again - against a passive Ultimate
Gohan on Wasteland. Scenes saved as slots 0 / 7 / 2 at gaps **125 / 474 / 628**,
backed up to `work/state-backups/frieza-slot*.p2s`.

`L2+Up+Triangle` puts Frieza in **state 263** for about 100 vsyncs while the
rocks fly; the moment they land, both fighters enter the hit cinematic (263 ->
299, opponent -> 308). That transition is a clean impact clock.

| gap | 30fps impact | 60fps impact |
|---|---|---|
| 125 | v110 | v102 |
| 474 | v128 | v113 |
| 628 | v137 | v117 |

Fitting impact = pre-launch + gap/speed, predicting 109.9/128.5/136.7 against an
actual 110/128/137:

| arm | pre-launch | rock travel |
|---|---|---|
| 30fps | 103.2 vsyncs | **18.75** units/vsync |
| 60fps | 98.3 vsyncs | **33.19** units/vsync |

**Ratio 1.771x.** The summon phase before launch is nearly correct (1.05x); only
the travel is wrong. At the longest range the rocks land 20 vsyncs - a third of a
second - early.

> **Corrected 2026-09-09, after the play-test.** "The most legible case" was
> wrong, and wrong in an instructive way: it read the ratio at gap 628 and
> generalised it. At fighting range the summon phase is 103 of 110 vsyncs, so
> the travel is **6%** of the move and fixing it moves the impact by 67 ms. The
> user played v17 and felt nothing, correctly. **A ratio is not an impact** -
> weight it by the share of the move it owns. And the 1.05x summon, dismissed
> here as correctly paced, is ~5 vsyncs fast and is the part of this move a
> player can actually see.

Note the ratio is **not** 2.000 like the other two. The fits are too good for
that to be noise, so the rocks are either not at constant velocity or partly
compensated. Unexplained.

**`[60FPS - projectile travel]` does not touch it.** Preset `noproj` gives
impact at v102 / v113 / v117 - identical to `full`, to the vsync, at all three
ranges. So v16 fixes plain ki blasts and nothing else yet confirmed.

### The second mover: a fourth candidate ruled out

Frieza's rocks were found in RAM easily - nine or more moving vec3s around
`01ACCxxx` and `01A20xxx`, stepping 37.04 units a vsync, matching the fitted
speed. Every watchpoint on them still lands in a **copy**: `0015AB90`
(`ra 0015AB70`), which reads its source from `[obj+0x38]` exactly like
`00176434` and `001555DC` before it.

Following that chain to the rock's own object (`01ACC320`) found its position
fields static - the breakpoint only ever yields one object and it is not the one
in flight - and a direct watchpoint on a moving rock landed at `ra 00184F5C`,
inside `FUN_00184BD8`, the same module as Buu's beam.

That module was then ruled out as the mover, twice over:

- `0018510C`, `[obj+0xB8] += $f20`: hooked and halved, executes six times out of
  six during the move, impact unchanged.
- **`$f20` itself.** It is set to 1.0 at `00184C1C` and used as the per-tick step
  at *twelve* add/sub sites across the function - the age at `[obj+0x10C]`, the
  length at `[obj+0xB8]`, and others. Poking `lui $at,0x3f80` to `0x3f00` halves
  every one of them at once. Impact stayed at v102 / v113 / v117.

So `FUN_00184BD8` draws these effects; it does not carry the hit. Four
candidates are now eliminated and the mover is still unfound. The next idea
worth testing is that the hit is **scheduled rather than collided** - the
scripted-sequence machinery (`FUN_00158850`) computing an arrival time from
range - which would explain why impact is perfectly linear in gap while no
position write governs it.

## The second mover, found: spawned projectiles advance per tick

Two corrections to the section above, both from re-measuring rather than
re-reasoning.

**The 1.771x was not real.** It came from fitting slope and intercept jointly
to three noisy points. Each impact is good to about a vsync, which puts the
slope ratio at 1.77 +/- 0.18 - 2.000 sits inside that. Fitting the 30fps arm
with the slope pinned at the directly measured speed gives
`impact = 103 + gap/18.52` with residuals under a vsync at all three ranges.
The rocks were always exactly 2x.

**The hit is an arrival, not a schedule.** Filming the rocks from launch to
impact shows them ending **20 units from the opponent** when the state flips.
The scheduled-hit idea was wrong; there was a real position to chase.

### Chasing it

The rocks' render positions are written from an origin that is *assigned* each
tick, so every writer found by watchpoint was a copy. The chain runs:

    FUN_0015BFB8   position(+0x30) += direction(+0x00) * step(+0x58C)
      -> 0015BAF4  Vec3Copy(sp, [obj+0x30])           the travelling position
      -> 0014FF50 -> 0014FF90                          effect dispatcher
      -> 0014EED8  [sp] = pos + dir * spread           per-particle offset
      -> 00186CB0  assigns it into the rock's origin
      -> 00184F58  rock render position = origin + local wobble

Every step below `FUN_0015BFB8` is a copy or a small local offset. Two blind
alleys are worth recording because both produced a *bit-identical* result and
neither meant "live writes do not work":

- `0014EF50`, halving `[$s3+0x10]`. That field is the per-particle spread
  (0, -5, -10 with `$f13` = 1.0), not the travel.
- `0015C248` / `0015C260`, halving the step where it is reloaded. The branch at
  `0015C240` skips that whole block for the rocks - the site executed **zero**
  times. Both hooks sat on dead code.

### The mover

`[obj+0x58C]` is **37.037**, and the per-tick delta `[obj+0x50]` has magnitude
**37.037**, in both the 30fps and 60fps arms. The position advances by exactly
that much per tick either way, so at 60fps the rocks cover the gap in half the
real time. It is the same defect shape as every other one in this project: a
quantity authored per tick, with no timestep to divide it by.

Two paths reach the integrator - one recomputes the delta from the step, one
reuses it - and they converge on the `jal Vec3Add` at `0015C28C`. Hooking that
one call covers both. The trampoline swaps the operands and calls the fused
scale-add `FUN_001225D0(dst, a1, a2) = [a2] + [a1] * $f12` with `$f12` = 0.5.

Note `FUN_001225D0`'s argument order, which cost several wrong turns: the
scaled operand is `a1` and the base is `a2`.

### Result

Impact clocked by the opponent's state flip, as shipped from the pnach:

| gap | 30fps | 60fps without | 60fps with |
|-----|-------|---------------|------------|
| 125 | 110   | 103           | 106        |
| 474 | 128   | 113           | 124        |
| 628 | 137   | 118           | 134        |

Travel paces 17.96 units/vsync against 30fps's 18.63, and the position closes
18.4 per tick where it closed 37.04. The remaining ~4 vsyncs is the summon
phase, which is a separate and much smaller defect.

### How global it is

Real but bounded. `FUN_0015BFB8` is the update for one projectile object class,
so every attack built on that class is fixed at once - but it is not the single
control behind every fast projectile:

- **Idle battle:** the site never fires, so the group is inert in normal play.
- **Plain ki blasts:** never fire it either, so it cannot double-compensate with
  `[60FPS - projectile travel]`, which hooks a different class at `00176A2C`.
- **Buu's charged blast:** `FUN_0015BFB8` does not run for it *at all*. Filmed
  with and without the group, Buu's blast is identical vsync for vsync - hit at
  v59, state 272 ending at v117. That beam is a different subsystem and is
  **still unfixed**.

So there are at least three separate projectile movers in this game. Two are now
paced correctly; Buu's beam is the third and remains open.

## The third mover: beams are a sibling of the rock mover

Buu's charged blast is **not** on the rock class - `FUN_0015BFB8` never runs for
it, and the beam is byte-identical with and without `[60FPS - blast object
travel]`. It is on a sibling class whose update is `FUN_00155C5C`:

| | rocks (`FUN_0015BFB8`) | beams (`FUN_00155C5C`) |
|---|---|---|
| position | `+0x30` | `+0x60` |
| per-tick delta | `+0x50` | `+0x80` |
| step scalar | `+0x58C` | `+0x04` |
| the `jal Vec3Add` | `0015C28C` | `00156004` |

Both have the same two-path shape - one branch recomputes the delta from the
step, the other reuses it - and both converge on a single `Vec3Add`.

The delta measures **37.037**, the same speed constant as the rocks, is written
once at launch and never rewritten, and reads identical in both arms.

### What made this one slow to find

The beam is a **particle pool**. Slots are recycled, so the net-displacement
detector that found the rocks reported an address "moving 656 units" when it was
really different particles occupying the same slot in turn. Requiring the step
vector to stay **constant across three consecutive vsyncs** filtered the pool
out and left the real objects.

Everything else found by watchpoint was a copy, including a bulk `ld`/`sd`
struct copy at `001555C4..00155608` that moves `[$s3+0x50..0x88]` into a render
node. That copy is what finally named the source: the delta it reads is
`[$s3+0x80]`.

The decisive step was a **data** experiment, not a code one. Poking the constant
delta to half mid-flight dropped the advance from 37.037 to 18.519 per tick and
moved the hit v59 -> v71, which proved the mechanism before a single instruction
was patched.

Note `00155FE4` was in the enumerated Scale-then-Add family the whole time. It
never fires for the beam because the branch at `00155FB4` skips that block -
exactly the trap that made `0015C248` look innocent for the rocks. An
enumerated site is not a tested site.

### Result

| gap | 30fps | 60fps without | 60fps with |
|-----|-------|---------------|------------|
|  86 |  50   |  44           |  45        |
| 657 |  81   |  59           |  76        |

The travel component paces **18.42 units/vsync in both arms** - taking the slope
between the two ranges, an exact match. The residual ~5 vsyncs is the pre-launch
animation, the same separate defect the rocks show (124 against 128 there).

Inert at idle, for plain ki blasts, and for Frieza's rocks, so it cannot
double-compensate with either shipped projectile group. Frieza re-measures at
v124, unchanged.

**Correction:** commit afb8fc4's message names the function `FUN_00155EE8`. The
containing function actually starts at `00155C5C`; the hooked instruction is
`00156004`, which is correct there and in the pnach.

### Where this leaves projectile pacing

Three movers, three classes, all the same defect and all now paced:

- `00176A2C` - plain ki blasts (`[60FPS - projectile travel]`, v16)
- `0015C28C` - spawned projectiles, Frieza's rocks (`[60FPS - blast object travel]`, v17)
- `00156004` - travelling beams, Buu's charged blast (`[60FPS - beam object travel]`, v18)

The shared shape is worth stating plainly: a projectile keeps a per-tick delta
vector, and doubling the tick rate doubles the distance covered per second. The
fix is always to halve the advance at the one `Vec3Add` the update converges on,
never to touch the stored delta - that field is read by other things and, on the
rock class, recomputed from a step scalar.

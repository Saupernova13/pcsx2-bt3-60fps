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

Frieza's I Might Die This Time rocks were found in RAM easily - nine or more moving vec3s around
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
- **Buu's Super Kamehameha:** `FUN_0015BFB8` does not run for it *at all*. Filmed
  with and without the group, Buu's blast is identical vsync for vsync - hit at
  v59, state 272 ending at v117. That beam is a different subsystem and is
  **still unfixed**.

So there are at least three separate projectile movers in this game. Two are now
paced correctly; Buu's beam is the third and remains open.

## The third mover: beams are a sibling of the rock mover

Buu's Super Kamehameha is **not** on the rock class - `FUN_0015BFB8` never runs for
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

Inert at idle, for plain ki blasts, and for Frieza's I Might Die This Time rocks, so it cannot
double-compensate with either shipped projectile group. Frieza re-measures at
v124, unchanged.

**Correction:** commit afb8fc4's message names the function `FUN_00155EE8`. The
containing function actually starts at `00155C5C`; the hooked instruction is
`00156004`, which is correct there and in the pnach.

### Where this leaves projectile pacing

Three movers, three classes, all the same defect and all now paced:

- `00176A2C` - plain ki blasts (`[60FPS - projectile travel]`, v16)
- `0015C28C` - spawned projectiles, Frieza's I Might Die This Time rocks (`[60FPS - blast object travel]`, v17)
- `00156004` - travelling beams, Buu's Super Kamehameha (`[60FPS - beam object travel]`, v18)

The shared shape is worth stating plainly: a projectile keeps a per-tick delta
vector, and doubling the tick rate doubles the distance covered per second. The
fix is always to halve the advance at the one `Vec3Add` the update converges on,
never to touch the stored delta - that field is read by other things and, on the
rock class, recomputed from a step scalar.

## 2026-09-16 - issue #5, Hercule's ki blast: a second projectile system

`[60FPS - projectile travel]` has been confirmed in play since v16 and halves
the effect-node stepper at `00176A2C`, which is `pos += vel * step` for every
moving effect node. So a report that a character's ki blasts are still fast
should have been impossible. It is not, because Hercule does not throw one.

### Finding Hercule at all

#5 and #8 sat blocked for a session on "Hercule has not been located in
character select", after five of fifteen roster rows were walked one screenshot
at a time. The grid is 7 wide and in the same order as SuperCombo's character
list, so Hercule is index 24, row 3, column 3 - **three `Down` presses from
Vegeta (Scouter)**, who is already in save state 3 and shares his column. The
rule is in [`rig.md`](../rig.md).

The scene is `work/state-backups/rocky-hercule-vs-standing-gohan.p2s`, also save
slot 5: Hercule against a standing Ultimate Gohan on Rocky Area - Evening.

### The stepper never runs

A breakpoint on `00176A2C` fires zero times while the throw is in the air, from
the press through the landing. Not "rarely" - never. So this is a different
system, and the existing group could not have covered it.

`FUN_00121EC0` is Vec3Add, which every mover in this game eventually calls.
Breaking there and tallying `ra` against an idle baseline is a two-minute answer
where a RAM scan is an afternoon:

| `ra` | hits | |
|---|---|---|
| `00160FA8`, `00160FD0`, `00161018`, `00162EF0`, `0024A640` | 32, 32, 32, 32, 24 | idle too - auras |
| `001373AC` | 7 | only with the blast - a bounded loop, not a mover |
| **`00178D98`** | 1 | **only with the blast** |

One hit is not weakness. That site fires once per tick per object, while the
aura callers fire many times a tick, so a 160-stop sample is dominated by them.

### Two classes, and neither is only a flight

A tapped `Triangle` and a held one throw different objects. Breaking on each
mover while pressing each tells them apart in one run:

| input | update | mover |
|---|---|---|
| tap `Triangle` | `FUN_00178A28` | `FUN_00178D18` |
| hold `Triangle` (charged ki blast) | `FUN_00177968` | `FUN_00177CF8` |

Both movers start the same way - `pos(+0x60) += vel(+0x80)`, then
`vel.y += gravity(+0xF0)` - and neither stops there. Read field by field at
30fps, per tick:

| field | tapped | charged |
|---|---|---|
| flight | 17 ticks, then lands | flies, bounces three times, rests |
| spin angle `+0xE8` | `age(+0xF4) * spin(+0xEC)`, -34.48 degrees a tick | same, 35.6 halving at each bounce |
| debris | 5 fragments at `+0x130`, ballistic, for 15 ticks (`+0x1D4`) | - |
| fuse `+0xF6` | - | 300 ticks |
| rest before exploding `+0xD4` | - | 24 ticks |
| after-life `+0xFA` | - | 15 ticks |

All of it runs twice as fast at 60fps. The first version of this fix halved the
flight of the tapped class only.

### Why the halved flight landed 7 units short

It flew for exactly the right time and landed at (-108.3, -2.8, 210.4) instead
of (-112.3, -3.0, 216.7). The first write-up blamed a launch offset. Traced per
vsync, that is wrong: both arms spawn on the same vsync at the same point, and x
and z match the 30fps arc to 0.01 at every matched moment. Only y differs.

The game adds velocity to position **before** it adds gravity to velocity. At
30fps gravity therefore reaches the position one whole tick late. Halving both
terms and running two half ticks lets it reach the position after half a tick,
so the arc sags by `g/4` more every tick:

```
30fps, n ticks:          y0 + n*v0 + g*n*(n-1)/2
two half ticks, n times: y0 + n*v0 + g*n*(2n-1)/4     lower by n*g/4
```

With g = 0.5 over 17 ticks that is 2.1 units, measured 2.17. A lower arc meets
the ground sooner, which is where the 7 units along the path went.

Subtracting `g/8` from each half step cancels it exactly - even ticks match the
30fps positions and odd ticks fall on the same parabola between them. That
landed the tapped blast within 0.13 units.

### Why half steps are still wrong

Collision is tested at the positions the object visits, and half steps visit
positions the 30fps game never does. The exact half-step integrator, with every
timer above counted on even ticks, on the charged blast:

| arm | first bounce | second bounce | rests at | explodes |
|---|---|---|---|---|
| 30fps | v59 (-286.3, -5.0, 322.0) | v81 (-349.4, -27.4, 382.7) | (-384.7, -25.5, 412.1) | v211 |
| half steps | v59 (-285.7, -5.1, 321.7) | **v76 (-334.1, -25.6, 366.6)** | **(-356.4, -4.4, 318.5)** | **v242** |

The second bounce met a rock lip that the 30fps arc steps over, bounced back
toward Hercule, and the bomb came to rest 70 units away, 31 vsyncs late.
Unpatched 60fps does not have this problem - it bounces where 30fps does, only
twice as fast - because it samples the same positions.

### The fix: think at 30Hz, draw at 60

Both updates begin by calling the game's own freeze check, `FUN_0012CED0`, and
skip the tick when it says so. `[60FPS - particle update rate]` already reuses
that check. `[60FPS - thrown object rate]` wraps it so the answer is also "skip"
on odd ticks: one 11-word helper at `000F1600` and a `jal` at each of
`0017797C` and `00178A3C`. The object keeps drawing every frame.

Verified as shipped from the pnach, save state 5:

| | spawn | lands / rests | explodes | gone |
|---|---|---|---|---|
| tapped, 30fps | v18 | v53 (-112.28, -2.95, 216.68) | - | v85 |
| tapped, 60fps | v19 | v37 (-112.09, -2.95, 216.52) | - | v53 |
| tapped, this group | v19 | **v54** (-112.12, -2.95, 216.57) | - | **v86** |
| charged, 30fps | v50 | v163 (-384.68, -25.53, 412.13) | v211 | v239 |
| charged, 60fps | v50 | v107 (-384.2, -25.6, 412.1) | v131 | v145 |
| charged, this group | v51 | **v164** (-384.22, -25.55, 412.09) | **v212** | **v240** |

Every beat is one vsync after 30fps because the throw leaves the hand one vsync
later. The positions differ from 30fps by the throw's aim, which unpatched 60fps
shares. Debris directions are random, so only their lifetime compares: 30
vsyncs in both.

### What this section used to claim

That 9 constructors write gravity at `+0xF0` for this mover, so halving it in
the mover was the global fix. `+0xF0` is a common offset: the scan matched
unrelated structures, and `00177770` belongs to the charged class, whose mover
the old fix never touched. The rule it was illustrating still holds - patch
where a per-object value is used unless its setter is unique - but here the real
miss was a second mover, found only by pressing a second button.

### Not established

- **Damage.** From this save both throws pass over a standing Gohan, so a hit
  was never compared. Identical positions and timings mean the hit test sees
  the same inputs, but that is inference.
- **Other characters' thrown objects.** Only Hercule's two classes were traced.
  Any object with its own update and a mover like these needs the same check.
- **How 30Hz motion looks.** The object now moves every other frame while the
  camera moves every frame. That is how the original game looks, but next to a
  60fps camera it may read as judder. Worth a look in play.
- **#8, the speed lines on Present Bomb**, is a separate effect and is not
  addressed here.

## 2026-09-21 - issue #43, ki blasts die early: the projectile's life is counted in ticks

The report: ki blasts travel at the right speed but vanish before the 30fps
game's do - Kid Buu's regular blasts die early, his charged ones do not.

### The life

The effect-node update, `FUN_00176980`, is the one `[60FPS - projectile travel]`
hooks for the step. Straight after the move it counts the node's life down:

```
00176A64  lw    $v0, 0x5B4($s1)     life in ticks, armed at spawn from the class (0017688C)
00176A68  addiu $v0, $v0, -1
00176A6C  bgtz  $v0, 00176A80
00176A70  sw    $v0, 0x5B4($s1)
00176A74  ...   +0x5B0 |= 0x10       dead: the move is skipped from then on (00176A1C)
```

Krillin's Rush Ki Blast is armed at 118. At 30fps that is 3.9s at 27.8 units a
tick; at 60fps with the step halved it is 2.0s at 13.9 a tick, so a blast that
misses gets half the range.

A blast that **hits** never shows it: the impact sets `0x10` itself, and the
stage caps separation at about 785 units, well inside even the halved range. On
save state 7 (Krillin 703 units from a standing Ultimate Gohan) the shot ends
at 663 units in every arm. The shortfall is only visible on a miss, which is
exactly how the report describes it - a blast that "stops existing sooner".

Moving the opponent to force a miss does not work: `fighter+0x14` is rewritten
from the model every tick. So the life was set to 10 ticks on the blast's first
step instead, and the flight timed to the `0x10` flag:

| arm | flies | travels |
|---|---|---|
| 30fps | 18 vsyncs | 250 units |
| v24 | 9 vsyncs | 125 units |
| v24 + `[60FPS - projectile life]` | 19 vsyncs | 264 units |

### The fix

The decrement is reached two ways: after the move, and from `001769BC`, which
skips the move for a node flagged `0x100` and branches to `00176A68` with the
life loaded in its delay slot. The hook therefore replaces the branch after the
decrement, where both paths meet, with a jump to a helper at `000F1880` that
adds the tick's parity back, re-stores the life and takes the original branch.
`$t0` is unused in `FUN_00176980`.

### Not this group

- **Charged ki blasts** are not effect nodes: holding `Triangle` never reaches
  `00176A34`. They are the spawned-object class, whose end comes from its blast
  script's events - the clock `[60FPS - blast script clock]` (#31) paces - not
  from a tick life. That matches the report's own split: Kid Buu's charged
  blasts last, his regular ones do not.
- Videl's charged blast was not tested; whether it is an effect node or a
  scripted object decides which group it needs.

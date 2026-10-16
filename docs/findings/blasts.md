# Blasts: hit cadence, effects, sequences and Flame Shower Breath

Blast 2 and Ultimate Blast timing: hit cadence, effect duration, the sequence clock, the beam charge hold.

## 2026-09-05 - ki blasts are cut short: four hypotheses, all wrong

Reported by the user: ki blasts (Kamehameha and friends) last a shorter time and
land fewer hits at 60fps, and in ultimate-attack cutscenes the *blast* runs at
double speed while the bone and mesh animation plays correctly - so the energy
ball forms too fast and the sequence "ends early".

**Not solved.** What follows is what was measured and ruled out, so the next
attempt does not repeat it.

### The instruments

Two globals hold the combo readout, found by intersecting two moments whose
on-screen values were known (1760 at one frame, 2310 eight frames later):

    0033371C   combo damage
    00333724   hit count

`00331D64` is the frame counter, which rose by exactly 8 over those 8 vsyncs and
so confirms 60fps ticks once per vsync.

Save states, all captured live from the user's own session:

    slot 6   mid-Kamehameha, beam on screen, captured patched
    slot 7   the ultimate just started, camera on Goku, ball not yet formed, patched
    slot 8   the same moment of the same ultimate, captured UNPATCHED at 30fps

### A contaminated measurement, and the state that fixed it

From slot 7, running the two arms against each other, the ultimate's damage
landed at vsync 128 patched and vsync 200 unpatched - apparently a large real
difference. **It was an artifact.** Slot 7 was captured with the patch running,
so every tween already in flight carried a step computed from the fixed 60.0
constant; replayed unpatched those tweens run at *half* speed and stretch the
sequence. A state captured under one configuration cannot serve as the reference
for the other whenever the patch changes stored data rather than only code.

Asking the user to capture the same moment with the patch off gave slot 8, and
measuring each state in the configuration it was captured in:

| state | configuration | beam bright until |
|---|---|---|
| slot 8 | unpatched 30fps | vsync 152 |
| slot 7 | patched 60fps | vsync 160 |

**The ultimate's overall duration is not halved.** Frames captured at matched
vsyncs in the two arms show the same body pose, the same camera and the same QTE
prompt at vsync 60.

### Ruled out

- **The sequence length.** 152 vs 160 vsyncs, above.
- **The beam's remaining life.** From slot 6, frame-exact brightness gives 64
  vsyncs unpatched against 62 patched.
- **The blast node's own lifetime.** `FUN_0017C8F4` runs a duration down at
  `0017C99C` by exactly 1.0 a tick, from the `1.0` at `0017C990` - a genuinely
  uncompensated per-tick timer of precisely the shape being hunted, in a node
  type neither the aura nor the particle gate covers. Halving it changed nothing
  the user could see. Worth knowing it exists; it is not this bug.
- **Ki drain.** No word behaves like a gauge emptying during a beam. The
  candidates near `0031C118`-`0031C158` read ratio 0.96 - correct - and the one
  that moves (`0031C128`) wobbles rather than draining, at ratio 1.39.
- **An earlier claim, withdrawn.** A ki barrage was reported here as delivering
  its hits "in half the real time". That came from sampling on a 10-vsync grid;
  at 2-vsync resolution the last hit lands at vsync 12 unpatched against 10
  patched, a factor of 1.25, and the move is front-loaded enough that most of its
  hits land before sampling begins. It is not evidence of anything.

### What the next attempt should do differently

Every measurement above looks at *duration*. The user's description is about a
blast that stops early, which duration should capture - and does not. Two
readings survive:

1. The affected quantity is not on any clock that was watched. A beam in this
   game may persist while a resource lasts rather than while a timer runs, and no
   such resource has been located yet.
2. The situations are not the same situation. Slots 7 and 8 are different
   battles - different health, different blast stock, different positions - and
   only the *phase* of the move is comparable between them, not the outcome.

The cleanest experiment not yet run: have the user fire **the same beam twice
from one save state**, once with the patch and once without, capturing a state
immediately before the input in each case, and compare the hit count. Hit count
is the thing the user actually reports losing, and it is a single integer that
needs no alignment between runs. Everything measured so far has been a proxy for
it.

## 2026-09-05 - ki blasts, reproduced at last: 28 vsyncs against 16

The previous section recorded four wrong hypotheses about this bug and, worse, a
measurement that had to be withdrawn. The thing that broke the deadlock was not
a better hypothesis - it was being able to fire the move on demand.

### Ask the game for the controls

Guessing the control scheme cost most of a session. Every "modifier + button"
probe returned the same result for `L1`, `L2` and `R2`, which looked like proof
the shoulder buttons were not reaching the game - but `tools/padcheck.py` shows
all four reaching it perfectly. The probes were identical because the *move* was
identical: the modifier was right and the assumption about which button ran the
Kamehameha was wrong.

**The game documents itself.** Pause, choose *View Skill List*, and the panel
lists the character's Special Attacks with the stock each costs, drawing the
input for the highlighted one at the bottom:

| move | input | stock |
|---|---|---|
| Wild Sense | L2 + Circle | 2 |
| Now I'm Mad! | - | 3 |
| **Super Kamehameha** | **L2 + Triangle** | **3** |
| Meteor Smash | - | 3 |
| **Angry Kamehameha** (ultimate) | - | 4 |

One screenshot answered what a dozen input probes could not.

### Script input in ticks, not vsyncs

The first A/B with the correct input still failed, and failed silently: at 30fps
the move never came out at all, so the reference run measured an empty screen.
The input script was written in vsyncs - 20 held, 6 pressed - which is 20 and 6
ticks at 60fps but only 10 and 3 at 30fps, too short to register. Lengthening it
to 48 and 16 vsyncs makes the move fire at both rates. **A scripted input has to
be long enough in TICKS at the slower rate**, and a run has to check the move
actually happened rather than assume it.

### The measurement

`tools/blasttest.py`. Same save state, same scripted input, same vsyncs:

| configuration | damage | hits | beam on screen |
|---|---|---|---|
| unpatched 30fps | 8520 | 6 | **28 vsyncs** (8..32) |
| patched 60fps | 8520 | 6 | **16 vsyncs** (8..20) |
| battle group only | 8520 | 6 | 16 vsyncs |

The beam is on screen for roughly half as long, and the way the damage arrives
is the tell: unpatched it *ticks out* - 1520, 4260, 7100, 8520 over about twelve
vsyncs - while patched the whole 8520 lands at once. That is the reported "cut
short, fewer hits", measured.

**Battle-group-only reproduces it exactly**, so no group in the patch causes
this and none compensates it. It is a missing compensation, not a regression.

### The beam is FUN_00186250

A sweep during the beam for words moving the same amount per tick at both rates
- excluding the tween pool, whose countdowns legitimately read 2x - pointed at
`01A0D4D0`, `01A0D764` and `01A36xxx`. Write watchpoints on those land in the
`00183xxx`/`00184xxx` module, whose caller is **`FUN_00186250`: a vtable entry
at `002C3EF4`, no direct callers**, the same shape as the ki aura's
`FUN_00164860` and the particle node's `FUN_00168084`.

Gating that function wholesale on frame parity stretches the beam from 16 vsyncs
to 56 and drops the damage to zero, so it is unquestionably the beam - but a
blanket gate is not the fix, because the same call does the hit detection.

### Eliminated

Every `lui $at, 1.0` in `FUN_00186250`, tested one at a time against the harness,
all leaving the beam at 16 vsyncs:

    001863BC   0018672C   001867C8   00186810   00186850   00186890   001868CC

`001867C8` feeds a countdown at `+0x1F8`; `00186810` feeds a counter at `+0x20C`
compared against a limit at `+0x210` that calls `FUN_00182DE0` - which looks
exactly like a hit-cadence timer and still is not it. Also eliminated earlier:
`FUN_0017C8F4`'s per-tick lifetime at `0017C990`.

### Where to pick this up

The harness is the asset: `tools/blasttest.py` turns any candidate into a
two-minute yes/no, with `--pokes label=ADDR:WORD`. The target is confirmed. What
is not yet known is which channel inside `FUN_00186250` sets how long the beam
lives - it is not any of its seven `1.0` constants, so it is likely a duration
read from the move's data table and stepped somewhere else, or a stage counter
whose threshold rather than whose step is the per-tick quantity.

The next thing to try is a write watchpoint on the beam object's own fields
during the beam - `+0x1F8`, `+0x20C`, `+0x210`, `+0x1F4` - rather than a search
for constants, and to find where the beam decides to end rather than assuming it
counts down.

## 2026-09-06 - ki blasts solved: a hitbox counter authored in ticks

Two sessions had hunted this as "which constant makes the beam short". It was
never a constant. It is a counter, and finding it took abandoning three separate
lines of attack that all looked promising.

### The oracle that made it tractable

Screen brightness had been the measure of a beam all along, and it is a bad one:
a fixed luma threshold catches the launch flash, misses the beam, and resolves to
+/- the sampling step. The damage counter is far better - `0033371C` moves in
exact integers, needs no screenshots, and can be read every single vsync:

| configuration | damage steps | cadence | span |
|---|---|---|---|
| unpatched 30fps | 2840 4260 5680 7100 8520 | every **8 vsyncs** | 32 |
| patched 60fps | the same five values | every **4 vsyncs** | 16 |

Identical damage, identical hit count, exactly half the real time. Uniform 1420
steps. That is the whole bug in one table, and it took two minutes to produce
once the instrument was right. **Reach for the exact integer the game already
maintains before reaching for a picture of the screen.**

### Three wrong turns, and what each one cost

**`FUN_00186250` is a constructor, not an update.** The previous session had it
as "the beam update, confirmed". Breaking on it shows 18 calls clustered in four
frames, each building a 0x40-byte node - and its first act is copying 0x40 bytes
from a template. The real update is `FUN_001866C0`, slot [0] of the same
six-word class descriptor at `002C3EF0`; `00186250` is slot [1]. The descriptor
table at `002C3E00` holds eighteen of these records, and slot [0] is always the
update-and-draw.

**The `seconds * 30.0` family is real, and is not this bug.** The shipped tween
fix was exactly that shape, so enumerating every `lui $at, 0x41F0` in the code
segment seemed certain to find it: 145 sites. Breaking on all of them narrows to
the 33 that execute during a blast, and **none of the 33 changes the cadence** -
tested in two batches and individually. A complete, mechanical elimination of a
whole hypothesis class is worth the twenty minutes it costs.

**A dead field that looked alive.** `+0x1F4` of a beam node visibly counts down
and freezes the instant the beam ends. It is neither: a write watchpoint on it
catches nothing at all, because the pool at `01A2Exxx` is being recycled and the
"countdown" was successive nodes landing on the same address. A value that
changes with no writer is not a clock, it is different memory.

### The actual mechanism

Trace backwards from the symptom instead. The opponent's HP is `018726A4` -
found by scanning all of RAM for words whose change pattern matches the damage
schedule *exactly*, which returns six addresses out of eight million. A write
watchpoint on it names `FUN_001CE630`, whose live call site is `001CBEF4`, and
walking up gives the chain

    FUN_001AFE70  -> 001CD320 -> 001CC588 -> 001CBD70 -> 001CE630 (apply damage)

with `FUN_001AFE70` called **every frame** and everything below it only every
fourth. The gate is inside it, and it is not a float anywhere:

    H = [obj+0x60]                    the live hitbox
    D = [[obj+0x64]+0x24]             the move's data record
    H[0x0A]   tick counter, ++ once per frame by FUN_0012E7C8 at 001AFE98
    D[0x0B]   the hit interval, AUTHORED IN TICKS
    H[0x0B]   hits landed so far
    D[0x0A]   the maximum number of hits

A hit lands when `H[0x0A] >= D[0x0B]`, which resets `H[0x0A]` to zero; the attack
ends when `H[0x0B] > D[0x0A]`. **One counter paces both the cadence and the
duration** - hits arriving twice as fast spend the hit budget in half the time -
which is why the beam was short *and* felt like fewer hits. The designers wrote
these intervals as tick counts, so there is no constant to scale.

### The fix

`FUN_0012E7C8` has exactly one caller and `H[0x0A]` is read and reset only inside
`FUN_001AFE70`, so gating that single call on frame parity is as narrow as a fix
in this project gets. Single-hit attacks cannot regress: the `blez` at `001AFF08`
short-circuits while no hits have landed, so the first hit of any attack is never
delayed.

### Still open: the launch flash

The visual white-out is a separate channel and is **not fixed**. It lasts 8
samples at 30fps and 4 at 60 on a 3-vsync grid - **12 ticks either way** - so it
is a per-tick effect-node lifetime of the `seconds * 30.0` family after all, just
not one that touches damage. Doubling the 22 such sites that fire during a blast
restores most of it (21 vsyncs against the oracle's 24); doubling all 31 sites
that structurally convert seconds to a stored frame count makes it *worse*, so
they interfere and the set is not simply additive.

That is where it stands, and it deliberately was not shipped: tuning twenty-two
simultaneous constants against mean screen luma is how you get a change that
measures well and looks wrong. The next attempt should bisect the 22 against the
brightness curve, one class at a time, and confirm each in play.

## 2026-09-06 - the fix that measured right and looked like nothing

The hit-cadence fix above is real and the user saw no change at all from it, and
that is worth recording as plainly as the fix itself. It moves *when* damage is
applied - 8 vsyncs apart instead of 4 - while leaving the hit count, the total
damage and every drawn frame identical. Nothing about it is visible unless you
are reading the combo counter. **A quantity being provably wrong does not make it
the quantity the player is complaining about.**

What the player sees is the effect, and the effect is drawn by two node classes:
the beam core at descriptor `002C3EF0` and the flare that follows it at
`002C40F0`. Each update carries half a dozen coupled per-tick channels - start
delay, emit countdown, a geometry cadence driving the segment builders
`FUN_00182DE0` and `FUN_0018322C`, lifetime, stagger, fade - all compared against
each other, which is why every single-constant test came back clean. Both open
with a call to `FUN_0012D1D0` and a branch that skips the whole update while
still reaching the draw, so parity into that branch is the same fix the aura and
the particles already use. The flare's skip is a *likely* branch, so its delay
slot has to be nopped and replayed only on the taken path.

    flash on screen        off 30fps   gates off   gates on
                            30 vsyncs   12 vsyncs   24 vsyncs

Twelve to twenty-four is exactly the doubling a parity gate should produce, and
the two-humped curve - the charge, then the fire - comes back; at 60fps the two
humps had merged into one.

### Two instrument failures worth remembering

**Poking a stock value back does not disable a group.** The three-way comparison
first came back with the gated and un-gated arms byte-for-byte identical, because
PCSX2 rewrites every `patch=1` line each frame and had simply put the hooks back.
This is already written down in this document and it still cost a run. Toggle by
group through `patchctl`, never by poke.

**The 30fps arm drifts between boots.** The same `off` measurement gives 21, 27
and 30 vsyncs on different launches while being bit-identical when repeated
inside one session. Only ever compare arms measured in the same session.

## 2026-09-06 - the blast sequence, found by bisecting code instead of constants

Two fixes shipped before this one measured correctly and changed nothing the
player could see. Both were developed against a scripted Super Kamehameha from
slot 1 - a move that turns out **not to exhibit the bug at all**: 6 hits and 8520
damage at both rates, with the beam only marginally shorter. Everything tuned
against it was tuned against a case that was already fine.

**Reproduce the case the user described, not a convenient one.** From the user's
own capture of the Angry Kamehameha, photographed in real time, the difference is
obvious: the camera cuts back to the fight at 2.1s unpatched and 1.4s patched.

### Two instruments that were lying

**A screenshot needs a running VM, so frame-advance plus screenshot cannot time
anything.** Each sample let the game run about five uncontrolled ticks - the
first one after a load slipped 181. Every "vsync" label on the earlier brightness
curves was fiction. The fix is to stop stepping: let the emulator run free and
sample on the wall clock, so each frame is a real instant and two runs at
different frame rates line up on real time.

**A counter read mid-climb is not a result.** The frames showed 8 hits at 30fps
against 6 at 60fps, which looked like the reported "does less hits". Both runs
end at 8 hits and 16640 damage; the combo readout was simply caught part-way up.
Hit count and damage are identical at both rates, in every case measured.

### The decomposition that pointed the way

The cut happens 79 ticks in at 30fps and 107 at 60fps - neither equal in time nor
equal in ticks. Solving `T + N/30 = 2.47` and `T + N/60 = 1.66` gives `T = 0.85s`
correctly compensated and `N = 49` ticks not compensated at all. A mixed
sequence, which is why every whole-sequence measurement looked ambiguous.

### Bisecting the code

Searching for the constant failed repeatedly - it is not a constant. What worked
was gating a call on frame parity and asking one question of the picture: *did
the camera cut move?* One screenshot per candidate, each probe from the same
state so nothing accumulates.

    0012B700 -> FUN_0012CB60 -> 0012CB84 -> FUN_001AD150

`FUN_001AD150` is the scene-graph walker: for every node it loads the class at
`[node+0x28]` and calls `vtable[0]` through a single indirect call at `001AD188`.
Gating that call for a *range of vtable addresses* turns "which class?" into a
binary search, and the range narrows to one: **vtable `002C3940`, update
`FUN_001587B8`** - an action/state controller, not a renderer, whose per-tick
counter at `+0x14` is advanced at `001589D0`. Nothing is drawn from it, so gating
costs no frame.

    camera cut      unpatched 30fps   patched   with the gate
                          2.1s          1.4s        2.0s

The normal-battle blast schedule is byte identical with and without it.

### A trampoline bug worth recognising

The first range sweep answered "delayed" for every range including disjoint ones.
The cause was a branch offset off by two instructions, so classes *below* the
range fell into the parity check as well and everything was gated. **When a
bisection reports the same answer for disjoint halves, suspect the instrument
before the hypothesis.**

## 2026-09-06 - gating an effect update deletes the beam, and how that was found

v5 shipped two groups together and broke rendering: the ultimate drew no beam at
all, the Super Kamehameha drew its charge but no output beam, and a half-built
charge effect stayed **stuck to the character's hands** after the move ended.

### Why gating was wrong here

The ki aura and the particle system are both fixed by gating their update on
frame parity, so gating the blast's effect classes looked like the same move. It
is not. **These updates rebuild the beam's geometry every frame.** Skipping one
does not slow the beam down, it leaves nothing to draw that frame - and because
the lifetime countdown lives in the same skipped block, a node that should have
expired never does. That is the stuck effect, exactly.

The correct fix is to halve every per-tick step instead: 1.0 becomes 0.5 at all
six sites in the beam core `FUN_001866C0` and all thirteen in the flare
`FUN_001961A0`. The geometry is still rebuilt on every frame, and all the
channels move together - which is the whole point, because they are compared
against each other. **Halving any ONE of them does nothing at all**, which is why
every single-constant test across three sessions came back clean and why the
pattern was invisible until they were changed as a set.

    Super Kamehameha, beam on screen (real time, game running free)
      unpatched 30fps   0.6s .. 3.0s
      60fps, no fix     0.6s .. 1.75s
      60fps, halved     0.6s .. 2.9s

### The measurement that was lying about the gate

The gated version *measured* as an improvement - mean screen luma stayed high
for longer. It stayed high because the stuck effect was still on screen. **A
brightness metric cannot tell a longer beam from a leaked one**; the frames had
to be looked at. Every brightness result in this project that was not confirmed
by looking at the picture should be treated as suspect.

### Blaming the wrong half of a pair

Both groups were withdrawn together because both shipped together. Re-measured
separately on the corrected patch, the sequence gate turned out to be innocent:
it draws nothing, so it has no geometry to skip, and it costs the beam nothing
(0.6s..2.9s with it, the same without) while moving the ultimate's camera cut
from 1.4s to 2.0s against a 2.1s target. **When two changes ship together and
only the pair is measured, a good change can be discarded on the evidence
against the bad one.**

## 2026-09-06 - the charged blast is a different code path, and SEQ kills it

The sequence gate was withdrawn, restored as "innocent", and then withdrawn
again for good. The restore was wrong, and the reason is worth more than the
fix: **it was cleared using an uncharged tap of the move, which never exercises
the charge path at all.**

A Super Kamehameha can be tapped or charged - hold Triangle, get a BOOST!
prompt, release to fire a bigger beam. Every automated test in this project
tapped it. Charged, with the sequence gate enabled:

| configuration | hits | damage | beam on screen |
|---|---|---|---|
| unpatched 30fps | 6 | 12120 | 0.3s .. 2.6s |
| shipped groups only | 6 | 13680 | 0.3s .. 1.3s |
| + blast effect duration | 6 | 13680 | **0.3s .. 2.7s** |
| + blast sequence rate | 5 | **1520** | **nothing renders** |

The move still fires - banner, BOOST! prompt, correct firing pose, correct
controller rumble, correct duration - and draws nothing and deals nothing. The
gated controller is what SPAWNS the effects, so gating it at half rate loses the
spawn entirely on the charge path.

**Both withdrawn groups failed the same way for the same reason: an effect that
is gated is an effect that does not get built.** One skipped the geometry
rebuild, the other skipped the spawn. Gating is the right fix for a system that
only advances state; it is never the right fix for one that constructs
something every frame.

### What that says about test inputs

A scripted input exercises exactly one path. This one tapped a button that the
player holds, and three sessions of measurements inherited that blind spot -
including the measurement that "cleared" a group which breaks the game outright.
When a move has a charge, a level, or a direction, the script has to cover it,
and the user's description of how they play it is the specification.

## 2026-09-06 - what is left, and what has been ruled out on it

Shipping state after the charged-blast regression was fixed: rendering is
correct on both moves, the beam's damage window matches the unpatched game
exactly, and the beam's visible duration is restored by halving the effect
nodes' per-tick steps. **The ultimate's cinematic is still paced in ticks and
cuts back to the fight early**, and that is stated in the released file's header.

### The decomposition, for whoever picks this up

The camera cut lands 79 ticks in at 30fps and 107 at 60fps - neither equal in
real time nor equal in ticks. Solving the pair gives about **0.85s that is
correctly compensated and about 49 ticks that are not**. Only that 49-tick piece
needs fixing.

### Ruled out, with the evidence

- **Gating the controller class** (vtable `002C3940`, `FUN_001587B8`). It does
  pace the cut correctly - 1.4s becomes 2.0s against a 2.1s target - and it is
  unshippable: it costs the *spawn*, so a charged blast renders nothing and
  deals 1520 damage instead of 13680. Worse, the pacing it produces looks like a
  side effect rather than a mechanism: gating each of its three calls
  individually (`0012CE88`, `00158F00`, `00158C70`) changes the timing not at
  all, so what actually moved the cut was leaving the node's "processed this
  frame" bit `0x10` set at `001587DC`. A fix that works by accident is not a fix.
- **The sequence counter** at `+0x14`, advanced at `001589D0` - the only per-tick
  increment in `FUN_00158980`. Halving it changes nothing.
- **`FUN_00158980`'s call site** at `00158818`, and **`FUN_00158C70`'s** at
  `00158804`. Neither moves the cut.
- **Constants.** The whole `00158000..00159400` module contains no `1.0` and no
  `30.0` float constant at all; it is an integer state machine.
- **The charge meter.** `0031C4AC` fills at +6.0 a tick at 30fps and +3.0 at
  60fps - **+180 a second either way**, and it reaches its cap in the same real
  time. Its timestep `0031C4F0` is tween-driven and equally correct. The charge
  is not what runs fast.

### The one lead not yet followed - followed on 2026-09-07, and wrong

`FUN_00158F00` decides whether the sequence advances by asking whether an
animation is still playing (`FUN_00206C20`, on `[obj+0x24]` and the bytes at +4
and +5). The guess was that the cinematic waits on an animation whose clock the
patch does not fix.

**It does not.** `FUN_00206C20` is not an animation query at all - it compares a
character id against the ranges 0x12D..0x130 and 0x139..0x13C. And the animation
clock *is* correct inside the cinematic: Goku's model advances `+0x138` by 2.0 a
tick unpatched and 1.0 a tick patched, and every clip that ends naturally ends
at the same real time in both arms.

The wait is in `FUN_00158980`'s sibling `FUN_00158850`, and it is an integer
countdown, not an animation. See "the two clocks behind everything the game
stages" below.

## 2026-09-07 - MILESTONE: the blasts keep their real timing

Shipped as `releases/v9-scripted-clocks/` and deployed to the user's PCSX2: 17
groups, 424 patch lines, validated. The two new groups are `60FPS - sequence
wait` and `60FPS - state phase timers`.

### Confirmed in play, not by frame stepping

The instrument that matters here is `rtcharge` - the game running free at 100%
speed at both rates, the button going down on the wall clock, the opponent's HP
polled on the wall clock. That is the same clock the player is sitting through.
Held Super Kamehameha from save state 1, L2 for half a second and then L2 +
Triangle held down:

| | unpatched 30fps | patched 60fps |
|---|---|---|
| ticks in six seconds | 181 | 363 |
| the six hits land at | 2.92 3.05 3.19 3.32 3.45 3.59 s | 2.89 3.02 3.15 3.29 3.42 3.55 s |

A 24-frame filmstrip of the same two runs matches shot for shot to within one
0.3s frame: title card, charge ball, lightning, spikes, the beam, the white
flash, 12420 damage, and the aura afterwards. Nothing sticks to Goku's hands and
nothing fails to render.

The frame-stepped oracle agrees: first hit at 176 vsyncs unpatched, 115 with the
rest of the patch, **175** with this. Six hits, 10900 damage and eight-vsync
spacing in all three.

### No regression

| check | unpatched | patched |
|---|---|---|
| mashed rush, three seconds | 4 hits / 2160 damage | 4 hits / 2160 damage |
| the rush's fourth hit lands at | 122 vsyncs | 114 vsyncs |
| forward walk, two seconds | 1.45 units | 1.50 units |

### The ultimate, and where it stands

The Angry Kamehameha from save state 8, to its first hit: 191 vsyncs unpatched,
124 with the rest of the patch, **161** with `sequence wait`. Every staged beat
before the beam launch now lands within two vsyncs of the unpatched game - the
title card, the arm, the ball, the camera cut, the release. What is left is the
flight itself: 27 game ticks in both arms, which is half the real time.

That last half second is not an integer tick counter and not a per-tick float
step. Both classes were enumerated statically and swept exhaustively:

| class | how many | how they were tested | result |
|---|---|---|---|
| integer `field += 1` / `-= 1` | 513 binary-wide, 91 executing during the flight | gated to even ticks one at a time | none moves the first hit; eight break it outright |
| float `field += 1.0` | 140 binary-wide, including hoisted constants | all halved together | no change |
| the fighter state's own phase timer | reaches 28 at the hit in **both** arms | gated | no change - it is a passenger, not the driver |
| the beam node's own clocks (`FUN_00184BD8`, `+0xA8` age against `+0xAC` life) | the whole function's hoisted 1.0 halved | gated and halved | no change |

Whatever schedules that hit is neither. The next thing to try is the collision
itself: `001CE8DC` applies the damage, called from `001CE888`; walking up from
there to whatever decides the hitbox has arrived is the remaining thread.

## 2026-09-07 - WITHDRAWN: blast flash duration, and a probe left live in RAM

`[60FPS - blast flash duration]` (one word at `0017D940`, repointing the load
at the pool's 1/60) is **withdrawn**. The user reported Goku getting stuck in a
loop while it was in force.

### The measurement is still sound; the conclusion drawn from it was not

`[node+0x4E4]` really does drain by exactly 1/30 per tick and expire in exactly
9 ticks at **both** rates - 19 vsyncs unpatched against 10 patched - and the
repoint really does put it back on 19. None of that is in doubt.

What was wrong was assuming an uncompensated duration is therefore safe to
double. **A node that lives twice as long is a node something else may still be
waiting on.** This is the third time this project has hit that shape: gating the
blast effect update leaked a node whose lifetime never expired and stuck it to
the character's hands; gating the sequence controller lost the spawn. Extending
a lifetime is not the inverse of those, it is another way into the same class.

Anything that changes how long an effect node exists now needs a stuck-state
check in play before it ships, not only a duration measurement.

### The process failure, which is the more important half

`tools/sweep.py` and the ad-hoc probes here disable a probe group by renaming it
`[off]` **in the file**, and rely on the next `patchctl.apply` to restore the
original word. The last regression run renamed the group and then called
`resume()` without applying anything, so the repoint stayed in RAM. The session
then reported the change as "needs a restart to load" - true of the *named*
group, false of the word, which was already live in the user's play session.

    live RAM at 0017D940 while the user was playing:  C7818204   (the probe)
    original:                                          C7818A1C

**Renaming a group does not unpatch it. Only `patchctl.apply` does.** A probe
must be followed by an apply, and any claim about what the user is running has
to be a readback, not an inference from the file.

### Not assumed: the loop may predate this

The user notes the stuck loop "has happened a few times", so it is not
established that this change caused it - only that the change was live and is
the obvious suspect. It is worth reproducing against the shipped 17 on its own.

## 2026-09-08 - Buu's Flame Shower Breath: the DURATION is not the bug

Save state 1 (the user's, versus, CPU active, Buu vs an aggressive opponent).
`L2+Up+Triangle` after about 60 ticks of L2 charge puts Buu in **state 272**,
which is the move. Measured from state entry to state exit, in vsyncs, which are
real time at either rate.

### The scene as saved cannot answer the question

With the CPU live the 30fps arm is not reproducible:

    charge 80 ticks   272 lasted  50, 138, 50, 138, 50, 138 vsyncs
    charge 60 ticks   272 lasted  90, 132, 90, 132, 90, 90, 90, 132

Both values end cleanly in idle, so neither is an "interrupted" run in the
obvious sense. The split tracks a **one-vsync difference in when the move
starts** - 87 vs 88 vsyncs of waiting for Buu to become idle. The CPU fires its
own beam (state 271) and whether the two interact decides the length. A test bed
where one vsync of phase changes the answer by 47% is not a test bed.

The 60fps arm was stable at 98 vsyncs throughout, which is exactly the trap: one
arm looking clean says nothing if the other is bimodal.

### With the opponent removed, both arms are clean

Teleporting the opponent to (4000, 0, 4000) every vsync - no clash, no
interruption, both arms identical treatment:

| arm | state 272 | real time | ticks |
|---|---|---|---|
| 30fps unpatched | 90, 92, 90 vsyncs | **1.50 s** | 45, 46, 45 |
| 60fps patched | 104, 104, 104 vsyncs | **1.73 s** | 104, 104, 104 |

**The move is 15% LONGER at 60fps, not shorter.** Duration is not the defect
here. Note also the tick counts: 45 against 104. A raw per-tick count would give
45 in both arms and finish in half the real time; this one is being held for
approximately the right real time already - `sequence wait` doing its job - and
overshooting slightly, the same sign as the transformation overshoot.

### What this does and does not settle

It settles that **this move's duration is fine**. It says nothing about
**projectile travel speed**, which is the actually-open item: Flame Shower Breath
is a breath attack, not a travelling ki blast, so it never exercises the
projectile path at all. Those need a blast that visibly crosses the gap.

Caveat: banishing the opponent could in principle change how the move plays -
no target to lock onto. It is applied identically to both arms, so the
comparison stands, but the absolute 1.50s should not be quoted as the game's
authored length without a passive-CPU state to confirm it.

## 2026-09-09 - Flame Shower Breath, measured properly, and two of my own errors

The user: "my bad. it's L2 + Triangle only for the flame shower breath with Buu.
I put you in an environment where the cpu does not fight back."

### Correction: the previous section measured the wrong move

Everything under "Buu's Flame Shower Breath: the DURATION is not the bug" was
measured with `L2+Up+Triangle`, which is a **different Blast 2** - fighter state
**272**. Flame Shower Breath is `L2+Triangle`, fighter state **262**. The 272
numbers (1.50s against 1.73s) are real but they describe another move, and the
"15% long" headline does not apply to Flame Shower Breath. Treat that section as
a measurement of state 272 and nothing more.

### The real measurement

Save state 5, captured live from the user's own passive-CPU setup (both fighters
idle, gap 86.5, opponent does not retaliate). Backed up to
`work/state-backups/slot05-buu-passive-cpu.p2s`.

| arm | state 262 | real time | ticks | CPU reacts |
|---|---|---|---|---|
| 30fps unpatched | 130, 130, 130 vsyncs | **2.17 s** | 65 | v82-83 |
| 60fps patched | 121, 122, 121 vsyncs | **2.02 s** | 121, 122 | v78-79 |

Three trials each, no spread worth reporting. **Flame Shower Breath runs 7%
fast at 60fps** - 0.15s short over two seconds. The tick counts are 65 against
121, so this is not an uncompensated per-tick clock either: it is being held for
approximately the right real time and falling slightly short.

So for BOTH of Buu's blasts now measured, **duration is very nearly correct**.
Whatever "blasts are way too fast" is, it is not the length of these two states.

### Travel speed is still unmeasured, and three instruments failed at it

Recorded because each failure was mine, and each looked convincing first:

1. **"Impact" via the opponent's fighter state.** At 60fps the opponent left
   idle 10 vsyncs after the shot at *every* gap tested - 20, 30, 45, 60, 86.5 -
   which cannot be a travelling projectile, and at 30fps it never happened at
   all. That looked like a dramatic result. It was not a hit: the **damage
   counter at 0033371C never moves in either arm**, so nothing connects, and the
   state change was the CPU reacting to being shot at.
2. **Forcing the target's position every vsync** to control the gap. Fighting
   the game's own physics every frame is not a controlled experiment; setting the
   position once and leaving it alone changed nothing here, but the earlier
   numbers were taken with the harness interfering.
3. **Tracking the blast on screen.** The brightest-region centroid is swamped by
   the muzzle flash and the camera move - 56,000 pixels of "blast" at one point.
   A small projectile needs a tracker that is not a global centroid.

The instrument that would settle it is the one not yet built: **find the
projectile in RAM** - a float triple that appears when the shot is fired and
moves smoothly away from the shooter - and read its position per vsync.
`tools/findmotion.py` is the right starting point. Distance covered per real
second is then unambiguous, which none of the above is.

## 2026-09-09 - Flame Shower Breath decomposed, and the projectile still not found

The user's framing, which is the right one: "you are NEVER fixing singular
things. you are fixing global systems, just with me giving you specific
examples." So the question is what global system Flame Shower Breath is an
example of. The honest answer today is that **it is not an example of the
blast-speed bug at all**.

### The move is 93% correct, and its phases say where the 7% goes

State 262 splits into three phases, delimited by resets of the state machine's
phase counter at `fighter+0x3D8`:

| phase | 30fps | 60fps | ratio |
|---|---|---|---|
| 0 | 62 vsyncs (30 ticks) | 61 vsyncs (60 ticks) | **0.98** |
| 1 | 52 vsyncs (25 ticks) | 46 vsyncs (45 ticks) | 0.88 |
| 2 | 16 vsyncs (7 ticks) | 14 vsyncs (13 ticks) | 0.88 |
| whole | 130 vsyncs | 121 vsyncs | 0.93 |

`fighter+0x3D8` itself runs at a clean **2x** - 22 against 43 at the same vsync,
1.95 - so it is one of the counters the withdrawn `[60FPS - state phase timers]`
group would have gated. **But the phases do not end when it hits a threshold**:
phase 0 is correct to within one vsync while its counter reaches 23 against 45.
Something real-time-correct ends these phases - almost certainly the animation
clock, which is already fixed. Gating `+0x3D8` here would therefore change
nothing, which is consistent with that group having been withdrawn for causing
state traps rather than for being needed.

A 7% shortfall spread as 0.98 / 0.88 / 0.88 is not the signature of an
uncompensated per-tick clock. Those produce 0.50. Nothing inside this move is
running at double speed, and a frame-by-frame film against the 30fps arm shows
the two tracking each other throughout.

**Conclusion: Flame Shower Breath does not exhibit the reported bug.** It is a
breath attack; nothing in it travels. It was never going to be an example of
"blasts travel too fast", and 7% is not what a player perceives as "way too
fast".

### The projectile: visible, and still not located in memory

A plain `Triangle` ki blast DOES produce a travelling projectile, and a
per-vsync film shows it crossing the screen. Screen-space tracking of the
brightest blob:

    30fps  x = 934 880 838 676 616 533 495 367 then settles ~363
    60fps  x = 898 835 636 500 457 381 373 351 328 283 208 176 162 then ~170

The 60fps blast ends up far further across. That **looks** like the bug, and it
is the best evidence so far - but it is not proof: the early samples are
contaminated by the muzzle flash (6,920 bright pixels at one point), the
projectile shrinks with perspective as it recedes, and neither arm's "settle" is
known to be the projectile rather than an impact effect. Do not quote these
numbers as a measured speed ratio.

Three searches for the projectile's world position all failed:

1. **Constant-velocity scan** over 29MB - floats whose deltas are equal across
   four consecutive vsyncs. Returned only the aura phases (the familiar
   0.10 / 0.23 / 0.27 per tick) and some integer counters read as floats.
2. **Fast-mover scan** - dropped the constant-velocity requirement, kept
   anything moving >0.5 units a vsync in a plausible world range, at three
   different times into the flight. The best candidates sat at the *opponent's*
   position, not in transit.
3. **Targeted region trace** of `00916000-0091A000` per vsync, looking for a
   word that starts near the shooter's x of 225.5 and sweeps toward the target's
   281. **Zero hits in either arm.**

So the projectile is not a plain float triple in the region searched. It may be
inside an effect node, packed, or stored relative to something. The effect
system is already partly mapped - `[60FPS - blast effect duration]` halves 19
per-tick steps in "the two effect classes that draw a ki blast" - so the next
move is to find the node that *owns* a live blast and walk its fields, rather
than scanning RAM blind again.

**No fix. Nothing shipped from this session's blast work.**

## 2026-09-22 - issue #72, a quickly released beam charges one count short

Found measuring #13, Imperfect Cell's Special Beam Cannon. Every beam Blast 2
runs state 272, `FUN_001F7860`, and holds its charge in animation `0x106`,
`0x128` or `0x14A`, one per Blast 2 slot.

### The charge hold

| site | what it does |
|---|---|
| `001F7A00` | counts `fighter+0x3D8`; gated to even ticks by `[60FPS - state phase timers]` |
| `001F7A44` | charge `fighter+0xE44 = 2 * count / max`, capped at 1.0 |
| `001F7ACC`-`001F7AD4` | leaves the hold when `fighter+0x3D0` bit 1 is set, by the release (input condition `0x6F`) or by full charge |

A breakpoint on the handler shows each tick runs the input phase (`a1 = 2`)
before the per-tick phase (`a1 = 1`). At 30fps a release seen at a tick also
counts that tick before leaving, and a tap leaves after two counts, since the
first input phase runs under the previous animation. The exit test is not
gated: at 60fps a release seen on an odd tick left before the next count, and a
tap left after one.

Training refills health, so damage here is the lowest HP reached.

| | 30fps | v24 |
|---|---|---|
| Special Beam Cannon, tapped: charge, damage | 0.067, 7860 | 0.033, 7660 |
| Kamehameha (Goku (Early), save state 0), tapped | 0.067, 7020 | 0.033, 6900 |
| full charge | 1.000, 13430 | 1.000, 13430 |

### The fix, and which variant

`[60FPS - beam charge]` replaces the exit branch with a jump to a helper that
leaves only on an even tick and only once the count is at least 2. Full charge
lands on an even tick, so it still leaves at once.

A second variant, which left only if the release had already been seen on the
odd tick before, was tried against it over eleven holds of 40-70 vsyncs:

| scene | 30fps ticks against the gate's even ticks | this group | the odd-tick variant | v24 |
|---|---|---|---|---|
| Goku, 6 holds | the same vsyncs | 6 of 6 exact | 3 of 6 | 3 of 6 |
| Special Beam Cannon, 5 holds | one vsync apart | 2 of 5 | 5 of 5 | 0 of 5 |

In the Special Beam Cannon's save state the 30fps arm ticks one vsync off from
the 60fps gate, so no rule can match it on every hold. Where the two line up,
this group is exact; the other variant only adds a vsync of latency.

From the pnach:

| | 30fps | v24 | v24 + this group |
|---|---|---|---|
| Special Beam Cannon, tapped | 0.067, 7860, fires v62 | 0.033, 7660, v60 | 0.067, 7860, v62 |
| Kamehameha, tapped | 0.067, 7020 | 0.033, 6900 | 0.067, 7020 |
| Kamehameha, held 61 vsyncs | 0.833, 9600 | 0.800, 9540 | 0.833, 9600 |
| Kamehameha, held 62 vsyncs | 0.867, 9720 | 0.833, 9600 | 0.867, 9720 |
| Special Beam Cannon, full | 1.000, 13430 | 1.000, 13430 | 1.000, 13430 |

With every group on, the nine smoke scenes end in idle.

### What else the Special Beam Cannon trace established (#13)

- **The charge and firing animations run at real speed.** `0x127` and `0x129`
  last the same vsyncs in both arms, and the firing loop `0x12A` advances one
  animation frame a vsync at 60fps against two a tick at 30fps.
- **The beam phase ends when the beam object dies.** Its destructor, `00155C10`
  in class `002C38E0`, sets flag `0xA8` on Cell, and case `0x12A` leaves on that
  flag (or after 150 ticks). The beam is ended by its collision callback,
  `FUN_001561F8`, setting bits `0x21` 43 vsyncs into firing at 30fps and 42 on
  v24. So the beam's life is right.
- **The rest of the lead is per-tick pipeline latency.** From the beam's end
  bits to Cell's next animation takes 9 vsyncs at 30fps and 4 at 60fps: about
  four one-tick hand-offs (end bit, destroy flag, the object sweep, the
  animation change). The beam's start is the same, two ticks from the fire cue
  to the first hit. None of these is a counter; each is a tick of delay, so
  60fps halves them.
- **The `0x400` event on animation `0x129` is the fire cue**, not the beam's
  end: it fires once, before the beam object exists.
- With this group the tapped Special Beam Cannon fires on the 30fps vsync, hits
  2 vsyncs early and ends 6 early; photographed, the beam's own effects run at
  the 30fps pace, a few vsyncs ahead.

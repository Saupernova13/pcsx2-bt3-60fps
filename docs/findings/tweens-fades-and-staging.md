# Tweens, fades and staged sequences

The tween service, the scripted-sequence clocks and the screen fade service.

## 2026-09-05 - the tween system: every ease in the game ran at double speed

Sweeping for words that **step twice as far** had run out of road. The metric that
found this asks a different question - which words **reverse direction twice as
often** in the same amount of real time. An animation at double speed has to, and
unlike a step size a reversal count needs no magnitude and no alignment between
the two runs, so it survives the state divergence that had been drowning every
positional field in noise.

### Three ways to get the reversal count wrong

Each of these was found by getting it wrong first, and each one alone is enough to
make the scan useless.

1. **Sample both rates on the same real-time grid, with the same number of
   samples.** Reading every vsync gives the 60fps run twice as many looks at the
   same two seconds, and twice as many looks at a noisy word find twice as many
   reversals whatever its speed. Sampling every second vsync in both fixes it, and
   is also exactly one sample per tick at 30fps so nothing is read twice there.
2. **Check the words are actually floats.** The two ~24 KB regions at `0x006E9000`
   and `0x007E9000` are DMA and GIF packet data. Read as floats they are denormal
   zeros punctuated by values like `2.5e30`, and their sign flips mean nothing.
   They accounted for almost the entire first result.
3. **Start from a state that needs no input** - `tools/mkstate.py airidle`.

Unfiltered the scan reported 6792 words at 2x. With the grid fixed and
non-floats excluded: 657, and the top six were unmistakable.

### The tell

Two copies of one small structure, at `0x01879368` and `0x018795F4`, sampled every
second vsync during an airborne idle:

```
01879370   30fps   0.000  0.333  0.667  1.000  0.667  0.333   period 12 vsyncs
           60fps   0.667  0.667  0.000  0.667  0.667  0.000   period  6 vsyncs
```

A triangle wave, ping-ponging 0 to 1 and back in steps of one third, at exactly
double the frequency. `+0x00` is a 1,2,3 phase index, `+0x04` the direction,
`+0x0C` the endpoint. A write watchpoint named `FUN_00267B00`, and its
constructor sits just above it.

### The bug

`FUN_00267AC8(obj, seconds, from, to)` builds a linear tween:

```
00267AC8  lui   at, 0x41F0        ; 30.0
00267AD4  mul.s f12, f12, f00     ; obj+0x08 = seconds * 30    frames remaining
00267AD8  swc1  f13, 0x10(a0)     ; obj+0x10 = from            current value
00267AE0  swc1  f14, 0x14(a0)     ; obj+0x14 = to              target
00267AF0  div.s f00, f00, f12     ; obj+0x0C = span / frames   step per call
```

and `FUN_00267B00` advances it exactly one step per tick, decrementing the frame
count by 1.0 and clamping at the target.

**The 30.0 is the game's frame rate written into the arithmetic.** A caller asks
for a duration in seconds; the constructor converts it to ticks assuming 30 ticks
per second. At 60fps the stepper is called twice as often against a duration still
counted in 30Hz frames, so every tween finishes in half the time it was authored
for. This is the same class of defect as everything else here - a per-tick
quantity with no timestep - but it is the first one found in a *general-purpose
service* rather than in a particular behaviour, which is why it survived so long:
it is not the aura's bug or the animation system's bug, it is every ease, pulse,
fade and blend in the game at once.

One word repairs both halves, because both derive from the same constant:

    patch=1,EE,00267AC8,word,3C014270 // lui $at, 0x4270   30.0 -> 60.0

60.0 doubles the frame count and halves the step together.

### Verification

Through the shipped pnach group, not a memory poke, from the identical
airborne-idle state:

| preset | word at `00267AC8` | tween period |
|---|---|---|
| `off` (the 30fps oracle) | `3C0141F0` = 30.0 | 12 vsyncs |
| `air` | `3C0141F0` = 30.0 | **6 vsyncs** |
| `tween` | `3C014270` = 60.0 | 12 vsyncs |

No regression: dash 0.988 and launched-opponent coast 0.985, both unchanged from
before the group existed.

### What this does not yet explain

The reversal scan still finds 191 real-float oscillators at 2x outside the display
packets, about a hundred of them in the effect pool at `0x0198F000`-`0x0199A000`.
Some of that is an artifact of the method rather than a defect: **a save state cut
before the fix contains tween objects whose `step` was already computed from the
30Hz constant**, and those keep running fast until something rebuilds them, which
in a two-second window most long tweens never do. The ping-pong pair rebuilds
every six ticks, which is exactly why it was the clearest signal in the sweep.

Two dead ends worth not repeating, both ruled out by measurement from the
identical-state oracle:

- **The per-tick timer pool** at `0x018768A8`-`0x0187C6F8` is dead-clean 2.000 on
  values like `0.5 -> 1.0` and `25.60027 -> 51.20022`, and it is the countdown
  field of these same tween objects. It stays at 2.000 *after* the fix and that is
  correct - the duration is now legitimately twice as many frames. Counting
  "words at 2x" is the wrong success measure for this bug; the value field is what
  has to come back to 1.0, and it does.
- **The same pool is just as busy on the ground** - 341 moving words and 65 at 2x,
  against 334 and 51 in the air - so it was never going to be an air-specific
  defect on its own.

## 2026-09-07 - the two clocks behind everything the game stages

Three sessions of chasing individual effects ended here: the blasts are not
paced by the effects at all. They are paced by two integer counters, and both
were invisible to every scan run before today because every scan looked for
floats.

### The instrument that found them

`tools/ratediff.py` asks every word in RAM whether it still moves at double
speed: same save state, same input, the same number of **vsyncs** - the same
real time - once unpatched and once patched. A quantity the patch compensates
covers the same distance in both arms; one it misses covers twice as much.
Three snapshots per arm rather than two, because a word that only moves when
its pool is freed and refilled jumps once, while a clock advances the same
amount in each half of the window. That one requirement cut 805 false
candidates to 28 real ones.

Its companion `eventdiff.py` stops both arms at the same **event** instead of
the same time. Whatever a script keeps time by has to read the same at that
instant in both arms, because the event is the same point in the script.

Neither found the answer directly, but between them they said what the answer
was not: no float in the game moves at double speed during an ultimate except
some long-dead tweens. The clocks had to be integers.

### The chain, from the symptom down

The ultimate is one fighter **state**. `FUN_001E23D0` is the state machine: the
current state index lives at `fighter+0x948`, the handler table at `002C4980`,
and the handler is called once a tick with message 2. Save state 8 sits in
state 261, which becomes state 264 (`FUN_001F6518`, the Angry Kamehameha) at
0.42s unpatched and 0.40s patched - the same real time, so the entry is fine.

Inside the state, the animation schedule is fine too. Goku's model at
`008C0E30` advances `+0x138` by 2.0 a tick unpatched and 1.0 a tick patched:
**the animation clock patch is doing its job**, and every clip that ends
naturally ends at the same real time in both arms. What differed was the moment
an external event *interrupted* a clip - and that traced to the fighter's
animation attribute bit 0xA7 (`FUN_001DAC78`, bitfields at `fighter+0x1085` and
`+0x10AD`), set by `FUN_00158980`'s action from a scripted sequence.

### Clock one: the scripted sequence's wait

`FUN_00158850` steps one node of a scripted sequence per tick. A step that is
waiting counts a plain integer down by one - `[node+4]` at `00158914`,
`[node+8]` at `0015894C` - and fires its action when it hits zero. Those waits
are authored in 30Hz frames, so at 60fps every beat the game *stages* rather
than simulates arrives in half its real time: camera cuts, mouth lines, fades,
and the instant an ultimate lets go of its beam.

Counting down on even ticks only moved the Angry Kamehameha's first hit from
124 vsyncs to 161 against an unpatched 191, and every staged beat before the
beam launch now lands within two vsyncs of the unpatched game.

This is the fix the two withdrawn groups were reaching for and getting wrong.
Gating a node's *update* skips its spawn and its draw. Gating only the *wait*
skips nothing.

### Clock two: the fighter state's phase timer

Every state handler keeps a counter in the scratch block the dispatcher zeroes
on entry (`memset(fighter+0x3D0, 0, 0x50)` at `001E247C`), advances it once a
tick, and compares it against a count authored in 30Hz frames. In the held
Super Kamehameha - state 271, `FUN_001F7860` - that is `001F7A00`:

    lw    $v0, ($s0)          # ticks in this phase
    addiu $v0, $v0, 1
    slt   $v1, $v0, $s3       # ... against the authored charge length
    bnez  $v1, skip
    sw    $v0, ($s0)          # delay slot: stored every tick either way

`tools/phasetimer.py` finds all 28 of them by the shape the compiler gives
them: `addiu $sN, fighter, 0x3d8` in the prologue, then `[$sN] += 1` with a
matching load and store. `tools/mkgate.py` writes a trampoline for each that
adds one on even ticks only - an integer cannot be halved, and freezing one
hangs the state.

Held Blast 2, button down throughout, to the first hit: **unpatched 176 vsyncs,
patched-without-this 115, patched-with-this 175.** Same six hits, same 10900
damage, same eight-vsync spacing.

### Why the blanket gate is wrong, and what it cost

Gating all 28 broke ordinary melee: the fourth hit of a mashed rush lands at
122 vsyncs unpatched, 114 with the rest of the patch, and never within five
seconds with all 28 gated. Some of these counters are clocks and some are
levels - a combo index, an input window - and the ones that are levels must not
be slowed. They have to be selected by measurement, not by shape.

### Which of the 28 to gate, measured one at a time

Two oracles, both counted in vsyncs so they mean real time at either rate: a
held Blast 2 to its first hit (unpatched 176, patched-without 115) and the
fourth hit of a mashed rush (unpatched 122, patched-without 114). Each site was
gated alone and scored on both.

| Site | charge | melee 4th | verdict |
|---|---|---|---|
| `001F7A00` | **175** | 114 | the held charge itself - state 271 |
| 21 others | 115 | 114 | neutral here; same shape, other states |
| `001F1C74` | 105 | 114 | cuts the charge short |
| `001F31C0` | 115 | never | costs the rush its fourth hit outright |
| `001FBF28` | 115 | 160 | slows the rush |
| `001FCE34` | 65 | 214 | breaks both |
| `001FF9A8` | 111 | 138 | slows both |
| `001FFC10` | 66 | 215 | breaks both |

Those six are excluded. The remaining 22 leave both oracles where the rest of
the patch leaves them and fix the one they are supposed to fix.

### A trap: shrinking a live group leaves its hooks in RAM

`patchctl` restores the original word for every address it can see in the
pnach. Rewrite a group with **fewer** addresses than it had a moment ago and
the addresses that were dropped are no longer in the file, so nothing restores
them - the game keeps jumping into a trampoline that is no longer being
maintained. That produced twenty minutes of unreproducible measurements: the
unpatched arm read 176, then 65, then 112, then no hit at all. Restarting the
emulator fixed it instantly. **Shrink a group and restart, or measure nothing.**

### A second trap: loading the state *after* disabling the patch

`realclock.py` loads the save state, applies the preset, then loads the state
again so the patch is live from the first frame. That is right for turning a
group **on** and silently wrong for turning it **off**: the save states were
captured while patched, so their RAM image contains the patched words, and the
second load puts them straight back after `patchctl` has just restored the
originals. The unpatched arm is then not unpatched.

It reads as a plausible result rather than an error. The "30fps" run measured
181 ticks in six seconds one way and 362 the other - the give-away is that the
unpatched game can only ever tick 30 times a second. **Check the tick rate of
the unpatched arm in any real-time measurement**; 60 ticks a second means the
patch is still in RAM.

Order that works: load the state, apply the preset, run. Never load again after
applying.

## 2026-09-09 - the Galick Cannon fade: measured, mechanism confirmed, not fixed

Vegeta (Scouter)'s Final Galick Cannon, save state 3, filmed per vsync with a
screenshot-and-flush film, scoring the fraction of pixels above luma 235.

| arm | fade window | length | in seconds |
|---|---|---|---|
| 30fps (`off`, tick 29.1/s) | v443 .. v498 | 56 vsyncs | **0.93s** |
| 60fps (`full`, tick 56.8/s) | v435 .. v463 | 29 vsyncs | **0.48s** |

**28 ticks either way.** The fade to white is a per-tick duration and runs in
half its real time at 60fps, exactly the shape of every other defect here.

### Why it looks the way the user describes it

The move's own timeline is *correctly paced*. Filming the fighter states across
the whole 650-vsync ultimate:

| beat | 30fps | 60fps |
|---|---|---|
| state 287 (cut-in) | v3 | v3 |
| state 302/314 (rush) | v179 | v178 |
| rush ends, 208 | v491 | v489 |
| back to idle | v657 | v651 |

Every beat lands within a few vsyncs of the 30fps arm. So the sequence around
the fade is right and the fade alone is short: at 30fps it ends at v498, *after*
the rush transition at v491, and covers it; at 60fps it ends at v463, twenty-six
vsyncs before the transition at v489, and the animation is left playing in the
open. That is precisely "the fade ends too early, revealing the animation still
playing behind it".

### Eliminated

- **The game's own dormant 60fps effect switch.** `FUN_00251A48` and
  `FUN_00250DE8` branch on `model+0xA40` bit 24 and load 60.0 / 2.0 / 0.5
  instead of 30.0 / 1.0 / 1.0. Nopping the branch at `00251AD8` so the 60fps
  path always runs leaves the fade at **29 vsyncs**, unchanged. This reproduces
  the 2026-09-05 result from a different direction; the path really is inert.
- **The `seconds * 30.0` sites that fire at the fade.** A breakpoint census of
  all 145 `lui rX, 0x41F0` sites, taken at v418 where the fade is set up, leaves
  five: `00165D84` (x25), `00251ACC` (x10), `00166B20`, `0018352C`, `00183A54`.
  Flipping the four non-switch sites to 0x4270 (60.0) leaves the fade at **29
  vsyncs**, unchanged.
- **Any integer per-tick countdown.** Scanning all of RAM for a u32 that falls
  by exactly one per tick across the plateau, with a starting value between 16
  and 40 (a 28-tick counter must be in that band), returns **zero** words. The
  duration is not an integer countdown.
- **Float ramps and alpha humps.** Both scans are swamped by the GS packet
  buffers at `003Exxxx`, `0044xxxx` and `006Bxxxx-007Dxxxx`, which are rebuilt
  every frame. The few candidates in the game heap (`0187BB58`, `0187D280`)
  trace to reused scratch - their values jump between garbage, and at one point
  `0187BB58` holds 37.033, the projectile speed constant - and their writers are
  a generic buffer fill at `ra 001319E0`.

### The instrument that made this tractable

`fadequick.py`: film only v415..v515 at 1/8 scale and report the span above half
the peak white fraction. One run is about two and a half minutes against roughly
ten for the full film, and it reproduces the full film's numbers exactly. Any
further attempt on this should use it rather than filming the whole move.

### Where to go next

The duration is not a counter and not one of the 30.0 conversions, so the
remaining candidates are a float accumulator inside an effect node - the same
place the 2026-09-06 launch flash ended up - or a beat inside the scripted
sequence that `[60FPS - sequence wait]` does not reach. The sequence is the
better bet precisely *because* the surrounding beats are correctly paced: a wait
that the group already halves would move with them, so a fade that does not move
is likely being timed by a different counter in the same machinery.

## 2026-09-09 - the Galick Cannon fade: it is the fade SERVICE, and it is fixed

`[60FPS - screen fade]`, two words. The fade is not specific to Vegeta, to the
Galick Cannon, or to ultimates: `FUN_00172810` is the game's **fullscreen fade
service**, and its callers hand it durations in **seconds**.

### What the earlier section got wrong

The 2026-09-09 entry above reports "28 ticks either way" and calls the fade
correctly paced in ticks but short in real time. The direction was right and the
number was not. `fadequick.py` scores the span above **half the peak** white
fraction, and the fade saturates the screen - so that window measures the
*plateau*, not the fade. Filming the mean luma per vsync instead gives the real
shape, and it is the same in both arms:

| phase | 30fps | 60fps |
|---|---|---|
| ramp up | 6 ticks | 6 ticks |
| plateau | 26 ticks | 25 ticks |
| ramp down | 14 ticks | 14 ticks |

**~46 ticks either way**, which is 92 vsyncs at 30fps and 46 at 60fps. Every one
of the four earlier eliminations still stands; they were all looking for a
28-tick control that does not exist.

**The scan that finally worked, and why the earlier ones could not.** A float
scan for the blend was run across v438-v450 - inside the plateau, where the
blend is pinned and *nothing moves*. Re-running the identical scan across the
fade-OUT instead put the answer on the first page.

### The node

Filming a 256-byte window every vsync and printing only the fields that move:

```
data+0x00..0x0C   255,255,255,255    the colour, as floats
data+0x10         15 .. 0            fade-in counter, -1.0 per tick
data+0x34         15.0               fade-in duration (the divisor)
data+0x14                            hold counter, -1.0 per tick
data+0x44         0 .. 180           hold cap, +1 per tick
data+0x18         30 .. 0            fade-out counter, -1.0 per tick
data+0x38         30.0               fade-out duration (the divisor)
data+0x30         blend handed to the renderer
node+0x01         phase: 0 in, 1 hold, 2 out
node+0x28         002C3C58, the vtable
node+0x38         the data block
```

`+0x30` is `counter/duration` in phase 0 and `1.0 - counter/duration` in phase 2,
which is why the screen saturates until the blend crosses ~0.55 in either
direction - the white is drawn over-bright, alpha 128 on the PS2's 0-128 scale.

### The bug, and why one word fixes all of it

The node's init, `FUN_00172718` (vtable `002C3C58` slot `+0x04`), is handed a
descriptor and converts it:

```
00172744  lui   at, 0x41F0       ; 30.0
00172780  mul.s f2, f2, f3       ; +0x10 = fade-in  seconds * 30
0017278C  mul.s f0, f0, f3       ; +0x14 = hold     seconds * 30
00172794  mul.s f1, f1, f3       ; +0x18 = fade-out seconds * 30
001727A4  swc1  f2, 0x34($s0)    ; the divisors are copies of the same counts
001727A8  swc1  f1, 0x38($s0)
```

**The same defect as the tween constructor at `00267AC8`, in a second
general-purpose service.** A caller asks for seconds; the constructor assumes 30
ticks make one. Changing the 30.0 to 60.0 doubles all three counts *and* the
divisors together, so the blend curve is bit-identical and only its rate halves.
The 180-tick hold cap at `001728C8` is a separate literal and is doubled on its
own.

    patch=1,EE,00172744,word,3C014270 // 30.0 -> 60.0
    patch=1,EE,001728C8,word,28430168 // hold cap 180 -> 360

### That the callers speak seconds is not an inference

The static descriptors are in the ELF. `FUN_001725F4` copies `002ECCC0` per
player; `FUN_001729F0` reads `002ECCF0`:

| descriptor | colour | fade-in | hold | fade-out |
|---|---|---|---|---|
| `002ECCC0` | 255,255,255 alpha 128 | **0.5 s** | **1.0 s** | **0.5 s** |
| `002ECCF0` | 255,255,255 alpha 0 | **1.0 s** | 0 | **1.0 s** |

Round authored seconds, not frame counts. The Galick Cannon's own node measures
15 and 30 frames - 0.5 s and 1.0 s - built on the stack by the caller rather
than from either static block. The three call sites into the service are
`00156FD4` (beam-object module, `FUN_00156E24`), `0015B9E4` (blast-object
module, `FUN_0015B92C`) and `0017268C` (the per-player block above); all three
enclosing functions are in the 0-callers group, reached from the effect script.

### Verified

Filmed per vsync on save state 3, scored on mean luma, **through the shipped
pnach group** and not a memory poke:

| arm | full white | lifts at | scene behind it | dark by |
|---|---|---|---|---|
| 30fps oracle | v446..v495 (50) | v508 | mean 170 | v524 |
| 60fps before | v437..v460 (24) | v476 | **mean 90 - the animation** | - |
| 60fps after | v443..v491 (49) | v504 | mean 168 | v519 |

The fall is value-for-value the 30fps curve over the same 28 vsyncs. The
remaining 3-5 vsyncs is the emulator running at 56.7 ticks/s against an ideal
58.6, not the patch.

Directly on the node, `nofade` against `full`:

    nofade   in 15f out 30f   blend 1.000 0.933 0.867   step 1/15
    full     in 30f out 60f   blend 1.000 0.967 0.933   step 1/30

**No regression.** The move's own beats are unchanged vsync for vsync across all
eleven state transitions of the 700-vsync ultimate:

    v0:11/11 v2:287/11 v177:302/314 v488:11/208 v517:11/217 v557:11/220
    v593:11/219 v616:11/216 v617:11/228 v644:11/56 v646:11/11

identical under `nofade` and `full`. The fade is cosmetic and moves no beat.

### What this does not cover

Not every impact flashes the screen. **Frieza's I Might Die This Time rocks and Buu's Super Kamehameha do
not construct a fade node at all** - a breakpoint on `FUN_00172810` through both
moves, in both arms, never fires. So no second *visual* sample was available
without a character-select run. The globality claim rests on the fix being at
the seconds-to-frames conversion every caller passes through, which is stronger
than a second sample would have been, but it is worth knowing that a move
looking wrong in this way may simply not be using this service.

### A four-site variant, measured and not shipped

Halving each per-tick step instead - `00172880`, `00172960`, `00172994` - reads
identically (white v443..v491, dark by v519). It is not shipped because the
fade-out's 1.0 does double duty as both the step and the 1.0 in
`blend = 1.0 - counter/duration`, so it needs `add.s $f2, $f2, $f2` inserted into
one of the two nops at `001729AC` to rebuild it. Two words with no inserted
instruction beat five with one.

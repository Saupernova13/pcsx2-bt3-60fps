# Rush Struggle and Beam Struggle

Both stick-rotation contests, their tick clocks and the CPU's synthetic stick.

## 2026-09-10 - the Rush Struggle: confirmed doubled, mechanism found, fix unfinished

The user, playing Cell against Devilman, hit a Rush Struggle - both fighters
throw a rush attack, they collide, and both players rotate the left stick as
fast as they can - and reported the CPU's hit count doubled at 60fps. It is
worse than that: **every part of the minigame is authored in ticks, so at 60fps
the whole contest runs in half its real time while the player's hands do not
speed up.**

### Getting the user's state onto the dev rig

Their PCSX2 writes savestate format 0x9A55; PCSXROO reads 0x9A59. Four bumps
apart - SPU voice decode buffers, then the EE and VU cycle counters widening to
64 bit - so the dev rig refuses the file, and rewriting the version stamp gets
as far as `Save state corruption in internal structures`. **The dev rig can no
longer load anything the user's install produces**, which had quietly blocked
this whole class of work.

`tools/transplant.py` solves it by not using the file format at all: the fight
is in EE main memory, the ELF is byte-identical in both builds, and every
pointer in it is an absolute EE address. Pause PCSXROO at a frame boundary with
the same game running, write the source's EE RAM and scratchpad over it, resume.
The fighter states came back 287/284 exactly as the source held them and the
scene ran. `--save-slot` then writes it out natively, so it is a one-time cost.

### The struggle, located

| what | where |
|---|---|
| fighter state | **250**, handler `FUN_001F47C8` from the table at `002C4980` |
| hit count | **`fighter+0xE50`** - zeroed on entry and on exit, and what the HUD shows as "N Hits!" |
| the registrar | `FUN_001E11D0`, the only thing that increments it |
| the state's tick counter | `fighter+0x964` |

Hits are registered on cadences authored in 30Hz frames, selected by character
attribute bits, plus one every-tick path:

    if QueryCondition(fighter, 0x33, 1)   -> a hit EVERY tick
    else attribute 0x6A -> every 28 ticks   (001F4958, literal 0x1C)
         attribute 0x69 -> every  8 ticks   (001F4980, andi 7)
         attribute 0x68 -> every  5 ticks   (001F49A4, literal 5)
         otherwise      -> every  4 ticks   (001F49DC, andi 3)
    and if [fighter+0x3D0] & 1 -> another every 15 ticks (001F49FC, literal 0xF)

Condition 0x33 resolves through the jump table at `002EF070` to a test of bit
`0x02000000` of **`fighter+0x74C`** (CUR_B in the fighter's own input block).
That is the rotation event. The player's copy is raised by real stick movement;
the CPU has no stick, so the AI's synthetic input raises its copy - and the AI
runs per tick.

Breaking on the registrar and reading `$ra` and `$a0` splits one struggle
exactly, and the totals reconcile with the counters:

| fighter | site | path | hits |
|---|---|---|---|
| CPU | `001F49C4` | the rotation condition | **36** |
| CPU | `001F49E8` | every 4 ticks | 10 |
| CPU | `001F4A1C` | every 15 ticks | 6 |
| CPU | `001F4AE4` | the finishing hit | 1 |
| player | `001F49E8` | every 4 ticks | 20 |
| player | `001F4A1C` | every 15 ticks | 6 |

### Measured, same save state, same input

With no input at all, so this is purely the CPU's automatic accrual:

| arm | struggle | CPU hits | per tick | **per vsync** |
|---|---|---|---|---|
| 30fps stock | 88 ticks / **177 vsyncs (2.95s)** | +50 | 0.568 | **0.2825** |
| 60fps, battle group only | 88 ticks / **88 vsyncs (1.47s)** | +50 | 0.568 | 0.568 |
| 60fps, full patch | 98 ticks / **98 vsyncs (1.63s)** | +51 | 0.520 | **0.5204** |

**The struggle is exactly 88 ticks in every arm.** Identical in tick space,
half the real time at 60fps, and `[60FPS - animation clock]` does not stretch it.

Driving the stick in a circle on the wall clock, identically in both arms:

| arm | player | CPU | contest |
|---|---|---|---|
| 30fps | 22.5 hits/s | 21.6 hits/s | **even** |
| 60fps | 32.4 hits/s | 35.3 hits/s | CPU ahead |

The player's figure at 60fps is **inflated** by the instrument: the debug link
caps the pad at ~43 updates a second, which the 30Hz arm cannot out-sample but
the 60Hz arm can, so a real hand on a real stick does worse than this shows. The
CPU's rise is clean at 1.6-1.9x, and it is purely a function of tick rate.

### Why the obvious fixes do not work

- **Halving the hit cadences** (doubling all five literals) cuts the player's
  automatic hits from 26 to 13 but the CPU's only from 53 to 43, because the
  CPU's dominant stream is the rotation path, not the cadences.
- **Gating the rotation path to even ticks** works - a trampoline at `000F1500`
  redirecting the condition call at `001F4938` and honouring it only when
  `[fighter+0x964]` is even took the CPU from 0.5204 to 0.2449 hits per vsync,
  against the 30fps target of 0.2825. But **the player's hits come through the
  same call**, so it halves both sides and leaves the ratio - and therefore who
  wins - exactly where it was.
- **Doubling the struggle's duration** is what would actually give the player
  back their time, and the per-tick `[obj+0x94] += 0.5` at `001F4C34` is not it:
  halving that constant to 0.25 was verified in RAM and moved the duration not
  at all. The 88 ticks come from somewhere else - the outcome is signalled by
  animation event flags 0xBF and 0xC0 (`FUN_001DAAF0` registers them on entry,
  `FUN_001DAC78` tests them), so the next place to look is what drives that
  timeline, since it is demonstrably not the animation clock this patch halves.

### What a correct fix needs

Two things, and the second is not yet found:

1. **Halve the CPU's stream without halving the player's.** They share
   `001F49C4`, so this needs a per-fighter AI discriminator. `+0x04`, `+0x08`,
   `+0x0C`, `+0x940` and `+0x944` are all just the fighter index or shared
   constants; diffing a COM-on-Stand state against a COM-on-Level-5 state was
   swamped by ordinary fight divergence. Not found yet.
2. **Restore the 88-tick duration to its real time**, so the player gets the
   2.95s of rotating the fight was authored around instead of 1.63s.

Recorded unfixed rather than shipped half-done: a change that halves both sides
equally would move the numbers on screen without changing who wins, which is
precisely the complaint.

**Reproduce it with `roo.loadstate(3)` on the dev rig** - the transplanted state
is native now, and both fighters enter state 250 within a second of loading.

### 2026-09-10, continued - what the second pass ruled out, and a reframing

**The outcome decision, found.** `001D945C`/`001D9460` loads both fighters'
`+0xE50` and compares them with `slt` both ways. The winner of a Rush Struggle
is simply whoever has more hits, so the whole fix reduces to making each side's
hits-per-real-second match the 30fps arm.

**`fighter+0xD48`, found and set aside.** The handler writes it with 5, 11, 17
or **30** by character attribute (`001F4AC0`), and `001E1E2C` counts it down one
per tick. A 30Hz literal, but it is reloaded every tick by the handler, so it is
a latch - "was there a hit recently" - not the struggle's length.

**Ruled out as the duration clock:**

| candidate | how it was ruled out |
|---|---|
| `[obj+0x94] += 0.5` at `001F4C34` | halved to 0.25, write verified in RAM, duration moved 0 ticks |
| the model's animation clock, `model+0x138` | reads 0.0 for the whole struggle in both arms - this clip is not on it |
| `fighter+0x964` | the generic per-state tick counter (`001E23A8` increments, `001E2484` zeroes); 65 readers, none comparing it to a struggle length |
| `fighter+0x15E0/+0x15E4` | advance +1 a tick but are only read by HUD code at `00204D20` / `00211EC4` |

`FUN_001C47A8` shows the shape of the real answer: it compares an animation
object's `+0x138` against `+0x13C` with **`c.eq.s`** - current time against end
time, exact equality - and reports finished. So the struggle's length is a clip
length divided by a per-tick advance, on an animation object that is **not** the
model this project already patches. Finding that object is the open task.

**The AI discriminator, and why it may not be needed after all.**
`FUN_001D4658` steps byte-identically for both fighters over 220 instructions,
and the input-source copier at `001D45D0` is the same code for both, so the AI
writes further upstream than either. Flipping COM Settings from Level 5 to Stand
with the game paused - the clean way to diff - changed **zero** words in either
fighter struct, so the AI level is not a fighter field.

But the instrument, not the game, may be what made a discriminator look
necessary. The debug link caps the pad at ~43 updates a second: the 30Hz arm
cannot out-sample that, the 60Hz arm can, so the player's measured hits per tick
fall from 0.750 to 0.541 across the arms while the CPU's barely move. **A real
stick sweeps continuously**, so a real player's hits per tick should be the same
in both arms - and if that holds, the only defect is that the struggle gets half
its real time, and

    double the duration  +  halve every hit cadence

restores the counts *and* the fairness with no per-fighter discrimination at
all. Both sides then score what they scored at 30fps, over the real time the
fight was authored around.

That hinges on one number nobody has measured: **a human's hits per tick at
60fps.** One played struggle with the final two counts would settle it.

### 2026-09-10 - FIXED: the AI rotates twice as fast, and the fix is one flag

The instrument was the thing standing in the way, and the user named it: drive
**both** sticks, and drive them from **elapsed game time** rather than the wall
clock. Frame stepping with the angle computed as `vsync / 59.94 * rot_per_sec`
simulates a real hand exactly - one real second of rotation is one real second
in either arm - and removes the ~43-updates-a-second ceiling the socket imposed.

Measured that way, at a true 5 rotations a second on both sticks:

| arm | struggle | player | CPU | winner |
|---|---|---|---|---|
| 30fps oracle | 88 ticks / 2.95s | 66 | 59 | **player** |
| 60fps, before | 98 ticks / 1.63s | 47 | 53 | **CPU** |

**The outcome flips.** Not a cosmetic doubling - the fight is decided the other
way round.

### The discriminator, found

Tracing both fighters through `FUN_001D4370` - the input *source* function, not
the mask builder that had been traced before - the paths diverge at `001D43B0`:

    001D439C  lw   $v1, 0x1278($s1)
    001D43B0  beqz $v1, 0x1D4470      ; 0 -> read the pad
    001D43B8  ...                     ; nonzero -> synthetic input at
                                      ;   +0x127C buttons, +0x1280/+0x1284 stick

**`fighter+0x1278` is the game's own human/AI flag** - 0 on the pad-driven
fighter, 1 on the CPU. Confirmed live on both fighters.

And the CPU's stick is visibly synthetic: sampled through a struggle, the
player's `+0x93E/+0x93F` hold continuous analog values while the CPU's only ever
read `0x00`, `0x7f` or `0xff` - it snaps through cardinal directions, one step
per tick. That is why the CPU gains with tick rate and the player does not.

### The fix

`[60FPS - rush struggle]`: route the rotation query at `001F4938` through a
trampoline at `000F1500` that honours it only on even ticks of the state's own
counter, **and only when `fighter+0x1278` says the fighter is AI-driven**. The
player's input path is not touched at all.

Swept across hand speeds, as shipped from the pnach:

| rot/s | 30fps oracle | 60fps before | 60fps fixed |
|---|---|---|---|
| 2.0 | CPU 52-39 | CPU 53-33 | **CPU 37-33** |
| 3.5 | CPU 57-55 | CPU 53-40 | P1 41-37 |
| 5.0 | **P1 66-59** | CPU 53-47 | **P1 48-37** |
| 8.0 | **P1 82-60** | CPU 59-57 | **P1 58-37** |

The winner matches the oracle at 2, 5 and 8 rotations a second. 3.5 is a coin
flip in the oracle itself (55-57) and the fix lands on the other side of it.

**What is still not right:** the counts are low, because the struggle still runs
in 1.63s instead of 2.95s. The 88-tick duration is a clip length compared to a
clip end with `c.eq.s` in `FUN_001C47A8`, on an animation object that is not the
model this patch halves, and that object is still unfound. Doubling the duration
would restore the counts; it would not change the ratio, so it is a separate and
much less urgent defect than the one now fixed.

## 2026-09-12 - the Beam Struggle: the whole contest is on a tick clock

The user hit a Beam Struggle - both fighters fire a beam, the beams collide, and
both players rotate their sticks - and asked for the 30fps and 60fps screens to
be compared and the difference fixed. There is no hit counter on screen for this
one, so the comparison has to be made against the game's own internals.

### Getting the state onto the dev rig

Their save state was made **on the pause menu**: every fighter field is frozen,
`+0x964` included, and 600 vsyncs of film showed nothing moving at all. Twenty
screenshots of "1P PAUSE" is what that looks like. `tools/transplant.py` carried
the RAM across as before; Start then closes the menu, and the un-paused scene is
re-saved natively as dev slot 5. **The button press stays outside the measured
window** - it lands two ticks after a load, and a press is asymmetric in ticks
against vsyncs.

### The clash, located

| what | where |
|---|---|
| fighter state | **304**, handler `FUN_001FB660` |
| rotations counted into | **`fighter+0xE4C`** - and it does **not** start at zero |
| the rotation query | condition **0x33** at `001FB9BC`, the same condition the Rush Struggle uses, gated on `+0x964 >= 16` |
| the contest itself | **`FUN_001D8E50`**, an event manager dispatched once per tick from `FUN_001D9900` for modes 1..5 |
| the clash point | `pt = tug/(|tug|+20)`, written at `001D92BC`; `[m+0x10]` is its world position, lerped between the two fighters' bone 0x11 |

`+0xE4C` is seeded on entry from the move's power over 20, then +10/6/3 or
-10/6/3 by character attribute (`001FB6FC..001FB7D8`) - a head start that does
not scale with time, so halving the clash's duration doubles its weight.

The manager's phases, all counted in ticks:

| phase | what | length |
|---|---|---|
| 2 | fighter 0's introduction, then fighter 1's, then the tug: **+-1 per tick** toward whoever leads on cumulative `+0xE4C` | 30 + 30 + 46 |
| 3 | show the result | 16 |
| 4 | drive the tug out by 4 a tick until \|tug\| >= 71 | ~7 |
| 5 | resolve: winner gets flags 0xC1/0xC3, loser 0xC2 and state 260 | 1 |

The +-0.64 thresholds on `pt` only pick a camera mode; they do not end anything.

### Measured, same save state, both sticks at a true 5 rotations a second

| arm | clash | player | CPU | tug | winner |
|---|---|---|---|---|---|
| 30fps oracle | 130 ticks / **4.34s** | 91 | 88 | +45 | **player** |
| 60fps, before | 130 ticks / **2.17s** | 61 | 62 | -45 | **CPU** |

**The outcome flips**, and for two reasons at once: the whole cinematic plays in
half its real time, and a human's hands do not speed up while the CPU's
synthetic stick steps once per tick, exactly as in the Rush Struggle.

### What was tried and rejected: gating the manager itself

Running the manager only on even global ticks restores the duration exactly -
260 vsyncs, and the player's count lands on the oracle's 91 - but it **strobes**.
Six consecutive vsyncs photographed mid-tug alternate between two camera views,
because `FUN_001D8980` and `FUN_001D8B88` issue a camera request through
`FUN_001C6E78` every tick and a skipped tick leaves the previous frame's camera
standing. It also leaves the clash point stepping at 30Hz. A per-tick call that
looks like bookkeeping can be a render request.

### The fix

Keep the manager running every tick and halve its **clock** instead:

- double every phase length - 30 -> 60, 60 -> 120, 106 -> 212, and 16 -> 32 in
  phase 3 - so each phase lasts its 30fps real time;
- leave the tug at +-1 a tick. Over twice as many ticks it reaches twice the
  magnitude, so **halve the clash point constant** at `gp-0x6F40` from 0.05 to
  0.025. `pt` then lands exactly where 30fps puts it and updates smoothly every
  frame rather than in 30Hz steps. That constant has exactly one reader,
  `001D8E10`; nothing else in either segment addresses it;
- phase 4's limit 71 -> 142, its +-4 step unchanged, which is the same real-time
  speed in doubled units;
- gate the AI's rotation query to every other tick through the game's own
  human/AI flag, `fighter+0x1278`, exactly as `[60FPS - rush struggle]` does -
  its own trampoline at `000F1540`, because the validator refuses the same
  address in two groups;
- double state 304's rotation start, 16 -> 32 ticks.

### Verified

The AI gate is **exact**, and there is a clean way to prove it: with the 60fps
base patch alone the AI draws the same random stream as the 30fps game, and its
stepping is identical tick for tick (0.492 a tick, +54, in both).

| arm | idle | 5 rot/s |
|---|---|---|
| 30fps oracle | CPU 31-72, 4.34s | P1 91-88, 4.34s |
| 60fps base + this fix | CPU 31-**72**, 4.30s | P1 **91**-86, 4.34s |

Shipped (every group enabled), against the oracle:

| rot/s | 30fps oracle | 60fps fixed |
|---|---|---|
| 0 | CPU 31-72, 4.34s | CPU 31-59, 4.30s |
| 2 | CPU 55-72 | CPU 55-60 |
| 3.5 | **CPU 73-75** | **P1 73-69** |
| 5 | **P1 91-88** | **P1 91-74** |
| 8 | **P1 119-88** | **P1 128-74** |

The player's count matches the oracle exactly at 2, 3.5 and 5, and the duration
matches within two vsyncs. At 8 rotations a second the player scores *more* than
at 30fps - 128 against 119 - and that is not a defect in the fix: a hand turning
8 times a second crosses 32 quadrants a second, and the 30fps game only samples
the stick 30 times. The 60fps game sees crossings the 30fps game aliases away.

### Still not right: the CPU ends low in the full build

With every group enabled the CPU ends 10-18% below the oracle, and at 3.5
rotations a second - a near-tie the 30fps game gives to the CPU, 73-75 - that
flips the result. The cause is upstream of this fix: the CPU's clash stepping is
**0.377 a tick with the full preset against 0.492 with the 60fps base patch
alone**, so the gate halves an already-slowed AI.

That is not a random-stream side effect. Dropping any single group from the full
preset leaves it at *exactly* 0.377 and +42 - **all 24 tested one at a time, bit
identical** - so no one group owns it, and the AI's decisions are not sensitive
to those groups at all. Only `animation clock` moves it, and barely (0.385).

Building up instead of tearing down found it, and it is not an AI defect at all:

| arm | CPU stepping |
|---|---|
| 30fps, and 60fps with the base patch alone | 0.492 a tick |
| + `beam object travel` | 0.385 |
| + `animation clock` on top | 0.377 (the full preset) |

Adding any of the other 22 groups changes nothing at all. So what slows the CPU
is **the beams travelling at their correct speed**, which changes where and when
the two of them meet and therefore the geometry the AI is reacting to, plus a
little from the animation clock. The AI itself is per-tick and deterministic -
the same decisions in 24 different patch sets - and the gate is exact where the
approach is directly comparable. What is left is that the CPU enters the tug
phase from a slightly different situation than at 30fps, and this fix does not
reach that.

One arm of that sweep is worth keeping for its own sake: **with `beam object
travel` removed, the clash never happens at all** - 0 ticks in state 304 from a
save state that is 13 vsyncs away from it. Unpatched, the beams cross at double
speed and miss each other. A group that paces a projectile decides whether two
of them ever meet, which is also why subset bisects of this measurement kept
finding nothing to measure.

### Confirmed in play, 2026-09-12

The user played the clash from their own save state with v22 installed: **"it
indeed was fixed in terms of duration."** That is the half of this that is
visible without a counter on screen. Who wins when they rotate hard is not yet
reported, so the star stays.

### The player's input is still read every tick, and that is deliberate

Their next question was whether the *read rate* was fixed too. It is not. The
gate tests `fighter+0x1278` and only halves the **CPU's** query, so a human's
stick is still sampled once per tick - 60 times a second against the original's
30.

That sounds like a defect and is not, because the clash counts one rotation per
quadrant crossing with no debounce: the sampling rate only matters once the hand
out-runs it.

| hand speed | quadrant crossings/s | 30fps | 60fps with v22 |
|---|---|---|---|
| 2 rot/s | 8 | 55 | **55** |
| 3.5 rot/s | 14 | 73 | **73** |
| 5 rot/s | 20 | 91 | **91** |
| 8 rot/s | 32 | 119 | **128** |

Below about 7.5 rotations a second - 30 crossings, the 30fps sampling rate -
both arms see every crossing and the counts are identical. Above it the *30fps
game* is the one that is wrong: it samples 30 times a second while the hand
crosses 32 quadrants, and silently drops rotations the player actually made.

Gating the player's side as well would be one word - the same trampoline without
the `+0x1278` test - and would reproduce the original's blind spot exactly. It is
deliberately not done: it would make the game eat input a player can feel
themselves giving it. Recorded here so the choice is visible rather than assumed.

### A lead for the Rush Struggle

The same dispatcher runs the Rush Struggle: modes 6-8 go to `FUN_001D9330`,
which contains `001D945C`, the winner decision found on 2026-09-10. **The Rush
Struggle's 88-tick duration is almost certainly that manager's own clock**, not
the animation clip that was hunted and never found. The technique above - double
the phase lengths, leave the per-tick work alone - should apply to it directly.

## 2026-09-22 - the Rush Struggle's length (#56)

The lead above was right. `FUN_001D9330` is the Rush Struggle's manager:

| mode | what it does |
|---|---|
| 6 | zeroes `[m+0x70]` and starts the contest |
| 7 | counts `[m+0x70]` once a tick, cues each fighter's introduction (event `0x18`) at 0 and at 15, and after 76 ticks (`001D940C` `slti $v1, $v0, 0x4C`) hands over to mode 8 |
| 8 | compares the two `fighter+0xE50` counts once (`001D945C`), raises `0xBF`/`0xC0`, and runs until `FUN_001D87D8` reports the finish |

So the contest was always 76 ticks plus an animation-paced finish. Doubling the
cue (`001D93D8` and `001D93EC`, both `li $v0, 0xF`) and the length puts it back
on its real time.

Twice the ticks would also double the automatic hits. Those land when the
state's tick counter `fighter+0x964` is a multiple of an authored cadence, so
the five literals double with it:

| site | was | cadence |
|---|---|---|
| `001F4958` | `li $v0, 0x1C` | every 28 ticks, attribute `0x6A` |
| `001F4980` | `andi $v0, 7` | every 8, attribute `0x69` |
| `001F49A4` | `li $v0, 5` | every 5, attribute `0x68` |
| `001F49DC` | `andi $v0, 3` | every 4, the default |
| `001F49FC` | `li $v0, 0xF` | every 15, while `fighter+0x3D0` bit 0 |

Cell against Devilman, the 2026-09-10 transplant, now kept as
`work/state-backups/cell-vs-devilman-rush-struggle.p2s`:

| no input | 30fps | v24 | v24 + this |
|---|---|---|---|
| struggle | 196 vsyncs | 116 | 192 |
| player's hits | 26 | 26 | 26 |
| CPU's hits | 52 | 36 | 49 |

| player's stick at a true N rotations a second | 30fps | v24 | v24 + this |
|---|---|---|---|
| 3 | 51-56, CPU | 40-37, player | 54-53, player |
| 5 | 66-59, player | 48-37, player | 72-57, player |
| 8 | 82-60, player | 58-37, player | 95-57, player |

The counts are back on the 30fps scale, and the winner matches at 5 and 8. At 3
the 30fps game gives it to the CPU by 5 and this build to the player by 1, which
v24 already did.

Two residuals, both outside this change:

- **The CPU is about 3 hits low.** By source, 30fps gives it 30 hits on the
  rotation and attribute path (`001F49C4`) and 15 on the every-4 cadence
  (`001F49E8`); this build gives 34 and 8. The every-4 cadence only runs on
  ticks where the rotation condition is false. The shipped AI gate honours
  rotation on even ticks, which are also the only ticks the doubled cadence can
  fire on, and the 60Hz AI's rotation lands on more of them.
- **A spinning player gets a few more hits than at 30fps**: 54 against 51 at 3
  rotations a second. The stick is read every tick, as the Beam Struggle section
  explains.

Whether #56's story-mode "clashes where we teleport a lot and must press buttons"
are this struggle is the user's call. The fighters do zip around the arena
between exchanges, and nothing else found so far runs a contest on this clock.

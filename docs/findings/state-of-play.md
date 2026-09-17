# State of play and the user's reports

The running summary, the user's defect lists and every play-test.

## STATE OF PLAY - read this first

Last revised 2026-09-08. **20 groups ship**, in `patches/428113C2.pnach` and
exported to `releases/latest/`.

**v13, v14 and v15 are confirmed in play by the user, 2026-09-08.** The Lightning
Attack, the Cell Perfect Barrier camera, and the mouths - cut-in and pre-fight
intro both. v14's star is cleared. None of it touches v12's input-timing flag,
which still stands unverified.

**Deploy `releases/latest/`, never the working pnach.** See the 2026-09-08
section at the bottom: an install running the working pnach has five groups on
that must never be on, and it fails silently.

> **Build confidence - read `releases/STATUS.md` before shipping anything.**
> `v11-back-to-v8-set` (15 groups) is the **DEFINITELY FINE** baseline; its
> ultimate blast ends early and that is an accepted tradeoff, not a bug.
> `v12-restore-sequence-wait` (16 groups) is fine but carries a **standing flag
> for a potential input timing issue**, inherited by every later build until it
> is explicitly cleared. `v9` (17 groups) is **DO NOT USE** - the state 157 trap.
> `[60FPS - state phase timers]` is withdrawn. Every one is verified against the unpatched
30fps game as its own oracle - same save state, same input, same number of
vsyncs - and the ones the user can see have been confirmed in play.

| group | what it does |
|---|---|
| `60FPS - battle` | battle loop stride 2 -> 1 at `0012BCE4`. The whole 60fps change; everything else compensates for it |
| `60FPS - animation clock` | halves the animation clock itself, at the step and getter sites around `FUN_001C47A4` / `FUN_001C4920` |
| `60FPS - input repeat timing` | doubles the menu auto-repeat delay and rate, `FUN_002577F8` |
| `60FPS - input timing` | halves the 128 per-button frame counters, `FUN_001D3C10` |
| `60FPS - aura update rate` | updates the ki aura on even frames while still drawing it every frame, `FUN_00164860` |
| `60FPS - effect rotation` | halves the three per-tick effect phase rates, `FUN_00251A48` |
| `60FPS - tween duration` | one word: the tween system's hard-coded 30.0 becomes 60.0, `FUN_00267AC8` |
| `60FPS - particle update rate` | gates the particle ageing pass on frame parity, `FUN_00167258` |
| `60FPS - hover bob` | halves the pi/30-per-tick sine phase behind the hovering idle |
| `60FPS - airborne motion` | halves `pos += dir * speed` and its ramp, `FUN_001DE000` |
| `60FPS - airborne vertical` | the same for `pos.y += vy`, `FUN_001DED78` |
| `60FPS - airborne residual` | halves the post-hit slide and its decay epsilon, `FUN_001DFD88` |
| `60FPS - gravity` | halves the gravity acceleration and the vertical step it drives, `FUN_001DED28` |
| `60FPS - blast hit cadence` | gates the hitbox tick counter `H[0x0A]`, so multi-hit attacks land at their authored spacing |
| `60FPS - blast effect duration` | halves 19 coupled per-tick steps in the two effect classes that draw a ki blast |
| `60FPS - sequence wait` | counts scripted-sequence waits down on even ticks - camera cuts, mouth lines, fades, beam releases |
| `60FPS - knockback flight` | doubles the three launch durations a Full Power Smash puts someone into, `FUN_001E9590` |
| `60FPS - pursuit timing` | the five frame counts and the intercept lead behind the Lightning Attack |
| `60FPS - camera pacing` | halves the camera blend rate and counts scripted camera moves down on even ticks, `FUN_001C69C8` / `001C5720` |
| `60FPS - mouth clock` | halves the cut-in keyframe clock, the second clip player, at `0024ED2C` / `0024F3D4` - scripted mouth and face tracks |
| `60FPS - state phase timers` | advances 22 of the fighter state machine's 28 phase counters on even ticks - charge lengths, recoveries |

**Read "The engine has no timestep" further down before anything else.** The
game has no delta anywhere. It is a fixed 30Hz tick loop now ticking at 60Hz,
so *everything* is 2x until it is individually compensated. Nothing
self-corrects.

### The three shapes a fix takes, and when each is right

1. **Halve a constant.** Right when a per-tick quantity is a float with its own
   step: `effect rotation`, `gravity`, `hover bob`, `blast effect duration`.
2. **Gate on frame parity.** Right when a system only *advances state*, and the
   draw is separate or still reachable: `aura update rate`,
   `particle update rate`, `blast hit cadence`, `sequence wait`,
   `state phase timers`. It is **wrong** for anything that *constructs*
   something each frame - see the withdrawn groups below.
3. **Double a duration.** Right when a length is authored in seconds and
   converted with a hard-coded 30. `tween duration` (`00267AC8`) and
   `screen fade` (`00172744`) both qualify - two general-purpose services
   with the same constant. **Look for this shape first in anything that
   takes a duration from a caller.**

### Withdrawn - kept in the repo pnach as a record, stripped from releases

- `60FPS - blast effect rate` gated the two effect updates. They rebuild the
  beam geometry every frame, so gating leaves nothing to draw and leaks nodes
  whose lifetime never expires.
- `60FPS - blast sequence rate` gated the sequence controller's vtable[0]. That
  call is what *spawns* the effects, so a charged blast rendered nothing at all
  and dealt 1520 damage instead of 13680.
- `60FPS - animation rate` is superseded by `animation clock`. Enable one or the
  other, never both.
- `60FPS - EXPERIMENT halve root motion` deliberately breaks ground movement.

**Both withdrawn gates failed the same way for the same reason: an effect that
is gated is an effect that does not get built.**

### Still wrong

| defect | status |
|---|---|
| An ultimate's beam lands its first hit ~0.5s early | The cinematic up to the launch matches within two vsyncs; the flight does not. **Neither an integer tick counter nor a per-tick float step** - all 513 of the former and all 140 of the latter have been gated or halved and none moves it |
| ~~Transformations run a few hundred ms **long**~~ | **FIXED, confirmed in play 2026-09-09** - and by nothing anyone aimed at it. Never investigated, no group was ever written for it, and nothing in v13..v19 has a mechanism that shortens a transformation. Closed on play, **attribution unknown** |
| ~~Pre-fight intro: mouths do not move at all~~ | **FIXED** by `mouth clock`, confirmed in play 2026-09-08. It was the same clip player after all, and it was a speed problem - the track ran out before the intro's first line. The old "not a speed problem" reading was wrong |
| ~~Death of an ordinary character: camera revolves too fast (item 3)~~ | **Solved**, reported by the user 2026-09-08 as fixed by earlier work. Never measured; closed on play |
| ~~Character switch: the sky stops rotating (item 5)~~ | **Solved**, reported by the user 2026-09-08. Never measured; closed on play |
| Death by a body-erasing attack: camera too fast, cuts weirdly (item 2) | **ASSUMED solved\*** - not checked by anyone. The user expects it to have gone with items 3 and 5. Asterisked deliberately: nothing has verified it |
| ~~The Galick Cannon fade to white ends early (item 7b)~~ | **FIXED** by `screen fade`, v19, **confirmed in play 2026-09-09**. Not a sequence beat at all: `FUN_00172810` is the game's fullscreen fade SERVICE and its init converts seconds to frames with a hard-coded 30.0 |
| ~~**Real-time blast travel speed** (item 1)~~ | **FIXED** across three movers. `projectile travel` (v16, ki blasts) and `beam object travel` (v18, Buu's Super Kamehameha **and his breath**) are **confirmed in play 2026-09-09**. `blast object travel` (v17, Frieza's I Might Die This Time rocks) is measured at 1.77x and halved, but the user **feels no change** - correctly, because at play range the rocks are 94% summon animation; see the 2026-09-09 play-test entry. **Explosive waves** are confirmed fixed in play, by which group nobody knows |
| ~~A Beam Struggle runs in half its real time, and the CPU wins it~~ | **FIXED** by `beam clash`, v22. The contest is an event manager counted in ticks; doubling its phase lengths restores 4.3s and the player's count matches the 30fps game exactly. **Duration confirmed in play 2026-09-12**; the outcome is not yet reported |
| A Beam Struggle: the CPU ends 10-18% low in the full build | **Not the gate** - with the 60fps base patch alone it reproduces the 30fps game outright, 72-72 idle and 91-86 at 5 rotations a second. It is `beam object travel`: beams at their correct speed change where and when the clash forms, and the AI reacts to that geometry. At ~3.5 rotations a second - a near-tie the 30fps game gives the CPU 73-75 - this build gives it to the player 73-69 |
| Frieza's I Might Die This Time rocks: the ~5-vsync fast **summon** phase | The travel is fixed; the 103-vsync pre-launch animation that dominates the move is not. 98.3 vsyncs at 60fps against 103.2 at 30. This is the part of that move a player can actually see. **The most legible thing still wrong** |
| Circling an opponent cruises at 0.80 of its 30fps speed | Root cause narrowed to a target value rather than the step. Refinement, not defect |
| Training-mode health regeneration ticks once per game tick | Cosmetic, training only, unfixed |

Everything else measures between 0.95 and 1.05 against the 30fps oracle.

### Do not re-open these - settled by measurement, not by argument

- **It is step SIZE, not step COUNT.** Call counters on the gameplay path read
  identically on the ground and in the air.
- **The ki aura is not a second bug.** It tracks a character whose motion was 2x.
- **The render chain is followers all the way down.** `fighter+0x15A0` <-
  `model+0x970` <- `bone[0]+0x40`. It is mapped in full below.
- **Root motion is the ground channel only.** During a launched flight the root
  delta is exactly `0.0000` every tick while the fighter still moves.
- **The charge meters are already correct.** `0031C4AC` and `0031C63C` both fill
  at +180 a second at either rate.
- **The animation clock works inside cinematics too.** Goku's model advances
  `+0x138` by 2.0 a tick unpatched and 1.0 a tick patched, and every clip that
  ends naturally ends at the same real time in both arms.

### Two claims elsewhere in this file are wrong

"There is no master framerate variable" - the effect system has a per-model
60fps flag at `model+0xA40` bit 24, which is never set. "Three `time += rate`
sites exist in the whole binary" - there are 620 in-place float accumulates.

### Instruments, and the traps that cost the most time

`tools/ratediff.py` asks every word in RAM whether it still moves at double
speed. `tools/tickcount.py`, `tools/tickstep.py` and `tools/phasetimer.py` find
the counters statically; `tools/mkgate.py` and `tools/mkhalf.py` write the
trampolines. `tools/realclock.py` times a move with the game running free.

- **A screenshot needs a running VM.** Any "frame-advance N, screenshot" loop
  lets uncounted ticks slip past every sample. Sample on the wall clock instead.
- **Check that the unpatched arm ticks 30 times a second.** The save states were
  captured while patched, so loading one *after* disabling the patch puts the
  patched words straight back.
- **Shrinking a live group leaves its dropped hooks in RAM**, because patchctl
  can only restore addresses the pnach still names. Shrink, then restart.
- **A new group name needs a restart** - the ini's enabled list is read at boot.
- **Never trust a deploy you have not read back.** `extended` writes one byte
  per line, not four; `python tools/apply-live.py --check` verifies.
- **Test inputs must cover the held path.** Three sessions of blast measurements
  tapped a button the player holds, and that blind spot cleared a group which
  breaks the game outright.

**Before doing anything, also read "Instrument notes for future agents" further
down.**

---

Scope agreed 2026-08-21: **battles only**. Movement, ki, combos, dashes, blast timing,
stun, gauges and AI must be correct at 60fps. Menus, world map and non-battle cutscenes
may stay at 30fps or be locked back to 30 with E-codes.

---

## 2026-09-07 - the user's full defect list

Everything below is the user's own observation of the shipped patch in normal
play, recorded verbatim in substance so no item gets lost between sessions.

### Still wrong, and running fast

Status column updated 2026-09-09, after the user's play-test of v16..v19.
**\*** = measured fixed against the 30fps oracle but **not yet confirmed in play
by the user**.

| # | What the player sees | Status |
|---|---|---|
| 1 | Blasts end too fast and travel too fast - **including explosive waves** | **CLOSED.** *ends* fixed and confirmed in play (v12-v15). *travels* fixed across three movers: ki blasts (v16) and Buu's Super Kamehameha + breath (v18) **confirmed in play 2026-09-09**; Frieza's I Might Die This Time rocks (v17) measured and halved but **still starred - the user feels no change**, see below. **Explosive waves confirmed fixed in play 2026-09-09**, group unattributed |
| 2 | Death by a body-erasing attack: the camera moves around the victim too fast and cuts weirdly | **ASSUMED solved\*** - nobody has ever checked it. Still the oldest unexamined item on this list |
| 3 | Death of an ordinary character: the camera revolves around the corpse too fast | **CLOSED**, user-confirmed 2026-09-08 |
| 4 | Camera is still too fast in some attack animations - Perfect Barrier named | **CLOSED**, user-confirmed 2026-09-08 (v14). But the user reported a *new* "some camera angles/speeds seem off" the same day - uncharacterised, open |
| 5 | Character switch: the sky stops rotating about a second in | **CLOSED**, user-confirmed 2026-09-08 |
| 6 | Pre-fight intro: mouths do not move at all; some intro animations are too fast or too slow for the camera | mouths **CLOSED**, user-confirmed 2026-09-08 (v15). **The intro animation pacing half was never addressed** |
| 7 | Vegeta's scouter "Final Galick Cannon": the start animation's mouth movement finishes early, and after the rush sequence the fade to white ends too early, revealing the animation still playing behind it | **CLOSED.** 7a mouth user-confirmed 2026-09-08; 7b fade fixed by v19, **user-confirmed 2026-09-09** |

### Running slow - overcompensated

| # | What the player sees | Status |
|---|---|---|
| 8 | Cell's Perfect -> Super Perfect transformation lasts roughly 0.3s longer than it should. Frieza final -> 100% likewise. Reads as a consistent transformation overshoot of a few hundred milliseconds. | **CLOSED, user-confirmed 2026-09-09** - and never investigated, never given a group. Nothing in v13..v19 has a mechanism that shortens a transformation, so **the attribution is unknown**. Closed on play, flagged as unexplained |

### What the list has in common

Items 2, 3, 4, 5 and 6 are all **camera or scene motion**, not fighter motion.
Items 6 and 7 are both **mouth animation** desynchronised from the shot it plays
over. Item 7 also has a **fade** ending before the animation under it does.
Blasts (1) are paced by the same scripted-sequence machinery as the ultimate's
camera cut already documented above.

That points at a single suspect rather than seven: a **scripted-timeline clock**
- the thing that advances camera keyframes, facial animation and screen fades
during a scripted shot - separate from the battle animation clock this patch
already compensates. One uncompensated tick source feeding all of them explains
why the fighters look right while everything staged around them runs double.

Item 8 is the opposite sign and so is almost certainly a *different* cause: a
transformation is being held slightly too long, which is what over-halving a
duration that was already partly compensated looks like.

## 2026-09-07 - play-test of v9, and the constant pool nobody had looked at

### What the user confirmed in normal play

The first report against the shipped 17-group patch, and it splits cleanly.

| | |
|---|---|
| **Confirmed fixed** | Blasts inside pre-load / cinematic animations. Goku's Angry Kamehameha **does not end early**: the full 3D bone animation plays, and the spawning Kamehameha's charge plays through properly |
| **Semi-confirmed** | Blasts generally "seem to last longer". Improvement, not a clean pass |
| **NOT fixed** | The character-switch sky rotation; Vegeta's scouter / Final Galick Cannon; Cell's Perfect -> Super Perfect transformation; mouth movement |

The user's own read, and it matches the grouping in the 2026-09-07 defect list:
**the sky, the scouter and the transformations all seem to stem from one issue.**

This retires the "predicted, not measured" row for the ultimate's cinematic -
`sequence wait` really did fix the staged beats, in play, which is what the
frame-stepped 161-vs-191 measurement claimed. It does **not** retire the row for
the death cameras or Perfect Barrier, which are still unmeasured.

### The symptom class, stated more precisely than before

Every unfixed item is a thing that **ends** at the wrong time while the animation
underneath it plays correctly:

- the sky **stops** rotating about a second into a character switch
- the Galick Cannon's fade to white **ends** before the animation behind it does
- the scouter line's mouth movement **finishes early**
- transformations **run long** - the same class, overshooting instead

That is not a rate that is too fast. It is a *duration* expiring at the wrong
time. Which is fix shape 3 - "a length authored in seconds, converted with a
hard-coded 30" - and so far exactly one group in the patch is that shape.

### Correction: the data segment DOES contain 1/30 and 1/60

This log has claimed since 2026-08-22, as evidence for "the engine has no
timestep", that *"the data segment contains no 1/30, 1/60, 30.0 or 60.0 float
anywhere"*. Half of that is wrong, and the half that is wrong is the important
half.

The reason nobody found them: **no scan in this project has ever read `.lit4`.**
The ELF's section table survived stripping, and it has a section layout that was
never examined:

    .text      00100000  0x1bf6b0     (NOT 0x1c33c0 - that figure swallowed .vutext)
    .vutext    002bf6b0  0x3cd0       VU microcode
    .lit4      002fc280  0x25a0       2408 pooled float constants  <- here
    .sdata     002fe880  0x8ee
    .DVP.overlay..* x12               VU1 microprogram overlays

ee-gcc materialises a float with `lui` when its low half is zero and pools it in
`.lit4` otherwise. So:

- `30.0` (0x41F00000) and `60.0` - low half zero - are **always** `lui $at, 0x41F0`.
  The old claim is correct for these, and the 145-site enumeration of that
  immediate was complete.
- `1/30` (0x3D888889), `1/60` and `pi/30` have non-zero low halves, so they are
  **never** an immediate and **always** a `lwc1` from `.lit4`. Every scan that
  looked for immediates was structurally blind to them.

This is the same failure as "every scan looked for floats, and the clocks were
integers", one level down.

### 24 pooled per-tick rates, 24 readers, one reader each

    1/30   x18      1/60   x2      pi/30  x3      pi/60  x2

Each constant has exactly one `lwc1 ...($gp)` reading it - a clean 1:1 map, so
each site is independent and can be swept alone.

| site | const | shape |
|---|---|---|
| `0017D940` | 1/30 | `[s1+0x4E4] -= 1/30`, then `c.olt.s` against 0 - **a countdown in seconds, in the effect-node region** |
| `0023F438` | 1/30 | `[a0] -= 1/30` - another per-tick countdown |
| `001DFEA0` | pi/30 | `[s0+0xA8] += pi/30` - a **second** bob channel in `FUN_001DFD88` |
| `001DFF0C` | pi/30 | `[s0+0xA8] -= pi/30` - the wrap-down path of the same |
| `001DFF44` | pi/30 | **already patched** - this is `[60FPS - hover bob]` |
| `001C670C` | pi/60 | `[s1+0x80] -= pi/60` per tick |
| `001C66D0` | 1/30 | `[s1+0x80] += x * 1/30` |
| `001C4F38` | pi/30 | phase fed to `FUN_0011F588` (sine) |
| `00143A9C`, `00144904`, `00145164`, `00210BE8`, `00210C60`, `00210ED8`, `002121D8` | 1/30 | **store 1/30 into an object field** next to a `lui $at, 0x4334` (180.0) and a `div.s` - seeding a per-tick step as instance data |
| `0020F09C` | 1/30 | a clamp - `if (x < 1/30) x = 1/30` - with `lui $at, 0x41F0` immediately after |
| `0013D2C0`, `0024C668`, `0024CCE0`, `0024E6D4`, `001C4534`, `001F5B7C` | 1/30, 1/60 | not yet classified; four sit in the clip-player module around `FUN_0024D038` |

**`[60FPS - hover bob]` is one of twenty-four.** It was found by a write
watchpoint on a symptom, never as a member of a class, and the class was never
enumerated. Two more pi/30 phase increments sit in the very function that fix
patched, untouched.

The constructor-seeding group matters most for method: a rate copied out of
`.lit4` into a struct field at construction is **invisible to any scan of the
update code**, because at update time it is data. That is the same reason the
particle system's alpha ramp and position rate resisted every constant hunt.

### Next

1. Census all 23 unfixed sites from an ordinary battle. Sites that do **not**
   fire there belong to the special situations the user is reporting - character
   switch, transformation, intro - which is the partition worth having before
   building any of those save states.
2. The clip-player cluster (`0024C668`, `0024CCE0`, `0024E6D4`) is the first
   place to look for mouth animation; facial animation is clip playback and
   "mouths do not move at all" has never been A/B'd against the unpatched game.
3. `0017D940` is a per-tick countdown in seconds in the effect-node region and
   is the strongest single candidate for "blasts end too fast" surviving at all.

## 2026-09-08 - status from the user, and blast travel is still the big one

Three of the reported defects closed on play rather than on measurement, and one
that had drifted into "semi-confirmed" came back as definitely broken.

| item | what the user says |
|---|---|
| 3 - ordinary death camera | solved |
| 5 - character-switch sky | solved |
| 2 - body-erasing death camera | not checked. **Assumed** solved, asterisked |
| 1 - real-time blast travel | **"definitely still the issue ... blasts traveling way too fast"** |

Items 3 and 5 were on the "predicted, not measured" row - `sequence wait` and
`camera pacing` were expected to move them and now evidently did. They are closed
on the user's word, with no oracle behind them; item 2 is closed on nothing at
all and is marked with an asterisk so that stays visible.

### Blast travel was never fixed, and the record half-hid that

Item 1 read "blasts end too fast and travel too fast". The *duration* half got
attention - `blast hit cadence`, `blast effect duration`, `sequence wait` - and
the user's feedback then became "blasts generally seem to last longer",
recorded as **semi-confirmed**. That phrasing let the untouched half drift out of
view. Travel speed has never been fixed and never been claimed as fixed: the
class table has said `ki blast + beam travel | procedural motion | open` since
2026-08-22.

The one substantive lead is also a warning. On 2026-08-22 the reasoning was
"airborne movement is position integrated per loop iteration with no delta-time
term, and projectiles use the same path, so this is one bug, not two". The
airborne half was then fixed - four groups, all confirmed - but that shared-path
claim was **never tested**, and the same section carries a later correction:
"position integrated per loop iteration was a guess and no such integrator
exists". So the projectile's motion path is genuinely unidentified. Inheriting
the airborne conclusion would be inheriting a guess that was already retracted.

A blast that travels at 2x also changes dodge timing, which makes it the highest
priority open item: it is the only one left that changes how the game plays
rather than how it looks.

## 2026-09-09 - the play-test: three milestones, one invisible fix, two mysteries

The user played v19 on their own EmuDeck install (deploy verified live over
PINE: `00172744 = 3C014270`, `001728C8 = 28430168` read back out of EE RAM of
the running process, so the pnach was in force, not merely on disk).

### Confirmed in play - stars cleared

| build | group | what the user confirmed |
|---|---|---|
| v16 | `projectile travel` | ki blast travel |
| v18 | `beam object travel` | Buu's Super Kamehameha **and his breath** |
| v19 | `screen fade` | the Galick Cannon's white flash covers what it should |

The user's word for these is **milestones**. v16 and v18 are the first fixes in
this project that change how the game *plays* rather than how it looks, and they
are now confirmed by the only instrument that counts.

**Buu's breath was never measured.** It was not in any oracle, not in any
save state, and no scan ever touched it. It is fixed because `beam object
travel` hooks the one `Vec3Add` at `00156004` that the whole object class
converges on, and the breath is on that class. This is the class-level hook
paying out on a move nobody tested - the same argument made for `screen fade`
being global, now with an independent confirmation behind it.

### v17 stays starred - and the numbers say why

Frieza's I Might Die This Time rocks feel unchanged in play. **The fix is real and the report is also
right.** Impact is `pre-launch + gap / speed`, and the fitted 30fps split is
**103.2 vsyncs of summon** against rocks crossing at **18.75 units/vsync**:

| gap | travel share of the whole move | what halving the travel moves |
|---|---|---|
| 125 | 6.7 of 110 vsyncs - **6%** | 102 -> 106: **4 vsyncs, 67 ms** |
| 474 | 25.3 of 128 - 20% | 113 -> 124: 11 vsyncs |
| 628 | 33.5 of 137 - 24% | 117 -> 134: 17 vsyncs, 0.28 s |

At the range anyone actually fights at, this move is **94% summon animation**.
The travel fix moves the impact by a seventeenth of a second, which is below the
floor of what a player can perceive. At gap 628 it recovers a quarter-second and
would be plainly visible - but nobody fights at 628 units.

**So the remaining legible defect in that move is the summon phase, not the
travel**: 98.3 vsyncs at 60fps against 103.2 at 30, roughly 5 vsyncs fast and
uncompensated. That is the same ~5-vsync pre-launch residual measured on Buu's
Super Kamehameha during v18. **It is now the most legible thing still wrong that
has a known address to start from.**

The lesson is not "the measurement was wrong" - it was right, and it predicted
this outcome before the play-test. The lesson is that **a ratio is not an
impact**: a 2x error on 6% of a move is a 6% error on the move. Measure the
share, not only the ratio, before calling something the most legible case. The
2026-09-09 entry that called the rocks "the most legible case" was wrong on
exactly that point - it read the ratio at gap 628 and generalised it.

### Two things fixed that nobody fixed

The user also reports **transformations** (item 8) and **explosive waves** (the
second half of item 1) correct in play. Both close on that report.

- **Explosive waves** have a candidate: a fourth caller reaching one of the
  three movers. That is what a class-level hook is meant to do, and the breath
  result above shows it happening on a move nobody measured.
- **Transformations running ~0.3s LONG has no candidate at all.** It was the
  only defect on the list with the opposite sign; it was never investigated and
  never had a group written for it. Everything that landed in v13..v19 makes
  things *slower*, which is the wrong direction to cure an overshoot.

Recorded as fixed, and recorded as **unattributed**, deliberately. An
unattributed fix can regress without anyone knowing which change to look at.

### What this leaves open

1. Frieza's I Might Die This Time rocks: the ~5-vsync fast **summon** phase (the travel is done).
2. An ultimate's beam lands its first hit ~0.5s early - still unfound after all
   513 integer tick counters and all 140 per-tick float steps.
3. Item 2, death by a body-erasing attack: never checked by anyone.
4. Item 6's second half, intro animation pacing against the camera.
5. "Some camera angles/speeds seem off" - reported 2026-09-08, uncharacterised.
6. v12's input-timing flag, never cleared, inherited by every build since.
7. The state 157 trap: seen once on v9, never reproduced under control.

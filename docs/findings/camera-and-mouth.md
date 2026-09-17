# The camera and the cut-in mouth

Camera pacing and the second clip player behind the mouths.

## 2026-09-08 - Cell's Perfect Barrier: the camera located and measured, NOT fixed

> **Superseded the same day - see "the camera, FIXED" at the end of this
> file.** The measurement below is sound and the oracle it defines is the one
> the fix was scored against; the conclusion that the animator was elsewhere is
> wrong. There is no separate cinematic animator. Kept because the two dead ends
> it records are still worth not repeating.

The user set the player character to Cell and asked for the Perfect Barrier
ultimate (L2 + Down + Triangle in Max Power) to be tested before and after, "see
at every frame where the camera is, fix the issue". Their description of the
defect is precise and worth quoting, because it is what a numeric trace has to
reproduce before it can be trusted:

> at 30fps the camera smoothly spins around Cell, from the back to the front,
> with him getting into his crouch-like position as the camera animates. At
> 60fps he gets into his crouched-ball position well before the camera even
> starts rotating, so for a few milliseconds the camera is in place and not
> rotating while he is already posed.

**The camera was found and the defect measured. It was not fixed.** What follows
is the state of it, so the next attempt starts from the oracle and not from
scratch.

### Reproduction

Save state 4 is Cell vs SSJ Gohan, both idle. Hold `L2` for 400 vsyncs, then
`L2+Down+Triangle`, and poll until Cell reaches state 264. The command press is
outside the measured window, so the tick-versus-vsync bias cannot reach it.
State 264 lasts 240 vsyncs at 30fps and 228 at 60 - the cinematic's overall
length is already right, which is `sequence wait` doing its job. The defect is
entirely inside a correctly-timed cinematic.

### Where the camera is

    0x002FEBD0            pointer to the camera object (0x01874620 here)
    cam + 0x00 .. 0x30    the 4x4 view matrix; +0x20 forward, +0x30 position
    cam + 0x260           the authored eye position
    cam + 0x270           the authored direction

and the chain that fills it, recovered by write watchpoint at each step:

    fighter+0x430  --Vec4Copy-->  cam+0x260  --FUN_0023ead0-->  FUN_0023e608
                                                             -->  view matrix

`fighter+0x430` is a copy of `fighter+0x420`, and has two writers: `001C6D40`
(the ordinary camera follow) and `0023EC80` (which turns out to be the
camera-vs-geometry raycast, not the animator). **The animator that drives the
orbit during a cinematic has not been found.**

Note the frustum planes at `0x0031BE10`-`0x0031BE60` are *not* the camera,
though they rotate with it and a naive "find a rotating unit vector" scan finds
them first. `FUN_00130ba8` builds them from the camera each frame.

### The measurement

Camera forward vector, degrees from its value at the start of the cinematic,
per vsync, deterministic (frame-advance, no screenshots):

     vsync     8     12     16     20     24     36     48     58
     30fps  59.2   92.3  126.4  156.7  169.9  152.5  146.0  144.5
     60fps  86.4  133.0  151.8  159.3  162.3  164.2  164.4  164.4

Both arms end up in the same place - the 30fps camera settles near (13.1, 6.3,
-27.3) and the 60fps one at (13.5, 6.2, -27.0) - but the 60fps camera **arrives
by vsync 36 and is frozen from there**, while the 30fps camera is still moving
at vsync 58. It is roughly twice as fast: 60fps at v12 is where 30fps is at
v22-24.

That is exactly the reported symptom. The camera finishes its spin early and
then holds, so the pose - which is correctly timed - is still running while the
camera sits still.

**Total absolute rotation error against the 30fps arm: 446.6 degree-vsyncs.**
That number is the oracle. Any candidate fix has to move it down.

### The dead end, recorded in full

`[60FPS - camera follow]` was written, measured, and **withdrawn**. It halved
the lerp at `FUN_001C6C20` that converges `fighter+0x420`, plus the per-tick
ramp of that lerp's rate at `$gp-0x7208` (0.0133333, which is 0.4/30).

The per-tick defect it fixes is real and was measured cleanly - vsyncs for
`fighter+0x420` to settle within 1.0 of the 30fps value went 42/32 at 30fps,
22/15 at 60fps, 40/35 with the fix - and it caused no regression. It simply
**does not move the camera**. Applied and unapplied, the camera rotation table
above is identical to the decimal. During a cinematic the orbit comes from
somewhere else and overwrites it.

Two further things learned building it, both worth keeping:

- **The exact compensation `k' = 1 - sqrt(1-k)` broke the game.** It is the
  correct algebra for an exponential lerp taken twice as often, and it matched
  the dolly as well as halving did, but it reproducibly stopped the charge and
  the ultimate landing a hit at all, while plain `k/2` left both oracles
  unchanged to the vsync. The cause was not pinned down - the suspicion is a
  rate above 1.0 somewhere, where `1-k` goes negative and the EE's non-IEEE
  `sqrt.s` takes the absolute value, turning a "snap immediately" rate into
  zero - but the rates sampled in ordinary play only reached 0.632, so that is
  a hypothesis and not a finding.
- **A screenshot contact sheet cannot measure this.** Scoring tiles by image
  difference gave 13.34 for one pair of runs and 1.92 for the same configuration
  on the next, and the control - the *same* preset captured twice - scored 6.78
  against itself while the cross-arm score was 5.30 to 11.41. The between-arm
  signal sits inside the run-to-run noise, because at 30fps a one-vsync sampling
  slip during a fast camera move lands on a different animation frame. Every
  conclusion drawn from those sheets was withdrawn. The per-vsync memory trace
  above is deterministic and reproduces to the decimal.

### What to do next

Find what writes `fighter+0x430` during state 264 specifically. The two known
writers are the follow lerp (ruled out) and a raycast (not an animator), so
there is a third path that only runs for cinematics - most likely the same
scripted-sequence machinery that `[60FPS - sequence wait]` already paces, but
stepping a camera track by a per-tick amount rather than counting a wait down.

## 2026-09-08 - the camera, FIXED, and it was never a Cell problem

The user's instruction was to re-evaluate the camera from scratch, with the
observation that "this would also probably be a global fix for all attacks on
all characters, and not strictly just Cell. Cell is just our clearest working
example to observe." That reframing is what solved it. The previous attempt hunted
for a Cell-specific cinematic animator and never found one, because there isn't
one: there is a single camera update that every camera in the game goes through,
and it is wrong twice.

### First, the harness was lying

`movieshot.py` and `stomptest.py` both did **loadstate -> apply preset ->
loadstate again**, the second load commented "so the patch is live from frame
one". `README` states the opposite rule and states it for a reason. Save state 4
- the Cell state - was captured while patched, so the second load wrote
`[60FPS - battle]` straight back:

    slot 4 off  load -> apply          30.0 ticks/s   0012BCE4 = 24040002
    slot 4 off  load -> apply -> LOAD  60.0 ticks/s   0012BCE4 = 24040001

The "30fps" arm of every contact sheet ever taken of Perfect Barrier was running
at 60fps. Slot 9 was captured *unpatched* and is immune, which is why the Lightning
Attack measured on it is unaffected, and the deterministic memory trace was written
separately and was always correct - the 2026-09-08 rotation table reproduces to
the decimal. Fixed in both tools.

**Check the tick rate of the unpatched arm inside the harness that will do the
measuring, not in a separate script that happens to get it right.**

### The camera, actually

`FUN_001C69C8` updates every camera object in the game, once per tick per
fighter. It builds a target for this tick and then lerps the camera's euler
angles - `fighter+0x420`, wrapped into +-pi and copied to `fighter+0x430`, which
is what `FUN_00207DD0` hands to the view matrix - toward it:

    cur += wrap(target - cur) * $f20

Both halves are per-tick and neither was compensated.

**The chase.** `$f20` is the blend rate. Broken at `001C6C20` in both arms it
reads exactly `0.20000`, tick after tick - so at 60fps it is applied twice as
often and the camera converges in half the real time, then sits still. It is
also reused further down at `001C6CD4` for the look direction, so one halving
fixes both. The rate is *pinned* during a cinematic, which is why the withdrawn
`[60FPS - camera follow]` group - which halved the per-tick **ramp** of that rate
at `$gp-0x7208` - correctly had no effect at all. It was compensating a ramp that
never runs here.

**The target.** A scripted camera move counts `fighter+0x558` down once a tick
from a length in `fighter+0x55C`, and `FUN_001c4f68` builds the target from
`1.0 - remaining/total`. The length is authored in 30Hz frames:

    off   +0x558  8 6 4 2 0 ...      16 vsyncs, 0.27s
    full  +0x558  8 4 0 ...           8 vsyncs, 0.13s

9 frames for Perfect Barrier, 30 for the camera move before it. One site advances
it, `001C5714`-`001C5728`, and it is the same site for every scripted camera move
in the game.

The proof that the target and not the chase carries the shape: broken at
`001C6C20`, the target vector is **identical tick for tick between the arms** -
`[-42.63 -19.11 -50.94] [-42.55 -17.58 -41.54] [-39.60 -16.22 -33.16]` at 30fps
against `[-42.65 -19.25 -50.95] [-42.58 -17.76 -41.55] [-39.63 -16.43 -33.17]` at
60. A track playing at the same rate per tick, in both arms.

### The oracle, and why one fix was never going to do it

Mean absolute **orientation** error against the 30fps camera - the angle between
the two arms' forward vectors at the same vsync, which is the honest measure;
"degrees rotated from each arm's own start" hides a divergence that is already
present at vsync 0.

    arm                      shot 1     whole cinematic
    unpatched 60fps           22.96                9.62
    halve the blend only      12.84                5.87
    gate the move only        14.01                6.32
    both                       1.52                1.57

Neither half is a fix on its own, and either one alone looks like a
disappointment. Peak error goes 89.3 -> 4.2 degrees. The orbit stops moving at
vsync 66 where the 30fps orbit stops at 70, against 34 unpatched.

**It is global, and this was measured, not assumed.** Goku's ultimate from save
state 8 needs no input whatsoever - the whole window is frame-advance from a load,
so nothing can bias it - and the mean error goes 5.00 -> 1.93 with the peak
14.6 -> 0.7.

In play, photographed at 0.12s on the wall clock with the VM free: the fixed arm
matches the 30fps arm tile for tile through the orbit - behind and above at
mid-crouch, then the low front angle fully crouched - where unpatched 60fps is a
whole beat ahead at tile 3 and already firing at tile 4. That is the reported
symptom and it is gone.

### No regression

    arm             charge   melee  ultimate   Lightning Attack
    off (30fps)        168    None       191   CONNECTED 1.22s
    nocamera (v13)      99    None       161   CONNECTED 1.09s
    full (v14)          99    None       161   CONNECTED 1.11s

`melee` returns None in every arm including 30fps - a pre-existing limitation of
that oracle on that save state, not something this touched. The **ordinary**
battle camera, holding a direction for 120 vsyncs, improves from 3.71 to 2.88
degrees mean error; halving a global blend rate could have made it sluggish and
it does not.

### What this closes and what it does not

The `KNOWN NOT FIXED` header entry for the camera is removed. The ultimate's beam
still lands ~0.5s early - and note that it moves a camera *cut* with it, which is
the residual bump at vsync 132 in the Goku trace above. That is the beam defect
showing through the camera, not the camera.

## 2026-09-08 - the mouth, and the second clip player nobody had looked at

The user's report: "Mouth movements are NOT aligned. They always stop too early.
Load into a training battle with Vegeta (SScouter) and keep performing his Final
Galick Cannon (l2, up, triangle) ... in the 30fps version his mouth animates the
whole sequence. It cuts halfway in the 60fps patch."

Fixed. `[60FPS - mouth clock]`, two words plus two trampolines.

### The instrument that made it tractable

Every previous attempt at this failed on the oracle, not the search. Screenshots
were being taken on the wall clock, because the README says a screenshot needs a
running VM - which is true. What nobody had tried is that **a screenshot issued
while paused is queued, and `frame_advance(1)` flushes it**. Verified three times
in a row: `exists=False` after the request, `exists=True` after one advance.

That turns the picture into a per-vsync signal as deterministic as memory. The
film charges on the wall clock, presses the command, pauses, frame-advances to
the exact first vsync of state 287, and from there does screenshot,
`frame_advance(1)`, screenshot - so each sample costs exactly one vsync in both
arms and the two films are aligned frame for frame.

With the mouth box at x 0.486-0.522, y 0.538-0.574 and "open" defined as more
than 12% of the box darker than its own 75th percentile minus 45:

| arm | open/close transitions | first | last | span | rate |
|---|---|---|---|---|---|
| 30fps unpatched | 10 | v43 | v163 | 120 vsyncs = 2.00s | **5.00 /s** |
| 60fps, 19 groups | 12 | v43 | v115 | 72 vsyncs = 1.20s | **10.00 /s** |
| 60fps + this group | 14 | v43 | v167 | 124 vsyncs = 2.07s | - |

**Exactly 2.00x.** That single number is the whole diagnosis: a track advanced
once per tick, authored in 30Hz frames, that runs off the end of its data and
holds. Not a camera problem, not a sequence problem - the cinematic itself is
already the right length in both arms.

The earlier metrics all failed for the same reason: they averaged. Whole-frame
difference, mean luma, mean abs change in a box - the mouth is about 0.1% of the
frame, so every one of them measured the aura and the banner instead. Counting
*state transitions of a thresholded box* is what separated the arms.

### What the mouth actually is

Not skeletal animation. `[60FPS - animation clock]` already paces the
`model+0xB40` controller correctly and its three `time += rate` sites really are
the only ones on that controller. This is a **second clip player in the same
module**, keyed on a different struct, and it had never been looked at. The
2026-09-07 note "the clip-player cluster is the first place to look for mouth
animation" was pointing at the right module and was never followed up.

A track object:

| field | meaning |
|---|---|
| `+0x18` | track type - dispatched through the 15-entry jump table at `002F27B0` |
| `+0x1C` | key index written by the type-3 case |
| `+0x28` | keyframe array; key times are plain `lhu` shorts |
| `+0x2C` | **rate, advanced per tick. It is 2.0** |
| `+0x30` | clip length |
| `+0x34` | clip time, stepped at `0024ED2C` |
| `+0x40` / `+0x42` | current key index / key count, `sh` at `0024F334` |
| `+0x44` | track time, stepped at `0024F3D4` |

Two step sites, both `time += [track+0x2C]` once per tick, both at rate 2.0 - the
usual BT3 60Hz authoring. At 60fps a track burns 120 keyframe units a second
instead of 60, walks off the end of its key array in half the real time, and
holds the last key. A mouth that stops mid-sentence.

Only **two track objects exist**: `009212F0` and `00921360`. Vegeta's cut-in uses
`00921360`; Goku's ultimate uses both. `009212F0` is the "cycling countdown still
running at 2x" that 2026-09-07 flagged and could not explain - it is a track of
this same player, and it is now explained and fixed.

### Hook the add, not the rate load

`0024F290` branches straight to `0024F3D0`, past any hook placed on the
`lwc1 $f0, 0x2c($s0)`, and that path would keep the full rate. Hooking the `add.s`
itself catches every path into it. The cost is that each trampoline has to repair
what the hook's delay slot did with stale data: at `0024ED2C` the delay slot is
the `c.le.s` compare, which saw the un-added time, so the trampoline redoes it;
at `0024F3D4` the delay slot is `swc1 $f0, 0x44($s0)`, which stores the raw rate,
so the trampoline stores again. Nothing reads `+0x44` in between - the next
instruction is `ld $s0, ($sp)`.

### Blast radius, measured rather than argued

- Neither site fires **at all** in ordinary battle: a breakpoint on `0024ED2C`
  with a 6-second wait, sixty times over, never hit. Nothing outside a scripted
  cut-in is touched.
- `tools/hitclock.py --baselines` with the group on is **byte-identical** to
  without: 6 hits, 8940 damage, first 32, last 64, span 32.
- On Goku's ultimate the group does change the picture, on 90 of 170 vsyncs. That
  is the second track, `009212F0`, driving the radial speed-line effect, which was
  running at 2x for the same reason. The hit counters land on identical vsyncs in
  both 60fps arms, so the schedule is untouched; only the effect's own phase moved.
  Not independently verified as an improvement, but it is the same correction for
  the same cause.
- On the Vegeta cut-in the whole-frame difference from the 30fps reference is
  unchanged to three significant figures - 3.46 against 3.46 - so nothing else in
  that shot moved.

### The hour this cost, so it does not happen again

`config.game_ini()` points at the user's installed PCSX2 under EmuDeck.
**PCSXROO does not read that file.** It is a separate portable build and keeps
its per-game settings in `<pcsxroo>/bin/gamesettings/SLUS-21678_428113C2.ini` -
at the data root, not under `inis/`. That file's `[Cheats] Enable` list is read
at **boot**, and it is what carries the `60FPS - spare 1/2/3` names that
`ENABLED_IN_INI` mirrors.

A group whose name is missing there applies nothing and says nothing. Worse,
`patchctl --status` reported it `ON`, because ON there only ever meant "in
ENABLED_IN_INI" - so the pnach was right, the words were right, patchctl said ON,
and the A/B scored the unpatched game twice in a row. `deploy.py` wrote the name
into the EmuDeck ini, which the running emulator never reads.

One self-inflicted error inside that: after injecting the same sixteen words into
an already-enabled group as a bisect, the words stayed in RAM, and reading them
back looked like the group had started working. It had not. **Words in RAM after
a `patch_reload` are only evidence if nothing else wrote them.**

`patchctl --status` now names any group the emulator will ignore and says to add
the line and restart. It writes nothing - that ini is the user's.

## 2026-09-08 - confirmed in play: the camera and the mouth

The user, on their own hardware: "the fix you tried on cell worked. the mouth
movement fix worked."

That closes two defects that had been open since the first report against the
17-group patch, and it clears the star v14 was carrying. Both were fixed against
the frame-advance oracle first and then held up in play, which is the order this
project has settled on - but note that the oracle has been wrong before, and the
only reason to trust these now is that they were played.

What it does **not** clear:

- **v12's input-timing flag** still stands. Nothing since v12 has tested it.
- **The Galick Cannon fade.** Defect 7 of the 2026-09-07 list had two halves:
  the mouth finishing early, and the fade to white ending early and revealing the
  animation still running behind it. Only the mouth half is fixed. The fade is a
  scripted-sequence beat and is still in the "predicted, not measured" row.
- **The pre-fight intro mouths**, which do not move at all rather than stopping
  early. Different symptom, never A/B'd, and it is still unknown whether the
  intro even uses the same clip player.
- **v13's Lightning Attack** has still not been play-tested.

The v15 half that remains unverified is the *second* track object, `009212F0`,
which drives the radial speed-line effect in Goku's ultimate. It changed on 90 of
170 vsyncs and the hit schedule did not move, so it is the same correction for
the same cause - but nobody has looked at whether that shot reads better.

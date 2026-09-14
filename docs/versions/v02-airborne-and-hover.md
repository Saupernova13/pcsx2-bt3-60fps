# v02 - airborne motion and the hovering idle

| | |
|---|---|
| Tag | `v02-airborne-and-hover` |
| Date | 2026-09-05 |
| Built on | [v01](v01-60fps-input-fixed.md) |
| Groups | 13 (155 patch lines) |
| Confidence | The first release published as the latest stable patch; the ki aura and the hovering idle confirmed in play |

## What it changed over v01

Replaced `animation rate` with `animation clock`, and added nine groups.

| group | what it does |
|---|---|
| `60FPS - animation clock` | halves where animation time advances instead of the rate that is written: the step sites in `FUN_0024D410` (with two getter hooks, so the call sites that read the rate still see the old halved value) and the entity steppers `FUN_001C47A4` (play once) and `FUN_001C4920` (looping), which add rate to time at `controller+0x138` - where gameplay animation actually advances. Enabling it together with `animation rate` gives quarter speed |
| `60FPS - effect rotation` | halves four rotation-phase rates read by `FUN_00251A48` - 0.10, 0.23 and 0.27 per effect slot and 0.90 for the parent branch. They are plain data words, each read by exactly one instruction, so no trampoline is needed |
| `60FPS - aura update rate` | the ki aura: its node's `vtable[0]`, `FUN_00164860`, runs the full update on even frames and jumps straight to the draw tail at `00164A9C` on odd frames |
| `60FPS - particle update rate` | aura and trail particles: ORs frame parity into the skip-update flag test at `00168104` inside `FUN_00168084`, so the particles advance at 30Hz and are still drawn at 60 |
| `60FPS - tween duration` | `FUN_00267AC8` converts every tween's duration from seconds with a hard-coded 30.0; one word makes it 60.0, doubling the frame count and halving the step together |
| `60FPS - hover bob` | the hovering idle's bob phase increment, pi/30 at `gp-0x6DF0` and read once in `FUN_001DFD88`, halved to pi/60 |
| `60FPS - airborne motion` | `FUN_001DE000`: halves both the approach step (through `FUN_001DBFF8`) and the applied displacement |
| `60FPS - airborne vertical` | `FUN_001DED78`: the same two halvings for vertical speed |
| `60FPS - airborne residual` | `FUN_001DFD88`: halves the post-hit slide's displacement and the epsilon that decays it |
| `60FPS - gravity` | `FUN_001DED28`: halves g (0.462963 a tick) in data and its application by trampoline, leaving the terminal velocity in its 30Hz units |

## What was discovered

- **The engine has no timestep.** `0012BCE4` is not a stride but the delay slot of
  `jal 0x102060`, the end-of-frame present, and its argument is a vblank count. The
  battle loop is a flat list of subsystem calls with no delta between them, so every
  per-tick quantity runs at 2x until it is halved by hand. (This window also claimed
  the data segment holds no 1/30 or 1/60; v10 corrected that.)
- **The ki aura, the oldest open symptom.** `vtable[0]` is update and draw in one
  call, so gating the call deletes a frame of the effect instead of slowing it - and
  drops its collision, which is why a range probe made beams stop dealing damage. It
  was found by measurement after nine failed narrowings: a guarded 0-ki versus max-ki
  activity diff isolated 529 words, 481 of them in one region, and a pointer-ownership
  scan named the node that owns them. Along the way `effect rotation` was declared the
  wrong fix and reverted, then reinstated on 2026-09-05 when a rate scan showed it was
  a real and separate 2x.
- **Airborne 2x is step size, not step count.** Ground movement is root motion through
  the skeleton, and the animation clock already halves it. Airborne movement never
  touches the skeleton: over a launched opponent the root bone delta is exactly 0.0000
  every tick while the fighter still moves 6.4815 units a tick, identically at both
  rates. A deliberate experiment that halved all root motion changed ground speed and
  left the air untouched, which is what proved the channels are separate.
- **Both halves of an approach must be halved.** Halving only the applied displacement
  gives the right speed but lets the ramp and the decay run at double rate, so a
  knockback ends in half the time; halving only the step leaves the fighter at 2x. The
  stored speed stays in its 30Hz units, because other code reads it.
- **Free fall is a fourth channel.** A breakpoint in `FUN_001DED78` never fires during a
  descent; a write watchpoint on `fighter+0xAC` named `FUN_001DED28` instead.
- **The tween system** was found by sweeping RAM for words that reverse direction twice
  as often, rather than words that step twice as far - an airborne-idle triangle wave
  with a 12-vsync period at 30fps and 6 at 60.
- **The particle system** was located by freezing the clock and seeing what was still
  moving. Halving constants reaches only the channels that are constants, so the update
  is gated instead - safe here, because this update only advances state.
- **The hover bob is not the animation.** It is a phase fed to a sine and stored as the
  fighter's anchor Y; world position never moves, so position traces looked perfectly
  still, and scans taken in the crouched flight pose never saw it bob at all. A
  2026-08-22 measurement had concluded the bob was correct - it had measured the body
  animation, not the bob.
- **PCSXROO**, a scriptable PCSX2 fork with a debug server, was built in this window,
  and the 30fps oracle was mechanised on it: the same save state run unpatched as the
  reference for every measurement since.

## Evidence

- Airborne, against the 30fps game over the same vsyncs: sustained flight 2.470x ->
  1.049x, boosted dash 1.684x -> 1.009x, launched opponent 1.414x -> 0.954x, melee rush
  0.621x -> 1.033x. The per-tick airborne step is now 3.2407, exactly half of 6.4815,
  and sustained backward flight reaches exactly 125.000 units a second at both rates.
- Gravity: per-tick acceleration 0.4630 -> 0.2315, and the height change per tick is
  exactly 0.500 of `vy`.
- Hit slide: 0.9259 -> 0.6173 -> 0.3086 -> 0, the same slide over the same real time.
- Tween: a ping-pong period of 12 vsyncs at 30fps, 6 unpatched, 12 with the group.
- Particles: lifetime, alpha ramp and phase counter back on the 30fps period; the
  effect region's 2x oscillators fall from 107 to 70.
- Hover bob: 2 reversals per 150 vsyncs at 30fps, 5 without the group, 2 with it,
  amplitude unchanged at 4.0000.
- No regression throughout: dash 0.988, launched-opponent coast 0.985.
- The aura, in the user's words: "finally, the aura is at normal speed, no flicker."

## Still open after this build

Circling an opponent cruises at about 0.80 of its 30fps speed - narrowed to a target
value rather than the step, and treated as a refinement rather than a defect.

## Get this version

    git show v02-airborne-and-hover:releases/v2-airborne-and-hover/428113C2.pnach > 428113C2.pnach

# Effects, the ki aura and particles

The effect-node system, the aura, effect rotation and the particle system.

## Effects at 2x - what has been ruled out (2026-08-22)

Still wrong after the input fix: ki aura, air idle, ki blast and beam travel, beam
duration, impact animations. Character skeletal animation, ground idle, grabs, rush
blasts and general fighting are all correct.

Three experiments, all reverted, none of which changed anything:

1. **`0024D030`** - the only other writer of `+0xC80` in the binary, a two-instruction
   leaf `jr $ra / swc1 $f12, 0xc80($a0)`. Replaced the whole function with a halving
   trampoline. User: "I don't think anything changed... if anything the speed is less
   consistent in movement now." Reverted. It is vtable-dispatched with zero direct
   callers, so there was no way to predict what it drives - this was a guess and it lost.
2. **`001C44E4` (`+0xC8C`) and `001C4594` (`+0xCB8`)** - the animation module has exactly
   three float setters and only `+0xC80` was hooked. The other two are structurally
   identical (same prologue, same `jal 0x1dc280`, same `swc1 $f20`). Hooked both.
   User: "no change at all." Reverted.
3. **Object pools.** Scanning for the `lw rA, off($gp); jr $ra; lw $v0, 0(rA)` count
   accessor that identified the fighter pool finds only three in the whole binary:
   `002FEB14` (fighters, count 2), `002FEB38` (count 3, but `+4` holds a *code* address
   so the layout differs - and its only user computes `count == 3`), and `002FF160`
   (null during battle). **There is no effect entity pool reachable this way.**

Also already ruled out, from earlier sessions: calls 19/20 of the battle loop are the
3D scene renderer, not simulation; call 8 is a one-shot, not a timestep.

### Where the evidence actually points

From the saved capture `work/captures/grabs.npz`, fields advancing **+2 per frame** -
the signature of a counter authored for 30Hz - are `fighter+0x964`/`+0x968`
(range 0..197), `+0x910`/`+0x914` (0..7) and `+0x132C` (0..29). `+0x968` is the best
candidate for an effect or sub-animation frame index: it is still stepping 2 per frame
after the animation fix, which is exactly the reported symptom.

Confirming it needs a live watch while the aura is active. Finding its *writer* is the
hard part - PINE has no write breakpoints, and offset-scanning `.text` is unreliable
because struct offsets are not unique (`0x1470` resolved to an unrelated global holding
`0x80808080`).

**Note the split:** aura and sprite animation are cosmetic, but blast *travel* speed is
position integrated per frame and changes dodge timing, so it is a gameplay issue and
the higher priority of the two.

## The effect system, and the aura at 2x (2026-08-22)

Found by measurement, not static analysis, after four static attempts failed.

### How it was found - the method that worked

1. **A live 30/60 fps toggle.** `FUN_00264D98` copies its vblank-count argument
   into `$s1` at **`00264DA4`**, and that address is not a pnach line, so a
   single PINE write pins the frame rate from outside the patch:
   `24110002` = 30fps, `24110001` = 60fps, `0080882D` = stock. Verified
   60.0 -> 30.0 -> 60.0.
   **Caveat that cost a cycle:** our fixes halve per *tick*, so they apply at
   30fps too. A fixed field and a broken field therefore both show the same
   movement per frame at both rates. The ratio in `tools/ratecheck.py` cannot
   separate them without an unpatched reference. It is still useful for
   "is this field time-driven at all".
2. **A RAM-wide sweep for per-frame state** (`tools/findmotion.py`): read every
   chunk twice back to back, keep the words that differ, then re-sample just
   those at frame precision. 28 MB in about 6 seconds. Effects are not in the
   model table - **only two models exist, the two fighters** - so this is the
   only way to find them.
3. **A write breakpoint on the address the sweep produced.** One shot, again.

### What the aura is

Nine slots of 0x40 bytes at **`model + 0x1010`**, each carrying three rotation
phases at slot `+0x28`, `+0x2C`, `+0x30`. They ramp and wrap at +/-pi:

```
frame N     +28 -1.92840   +2C  3.10462   +30 -0.17988
frame N+1   +28 -1.82840   +2C -2.94857   +30  0.09012     <- 2C wrapped
per-frame delta (0.10, 0.23, 0.27) on 109 of 111 frames, wrap = -6.28319 = -2pi
```

`FUN_00251A48` updates them; `FUN_00251A10` is the +/-pi normaliser. The rates
and the normaliser bounds are `$gp` constants, and **each is read by exactly one
instruction in the whole binary**, so halving them carries no collateral risk:

| address | gp offset | value | read by | meaning |
|---|---|---|---|---|
| `002FE708` | `-0x5b68` | -3.1415925 | `00251A10` | normalise lower bound |
| `002FE70C` | `-0x5b64` | +6.2831850 | `00251A20` | normalise add 2pi |
| `002FE710` | `-0x5b60` | +3.1415925 | `00251A28` | normalise upper bound |
| `002FE714` | `-0x5b5c` | +6.2831850 | `00251A38` | normalise subtract 2pi |
| **`002FE72C`** | `-0x5b44` | **+0.10** | `00251E5C` | phase rate, slot `+0x28` |
| **`002FE730`** | `-0x5b40` | **+0.23** | `00251E74` | phase rate, slot `+0x2C` |
| **`002FE734`** | `-0x5b3c` | **+0.27** | `00251E90` | phase rate, slot `+0x30` |
| **`002FE738`** | `-0x5b38` | **+0.90** | `00251EB0` | phase rate, inherited-parent branch |

These are data, not code, so they can be halved with plain pnach word writes -
no trampoline. Halving a positive normal float is exactly one decrement of the
exponent field, i.e. subtract `0x00800000` from the bit pattern.

**Neither the rates nor 2pi appear anywhere in the ELF as literals** - they are
`.data`/`.bss` words, which is why four static searches for them found nothing.
That is the lesson: a constant that is not an immediate and not in the ELF
image is still findable, but only from the running game.

### Things this rules out, and what is still open

The hover bob is **not** a defect. It is the air-idle animation's root motion:
autocorrelation of `fighter+0x15A4` peaks at lag 107 frames against a 108-frame
animation, with the clock stepping exactly 1.0/frame. Correct at 60fps. What
looks wrong while hovering is the aura drawn on top of it.

Still open: ki blast and beam travel, beam duration, knockback and fall speed.
Those are motion, not rotation phases, and `FUN_00251A48` is the effect
updater - the same sweep run while a beam is in flight is the way in.

## The ki aura at 2x - five eliminations, and the oracle that makes them trustworthy (2026-08-24)

The user's long-standing report: **"the ki aura around the characters plays at double
speed."** Earlier sessions repeatedly answered this with `[60FPS - effect rotation]` and
treated it as fixed. It was never confirmed by the user, and it is now proven **not** to be
the defect. This section records what was established and - more importantly - everything
definitively ruled out, so nobody re-walks these paths.

### The symptom, stated precisely

Established with the user, not assumed:

- The aura is the character's ki aura - the flame streaks radiating off the body.
- It is present in **both** base and Super Saiyan form; SSJ's is gold, base is blue-white.
- **Intensity scales with ki, and at 0 ki there is no aura at all.** That is the only clean
  on/off control that exists, and it is the one measurement this session never managed to
  take uncontaminated.
- Skeletal animation, grounded movement, grabs and combos all look correct. Only the aura.

### The 30fps oracle - the most useful single test in this project

The rate pin at `00264DA4` (from `tools/ratecheck.py`) is far more than a ratio tool.
Pinning the game to 30fps produces a **falsifiable prediction**, because our fixes halve
per tick unconditionally:

| at 30fps | quantity |
|---|---|
| runs at HALF speed | anything we have halved (animation clock, input counters) |
| runs at CORRECT speed | anything uncompensated |

Predicted before looking: *Goku's body animates in slow motion while the aura looks
normal.* The user confirmed exactly that.

**Therefore the aura is a plain per-tick quantity that nothing in the patch halves.** This
is the firmest fact in the investigation, it cost one write, and it should be the first
test applied to any future "X is at 2x" report.

    30fps: p.write(0x00264DA4, 0x24110002)
    60fps: p.write(0x00264DA4, 0x24110001)
    stock: p.write(0x00264DA4, 0x0080882D)

### Eliminated by direct visual test - not by inference

Every row below was confirmed by the user looking at the screen. This is the important part
of this session: inference has a poor record in this codebase, and each of these was a
plausible theory that turned out wrong.

| candidate | how it was tested | result |
|---|---|---|
| `model+0x1010` rotation phases - what `[60FPS - effect rotation]` patches | nopped all 10 phase stores in `FUN_00251A48`; verified 18 phase values across 3 slots moved **0.00000** over 150 frames | **no visible change at all** |
| the dormant 60fps effect mode (`model+0xA40` bit 24) | nopped the two gating branches so both effect updaters always take the 60fps path | no visible change |
| `FUN_00166E28` aura-adjacent particle system | halved BOTH the `life -= 1.0` per-tick decrement AND the per-tick motion step | no visible change |
| `FUN_00250DE8`, the sibling effect updater | writes the identical `+0x28..+0x3C` offsets as `FUN_00251A48`, already disproven above | ruled out by construction |
| the **entire scene-graph render tree** (`FUN_001AD150`) | gated the whole walk to even frames only | environment, explosions, Kamehameha and the special-attack camera all flickered - **aura unchanged, still 2x** |

That last one is the most valuable negative result here. It rules out a very large branch
in one test, and it establishes that `FUN_001AD150` is the **render submission** tree:
skipping it for one frame drops those draws entirely rather than slowing them.

### `[60FPS - effect rotation]` is wrong - revert it

Two independent reasons:

1. **It fixes something invisible.** Freezing those phases outright produced no visible
   change whatsoever. Whatever `model+0x1010`'s six phases drive, the player cannot see it,
   so halving their rates cannot have fixed a visible symptom.
2. **It is incomplete even on its own terms.** `FUN_00251A48` advances *two* rotation
   triples. The patch halves the four `$gp` constants behind the first
   (`002FE72C`/`730`/`734`/`738`); the second triple at slot `+0x34/+0x38/+0x3C` is driven
   by `002FE73C`-`002FE754` (0.30, 0.90, 0.10, 0.70, 1.30, 1.5708, 0.10) and was never
   touched.

The group was deployed 2026-08-22 20:42 and the session moved straight on to beams without
ever asking the user. The `STATE OF PLAY` table listing four confirmed groups was right;
the fifth was never confirmed.

Verified live that the group really is in force, so this is not a deployment failure: the
phases step at exactly `+0.05 / +0.115 / +0.135` per frame - the halved values - at a
measured 60Hz.

### The engine DOES have a framerate flag - this file was wrong about that

"There is no master framerate variable" is false for the effect system. Both big effect
updaters open with:

    00251A4C  lui  $v1, 0x100            ; mask 0x01000000
    00251AB8  lw   $v0, 0xa40($s5)       ; model flags
    00251AC8  and  $v0, $v0, $v1
    00251ACC  lui  $at, 0x41f0           ; 30.0   default
    00251AD8  beqz $v0, 0x251AF8
    00251AE0  lui  $at, 0x4270           ; 60.0   flag set
    00251AE8  lui  $at, 0x4000           ; 2.0
    00251AF0  lui  $at, 0x3f00           ; 0.5    <- halves its own per-tick deltas

| constants | function | gating branch |
|---|---|---|
| `00251ACC` / `00251AE0` | `FUN_00251A48` | `beqz` at `00251AD8` |
| `00250E6C` / `00250E7C` | `FUN_00250DE8` | `beqz` at `00250E74` |

`model+0xA40` reads `0x10020016` / `0x1001001E` - **bit 24 clear** - both in the battle
save state and live in a real fight. The path is dormant. Enabling it changed nothing
visible, so it is not the aura lever, but it is real: if it is ever enabled, the four
halved rotation constants must be restored to stock or they run at quarter speed.

Binary-wide there are exactly **six** places pairing a 30.0 with a 60.0 constant:
`001E5EA0`, `001E5F24`, `001F2FEC`, `001F307C`, `00250E6C`, `00251ACC`. The first four are
unconditional `rate * 30.0 / 60.0` conversions, not switches.

### The scene graph, mapped

Worth keeping - it dispatches most of the game's per-frame work, and it is invisible to
static xref because every update is an indirect call.

    ptr  = *(u32*)0x002FE9A0        // gp-0x58D0
    root = *(u32*)ptr
    FUN_001AD150(root)              // called from 0012CB84

| field | meaning |
|---|---|
| `node+0x00` | flags byte; bit 0 = leaf, handled by `FUN_001ADA80` |
| `node+0x04` | first child (the walker reads `param+4`) |
| `node+0x24` | **child list pointer** - recursion passes this, not the node itself |
| `node+0x28` | vtable; `vtable[0]` is the per-frame update |
| `node+0x30` | next sibling |

The dispatch is `jalr $v1` at `001AD188`, and `gp-0x5780` (`0x002FEAF0`) holds the node
currently being updated. Typically **73-75 nodes, 55-58 distinct update functions** in a
fight.

**`FUN_0012D9A0` is a bare `jr ra`.** Pointing a vtable's slot 0 at it disables that node
type without modifying any code - a clean, reversible way to bisect by data. It is still
destabilising in bulk (see the method notes).

### The aura-adjacent particle system - mapped, but NOT the aura

Reached by activity diff, then node ownership by pointer, giving update fn `FUN_00168088`:

    node with vtable[0] == 00168088    // the owner
    data = *(u32*)(node + 0x38)        // the particle object

Two particle arrays, both confirmed against measured strides:

| array | slots | stride | element check |
|---|---|---|---|
| A | 10 | `0x90` (`iVar5*0x24` words) | `data[iVar5*0x24 + 7]` |
| B | 20 | `0x70` (`iVar5*0x1c` words) | `data[iVar5*0x1c + 0x16c]` |

`FUN_00166E28` updates array A. Per-particle fields:

| offset | meaning |
|---|---|
| `+0x14` / `+0x18` | integer progress and its limit |
| `+0x1C` | flags; bit 0 alive, bit 1 finished, bit 2 dead |
| `+0x2C` | **lifetime, `-= 1.0` per tick** (`lui $at,0x3f80` at `00166F98`, store at `00166FB0`) |
| `+0x30` | **per-tick motion step** (loaded at `00166EA4`) |
| `+0x40/44/48` | position, integrated `pos += vel * step` with no delta-time |

Both are genuinely uncompensated per-tick quantities, and halving both produced **no visible
change**, so this system is not what the player sees. Do not spend time here again without
first proving it is on screen.

`00166FB0` sits in the delay slot of a `bc1f`, so it must not be displaced by a hook. The
clean lever is the constant at `00166F98` (`3C013F80` -> `3C013F00`).

### New bug found in passing - a HUD animation at 2x

`0x01877F18` steps **exactly +/-2.0 per frame** through a 30-frame range, and is the *only*
value in all of EE RAM with that signature. Bisected to:

    0012BBD0 -> 0012B7F8 -> 002129C8 -> FUN_00219710

`FUN_00219710` dispatches the HUD/UI draw calls (`FUN_00218848`, `FUN_002188B8`), so this is
a 30-frame HUD animation running at double speed - real, minor, unrelated to the aura. Also
note **`0012B7F8` is not purely the "3D scene renderer"** as recorded earlier; it contains
the HUD as well.

### INSTRUMENT BUG - the RAM sweep was mostly blind

This invalidates an unknown amount of earlier scanning work, including anything that used
`tools/findmotion.py`.

The sweep reads each chunk **twice back-to-back** and keeps words that differ. Those two
reads take microseconds; a frame is 16.7 ms. So both reads almost always land inside the
same frame and nothing appears to have changed - unless a frame boundary happens to fall
between them, in which case everything does. Measured across successive passes at one
moment: 7573, 1001, 169, 38571 words "changing". Set intersections across passes came out
empty every time, which is what exposed it.

**Fix: gate the second read on the frame counter.**

    a = pine.read_block(base, n)
    f = pine.read(FRAME_COUNTER)
    while pine.read(FRAME_COUNTER) == f:
        pass
    b = pine.read_block(base, n)

Same sweep, same moment: **169 -> 16,539** words correctly identified as changing every
frame. `tools/findmotion.py` still carries the old design and should be fixed before it is
trusted again.

### Two bugs fixed in tools/bisect.py

Both produce confident false positives, and one fabricated a 22-entry result table during
this session.

1. **No resume check.** If the watched value stopped for any reason other than the nop - the
   effect ended, the slot was recycled, the game died - the first affected test was reported
   as a hit and *every subsequent test inherited it*. `descend` now re-measures after
   restoring and refuses to call it a hit unless the value resumes.
2. **`all(result)` instead of a baseline comparison.** An address already still at baseline
   made `not all(result)` true on every test, so the **first call site tested always won**.
   `descend` now takes the baseline and only lets addresses that were actually moving
   testify. (`main()` already guarded this with an `all(base)` check; calling `descend`
   directly bypassed it - which is exactly how the bogus table was produced.)

### Static asset - every in-place float accumulate in the binary

This file previously claimed "three `time += rate` sites exist in the whole binary and there
are no others". That was already wrong once - commit `dadda4f` added two more. An exhaustive
scan for the `lwc1 fT,off(rB) ... add/sub.s fT ... swc1 fT,off(rB)` idiom finds:

| count | what |
|---|---|
| **620** | in-place float accumulates in `.text` |
| 166 | of those whose operand is a literal 1.0 |
| 74 | of those that **subtract** 1.0 - the per-tick countdown shape |

None of the 74 sits inside a live scene-node update function; they are all in callees.

### Leads from the previous session that were never written down

Recorded here because they existed only in commit messages (`93e5900`, `ad436c5`):

- `01B1F038` - effect clock, +2.0/frame, loop of 138, owned by `FUN_0012B6E0`. Unresolved.
- `01A301C0` - position vec4 with a unit direction, owned by `FUN_001BB620`. Unresolved.
- **PCSX2 write breakpoints do not trip on the effect clocks.** A Write breakpoint on
  `01B1F038` never fired even though the value ticks every frame, so those writes are not
  plain cached EE stores. This is why `bisect.py` exists - do not burn time setting
  breakpoints on this class of value.
- Nopping a display-list subsystem for even a fraction of a second aborts the emulator with
  `FQC = 0 on VIF FIFO READ`, and restoring the instruction does not undo it.

### Where the aura's memory probably lives

From an activity diff of max-ki against 0-ki - contaminated by a respawn between captures,
so treat as a hint rather than a result. 7277 words were active only with the aura up:

| region | words | reading |
|---|---|---|
| `007E0000` | 4045 | the GIF/DMA display list - the aura being **drawn**. `work/beamscan3.py` already skips this range deliberately |
| `00900000` | 1818 | the most promising unexplored candidate for aura state |
| `007D0000` | 865 | likely more display list |
| `0199xxxx` / `008Cxxxx` | ~280 | the particle system above, now ruled out |

### What to do next

The one measurement that would settle it, and the only one this session failed to get
cleanly: **a 0-ki (no aura) versus max-ki (full aura) activity diff on a single stable
character, standing still for both halves, using the frame-gated sweep.**

Guard it properly this time - capture the fighter manager, fighter bases and model pointers
alongside each half, and **abort if any of them changed between captures**. A death and
respawn silently invalidated the first attempt, and mid-fight character swaps invalidated
several others. Run it against an opponent that cannot fight back.

With the aura's memory isolated, `bisect.py` - now that it no longer lies - names the owning
call, and the fix takes the same shape as every other fix in this patch: halve the per-tick
constant.

### Method notes worth keeping

- **Make a falsifiable prediction, then test it.** The 30fps oracle worked because the
  outcome would have disproven the model if it were wrong. "It looks different" is not
  evidence; "the body goes slow-motion and the aura does not" is.
- **A freeze is a better probe than a fix.** Nopping a store to freeze a value changes no
  control flow and answers "is this the thing I am looking at?" in one round trip. Halving
  answers a much narrower question at the same cost.
- **Never disable many things in sequence without re-baselining.** Swapping ~22 vtable
  entries one after another crashed the emulator and produced a table of 22 identical false
  hits. One change, verify it reverted, re-measure, then the next.
- **Confirm the control actually controls something.** "Detransform so the aura goes away"
  failed because base form has an aura too. The user caught it; the capture would otherwise
  have been silently meaningless.
- **Gating a subsystem to even frames is a strong, cheap probe.** It answers "does this
  subtree drive the symptom?" for a whole branch at once, and the failure mode is
  informative too: things that *flicker* rather than slow down are render submission, not
  simulation.

## BREAKTHROUGH - the aura runs at correct speed when FUN_0012CB60 is gated (2026-08-24)

**User-confirmed: "This is definitely the correct speed, it just has the flicker."**

Gating the call at `0012B700` (`jal 0012CB60`) so it runs on even frames only puts the ki
aura at its correct real-time speed at 60fps. This is the first thing in the entire
investigation that has moved the symptom, after five systems were eliminated.

The remaining defect in that state is a **flicker** - the aura is drawn on even frames and
absent on odd ones - which is a separate, understood problem with an obvious shape (see
below).

### Why gating beat every previous approach

Every fix in this patch so far - and every failed attempt at the aura - went after an
individual clock, constant or field. The aura is not driven that way. It is ticked by a
**generic per-frame pass over the scene tree**, and the thing to halve is the pass, not
any value inside it.

### Three walkers over the same scene tree, three vtable slots

This is the structural fact that explains the whole investigation:

| walker | dispatches | gating it does |
|---|---|---|
| `FUN_001AD150` | `vtable[0x00]` | things **flicker**; no speed changes - this is **render submission** |
| `FUN_001AD200` | `vtable[0x0C]` | no flicker, no speed change |
| `FUN_001AD280` | `vtable[0x10]` | no flicker, no speed change on its own - this is an **animate** pass |

`FUN_0012CB60` calls the render walk directly. Its true body is short and ends in a tail
call:

    0012CB60  addiu $sp, $sp, -0x10
    0012CB64  sd    $ra, ($sp)
    0012CB68  jal   0x0012E040
    0012CB70  jal   0x0012F720
    0012CB78  jal   0x0012D868
    0012CB80  lw    $v0, -0x58d0($gp)
    0012CB84  jal   0x001AD150          ; the render walk - source of the flicker
    0012CB88  lw    $a0, ($v0)          ; delay slot
    0012CB8C  ld    $ra, ($sp)
    0012CB90  j     0x0012EB10          ; TAIL CALL
    0012CB94  addiu $sp, $sp, 0x10      ; delay slot

**The driver is one of `FUN_0012F720`, `FUN_0012D868` or `FUN_0012EB10`.** `FUN_0012E040`
and `FUN_001AD150` were both tested individually and neither changes the aura's speed.

### METHOD TRAP - `call_sites` walks past a tail call

`bisect.call_sites` scans forward until it hits `jr ra`. A function that ends in a **tail
call** (`j target` rather than `jal`) has no `jr ra`, so the scan runs straight on into
whatever function follows and reports its call sites as belonging to the first one.

That is exactly what happened here: gating "`FUN_0012CB60`'s" indices 2, 3 and 4
(`001AD200`, `0012DD08`, `001AD280`) actually gated a *different* function's calls, and the
real contents of `FUN_0012CB60` - `0012F720`, `0012D868`, `0012EB10` - were never tested at
all. Several confident negative results in this session are worth nothing for that reason.

**Check for a terminating tail call before trusting any `call_sites` output.**

### Gating is the right probe for a 60fps patch, and its failure modes are informative

Nopping asks "does this subsystem exist"; gating to even frames asks "does this subsystem
drive the SPEED of what I am looking at", which is the actual question here. Read the
outcome like this:

| what you see when you gate it | what it means |
|---|---|
| it **slows down** | simulation / animation - this subtree drives the timing |
| it **flickers** on and off | render submission - the draw is simply skipped |
| nothing changes | not involved |

`work/gate.py` implements this. It builds a 9-word trampoline per call site
(`lui/lw/andi/bnez/jal target/j resume`), takes `--root`, and restores everything on the
next run from `work/gate-state.json`.

**Confound to control for:** gating a large subtree can slow the *whole game*, in which
case the aura appearing to slow says nothing about its own driver - it is just following a
character whose state now updates at half rate. Gating `FUN_0012B6E0` did exactly this. Ask
the user to judge the aura against an absolute reference, not against the rest of the game.

### The flicker, and the shape of the real fix

The flicker is not a mystery: `FUN_0012CB60` gets skipped entirely on odd frames, and the
render walk `FUN_001AD150` is inside it, so nothing is submitted on those frames.

The fix follows directly - **halve the update, keep the draw**:

- run whatever drives the aura's animation (one of `0012F720` / `0012D868` / `0012EB10`) on
  even frames only
- let `FUN_001AD150` run **every** frame so the aura is drawn at 60fps

That gives 30Hz animation with 60Hz presentation, which is the correct outcome for
30Hz-authored content and is what the guide's run-one-skip-one design is for.

### Reference states for judging aura speed

Keep these three, and A/B/C between them rather than asking "does this look right":

| state | how |
|---|---|
| **A** broken 2x | nothing applied |
| **B** candidate | the gate under test |
| **C** known correct | pin to 30fps: `write(0x00264DA4, 0x24110002)` |

C is the ground truth the user already validated. "Normal speed" is ambiguous phrasing and
cost this session a whole chain of wrong eliminations - ask explicitly whether B matches C
or matches A.

## The aura is advanced TWICE per frame - why every single-call test failed (2026-08-24)

Continuation of the section above. This resolves the contradiction that made the previous
round's results look impossible, and it changes the shape of the fix.

### The contradiction

Three gate states, all user-confirmed against the 30fps reference:

| gated | aura speed | other effects |
|---|---|---|
| all of `FUN_0012CB60` | **correct** | flicker; beam duration restored; model appears duplicated; rush animations flickery; some beams linger slightly long |
| everything in it **except** `FUN_001AD150` | double | no flicker; **beams short, damage broken** - Gohan takes one light hit, no flinch |
| `FUN_001AD150` alone | double | heavy flicker across environment, explosions, Kamehameha, special-attack camera |

The second and third states together cover exactly what the first state covers. Yet only
the first fixes the aura.

### The resolution

**The aura's animation is advanced in two different passes in the same frame.** Halving
only one leaves roughly 1.5x, which reads as "still fast" and not as a clean halving.
Halving both gives exactly 1.0.

This is why nine separate single-call tests all came back negative while the combined gate
worked, and it is the single most important structural fact about this symptom.

### `vtable[0]` is update AND draw in one method

The decisive evidence: gating `FUN_001AD150` for *all* node types (via the range probe
below) did not merely make things flicker - **beams stopped dealing damage entirely**,
characters posed with nothing leaving their hands, the hand shine effect stuck on after the
animation ended, and camera angles broke.

A pure render pass cannot do that. So the `vtable[0]` method each node exposes both
advances its own state and submits its draw. That has two consequences:

- Gating the call can never be the fix. Skipping it does not slow a node down, it **deletes
  a frame of that node's existence** - no draw, no collision, no state advance.
- The fix must go **inside** the aura node's `vtable[0]`, halving only the animation
  advance and leaving the draw untouched.

### The dispatch-range probe - useful, but too destructive at full range

Rather than swapping vtables (which crashed the emulator earlier) or pairing calls off one
at a time, the dispatcher itself can be made selective. Hook `001AD17C`
(`sw $s0, -0x5780($gp)`, whose delay slot loads `$v0` with the vtable pointer), read
`vtable[0]` into `$v1`, and skip the call only when **`$v1` falls inside an address range
held in two safe-zone words** and the frame is odd:

    000F0600  LO          000F0604  HI
    000F0620  sw $s0,-0x5780($gp)   ; replay displaced
    000F0624  lw $v1, 0($v0)        ; vtable[0]
              ... parity check, then LO <= $v1 < HI ...
    000F0668  jalr $v1 / move $a0,$s0
    000F0670  j 0x001AD190

The range is changed by writing two words, so a binary search over node types costs no
reassembly and no vtable writes. It installs and runs cleanly (verified: game still ticking
at 60Hz afterwards).

**But at full range it produces the worst state seen in this project**, for the
update-and-draw reason above. Any future use must start from a narrow range, not a wide
one. Keep a liveness check in the installer - read the frame counter after hooking and
auto-revert if it stalls; that is in the applied script and it is cheap insurance.

### Every gate state tried, and what it proved

Recorded so nobody repeats them:

| gated | result |
|---|---|
| `FUN_001AD150` (render/update walk) | flicker everywhere, aura speed unchanged |
| `FUN_001AD200` (`vtable+0x0C`) | no flicker, no speed change |
| `FUN_001AD280` (`vtable+0x10`, animate) | no flicker, no speed change alone |
| whole scene-graph walk, early attempt | environment/explosions/beams flicker, aura unchanged |
| `FUN_0012B6E0` (whole gameplay update) | whole game slow-motion, aura slowed **with** it - a confound, not evidence |
| first half of `0012B6E0`'s calls | game slowed, aura still 2x |
| second half of `0012B6E0`'s calls | Goku's model flickers, Gohan's does not, aura still 2x |
| `FUN_0012E040` + `0012DD08` | aura still 2x - but contaminated, `0012DD08` is in another function |
| `0012F720` + `0012D868` + `0012EB10` | aura still 2x, no flicker |
| all four non-render calls of `0012CB60` | aura still 2x, **beams short and damage broken** |
| all of `FUN_0012CB60` | **aura correct**, flicker |
| all node updates via the range probe | worst state - beams do no damage, cameras break |

### Next steps, in order

1. **Identify the aura node, read-only.** Re-run the identity-guarded 0-ki -> max-ki
   activity diff (the guarded version worked: 691 words, no display-list contamination).
   Then map those addresses to the scene node that owns them with the pointer-ownership
   scan - the same technique that correctly identified `FUN_00168088` for the particle
   system. That names the node and its `vtable[0]` without redirecting a single instruction.
   **Exclude the HUD.** At max ki the ki gauge is full and animating, so gauge state will
   appear in the diff; the earlier HUD stepper at `0x01877F18` (`FUN_00219710`) is the
   marker for that region.
2. **Confirm the node visually with a narrow range probe** - set `LO`/`HI` to just that one
   update function. Expect the aura alone to flicker and slow, with nothing else affected.
   That is the confirmation that costs one round trip and no breakage.
3. **Find the animation advance inside that function** and halve it, leaving the draw. The
   620-entry in-place float accumulate table is the place to look first, scoped to that
   function's address range.
4. **Find the second advance.** The two-pass finding says there will be another one - most
   likely in the `vtable+0x10` animate method of the same node, dispatched by
   `FUN_001AD280`. Halving one alone will read as "still fast"; both must be halved before
   asking the user to judge.

## MILESTONE - the ki aura is fixed (2026-08-24)

**User-confirmed: "finally, the aura is at normal speed, no flicker."**

Shipped as `[60FPS - aura update rate]`. The oldest open symptom in this project, and the
one previous sessions repeatedly mis-answered with `[60FPS - effect rotation]`.

### The fix

    patch=1,EE,00164888,word,0803C1D0    // FUN_00164860 entry -> trampoline
    // + an 11-word trampoline at 000F0740

`FUN_00164860` is the aura node's `vtable[0]`. It updates first and ends in a **tail call
that draws** - `FUN_00164268`, or `FUN_001ADA58` when `flags & 2` - and both are reached
from `00164A9C`. The hook lets the prologue run (it must: the tail needs `$s2` and `$s6`),
replays the displaced `lw $s2, 0x38($s6)` and its delay slot `addiu $s3, $s2, 0x64`, then:

- **even frame** - jump to `00164890` and run the whole update as normal
- **odd frame** - jump straight to `00164A9C`, skipping every update and going to the draw

Result: the aura advances at its authored 30Hz while still being presented at 60fps.
Measured live, the aura's own frame counter at `data+0x30` drops from 60/sec to 30/sec
while the game stays at 60Hz.

### Why nothing else worked - `vtable[0]` is update AND draw

This is the fact that had defeated every earlier attempt. Gating the *call* can never fix
an effect in this engine, because skipping `vtable[0]` does not slow a node down, it
**deletes a frame of that node's existence**: no state advance, no draw, and - as the
range probe proved - no collision either. Beams stopped doing damage entirely.

The fix has to go *inside* the method, between the update and the draw. That is only
possible because this particular function happens to update first and draw last, with a
single convergence point at `00164A9C`.

### The method that actually found it, after nine failed narrowings

Every static approach failed. What worked, in order:

1. **The 30fps oracle** established the class of defect with a falsifiable prediction:
   pin to 30fps, and if the body goes slow-motion while the symptom looks correct, the
   symptom is an uncompensated per-tick quantity. It held.
2. **A frame-gated activity diff** isolated the aura's memory: 0-ki (no aura) versus
   max-ki (full aura), same character, standing still, with the fighter and model pointers
   captured on both sides and the capture discarded if anything reallocated. That produced
   **529 words, 481 of them in one 64KB region**, with no HUD and almost no display-list
   contamination. The unguarded version of this same diff had been useless.
3. **A pointer-ownership scan** named the owner: walk the scene graph, then find the node
   whose own storage contains those words. One node, unambiguously - `019965C0`, holding
   161 of them directly.

| slot | function |
|---|---|
| `vtable[0x00]` update **and** draw | `FUN_00164860` |
| `vtable[0x0C]` | `FUN_00164B08` |
| `vtable[0x10]` animate | `FUN_00164B28` - only a tail call to `FUN_001ADA58` |

### Dead ends inside the right function, worth recording

Even with the correct function identified, two obvious targets were wrong:

- **`data+0x30` is a free-running frame counter** incremented at `00164A90`. Halving it
  (verified live: 60/sec -> 30/sec) changed **nothing visible**. It counts frames; it does
  not drive the visuals.
- **There is no in-place float accumulate anywhere in `00164000`-`00166000`.** The aura has
  no clock and no rate constant. It is rebuilt from twelve sampled bone positions every
  frame, which is why every scan for a `time += rate` idiom missed it, in this session and
  in every previous one.

### Correction to the "advanced twice per frame" conclusion

The previous section inferred from gate states that the aura must be advanced in two
passes. **That inference was wrong.** It rested on `FUN_0012CB60`'s call list, which
`bisect.call_sites` had over-reported by running past a tail call, so the subsets being
compared were not the subsets being tested. There is one advance, in `FUN_00164860`.

The general lesson stands and is worth more than the specific claim: **when subsets of a
set do not reproduce what the whole set does, suspect the set enumeration before inventing
a mechanism.**

### Still open

- `0x01877F18` - a 30-frame HUD animation stepping 2.0/frame, driven from `FUN_00219710`.
  The only +/-2.0 stepper in RAM. Minor.
- Airborne motion, knockback, falling, ki blast and beam travel - the older open items.
  Worth retrying with `tools/gate.py` now that gating is an established probe, and with the
  guarded activity diff now that it is known to work.
- `[60FPS - effect rotation]` should be **removed**. Freezing its target outright produced
  no visible change, so it compensates nothing observable.

## 2026-09-05 - ratescan, and effect rotation was not wrong after all

`tools/ratescan.py` makes the audit mechanical. It records the same memory tick by tick
under both configurations and reports the ratio of per-tick motion: **0.50 compensated,
1.00 still at double speed**. Per tick rather than per vsync, because at 30fps the game
ticks every second vsync. The metric is total absolute variation, which reads the same way
for a ramp and for an oscillator.

It needs one filter to be usable. Most of a fighter struct is counters, bitmasks and
pointers, and reading those as floats produces per-tick "changes" of 1e20 that bury
everything real; requiring every sample of a word to be finite and inside a million cut
one scan from 78 false positives to 2.

Pointed at a hovering fighter, it found the effect-phase table at **`model+0x1038`** and
upward - nine slots of stride 0x40, three angles each, stepping **0.10, 0.23 and 0.27 per
tick at both frame rates**. A write watchpoint puts the stores at `00251E80`, `00251E9C`
and `00251EE0`, inside `FUN_00251A48`, writing `0x28`, `0x2C` and `0x30` of the slot.

That is exactly what `[60FPS - effect rotation]` halves - the group this log had written
off with *"and it is wrong. Revert it."* **That verdict is withdrawn.** It rested on a
2026-08-24 test that froze the phases outright and produced no visible change, but that
test was run **on the ground**. In an airborne hover these are the only cleanly
uncompensated per-tick quantities left in the fighter's model. Enabling the group takes
the rates to 0.05, 0.115 and 0.135 and drops the model's uncompensated word count from 30
to 3, which is what the ground reads too.

The other claim about that group - that it is incomplete, "four of the eleven per-tick
constants in that function" - is also wrong. `FUN_00251A48` reads 19 gp-relative float
constants; the rest are `3.141593`, `1.570796` and thresholds, not rates. For the phase
table the group is complete, and the measurement confirms it.

No regression from enabling it: flight 1.000, dash 0.988, rush 1.031, launched opponent
0.962.

## 2026-09-05 - the particle system, and the freeze that finally located it

The tween fix was real but it was not the airborne idle - the user tested it and
reported no change. What follows is what found the actual one.

### Freeze the clock and see what is left moving

`[60FPS - animation clock]` hooks **seven** sites, not the five an earlier
diagnostic froze, so no previous run of this test meant anything. Zeroing the
rate multiplier at all seven - `000F0104, 000F0124, 000F0144, 000F0164,
000F0184, 000F01A4, 000F01C4` - pins the fighter's clock solid at 62.0 while the
game keeps running. Anything still moving is then, by construction, not driven
by animation time.

Counting plausible-float words that move at all, in a settled airborne hover:

| region | normal | animation clock frozen |
|---|---|---|
| display packets `006E`/`007E` | 4982 / 4951 | 1139 / 1127 |
| `00900000` | 5495 | 526 |
| **effects `01900000`** | **3913** | **3494** |
| fighter 0 model | 128 | 106 |

The rendering collapses, as it should. The effect pool barely notices. **The
effect system runs almost entirely independently of the animation clock**, which
is why every measurement aimed at the clock kept coming back correct while the
user kept seeing something at double speed.

### What the effects were doing

An oscillation scan of `0x01870000`-`0x019A0000` from the identical-state oracle
put 41 of its 107 candidates on a single page. Their raw series, sampled once per
tick:

```
0199AD64   30fps   5  4  3  2  1  0 -1 -1        lifetime, -1.0 per tick
           60fps   5  3  1 -1 -1                 same per tick, half the real time
0199ADAC   30fps   0.504 0.420 0.336 0.252 ...   alpha ramp, -0.084 per tick
0199A7CC   30fps   29 28 27 26 25 24 23 23       a phase counter, -1 per tick
```

A particle system. Particles are born, age one unit per tick and die, so at 60fps
every particle lives half as long and the whole effect cycles at double speed. In
an airborne hover the body is almost still and the aura and its ki wisps are
nearly all the motion there is - which is exactly why this reads as "the air idle
is 2x" while the ground looks fine.

`FUN_00167258` is the updater: 20 entries of stride `0x70`, with

```
00167318  lui at, 0x3F80     ; f05 = 1.0
001673B0  sub.s f00,f00,f05  ; lifetime -= 1.0
001672DC  mul.s f00,f00,f03  ; position += direction * rate(+0x5D4)
0016732C  add.s f02,f02,f00  ; +0x60C += +0x5D0
00167368  sw a1, 0x5BC(s1)   ; four-phase counter, +1
```

Halving the `1.0` at `00167318` does fix the lifetime - it steps `5.5 4.5 3.5` and
lands back on the 30fps period - but the alpha ramp is untouched, because it is a
different channel. **Chasing per-tick constants one at a time reaches only the
ones that happen to be constants**; the position rate and the ramp are
per-instance data fields, and the phase counter is an integer.

### The fix, and why it is a gate rather than a constant

The only caller of `FUN_00167258` is `FUN_00168084`, an effect node's vtable[0] -
reached indirectly, no direct callers. It has the same shape as the ki aura's
`FUN_00164860`: **that one call updates and then tail-calls the draw**, ending in
`j FUN_001ADA58` or `j FUN_00167E68`. Gating the whole call would delete a frame
of the effect rather than slow it, which is the trap the aura work already fell
into once.

But the game has the branch already. At `00168104` a global flag sends execution
straight to `001681D4`, which sits **after all the update work and before the draw
tail call**. ORing frame parity into that flag test makes the particles advance at
their authored 30Hz while still being drawn every frame - and it fixes every
channel at once instead of one constant at a time.

One detail: the hook goes on the `ld` at `001680FC`, not the `andi` at `00168100`.
The andi's delay slot is the branch itself, and a branch cannot sit in a delay
slot. Hooking one instruction earlier means replaying both the load and the andi
in the trampoline.

### Verification

From the settled airborne-idle state, against the 30fps oracle, through the
shipped group:

```
0199AD64   off  5 4 3 2 1 0 -1 -1   |  gated  5 4 3 2 1 0 -1 -1   (was 5 3 1 -1 -1)
0199ADAC   off  .50 .42 .34 .25 ... |  gated  .50 .42 .34 .25 ... (was .50 .34 .17)
0199A7CC   off  29 28 27 26 25 ...  |  gated  29 28 27 26 25 ...  (was 29 27 25 23)
```

Every channel back on the 30fps period. Across `0x01870000`-`0x019A0000` the
plausible-float words oscillating at 2x fall from 107 to 70, and the whole
`0199A000` cluster disappears. No regression: dash 0.988 and launched-opponent
coast 0.985, unchanged.

### What is left

70 float words in the effect region still reverse about twice as often, spread
over `0198F000`-`01995000` with no single dominant cluster. Several of them step
*less* at 60fps than at 30 (`0.0106 -> 0.0059`, `0.1407 -> 0.0734`), so that
count is an upper bound and part of it is noise rather than defect. There is no
second obvious particle pool; the next one will have to be picked out
individually.

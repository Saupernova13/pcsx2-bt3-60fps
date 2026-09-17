# Airborne motion, gravity and the hovering idle

Flight, gravity, the airborne idle animation and the hover bob.

## The remaining 2x is AIRBORNE PHYSICS, not effects (2026-08-22)

> **PARTLY SUPERSEDED (2026-09-02).** "Position integrated per loop iteration" was a
> guess and no such integrator exists. The correct/wrong table at the top is still right.


The user's observation that reframed it: **everything wrong is in the air.**

| correct | wrong |
|---|---|
| ground idle | air idle |
| general fighting, grabs, rush blasts | Hard Knockback after a Full Power Smash |
| ground dash | falling after a stun |
| | ki blast and beam travel |

Ground movement in BT3 is root motion driven by the animation clock, which the
`+0xC80` fix already halves - so it is correct. Airborne movement is position
integrated per loop iteration with no delta-time term, so at 60fps it covers
twice the distance per second. Projectiles use the same path, which is why
beams behave identically. This is one bug, not the two ("effects" and
"projectiles") previously assumed.

### The fighter's world position

Found by capturing a fighter while flying (`work/captures/airborne.npz`) and
looking for smooth, every-frame float motion:

| offset | meaning |
|---|---|
| `fighter+0x15A0` | position X |
| `fighter+0x15A4` | position Y (seen climbing 4.25 -> 15.9 during a flight) |
| `fighter+0x15A8` | position Z |
| `fighter+0x15B0..B8` | facing, a unit vector (norm 1.0) |
| `fighter+0x15C0` | mirrors Y; initialised in `FUN_001D6438` |

### Why the integrator is hard to find

**Nothing stores to those offsets directly.** Scanning every `swc1`/`sq`/`sw`
against `0x15A0`/`0x15A4`/`0x15A8` returns zero hits. The position is passed
*by pointer* (`addiu rX, fighter, 0x15a0`) into a vector math library
(`FUN_001208xx`/`FUN_00121Exx`/`FUN_00122168`), so the write happens inside
generic vector code shared by everything in the game. Offset scanning cannot
find it and PINE has no write breakpoints.

Callers that materialise the pointer: `001D6454`, `001D64B4`, `001D6598`,
`001D6C18`, `001DB9CC`, and a cluster at `00285C6C`-`00286518`.

### Ruled out along the way

- `FUN_001D6580` / `FUN_001D6C08` take both the position and facing pointers but
  are the **camera/aim** system. Worth noting: `FUN_00122168(rate, cur, target,
  out)` lerps toward a target with a fixed per-frame rate read from `$gp`, so it
  converges twice as fast at 60fps - a real but separate 2x bug.
- **`001DCB40`, the second code in the circulating patch.** It is
  `lui $at, 0x4000` (2.0) -> `mtc1 $f12` -> tail call to `001C44F8`, our hooked
  animation-rate setter. That caller already yields 1.0 with our fix; halving it
  again would give 0.5. Redundant, not a missing fix.
- **`FUN_001E16BC`'s 30-frame periodic trigger** (`001E188C`, `slti $v1, $v0,
  0x1e`). Changed to 60 frames live; the user never confirmed any change, so it
  was reverted rather than shipped. The broader scan found **429 periodic frame
  counters in 310 functions**, nine of them in the effects module - a real class
  of 30Hz-authored timers, but they cannot be doubled blindly because most are
  correct as they stand.

### Next step that would actually crack it

A **write breakpoint** on `fighter+0x15A4` in the PCSX2 debugger. That names the
writing instruction directly, which is the one thing static analysis cannot
supply here. Everything else is guesswork.

## Airborne motion - the full investigation, and where it stopped (2026-08-22)

> **PARTLY SUPERSEDED (2026-09-02).** Its framing - "airborne movement is a separate
> integrator" - is not supported. Movement is root motion through the skeleton, and the
> position chain is now mapped by write breakpoint. Its *ruled-out* table below is still
> valid and still worth reading. Ignore its "next step"; see the 2026-09-02 sections.


The last unsolved symptom. **Everything airborne runs at 2x; everything grounded is
correct.** Air idle, Hard Knockback after a Full Power Smash, falling after a stun, ki blast
and beam travel, beam duration. Ground idle, general fighting, grabs, rush blasts and
ground dash are all right.

Ground movement is root motion driven by the animation clock, which the `+0xC80` fix
already halves. Airborne movement is not, so it is a separate integrator somewhere.

### What the write breakpoint found (the technique that works)

PINE cannot set write breakpoints. The PCSX2 debugger can, and it answered in one shot
what hours of static analysis could not. The procedure, for whoever picks this up:

1. `python tools/fighter.py --info` for the live fighter bases.
2. Debug -> Open Debugger, Breakpoints -> New, Type **Memory**, **Write**, size 4, at the
   address of interest.
3. When it trips, read the **Stack** tab. It gives the full call chain with PCs.

Doing that on `fighter+0x15A4` (position Y) produced:

```
0012BBD0   battle loop
  0012B6E0
    001C2C80
      001D64A0                       <- the writer
        001D6550  jal 00121EA8       <- pos += delta
```

### The EE vector math library (worth knowing, decoded by hand)

capstone has **no R5900 COP2 support**, so these decode as garbage (`bbit032`, `.word`)
in every tool in this repo. PCSX2's debugger decodes them correctly. This is a permanent
blind spot for `ps2ee/disasm.py` and it is precisely where BT3's motion code lives.

| address | signature |
|---|---|
| `00121EA8` | `Vec4Add(dst, a, b)` - `lqc2/lqc2/vadd.xyzw/sqc2` |
| `00121EC0` | `Vec3Add(dst, a, b)` - `vadd.xyz` |
| `00121ED8` | `Vec4Sub(dst, a, b)` - `vsub.xyzw` |
| `00121EF0` | `Vec3Sub(dst, a, b)` - `vsub.xyz` |
| `00121F38` | `Vec4Scale(dst, src, f12)` |
| `00121E90` | `VecSwap(a, b)` - `lq/lq/sq/sq` |

`Vec4Add` alone has **hundreds of callers**, so a static xref cannot identify a caller.
Only the runtime stack can.

### FUN_001D64A0 is a FOLLOWER, not the driver - the mistake that cost the most

```c
target = model[0x970] - bone[0x40];
pos   += (target - pos) * k;          // k = 0.2, from gp-0x6fc4 = 0x002FD2AC
```

This is exponential smoothing that makes the fighter's logical position chase the
rendered model. It looked exactly like the physics integrator and it is not.

`k` was halved to the exact half-step equivalent `1 - sqrt(1-k)` = `0.105573`
(`0x3DD8368F`), which preserves the convergence curve rather than approximating it with
`k/2`. **The constant is read by exactly one instruction in the whole binary**
(`001D6508`), so there was no collateral risk. Result: **no visible change whatsoever.**
Reverted to `0x3E4CCCCD`.

The lesson: a field that moves smoothly every frame and looks like position may be a
*smoothed copy* of the real thing. Check whether anything upstream feeds it before
patching. `pos += (target - pos) * k` is a follower; `pos += velocity` is an integrator.
They look identical in a memory watch.

### The object chain, for whoever continues

```
manager    = *(u32*)0x002FEB14
count      = *(u32*)(manager + 0)               // 2 in a normal battle
fighter[i] = *(u32*)(manager + 4) + i*0x1600
model_id   = fighter[0x0C]                      // 0 and 1, an index not a pointer
model      = *(u32*)(0x0031C640 + model_id*4)   // = FUN_002499B0
```

| what | where | note |
|---|---|---|
| fighter position XYZ | `fighter+0x15A0/A4/A8` | smoothed follower, NOT the driver |
| fighter facing | `fighter+0x15B0..B8` | unit vector |
| **model position XYZ** | **`model+0x970/974/978`** | different coordinate space, and it moves - this is upstream |

Live sample: fighter pos `(-0.63, 11.84, 3.04)` while model `+0x970` read
`(294.11, 26.63, 878.25)`. Both move; the model is the driver.

**The next step is a write breakpoint on `model+0x974`** and its call stack. That was
requested but the session ended first. Expect it to be a hot breakpoint - skinning and
rendering may also write there, so keep hitting Run until a stack containing `0012BBD0`
(the battle loop) appears, which is the gameplay path rather than the renderer.

### Everything ruled out for the airborne symptom

| attempt | result |
|---|---|
| `0024D030`, the only other `+0xC80` writer in the binary | no change; "speed less consistent in movement". Reverted |
| `001C44E4` (`+0xC8C`) and `001C4594` (`+0xCB8`), the two unhooked sibling animation-rate setters | "no change at all". Reverted |
| Object-pool scan for an effect entity system | only 3 pools exist (`002FEB14` fighters, `002FEB38` count==3 with a code pointer at +4, `002FF160` null). No effect pool |
| `FUN_001E16BC`'s 30-frame periodic trigger at `001E188C` | applied 30->60; never confirmed by the user, so reverted rather than shipped |
| `001DCB40`, the circulating patch's second code | `lui $at, 0x4000` (2.0) tail-calling our hooked setter - already yields 1.0 with our fix. Redundant, not missing |
| `FUN_001D64A0`'s smoothing constant `k` | no visible change. Reverted |
| Static scans for `swc1`/`sq`/`sw` to `0x15A0/A4/A8` | **zero hits** - position is passed by pointer into the vector library |
| `pos[t+1] - pos[t] == V[t]` search over a 1426-frame airborne capture | no exact match, because the update is a lerp not a plain integrator |

Also still open but lower priority: `FUN_00122168(rate, cur, target, out)` in the
camera/aim path lerps toward a target with a fixed per-frame rate from `$gp`, so the
camera also converges twice as fast. Nobody has complained about it.

There are **429 periodic frame counters** in 310 functions binary-wide, found by scanning
for `addiu rX, rX, 1` followed by `slti rZ, rX, N`. Nine are in the effects module
(`001E0F54` period 2, `001E02F0`/`001E7ACC` period 4, `001E769C` 21, `001E7AEC` 24,
`001E188C` 30, `001E8148` 31, `001EEBB4` 91). They are a real class of 30Hz-authored
timers, but they cannot be doubled blindly - most are correct as they stand.

## Airborne 2x - it is the STEP SIZE, and the velocity is fighter+0x50 (2026-09-02)

The user's framing that started this round: *"everything we fixed - fighting, the ki aura -
is only correct ON THE GROUND. It all goes back to double speed in the air. Gravity
especially, knocking an opponent flying is air dependent and they move at 2x."*

### The aura is NOT a second bug - one bug, not two

Worth settling first, because it looked like the aura fix had regressed. It has not.

A pure call-counter on the gameplay path (`work/callcount.py`, no behaviour change) gave
**identical counts on the ground and in the air**, sampled twice:

| counter | ground | air |
|---|---|---|
| `FUN_0012B6E0` gameplay update | 1.00/frame | 1.00/frame |
| `FUN_001C2C80` fighter update | 1.00/frame | 1.00/frame |
| `FUN_001D64A0` position follower | 2.00/frame | 2.00/frame |
| `FUN_00164860` aura vtable[0] | 2.00/frame | 2.00/frame |

So nothing is called more often in the air. The aura still advances at its gated 30Hz; it
only *looks* 2x because it is faithfully tracking a character whose **motion** is 2x.
**The air defect is step SIZE, not step COUNT.** Any future hypothesis that needs an extra
update pass in the air is dead on arrival - this measurement is cheap, rerun it.

### fighter+0x50 is the per-tick airborne velocity

Found by capturing the whole fighter struct and 4KB of each model every frame for 300
frames of flight (`work/aircap.py`, `work/captures/air.npz`) and correlating every moving
word against the position delta.

| model axis | correlate | scale |
|---|---|---|
| `model+0x970` X | `fighter+0x50` | 1.0004 |
| `model+0x974` Y | `fighter+0x54` | 0.9099 |
| `model+0x978` Z | `fighter+0x58` | 0.9897 |

Sampled during flight, `fighter+0x54` tracks `d(model Y)` frame for frame:

    frame 30   v = -0.107   d(pos) = -0.265
    frame 40   v = -1.667   d(pos) = -1.400
    frame 45   v = -1.917   d(pos) = -1.766
    frame 50   v = -1.199   d(pos) = -1.202

Mean magnitude **6.7 units per FRAME**. That is the whole bug stated numerically: a per-tick
velocity with no delta-time term, so at 60Hz it covers exactly twice the ground per second
that it did at 30Hz.

It is not an *exact* match (max ~18% error) because the model position also carries
animation root motion on top of the physics translation. Do not expect
`pos[t+1]-pos[t] == v[t]` to hold to the bit here.

`fighter+0x40` is a sibling vector: X and Z are identical to `+0x50`, only Y differs, and
its Y sits pinned at ~0.463 whenever vertical motion is passive. Likely pre-gravity or
desired velocity. The 0.463 varies in its low bits, so it is **computed, not a stored
constant** - searching the binary for it is a dead end.

### The render chain is all followers - stop walking it

Three levels, each one a follower of the next. Prior sessions burned time on the first two;
this session proved the third. **Nobody should walk this chain again.**

    fighter+0x15A0  <- exponential smoothing (pos += (target-pos)*k)  FUN_001D64A0
    model+0x970     <- 128-bit COPY                                   FUN_0024E3F8
    bone[0]+0x40    <- ???

`FUN_0024E3F8` computes `$a0 = model+0x950+0x20` = `model+0x970` at `0024E4C8` and passes it
to `FUN_00121FA8`, which is exactly `lq $t0,0($a1)` / `sq $t0,0($a0)` - **a copy, not an
integrator**. Hand-decoded; capstone shows these as garbage (no R5900 COP2 support).

Useful vector-library additions to the table in the earlier section:

| address | signature |
|---|---|
| `00121FA8` | `Vec4Copy(dst, src)` - `lq`/`sq` |
| `00121FB8` | `Vec4MulAcc(dst, src)` - `lqc2`/`lqc2`/`vmula.xyz`/`sqc2` |
| `00120B98` | `StoreMatrix(dst)` - `sqc2 vf16..vf19` |

### Static search for the velocity writer is closed

Scanning `0x00100000-0x00300000` for stores to offsets `0x40/0x44/0x50/0x54/0x58` with a
non-stack base returns hundreds of integer `sw` hits and **not one `sq`**. The velocity is a
128-bit vector written through the vector library by pointer - the same reason offset
scanning failed for `fighter+0x15A0`. Static analysis cannot answer this.

**The next step is a PCSX2 debugger write breakpoint on `fighter0+0x54`** (Memory, Write,
size 4), and reading the Stack tab. `python tools/fighter.py --info` gives the base.

### `work/trace.py` - an in-game tracer, and the three ways it crashed PCSX2

The technique works and answered in four rounds what static analysis could not: it narrowed
the writer of `model+0x974` from the whole battle loop to one call, by appending
`(id, watched value)` to a ring buffer at chosen function entries. Unlike gating or nopping
it changes no behaviour. Results: battle loop -> `FUN_001C2C80` -> first call of
`FUN_001C1EA0` -> `FUN_0024E3F8`.

**But it crashed the emulator four times.** Each cause is real and each is a trap for any
future code instrumentation in this project:

1. **Two-word displacement has a restore window.** Restoring `I1` before `I2` leaves the
   site as `I1 ; nop` for a moment, so a prologue store that saves a callee-saved register
   is skipped and the epilogue restores garbage. Displace **one** word instead: hook a store
   whose successor is also a store to a different slot. Stores write no registers, so the
   reordering is harmless and install/restore are each a single atomic write.
2. **`$t0-$t3` are only dead at a function ENTRY.** A site-picker that scans forward for a
   store pair will happily land in the function body, where they are live. The correct
   condition is not distance but **no branch between the entry and the site** - that keeps
   you in the entry basic block.
3. **An uninitialised cursor is a wild store.** The trampoline read its buffer cursor from a
   scratch word that was only initialised *after* all hooks were installed. On a fresh boot
   that word is zero, and a `cursor < END` bounds check passes zero happily - so every
   tracepoint wrote to **address 0x00000000** during installation. Check both ends with one
   unsigned compare: `(cursor - BUF) unsigned < SIZE`. Disable tracing before the first hook
   goes in.
4. **Unexplained, and the reason to stop.** After all three fixes the tracer installed and
   captured cleanly - then the game died minutes later while sitting idle with the
   tracepoints still resident and the buffer frozen. The hooks are provably inert in that
   state, so something about leaving them installed is still wrong. **Do not leave
   tracepoints resident.** Capture, then remove them immediately.

The honest summary: this is a powerful instrument and it produced every structural result in
this section, but it costs the user an emulator restart when it is wrong, and it was wrong
three times out of four. Prefer the PCSX2 debugger's write breakpoint when a write
breakpoint is what you actually need.

### The position round-trip - five breakpoint-confirmed links (2026-09-02)

Traced with PCSX2 write breakpoints (safe, unlike the tracer). Each link below was read off
a `ra` register at a real hit, not inferred. **Every one of them turned out to be a copy or
a difference of something further up**, which is why five rounds were needed.

    model+0x9D0  (matrix translation)  <- StoreMatrix, from 0024E370 in FUN_0024E2B0
    model+0x980                        <- Vec4Copy(model+0x980, model+0x950)  at 0024E314
    model+0x950                        <- Vec4Add(model+0x950, fighter+0x10, fighter+0x30)
                                          at 001D71F4, in FUN_001D7198
    fighter+0x10                       <- Vec4Sub(fighter+0x10, model+0x970, fighter+0x30)
                                          at 001D7118, in FUN_001D70E8
    fighter+0x50 (velocity)            <- Vec4Sub(fighter+0x50, fighter+0x10, anchor)
                                          at 001D8310
    model+0x970                        <- Vec4Copy from bone[0]+0x40, at 0024E4CC

`FUN_002505A8(model, i)` = `*(u32*)(model + 0xD6C + i*4)` - the bone pointer table.

**The per-frame cycle, and why grounded motion is already correct:**

| step | call in `FUN_001C1EA0` | what happens |
|---|---|---|
| 1 | *before* | something advances `fighter+0x10`  <- STILL UNKNOWN |
| 2 | `[10] FUN_001D7198` | `model+0x950 = fighter+0x10 + fighter+0x30` |
| 3 | matrix -> bones | skeleton evaluated, animation root motion applied |
| 4 | `[16] FUN_001D70E8` | `fighter+0x10 = model+0x970 - fighter+0x30` |

Position round-trips through the skeleton every frame, so ground movement rides the
animation clock and the existing `+0xC80` fix already covers it.

**Evidence that step 1 exists:** `fighter+0x30` is a pure vertical offset `(0, y, 0)`
(verified over 300 frames), so X and Z of `model+0x950` and `model+0x970` would be
*identical* if the round-trip were the only mover. Measured, they differ by **~4.1 units
per frame in XZ alone**, against a total motion of 6.75/frame. Something injects horizontal
movement into `fighter+0x10` between steps 4 and 2. **Finding that writer is the next step**
- breakpoint `fighter0+0x14` and enumerate every distinct `ra`, not just the first: the
known one is `001D7120` (the step-4 Vec4Sub), and the injector is whatever else appears.

Other useful facts from this round:

- `model+0x9A0` is the model's **world matrix** - rows 0/2 a unit Y-rotation, row 3 the
  translation with `w=1`. `model+0x990` is its rotation vector, and **`model+0x994` (yaw) is
  advanced by a per-tick rate from `$gp-0x5C18` and wrapped by `$gp-0x5C14`** at `0024E334`,
  inside `FUN_0024E2B0`. That is an uncompensated per-tick accumulator in its own right and
  has not been evaluated yet.
- Vector library additions: `00121FA8` `Vec4Copy` (`lq`/`sq`), `00121FB8` `Vec4MulAcc`,
  `00120B98` `StoreMatrix(dst)` writing `vf16..vf19` to `dst+0x00/10/20/30`.
- Do NOT print a full binary-wide xref dump into the transcript; cap it. One such scan in
  this session produced several hundred lines for no benefit.

### FAILED: halving (model+0x970 - model+0x950) is NOT the movement channel (2026-09-02)

The experiment `[60FPS - EXPERIMENT halve root motion]` hooked the step-4 read-back at
`001D7118` and substituted the midpoint of `model+0x950` and `model+0x970`, which by the
algebra above should have halved every per-frame displacement.

**Result, user-observed:**

| | predicted | actual |
|---|---|---|
| airborne | becomes correct | **still 2x - unchanged** |
| grounded | becomes half speed | **still correct - unchanged** |
| attacks | *(not predicted)* | **every punch drives the character metres BACKWARDS**; only the first punch connects |

The hook was verified in force before judging (`001D7118 = 0803C200`), so this is a real
negative, not a deployment failure.

**What it means.** Neither locomotion channel changed speed, so
`model+0x970 - model+0x950` does **not** carry general movement - if it did, halving it
would have halved walking and flight. What it does carry is **animation root motion**
(attack lunges), and halving that produced net *backwards* travel rather than a shorter
lunge. That signature - negative residue proportional to the root delta - is what you get
when the engine also **subtracts the full root delta somewhere else** to reset the root
bone. Applying only half leaves the other half as backwards drift every frame.

**The broken assumption.** The derivation `fighter+0x10 += (model+0x970 - model+0x950)`
assumed `model+0x950` still holds `fighter+0x10 + fighter+0x30` when step 4 runs. That was
**inferred from a single call site, never verified**. `model+0x954` was never breakpointed -
the only address in the chain that wasn't - and the static scan found **14 different sites**
that materialise a pointer to `model+0x950`. Something else almost certainly writes it
between steps 2 and 4, or `fighter+0x30` moves.

**Next step:** write-breakpoint `model0+0x954` and enumerate *every* distinct `ra` over
several hits, exactly as was done for `fighter+0x14` (where six hits proved a single
writer). Do not infer a sole writer from one call site again - that is what cost this round.

**Method note that generalises:** an inferred link in a data-flow chain is not evidence.
Every link in the chain above that was *breakpoint-confirmed* held up; the one link that was
*inferred from disassembly* is the one that broke the fix.

### Instruments built 2026-09-02, and how far to trust them

All live in `work/`, which is **gitignored** - a fresh clone will not have them. Rebuild
from the descriptions here if they are missing.

| tool | what it does | risk |
|---|---|---|
| `work/aircap.py` | frame-precise capture of both fighter structs and 4KB of each model, to `work/captures/*.npz`; plus a velocity-match analyser | **none** - read-only |
| `work/callcount.py` | counts entries to chosen functions, per frame | low - pure counters, but it is still code instrumentation |
| `work/aurabypass.py` | neutralises a shipped `patch=1` group live, for A/B | low - single-word hook at a known site |
| `work/trace.py` | logs `(id, watched value)` at function entries to a ring buffer | **HIGH - crashed the emulator four times.** Read its section above before reuse |

The capture in `work/captures/air.npz` (300 frames of flight, both fighters, no dropped
frames, objects verified not reallocated) answered several questions offline at zero risk
and is worth keeping. Prefer asking it a question over instrumenting the game again.

**The single most valuable habit from this session:** every link in the position chain that
was confirmed with a PCSX2 write breakpoint held up under test; the one link inferred from
reading disassembly is the one that broke the fix. Breakpoint the address, enumerate
*several* hits, and only then believe you know who writes it.

---

## 2026-09-04 - airborne motion, solved

### The measurement that reframed it

From a save state of a launched opponent, with no input at all, per game tick:

```
=== 30fps reference ===            === 60fps, shipped patches ===
tick   |dpos|  |root delta|        tick   |dpos|  |root delta|
4300   6.4815       0.0000         4302   6.4815       0.0000
4301   6.4815       0.0000         4303   6.4815       0.0000
4302   6.4815       0.0000         4304   6.4815       0.0000
...    6.4815       0.0000         ...    6.4815       0.0000
```

Two things at once. **The root bone delta is exactly zero** for the whole flight, so the
position round-trip through the skeleton - the thing four sessions had been mapping -
carries none of this. And **the per-tick step is identical at both rates**, so the channel
is completely uncompensated: twice the ticks, twice the distance, exactly 2x.

That also settles why the 2026-09-02 halve-root-motion experiment failed. It halved a
channel that reads zero in the air, which is why the air was untouched, and it was the
*ground* channel, which is why the ground broke.

### Finding the writers

A write watchpoint on the victim's `fighter+0x10`, over 25 hits, from the airborne state -
not from the ground, which is what the earlier session had done when it concluded there
was a single writer:

```
        pc         ra   hits  instruction
  00121EE4   001D7120     11  jr ra          Vec4Sub from FUN_001D70E8 - root motion
  00121EB4   001DE058      3  jr ra          Vec4Add from FUN_001DE000
  001DE064   001EAC4C      3  swc1 f00, 0xC(s0)
  001DEDC4   001EAC54      3  swc1 f01, 0x4(s0)
  00121EB4   001DFDC4      3  jr ra          Vec4Add from FUN_001DFD88
  001DFDD0   001DFDC4      2  jal 0x001221B8
```

Six sites, not one. Three separate airborne channels alongside the known root-motion one.

### What each channel does

```
FUN_001DE000                            directed travel: flight, dash, knockback
    s0     = FUN_001DC298(fighter)      = fighter+0x10, the position vector
    speed  = FUN_001DBFF8(*(+0xA8), target, step)   ; approach by at most step
    *(+0xA8) = speed
    pos   += *(+0x90) * speed           ; +0x90 is a unit direction vector

FUN_001DED78                            vertical: gravity, rising, falling
    vy     = FUN_001DBFF8(*(+0xAC), target, step)
    *(+0xAC) = vy
    pos.y += vy

FUN_001DFD88                            the short slide after taking a hit
    if (FUN_001D63A8(...)) return
    pos   += *(+0x80)                   ; the whole residual, every tick
    len    = Length(*(+0x80))
    if (len < eps) *(+0x80) = 0
    else           *(+0x80) *= (len - eps) / len
```

`FUN_001DBFF8(current, target, step)` is a move-toward-by-at-most-step helper, decoded
from its two `bc1fl` branches: return `current + |step|` while that stays below `target`,
else `current - |step|` while that stays above it, else `target`. It has 9 call sites;
`FUN_001DE000` has 17 callers and `FUN_001DED78` has 29, so these are the engine's general
motion primitives and patching them covers every move rather than one move type.

Confirmed by reading the fields during a launch: `+0x90` has length exactly `1.0000` and
`+0xA8` reads `6.48148`, which is the per-tick step to four decimal places.

### The fix, and why it is two halvings and not one

Each channel has a **value** and a **rate**, and both are per tick:

- Halve only the applied displacement and the fighter moves at the right speed, but the
  ramp and the decay still run at double rate - a knockback reaches its end in half the
  real time. Measured as 1.43x total distance with a correct instantaneous speed.
- Halve only the approach step and the fighter still moves at 2x.

So the trampolines halve `f14` (the approach step) before the call and halve the applied
displacement after it. **The stored speed is left in its authored 30Hz units**, because
other code reads it; only its use is halved.

The arithmetic, with `s` the stored speed in units per tick: applying `s/2` at 60Hz gives a
real speed of `30s`, matching `s` applied at 30Hz. Ramping by `step/2` per tick at 60Hz
gives `ds/dt = 30*step`, matching `step` per tick at 30Hz. Two halvings, no quarterings.

The decay confirms it directly - knockback speed, tick by tick:

```
30fps           6.4815  6.3272  6.1728  5.7099             (-0.1543, -0.1543, -0.4629)
60fps shipped   6.4815  6.3272  6.1728  5.7099  5.2469 ... (identical per tick: 2x in time)
60fps patched   6.4815  6.4043  6.3272  6.0957  5.8642 ... (exactly half per tick)
```

### Results

Against the unpatched 30fps game, same state, same input, same vsyncs
(`tools/speedtest.py`, cruise column - speed once both runs are already moving):

| situation | before | after |
|---|---|---|
| sustained flight | 2.056 | **1.000** |
| boosted dash | 1.507 | 0.988 |
| melee rush | 0.465 | 1.031 |
| backward flight, terminal speed | - | 125.000 vs 125.000 units/s |
| launched opponent, per tick | 6.4815, same as 30fps | 3.2407, exactly half |
| circling sideways | 1.911 | 0.803 |

Soak test: 63 seconds of live play with randomised input, 3757 ticks at a measured 59.6
ticks per second, no crash, rendering correct by screenshot.

### Open question: circling is now 20% slow

Holding the stick sideways circles the opponent, and that motion goes through
`FUN_001DE000` like everything else - the first ticks of the hold show its speed stepping
by exactly half, `-0.46296` against the reference's `-0.92593`, so the patch is doing what
it intends. What differs is later: all three configurations climb the same ramp toward a
terminal speed of about 88 units/second, and the patched run climbs it more slowly in real
time, 2.7 units/s squared against 6.4.

In that phase the speed is *clamped to its target* every tick rather than stepping toward
it, so the observed change is the target's own movement and the approach step is
irrelevant.

A breakpoint on `FUN_001DE000` during a sustained sideways hold, at matched real times,
narrows it to one value. Two calls land per tick, one per fighter:

```
30fps    ra=001EF314  a0=fighter0  target 0.911642  step 0.925926   speed 0.906403
         ra=001EEA88  a0=fighter1  target 0.000000  step 0.925926
patched  ra=001EF314  a0=fighter0  target 0.721057  step 0.925926   speed 0.719722
         ra=001EEA88  a0=fighter1  target 0.000000  step 0.925926
```

**The step is a constant `0.925926` and identical at both rates**, so it is uncompensated
and halving it is right. The *target* is the whole difference: 0.9116 against 0.7211 at the
same moment, and it climbs at half the real rate under the patch.

`FUN_001DE080` **tail-jumps into `FUN_001DE000`** rather than calling it, which is why `ra`
points at `FUN_001DE080`'s own caller and why a static scan for `jal 001DE000` does not
list this site. Its `a3` is a flag, not a vector - read live, it is `0` and `7`.

The target arrives already computed: at `FUN_001DE080`'s entry `f12` is the same 0.911642
that reaches `FUN_001DE000`. It is set at `001EF2F0` by **`FUN_001DAC78(fighter, 0xE)`**, a
per-fighter parameter getter, and that is the value evolving at half rate. The nearby
`0x41F00000` constant at `001EF2D8` is **not** a frame rate despite reading as `30.0f`:
`FUN_001E0708` compares it against a vector length, so it is a distance threshold.

**Next step if this is worth chasing:** a watchpoint on whatever `FUN_001DAC78(fighter,
0xE)` reads, to find the field behind parameter `0xE` and what advances it per tick.

It is a mild slowness against a former 91% overspeed, so it is a refinement, not a defect.

---

## 2026-09-05 - gravity, the fourth airborne channel

The user played the airborne fix and reported that **falling was still 2x** while rising,
flight, dashes and knockback were correct. They were right, and the reason is that free
fall does not go through `FUN_001DED78` at all.

Controlled vertical movement was already correct - measured, holding ascend against the
30fps oracle gives 0.995 and holding descend gives 1.004. What was still wrong was the
uncontrolled drop after a knockdown, which needs a six-hit combo to produce: three hits
leave the victim floating at the top of the arena indefinitely, and only a longer combo
puts them into the falling state.

A breakpoint on `FUN_001DED78` never fires during that fall. A **write watchpoint on the
victim's `fighter+0xAC`** named the routine instead:

```
FUN_001DED28
    v0 = FUN_001DC298(a0)               = fighter+0x10
    vy(+0xAC) += g                      g   = 0.462963 per tick, at $gp-0x6E4C
    if (vy > terminal) vy = terminal    terminal = 27.777775, at $gp-0x6E48
    pos.y += vy
```

Both constants are plain data words, and a scan of `.text` for `lwc1 fX, imm(gp)` finds
**exactly one reader of each**, so the acceleration can be halved in data. Only the
application needs a trampoline. The terminal velocity is deliberately left alone: `vy`
stays in its authored 30Hz units, so the value it clamps to is still correct.

Measured, in a real fall:

```
                per-tick acceleration      applied height change
30fps                     0.4630           dy = vy
60fps before the fix      0.4630           dy = vy          <- 2x in real time
60fps after               0.2315           dy = vy * 0.500
```

`dy/vy` reads exactly 0.500 on every tick of the descent, and vy reaches the same value at
the same wall-clock moment, so twice as many ticks cover the same ground.

**Do not try to A/B a fall by forcing it.** Writing `pos.y` verifies, and the game then
overwrites it from its own round trip on the very next tick; writing the height and vy
together produced a 20-second "fall" in one configuration and a 1.8-second one in the
other, purely because the two runs had diverged into different states. The per-tick
numbers above are the honest measurement.

## 2026-09-05 - airborne idle animation: what was ruled out

The user's second report was that **idle animation in the air is still 2x**, with the ki
aura and everything else correct. This is not yet explained. What is now ruled out, all by
measurement:

- **The body animation clock is correct in the air.** `model+0xB40+0x138` advances 2.0 per
  tick at 30fps and 1.0 per tick at 60fps, in the air exactly as on the ground, and the
  idle loop is 108 units long in both - 1.8 seconds either way.
- **The pose matches.** Screenshots taken at the same animation-clock phase while hovering
  are the same pose under both configurations.
- **Nothing else in the fighter struct is running fast.** During an air hover only five
  words move at all; the two with a ratio above 0.8 are `fighter+0x15A0` and `+0x15A8`,
  the known smoothed render follower, whose exponential filter does not produce a clean
  0.5 ratio in any case.
- **Nothing else in the model is running fast** once effect rotation is enabled: 3
  uncompensated words out of 123 moving, the same count the ground shows.
- **A 2 MB sweep either side of the model pool** finds 163 uncompensated words out of 3785
  moving, all of them stepping between 0.001 and 0.006 per tick - too small to be an
  animation and with ratios around 1.05 rather than a clean 1.0.

So either the effect-rotation group now fixes it - it is the only real 2x that was left in
an airborne fighter, and it is now shipped - or the thing the user is seeing lives outside
the fighter and its model. **Next step: ask which element looks fast** (hair, clothing, the
hovering sway, the whole body) and, if it is the character itself, sweep the model table at
`0x0031C640` for other entities attached to the fighter rather than only the two fighter
models.

## 2026-09-05 - the airborne idle: a clean oracle, and every clock in RAM

The previous section ended by asking for a sweep of the model table, on the theory that
some second entity attached to the fighter was the thing running fast. That is answered,
and so is a bigger question - but the defect is still not found, so what follows is mostly
elimination, recorded so it is not repeated.

### The measurement was wrong before it was inconclusive

Every airborne A/B up to here flew to the hover inside the measured window: hold `Cross`
with the stick forward for N vsyncs, release, sample. That is not an oracle. At 30fps those
N vsyncs are N/2 ticks of ascent and at 60fps they are N, so the two runs arrive at
different heights carrying different momentum, and every positional word in the fighter
then differs for reasons that have nothing to do with the patch. Read that way the fighter
struct reported 51 of 70 moving words "at double speed", including six at 44x - all of it
an artifact of comparing a run that had stopped drifting against one that had not.

The fix is to take the flight out of the measured window entirely. `scratchpad/mkair.py`
flies once, waits for the hover to settle - drift falls to exactly 0.00000 per vsync,
y frozen at -151.227 - and cuts a save state there. Both configurations then load
identical RAM and take **no input at all**, so any difference between them is the patch
and nothing else. A screenshot confirms the state is the real thing: the fighter hovering
high above the arena in the flight idle, aura lit, opponent a speck on the ground below.

Two facts about flight that are worth writing down, since neither is guessable:

- `Cross` plus left stick `(0.0, 1.0)` is the only input that gets airborne. `R1` alone
  does nothing at all, and `R1` with the stick forward barely leaves the ground.
- **World Y is inverted.** Altitude is negative - the ground is about -0.05 and a good
  hover is -150. A "height" check written the intuitive way passes on the ground and
  fails in the air.

### Every animation clock in RAM, found by shape

The model table at `0x0031C640` holds 128 pointers of which exactly **2 are live** -
`008C02F0` and `008C1970`, the two fighter models. There is no hair, cape, aura or
afterimage entity hiding behind it, so a search that follows pointers from the fighter can
only ever find what has already been searched.

Searching by shape instead has no such limit. An animation controller is recognisable
without knowing who owns it: the clock sits at `+0x138`, its per-tick rate at `+0x140`, and
the rate reads a stock `2.0`. So a moving float whose neighbour eight bytes along is
exactly `2.0` is a running animation clock, wherever it lives. Across all 32 MB there are
exactly **three**:

| clock | controller | 30fps | 60fps | ratio |
|---|---|---|---|---|
| `008C0F68` | `008C0E30` | 1.00000 | 1.00000 | 1.000 |
| `008C25E8` | `008C24B0` | 1.00000 | 1.00000 | 1.000 |
| `01995B84` | `01995A4C` | 0.03593 | 0.03593 | 1.000 |

The first two are the fighters' body controllers at `model+0xC78`. All three advance the
same amount per vsync at both rates, which is to say **at the correct speed in real time**.
Measured per tick the same numbers read 2.0 against 1.0, the halving the patch installs;
per vsync - per unit of real time, which is what the user sees - they read 1.00 against
1.00. There is no fourth clock and none of the three is fast.

That is as close to proof as this project gets that **the body animation is not what is
running at double speed in the air.**

### A per-vsync sweep of all 32 MB, and why the first one lied

With both runs starting from identical RAM, a full sweep becomes meaningful. Storing 20
snapshots of 32 MB is not possible, so `scratchpad/ramsweep.py` keeps running accumulators
instead - per word the sum of the non-zero absolute deltas, how many there were, and the
largest.

The first version dropped that largest delta before averaging, to stop a looping clock's
wrap from swamping its step. That quietly biased the whole comparison. At 30fps the game
ticks on every second vsync, so a 20-vsync window gives ten non-zero deltas against the
60fps run's twenty, and removing the maximum costs a ten-sample mean far more than a
twenty-sample one. Every merely noisy word came out looking 1.1-1.7x faster at 60fps: 8199
words in that band, more than sat around 1.0. Keeping every delta and letting a wrap
inflate one word rather than a whole class moved 9063 words onto 1.0 and shrank the
suspicious band by a third. **A robustness trick that is not symmetric between the two arms
of an A/B is a bug in the oracle, not a refinement of it.**

### What the sweep found, and why it is not the answer

One region stands out with ratios that are not noise at all - dead-clean `2.000` on values
like `0.50000 -> 1.00000`, `2.30000 -> 4.60000` and `25.60027 -> 51.20022`. It sits at
`0x018768A8`-`0x0187C6F8`, immediately past the two fighter structs, and it is a pool of
per-tick timers: a write watchpoint names `00267AE4 swc1 f12, 0x8(a0)` as the writer and
`FUN_00267B00` as the stepper, which does

```
lwc1  f00, 0x8(a1)     # the timer
sub.s f00, f00, 1.0    # exactly one per call
```

A countdown decremented by exactly 1.0 per call, uncompensated, which is exactly the shape
of the bug being hunted.

It is still not the defect. Running the same A/B from the **ground** state finds the pool
just as busy there - 341 moving words and 65 at 2x, against 334 and 51 in the air. The user
reports the ground as correct. Whatever these timers drive is either invisible or already
compensated somewhere downstream, and a patch aimed at them would be a change made for the
sake of a number rather than for anything on screen.

### Where this leaves it

Ruled out for the airborne idle, all by measurement from the identical-state oracle: the
body animation clock, every other animation clock in RAM, the whole model block
`0x0000`-`0x1600`, the model table, the fighter struct, and the per-tick timer pool behind
the fighters.

The next measurement drops step size altogether. Comparing how far a word moves is
confounded by state divergence; an animation that plays at double speed reverses direction
twice as often in the same number of vsyncs, and a count of sign changes needs no
magnitude, no alignment, and one word of state per address - so it can sweep all of RAM.
That is `scratchpad/oscscan.py`.

## 2026-09-05 - the hovering idle bob, and the state every scan had been missing

The user, after two fixes that were real but were not the one they were seeing:

> whenever you load state or I see you "playing the game" you're mostly on the
> ground. im in the air now.

They were right, and it was the whole problem.

### The synthesized hover was the wrong animation

Every airborne state built here was made the same way: hold `Cross` with the
stick forward, release, wait for the drift to reach zero. That does put the
fighter in the air, and it is settled, and it is reproducible - and it leaves
them in the **crouched flight pose**, leaning forward. The hovering idle is a
different clip entirely: upright, arms down, holding station. Screenshots of the
two side by side are not subtle.

**A character in the flight pose does not bob.** So every scan of the model came
back clean - "0 double-speed words in 0x0000-0x1600" - because the thing that
runs fast was not running at all in the state being measured. The measurement was
sound; it was pointed at the wrong animation for two sessions.

The fix for the method is to stop synthesizing the situation. `roo.savestate`
works on a running VM, so the user's own session became slot 5 while they were
sitting in the air. Every measurement below starts there.

### The bob is not the animation

In the real hovering idle the body animation clock is still correct - it steps
1.0 per vsync at both rates, exactly as it did everywhere else. But the fighter's
**world position never moves at all**, while the skeleton root Y swings through
about 4 units, and swings through it about twice as often at 60fps. That is why
a position trace of a hover looks perfectly still: the bob is absorbed by the
anchor, not expressed in world space.

Re-running the model scan from slot 5 - the same scan that had reported nothing -
lit up 19 words with clean 2.00 ratios, all in the hovering fighter's model:
`+0x954` and `+0x974` (root Y before and after the skeleton pass), `+0x9D4` (the
matrix translation Y), `+0xAF8`-`+0xB04`, `+0xF64`-`+0xFE8`, `+0x1120`-`+0x11A8`.
Their waveform is a clean sine that completes its arc in half the real time.

The fighter struct, scanned from the same state, gave the input: `+0x34` (the
anchor Y) and `+0xB8`, both at exactly 2.00.

### The generator

A write watchpoint on the anchor Y lands in the tail of `FUN_001DFD88`:

```
001DFF44  lwc1  $f0, -0x6DF0($gp)   phase increment
001DFF48  add.s $f0, $f12, $f0      phase += increment, once per tick
001DFF4C  c.lt.s $f1, $f0           wrap at a limit
001DFF54  swc1  $f0, 0xA8($s0)      the phase          -> fighter+0xB8
001DFF6C  jal   0x0011F588          sine of the phase
001DFF74  add.s $f0, $f0, $f0       doubled for amplitude
001DFF78  swc1  $f0, 0x24($s0)      the anchor Y       -> fighter+0x34
```

The increment measures **0.10472 per tick, which is pi/30** - one full revolution
per 60 ticks. That is two seconds at 30Hz and one second at 60. The game's frame
rate is written into the arithmetic exactly as it was in the tween constructor,
just spelled as a fraction of pi instead of as `30.0`.

### Resolving the constant without $gp

`$gp` reads zero wherever the VM pauses - the pause lands in the kernel idle loop
where r28 is not live - and a breakpoint on the instruction did not stop in time.
So the constant was found by value instead: measure the increment exactly, then
scan for it. Four identical copies of pi/30 sit in the small-data pool at
`002FD088`, `002FD468`, `002FD47C` and `002FD480` - the same pool as the gravity
constant at `002FD424`.

Halving each in turn says which is which, with no inference at all:

| halved | phase per vsync at 60fps |
|---|---|
| `002FD088` | 0.10036 |
| **`002FD468`** | **0.05018** |
| `002FD47C` | 0.10036 |
| `002FD480` | 0.10036 |

And scanning the whole code segment for `lwc1 f?, -0x6DF0($gp)` finds **exactly
one instruction** - `001DFF44` itself - with no `lw`, `sw` or `swc1` at that
offset either. The constant is private to the bob, so a one-word data patch is
completely surgical.

    patch=1,EE,002FD468,word,3D56774E // pi/30 -> pi/60

Halving a float is subtracting `0x00800000` from it, so `3DD6774E` becomes
`3D56774E`. Frequency halves; amplitude is untouched.

### Verification

From the user's own captured hover, through the shipped group, 150 vsyncs:

| configuration | `002FD468` | phase per tick | bob reversals |
|---|---|---|---|
| `off` - the 30fps oracle | `3DD6774E` = pi/30 | 0.10472 | **2** |
| `full` without this group | `3DD6774E` = pi/30 | 0.10472 | **5** |
| `full` - shipping | `3D56774E` = pi/60 | 0.05236 | **2** |

Same turns in the same real time, and the bob's span is 4.0000 in both - the
amplitude never changed. No regression: dash 0.988, launched-opponent coast
0.985, unchanged.

### The lesson worth keeping

Three separate sweeps of the model reported it clean, and all three were correct
about the state they were run in. **A negative result from a synthesized
situation only rules out what that situation actually exercises**, and the cost of
finding out was two fixes that were real defects but were not the reported one.
When the user can put the game in the situation, take the save state from them
rather than building an approximation of it.

## 2026-09-05 - MILESTONE: the hovering idle is fixed, confirmed in play

> that worked, this is a milestone

The hover bob group is confirmed by the user in normal play, not only by
measurement. That matters because two fixes before it measured correct and were
real defects, and neither was the thing being reported - **a patch is not
confirmed until the person who reported the symptom says the symptom is gone.**

### Where the patch stands

Thirteen groups ship. Every one is verified against the unpatched 30fps game as
its own oracle - same save state, same input, same number of vsyncs.

| group | what it fixes | confirmed |
|---|---|---|
| battle | the battle loop stride, 30 -> 60 | in play |
| animation clock | animation time itself, seven hook sites | in play |
| input repeat timing | menu auto-repeat delay and rate | in play |
| input timing | the 128 per-button frame counters | in play |
| aura update rate | the ki aura, advanced every other frame | in play |
| effect rotation | the four per-tick phase rates behind swirls | measured |
| airborne motion | directed travel: flight, dashes, knockback | in play |
| airborne vertical | rising and falling | in play |
| airborne residual | the post-hit slide and its decay | in play |
| gravity | the fall acceleration and the step it drives | in play |
| tween duration | every ease, pulse, fade and blend in the game | measured |
| particle update rate | aura and trail particle lifetimes | measured |
| **hover bob** | **the airborne idle's rise and fall** | **in play** |

Two groups stay in the repo pnach and never ship: `animation rate`, superseded by
`animation clock`, and `EXPERIMENT halve root motion`, which deliberately breaks
ground movement. `tools/export.py` strips both.

### The save states, and which one is worth keeping

| slot | what it holds |
|---|---|
| 1 | the hand-made ground state, never overwritten |
| 2 | the opponent launched and flying |
| 3, 4 | synthesized airborne hovers - **the crouched flight pose, not the hover idle** |
| **5** | **the user's own session, captured live while hovering** |

Slot 5 is the only state that contains the real hovering idle, and it is the one
that made the bob findable. `roo.savestate` works on a running VM, so capturing
the user's situation costs nothing and beats approximating it. Slots 3 and 4 are
kept only as a reminder of what a synthesized situation does and does not
exercise.

### What is still open

- **About 70 float words in the effect region** still reverse roughly twice as
  often, spread across `0198F000`-`01995000` with no dominant cluster. Several
  step *less* at 60fps than at 30, so that count is an upper bound and part of it
  is noise. There is no second obvious particle pool.
- **Circling sideways at 0.803 cruise**, from an earlier session. The next step
  written down there still stands: watchpoint whatever `FUN_001DAC78(fighter,
  0xE)` reads.
- Nothing else is reported broken in play.

### Working notes for whoever picks this up

- **Commit after each verified step.** Two power cuts during this session each
  destroyed a running emulator instance. Save states and the repo survive; a
  four-minute RAM sweep in progress does not.
- **One driver at a time.** The emulator serves a single client; a background
  sweep and a foreground experiment will fight over it and both will be wrong.
- **A `patch=1` line is re-applied every frame.** Poking the stock value back
  into a patched address does not disable the group - it is overwritten on the
  next frame. Use `patchctl` with an explicit group list instead.
- **`$gp` reads zero wherever the VM pauses**, so gp-relative constants cannot be
  resolved from the register. Measure the value and scan for it, then confirm
  which copy by halving each in turn.

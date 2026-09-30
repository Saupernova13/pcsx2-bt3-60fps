# Method

How this patch was made, and how to make more of it.

## The guide

The workflow follows Red-tv141's PCSX2 forums guide -
[AI-Assisted 60fps Patch Development for PS2 Games](https://forums.pcsx2.net/Thread-GUIDE-AI-Assisted-60fps-Patch-Development-for-PS2-Games-%E2%80%94-Full-Workflow) -
Ghidra static analysis, systematic isolation testing, and a two-role
Analyst/Implementer loop. The guide is not reproduced in this repo; the thread
is the source. The companion toolset lives at
[github.com/Red-tv141/PS2_Scoring_Radar](https://github.com/Red-tv141/PS2_Scoring_Radar).

## The three legs

1. **Static analysis.** Ghidra (EE extension) plus `ps2ee.disasm` find the
   per-frame routine and its eight call sites, and show that BT3 has no master
   framerate variable: every site hardcodes its vblank stride. The patch is one
   word per site, not a global branch kill - see
   [Why the obvious patch does not work](#why-the-obvious-patch-does-not-work).

2. **Isolation testing.** Neutralise one call at a time and watch what breaks
   (`tools/gate.py`, `tools/probe-loop.py`, `tools/sweep.py`). Gating beats
   nopping: it answers "does this subsystem drive the *speed* of what I am
   looking at", which is the question for a 60fps patch.

3. **The oracle A/B.** Every candidate is scored against the unpatched 30fps
   game as its own oracle - same save state, same input, same number of
   vsyncs. `tools/patchctl.py` switches between the arms without a reboot.

## Why the obvious patch does not work

The 60fps code in circulation forces one branch:

    patch=1,EE,20264DBC,extended,10000008    // skip the vblank wait loop
    patch=1,EE,201DCB40,extended,3C013F80    // halve one step multiplier (2.0 -> 1.0)

That removes the frame limiter for *every* game loop at once while compensating
exactly one timestep constant. Everything else the loop drives - physics, ki and
gauge fill, blast and combo timing, stun, AI cadence - still advances a full
30fps step per iteration and therefore runs at double speed.

BT3 has no master framerate variable. Its per-frame routine takes a vblank
stride as an argument, and all eight call sites hardcode it (`addiu $a0, $zero,
2` for 30fps, `1` for 60fps). So the right lever is a one-word change at the
specific loop being converted. The full table is in
[`findings/`](findings/README.md).

## How a patch is written

Patches are authored as **MIPS assembly with hook declarations**, never as
hand-encoded hex. `ps2ee.asm` assembles with keystone, places code in the safe
zone at `0x000F0000`, and computes the hook jumps:

```python
from ps2ee import PatchBuilder, Trampoline

b = PatchBuilder()
b.trampoline(Trampoline(
    hook_at=0x001DCB40,
    comment="halve the 2.0 step multiplier",
    body="""
        lui   $at, 0x3F00      # 0.5f
        mtc1  $at, $f12
        ld    $s0, 0($sp)
        j     0x001DCB48
        nop
    """,
))
print("\n".join(b.to_pnach()))
```

Delay slots are yours to fill - the assembler runs with `.set noreorder`, so
nothing is reordered and no nop is inserted behind your back.

`Pnach.validate()` runs before every deploy and rejects writes outside `.text`,
`.data` and the safe zone, unaligned word writes, dangling E-code conditions,
and two groups writing the same address.

## The four rules that cost the most

1. **Load the state, then apply, then run - never load again after applying.**
   The save states were captured while patched, so a second load silently
   restores the patched words and the "unpatched" arm is not unpatched.
2. **A paused VM queues screenshots instead of losing them.** `frame_advance(1)`
   flushes them, so a `screenshot, frame_advance(1)` loop gives a film as
   deterministic as memory - one vsync per sample, aligned between arms.
3. **A new group name needs a restart, and the enabled list is PCSXROO's own**
   (`<pcsxroo>/bin/gamesettings/SLUS-21678_428113C2.ini`), not the installed
   PCSX2's. A group missing from that list applies nothing and reports nothing.
4. **Shrinking a live group needs a restart too** - dropped hooks stay patched
   in RAM with nothing left to restore them.

## Driving the machine

The four rules above are the ones that cost the most *thinking*. The ones that
cost the most *time* are mechanical - a screenshot path that silently writes
nothing, a menu press too short to be sampled, a save state slot that accepts a
write it will not read back. They are all in [`rig.md`](rig.md), together with
how to reach any character and stage by driving the game's own menus, which is
what makes a report about a particular fighter on a particular map testable at
all.

## What shipped

Per-build confidence: [`status.md`](status.md).
The full derivation of every group: [`docs/findings/`](findings/README.md).

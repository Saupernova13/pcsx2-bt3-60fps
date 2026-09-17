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
   word per site, not a global branch kill - see the README's "Why the obvious
   patch does not work".

2. **Isolation testing.** Neutralise one call at a time and watch what breaks
   (`tools/gate.py`, `tools/probe-loop.py`, `tools/sweep.py`). Gating beats
   nopping: it answers "does this subsystem drive the *speed* of what I am
   looking at", which is the question for a 60fps patch.

3. **The oracle A/B.** Every candidate is scored against the unpatched 30fps
   game as its own oracle - same save state, same input, same number of
   vsyncs. `tools/patchctl.py` switches between the arms without a reboot.

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

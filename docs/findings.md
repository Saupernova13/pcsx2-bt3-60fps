# BT3 60fps - findings log

Running record of everything established about Dragon Ball Z: Budokai Tenkaichi 3
(SLUS-21678, CRC 428113C2). Shared memory between the Analyst and Interpreter roles.
Newest sections at the bottom.

Scope agreed 2026-08-21: **battles only**. Movement, ki, combos, dashes, blast timing,
stun, gauges and AI must be correct at 60fps. Menus, world map and non-battle cutscenes
may stay at 30fps or be locked back to 30 with E-codes.

---

## Environment

| | |
|---|---|
| PCSX2 | 2.7.419, portable, `%APPDATA%\EmuDeck\Emulators\PCSX2-Qt` |
| Disc | `G:\Emulation\roms\ps2\DragonBall Z - Budokai Tenkaichi 3 (USA) (En,Ja).cso` |
| Boot ELF | `SLUS_216.78`, 2,115,684 bytes, LBA 308 |
| Ghidra | 12.1.3 at `C:\Utils\ghidra`, JDK 21.0.12.1, EE-reloaded 2.1.36 (12.1.2 build, version-bumped) |
| Reference state | slot 1, mid-battle SSJ Goku vs Frieza, 10 hits / 8430 damage |
| PINE | enabled, 127.0.0.1:28011 |

Active PCSX2 settings for this game: `Widescreen 16:9` patch on, `EnableCheats = true`,
GS user hacks and texture replacements on. None of these were changed.

---

## Memory layout

Confirmed by diffing the loaded ELF against live EE RAM from the battle save state.

| Region | Range | Notes |
|---|---|---|
| `.text` | `00100000` - `002C33C0` | 1,848,256 bytes |
| `.data` | `002C3400` - `002FF16E` | 245,102 bytes file-backed |
| `.bss` end | `00334BF8` | |
| Safe zone | `000F0000` | 8 KB verified zero-filled in the battle state |

**ELF addresses are pnach addresses, verbatim.** The ELF loads at `00100000` with no
rebasing, no overlays and no self-modifying code, so a Ghidra address can be pasted
straight into a `patch=` line.

Diff of loaded ELF vs live RAM: **exactly one differing byte in `.text`**, at `00130BF0`
(`3C013F40` -> `3C013F10`). That is PCSX2's own bundled widescreen hack, not the game. The
remaining ~6,890 differences all sit in `.data`, which is mutable state as expected.

---

## The pre-existing 60fps code

Found in `cheats\428113C2.pnach`, present but not enabled. Preserved as
`patches/exp/000-baseline-broken.pnach`.

    patch=1,EE,20264DBC,extended,10000008
    patch=1,EE,201DCB40,extended,3C013F80

### Site 1 - `00264DBC`, the frame limiter

Function entry `00264D98`. Original code:

    00264D98  27BDFFE0  addiu $sp, $sp, -0x20
    00264D9C  8F83AEB8  lw    $v1, -0x5148($gp)     ; global vblank counter
    00264DA4  0080882D  move  $s1, $a0              ; a0 = target vblank count
    00264DAC  2630FFFF  addiu $s0, $s1, -1          ; s0 = target - 1
    00264DB0  0070102B  sltu  $v0, $v1, $s0
    00264DBC  10400008  beqz  $v0, 0x264DE0         ; <-- patched
    00264DC0  0000902D  move  $s2, $zero
    00264DC4  24120001  addiu $s2, $zero, 1
    00264DC8  0C09B8A4  jal   0x26E290              ; wait / vsync
    00264DD0  8F83AEB8  lw    $v1, -0x5148($gp)
    00264DD4  0070102B  sltu  $v0, $v1, $s0
    00264DD8  1440FFFB  bnez  $v0, 0x264DC8         ; spin while counter < target-1

This is the frame pacer: spin until a global vblank counter reaches `target - 1`. The
patch writes `10000008` = `beq $zero, $zero, 0x264DE0`, making the branch unconditional
and **skipping the wait loop entirely**. That is what unlocks the frame rate.

Callers: exactly one, `jal 0x264D98` at `001020C0`, with `$a0 = $s0`, where `$s0` is a
parameter of the enclosing function starting at `00102034`. That function has **zero
direct callers** - it is dispatched indirectly, the guide's "0 callers group".

The enclosing function is the main frame routine. Immediately after the pacing call:

    001020C4  3C100033  lui   $s0, 0x33
    001020C8  26101B30  addiu $s0, $s0, 0x1B30      ; s0 = 0x00331B30
    001020CC  8E030234  lw    $v1, 0x234($s0)       ; frame counter @ 0x00331D64
    001020D4  8E020230  lw    $v0, 0x230($s0)
    001020D8  24630001  addiu $v1, $v1, 1
    001020DC  2C420001  sltiu $v0, $v0, 1
    001020E0  AE030234  sw    $v1, 0x234($s0)       ; counter++
    001020E4  AE020230  sw    $v0, 0x230($s0)       ; flag = !flag

**`0x00331D64` is a per-main-loop frame counter.** Sampling its rate over PINE measures
how fast game logic is actually stepping - `tools/live.py fps` does exactly this. This is
the cleanest available ground truth for the 30-vs-60 question.

**`0x00331D60` is a companion boolean** toggled from the same block. Worth watching: a
0/1 alternation is exactly the shape of an every-other-frame gate.

### Site 2 - `001DCB40`, a step multiplier

Function entry `001DCB20`:

    001DCB20  44806000  mtc1  $zero, $f12           ; f12 = 0.0
    001DCB24  27BDFFF0  addiu $sp, $sp, -0x10
    001DCB30  0C071134  jal   0x1C44D0              ; call with f12 = 0.0
    001DCB34  0080802D  move  $s0, $a0
    001DCB3C  0200202D  move  $a0, $s0
    001DCB40  3C014000  lui   $at, 0x4000           ; <-- patched; 0x40000000 = float 2.0
    001DCB44  44816000  mtc1  $at, $f12
    001DCB4C  0807113E  j     0x1C44F8              ; tail call with f12 = 2.0

The patch changes the constant to `0x3F800000` = float `1.0`, halving the advance passed
into `0x1C44F8`. Standard 30-to-60 compensation for one system.

Callers of `001DCB20`: one, at `001DCB64`, inside the function starting `001DCB58`, which
calls `001DCB20` then `0x1E23D0`.

### Why the baseline breaks the game

The limiter removal at site 1 is global - the whole main loop runs twice as often. Only
one timestep constant (site 2) was compensated. Everything else the main loop drives -
physics, ki and gauge fill, blast and combo timing, stun duration, AI cadence, camera -
still advances a full 30fps step per iteration and therefore runs at 2x.

This matches the reported symptom exactly and is the problem the rest of this log tracks.

---

## The frame routine and the real stride control

Ghidra decompilation of the two functions involved.

`FUN_00264D98` - the pacer:

```c
void WaitVBlanks(uint target)
{
  bool waited = false;
  if (vblank_counter < target - 1) {
    waited = true;
    do { VSyncish_0026E290(); } while (vblank_counter < target - 1);
  }
  if ((vblank_counter < target) || (!waited)) {
    VSyncish_0026E290();
  }
  vblank_counter = 0;          // sw zero, -0x5148(gp) at 00264E0C
  return;
}
```

`FUN_00102060` - the per-frame routine, which receives the same stride and forwards it:

```c
void FrameStep(uint stride)
{
  FUN_00252F10();
  FUN_0023D160(stride);
  FUN_00267DC0();
  FUN_00268208();
  FUN_00263030(0x3347A0, 0x80404040);
  FUN_002630A0();
  FUN_00121DE0();
  FUN_00293738(0, 0);
  WaitVBlanks(stride);                              // 001020C0
  DAT_00331D64 = DAT_00331D64 + 1;                  // frame counter
  DAT_00331D60 = (uint)(DAT_00331D60 == 0);         // alternating 0/1 flag
  FUN_00293640(0x331B30, DAT_00331D64);
  FUN_00101E58(DAT_00331D60, 1);
  FUN_00293738(0, 0);
}
```

Two useful globals fall out of this:

- **`0x00331D64`** - increments once per `FrameStep`. Sampling its rate over PINE is the
  ground truth for how fast game logic is stepping (`tools/live.py fps`).
- **`0x00331D60`** - flips 0/1 every `FrameStep`. The game already maintains an
  every-other-frame flag, which is exactly the primitive a run-one-skip-one fix needs.
  Prefer this over allocating a toggle in the safe zone.

### There is no master framerate variable - the stride is per-call-site

`FrameStep` has eight call sites, and every one loads the stride as a hardcoded immediate
in the delay slot:

| Call site | Enclosing function | Instruction | Stride | Implied rate |
|---|---|---|---|---|
| `00125ECC` | `00125CF0` | `addiu $a0, $zero, 2` | 2 | 30fps |
| `00125F44` | `00125CF0` | `addiu $a0, $zero, 1` | 1 | 60fps |
| `00125F5C` | `00125CF0` | `addiu $a0, $zero, 1` | 1 | 60fps |
| `0012BCE0` | `0012BBD0` | `addiu $a0, $zero, 2` | 2 | 30fps |
| `002636A4` | `002635B0` | `addiu $a0, $zero, 2` | 2 | 30fps |
| `00264A00` | `002649A4` | `addiu $a0, $zero, 2` | 2 | 30fps |
| `002BEAD0` | `002BEA44` | `addiu $a0, $zero, 2` | 2 | 30fps |
| `002BF65C` | `002BF588` | `addiu $a0, $zero, 1` | 1 | 60fps |

This is the single most important fact so far, and it reframes the whole patch.

**The baseline patch is a sledgehammer.** Forcing the branch at `00264DBC` removes the
wait for *every* one of these loops at once - battle, menus, loading, everything - and
gives no way to treat them differently.

**The surgical alternative** is a one-word write per loop:

    addiu $a0, $zero, 2   ->   addiu $a0, $zero, 1
    24040002              ->   24040001

Flipping a single stride-2 site converts exactly that loop to 60fps and leaves the other
seven untouched. That gives a per-mode switch for free, which is precisely what a
battles-only scope wants, and it makes bisecting which loop is which trivial.

Note the guide's Dark Cloud 2 example expected a master controller behind a conditional
write. BT3 does not have one; the equivalent leverage here is the call-site immediate.

### The battle loop is `0012BBD0`, and it runs at 30fps

Resolved statically, no in-game testing needed. Every `jal FrameStep` leaves a return
address of `call + 8` on the stack, so the live call chain at the moment the mid-battle
save state was taken can simply be read out of EE RAM. Searching for each candidate's
return address found exactly one, at `0x01FFED08` - top of RAM, where the EE stack lives.

The surrounding stack window is a clean call chain, oldest frame at the highest address:

    01FFED50  00100240   boot
    01FFED40  00100270
    01FFED38  00100638
    01FFED30  00100640
    01FFED28  0012BD34   FUN_0012BD0C
    01FFED08  0012BCE8   FUN_0012BBD0    <- battle loop, calls FrameStep(2)
    01FFECF8  001020C8   FUN_00102060    FrameStep
    01FFECD0  00264DFC   FUN_00264D98    WaitVBlanks, inside the vsync call

So the chain during a fight is:

    boot -> 0012BD0C -> 0012BBD0 -> FrameStep(stride=2) -> WaitVBlanks(2) -> 0026E290

**Battle is a 30fps loop.** The minimal, surgical unlock is therefore one word:

    patch=1,EE,0012BCE4,extended,24040001    // addiu a0,zero,2 -> 1

This converts only the battle loop and leaves menus, loading and every other mode at
their original rate - unlike the baseline, which removes the wait for all eight loops.

Shipped as `Probe 2` in `patches/exp/001-stride-probe.pnach`. It is expected to double
the speed of battle logic exactly as the baseline does; the point is that it does so in a
controlled, isolated way, and gives a clean starting point for compensating the systems
that loop drives.

This technique generalises. Any time we need to know which loop is live in a given mode,
take a save state there and search for the eight return addresses.

---

## Open questions

1. What are the three existing stride-1 loops? If one of them is already a 60fps battle
   path, some systems may already be frame-rate aware and must not be halved twice.
2. What is `FUN_001C44F8`, and which system does its `f12` step drive? The baseline's
   second patch halves that constant, so it matters whether it belongs to the battle loop.
3. Which of the 156 `lui ..., 0x4000` (float 2.0) sites sit inside per-frame battle code?
   Scope with `tools/radar.py --near <loop> --group` once question 1 is answered.

## Radar baseline

Unscoped scan of `.text` for frame-pacing constants (`tools/radar.py`):

| Count | Constant |
|---|---|
| 5852 | integer 1 |
| 2007 | integer 2 |
| 1432 | float 1.0 |
| 319 | float 0.5 |
| 156 | float 2.0 |
| 145 | float 30.0 |
| 115 | integer 30 |
| 45 | integer 60 |
| 22 | float 60.0 |

Far too broad to act on directly, which is why the guide scopes the scoring pass to the
main gameplay loop. Use `--near` and `--group`, or the Ghidra script's call-graph scoping.

---

## Test 1 - Probe 2 in game (2026-08-22)

Deployed `Probe 2` (`0012BCE4` = `24040001`). User report:

- Battle runs at 60fps.
- **Everything in the fight is double speed** - fight logic and animations both.
- Music is normal speed. Sound effects *seem* faster but that is almost certainly
  because they are being triggered twice as often, not played faster.
- Menus are normal. Quitting to the main menu gives completely normal speed,
  animations and audio.

This confirms the model exactly:

1. The call-site stride is the right lever - the change is surgical and menus are
   genuinely untouched, which the baseline patch could never achieve.
2. Audio is SPU-driven and independent of the EE frame rate, so it needs no work.
3. Everything the battle loop drives per iteration is now running twice per unit time.

### What this rules out

**Differential save-state scanning cannot find the bug.** Per-iteration state is
identical at stride 1 and stride 2 - each iteration advances things by the same amount.
The defect is purely that iterations happen twice as often per second. Comparing two
states taken after the same number of iterations shows no difference at all, so the
guide's Section 4 memory-search approach does not apply here as written.

The work is therefore unavoidably: find every per-iteration delta the battle loop drives
and halve it, or gate it to every other iteration.

### Battle loop body

```c
void BattleLoop(void)                       // 0012BBD0
{
  do {
    ctx = GetCtx();                         // 00126EC8
    if (ctx->flags & 0x8000) { FUN_0012B570(); ctx->flags &= ~0x8000; }
    FUN_00263508();
    FUN_00102038();                         // -> 002630B0, 00248F38, 00252EC8
    ctx = GetCtx();
    if ((ctx->flags & 0x100) == 0) { FUN_00257A50(); FUN_00259030(); }
    FUN_001C2AA8();
    FUN_00122A38();
    FUN_00124A70();
    FUN_00125330();
    FUN_00212990();
    FUN_00126FB0();
    FUN_001BB620();
    FUN_001C2A28();
    a = FUN_0012B6E0();  b = FUN_002129B0();  c = FUN_0012AB10();
    if (c == 0 || a == 0) FUN_0012B7F8(); else FUN_0012B9C0();
    FrameStep(2);                           // 0012BCE0, patched to 1
    FUN_00100798();                         // GS display-list swap (pure render)
  } while (b == 0);
}
```

`FUN_00100798` is confirmed to be the GS double-buffer swap - rendering only, no timing.

### Dead ends recorded so far

- **`game_tick` (`0x002FEBC4`)** is 60fps-aware already (`FUN_0023D160` halves it at
  stride 1), but the battle engine never reads it. Its only consumer is `FUN_0023C6C8`,
  a keyframe-table helper with two callers. Not a lever.
- **`f12` float arguments in the battle tree.** 123 sites load 0.5/1.0/2.0/3.0/4.0 into
  `$f12` before a call, but the same callees (`00121F38`, `00121F50`, `001C44F8`) receive
  all five values. These are animation *playback speed multipliers*, not frame deltas.
  Halving them would slow animations down, not correct frame pacing.
- **Blanket float 2.0 halving.** 29 `lui ..., 0x4000` sites sit in the battle tree, but
  most are ordinary arithmetic. Not safe to halve without per-site evidence.

The baseline patch's site `001DCB20` *is* reachable from the battle loop (depth 5), so it
is a genuine battle-path constant - but on the evidence above it is one animation speed
multiplier among many, which is why halving it alone never fixed the game.

### Strategy from here

Two classes of problem need different treatment:

1. **Discrete game logic** - timers, stun, combo windows, gauge and ki fill, AI cadence.
   These want gating to every other iteration. The game already maintains a per-frame
   parity flag at **`0x00331D60`**, which is the natural primitive for a
   run-one-skip-one gate and avoids allocating one in the safe zone.
2. **Continuous motion** - animation and physics advance. These want their delta halved,
   so motion is sampled twice as often at the correct speed. This is what actually buys
   smoothness; gating these would just render 30fps twice.

Next step is to determine which of the battle loop's direct calls advance simulation and
which only render. With PINE that can be tested live by NOP-ing one call at a time and
observing, with no emulator restart between experiments.

### Radar output

`PS2_Scoring_Radar` ran headless (positional script args, not a .properties file):

    analyzeHeadless work/ghidra BT3 -process SLUS_216.78 -noanalysis \
      -scriptPath ghidra/scripts -postScript PS2_Scoring_Radar.java \
      no no 0012bbd0 skip 00264dbc <output path>

2590 targets in `work/radar/radar.txt`, 1068 global hook points, grouped by caller count
with the "0 direct JAL callers" group first as the guide describes. These are
function-disable cheats for bisection, so they are a fallback if the targeted approach
stalls, not the first tool to reach for.

### Profile of the battle loop's direct calls

Each safe-to-disable call profiled by its callee closure (depth 5), sorted by float
density - a proxy for "does this advance continuous motion or just do bookkeeping".

| # | Function | Fns | Bytes | FPU ops | FPU/KB |
|---|---|---|---|---|---|
| 8 | `001C2AA8` | 160 | 20,292 | 730 | 36.8 |
| 14 | `001BB620` | 182 | 28,216 | 854 | 31.0 |
| 20 | `0012B7F8` | 436 | 107,312 | 2534 | 24.2 |
| 19 | `0012B9C0` | 438 | 107,472 | 2534 | 24.1 |
| 9 | `00122A38` | 45 | 7,452 | 117 | 16.1 |
| 12 | `00212990` | 132 | 15,496 | 101 | 6.7 |
| 15 | `001C2A28` | 26 | 3,672 | 16 | 4.5 |
| 3 | `00263508` | 3 | 160 | 0 | 0 |
| 6 | `00257A50` | 23 | 1,920 | 0 | 0 |
| 7 | `00259030` | 59 | 4,340 | 0 | 0 |
| 10 | `00124A70` | 22 | 3,336 | 0 | 0 |
| 11 | `00125330` | 18 | 2,096 | 0 | 0 |
| 13 | `00126FB0` | 26 | 2,152 | 0 | 0 |

`0012B9C0` and `0012B7F8` are the two arms of the loop's if/else and are nearly identical
in size, so they share most of their tree - together they are the fight simulation.

**Working hypothesis.** If `0012B9C0`/`0012B7F8` is discrete game logic and `001C2AA8` /
`001BB620` advance continuous motion, the fix is:

- gate the simulation call to every other iteration, using the game's own parity flag at
  `0x00331D60` rather than a safe-zone toggle
- halve the per-frame deltas inside the motion code

That yields 30Hz logic with 60Hz animation, which is the outcome we want. Gating
everything would just present 30fps twice; halving everything would desynchronise
discrete timers.

Three isolation tests decide it: disable call 19, then 8, then 14, and record what
freezes in each case.

**Risk to verify on first use:** PCSX2's EE recompiler caches translated blocks. A PINE
write into `.text` may not invalidate that cache, in which case live code patching will
appear to do nothing and we fall back to pnach plus a restart per experiment.

---

## Live PINE session (2026-08-22)

### The live channel works

Attached to a running PCSX2 v2.5.274 with the game booted. Two facts established by
experiment, both of which change how testing is done:

**`patch=1` cheats are re-applied every frame.** Writing `24040002` over the deployed
Probe 2 site read back as `24040002` immediately, then `24040001` 1.5s later - PCSX2 had
rewritten it. So a live write cannot override an address a deployed cheat covers.

**Live code patching does take effect** - the recompiler-cache risk noted earlier is not
real. Writing `addiu $a0, $zero, 2` over `move $a0, $s0` at `001020BC` (an address no
cheat touches) dropped the measured logic rate from 59.65 Hz to 29.99 Hz, and restoring
the original brought it back to 59.99 Hz. PCSX2 invalidates on PINE writes.

**Loading a save state wipes live writes**, since it restores EE RAM wholesale. Restart
the fight from the in-game menu instead of reloading a state mid-experiment.

Baseline measurement with Probe 2 active: **59.98 Hz**, confirming stride 1 is in force
and the frame counter at `0x00331D64` is a trustworthy ground truth.

### Test 1 - disable the simulation candidates (calls 19 and 20)

NOPed `0012BCC4` (`jal 0012B9C0`) and `0012BCD8` (`jal 0012B7F8`) together.

Result: **the 3D environment renders completely black**, but the HUD, the 1P PAUSE menu
and the end-battle menu still draw over it, audio continues, and the fight still plays
out to its conclusion - still at double speed.

So `0012B9C0` / `0012B7F8` is the **3D scene renderer**, not the simulation. Its 2534
float operations are geometry transforms and skinning. This inverts the earlier
hypothesis, which had inferred "simulation" from float density alone.

The valuable part of this result: **rendering and game logic are cleanly separable in
this loop**, which is the precondition for any run-one-skip-one design.

### Test 2 - disable call 8 (`001C2AA8`)

Reported as "doubled if not tripled the speed, at 30fps, framerate lower than before,
logic runs faster with no visual benefit, game still plays normally".

Measured: **59.66 Hz with it disabled vs 60.00 Hz with it enabled** - the loop rate did
not change. The simulation did not speed up; motion became coarser, which reads as faster
and choppier. A subjective "it got faster" is not evidence of a rate change, and measuring
caught it.

Decompiled, `FUN_001C2AA8` is a one-shot guarded by bit 0 of `iGpffffa8a4 + 0x10`: it
calls `FUN_001C2858` once and sets the bit. Not a per-frame timestep.

### Dead ends from this session

- **`FUN_001DA970(entity, 2)`**, reached from `001C2A28`'s per-entity loop, looked like a
  stride. It is not: `param_2` is a **group id**, compared against a cached byte and
  passed to `FUN_001DA8B8`, which walks a 317-entry table of group ids copying bitflags
  between three bitmask arrays. Nothing to do with time.
- **The `+2/frame` globals** (`002D33D8`, `002D341C`, `002DE53C`, `002E43FC`) and the
  `+8/frame` one at `002D33C8` are counters inside `FUN_0027B6C0`, which ends in
  `sceSifSetDma`. They are IOP/SIF audio packet counters, not game timing.
- **An earlier heap scan** flagged values at `~0x006E3000` advancing +2/frame. That region
  is a GIF/DMA display list rebuilt every frame (`0x10000000` GIFtags, `0x80808080` fill);
  the matches were coincidence. Do not scan the heap for counters without a linearity
  filter.

### Two tooling bugs found and fixed

- `Scan._region_offsets` masked an exclusive end of `0x02000000` down to 0 with the 32 MB
  segment mask, silently producing an empty scan range and reporting "0 candidates" for
  every query. Now `_offset_of(..., exclusive_end=True)` maps a wrapped-to-zero end to the
  full RAM size, and an empty region raises instead of returning nothing.
- A three-state capture was taken while **the game was paused** at the 1P PAUSE menu, so
  nothing was animating and the scan found only global counters. Caught by extracting
  `Screenshot.png` from the save state and looking at it. **Always confirm the captured
  state is actually in gameplay** - the screenshot in every .p2s makes this free.
  `work/autocapture.py` now watches for memory churn across `.data`/`.bss` and only
  captures once real activity is detected.

---

## MILESTONE - working 60fps battle patch (2026-08-22)

**Status: the game plays at correct speed at 60fps, with smoother motion, and menus
behave normally.** Nothing is double speed. Saved as `patches/428113C2.pnach` and
archived as `patches/exp/002-milestone-anim-rate.pnach`.

Two changes, both one-liners in effect:

    patch=1,EE,0012BCE4,extended,24040001    // battle loop stride 2 -> 1
    patch=1,EE,001C450C,extended,0803C010    // animation-rate setter -> safe-zone hook
    // + a six-word trampoline at 000F0040 that halves the value before storing it

### How the animation fix was found

`FUN_001C44F8` is a tiny setter:

```c
void SetAnimRate(float rate)          // 001C44F8
{
    entity = FUN_001DC280();          // current entity
    entity->field_0xC80 = rate;       // swc1 $f20, 0xc80($v0)  @ 001C450C
}
```

with a matching getter `FUN_001C4700`. **`entity + 0xC80` is the animation playback
rate**, and the whole game funnels through those two functions - the offset is touched
from only four instructions in all of `.text`.

Callers pass literal rates: `001DCB40` passes 2.0, `001E3E20`/`001E3E48`/`001E40B0`/
`001E4134` pass 3.0, and so on. Those constants exist because **BT3 animations are
authored at 60Hz and the 30Hz game loop advances them 2 units per tick**. At stride 1 the
loop ticks twice as often, so every rate needs halving.

Rather than patch every caller, the fix hooks the single setter and halves whatever is
written:

    000F0040  3C083F00  lui   $t0, 0x3F00        ; 0.5f
    000F0044  44882000  mtc1  $t0, $f4
    000F0048  4604A102  mul.s $f4, $f20, $f4
    000F004C  E4440C80  swc1  $f4, 0xc80($v0)
    000F0050  08071145  j     0x001C4514
    000F0054  00000000  nop

The hook replaces the `swc1` at `001C450C`. Its delay slot (`001C4510`, `ld $ra, ($sp)`)
still executes before the jump, which is why the trampoline resumes at `001C4514` rather
than `001C4510`.

This is why the original circulating patch never worked: it halved `001DCB40`, which is
**one caller** of this setter, leaving every other animation rate at its 30Hz value.

### Remaining issues, in priority order

1. **Input responsiveness.** Presses are dropped or acknowledged late; sequences needing
   quick succession fail, including a basic grab (double-tap X). The input latch is polled
   once per loop iteration, so every frame-counted input window is now half as long in
   real time. This is guide Section 3 / Example 6 territory. Note the guide's author
   explicitly considers input the weakest part of this method.
2. **Sprite / UV animation still double speed.** Mouth movement in intro sequences, and
   the Kamehameha beam effect, finish early even though the skeletal motion is correct.
   These are almost certainly texture/UV animations on a separate path from `0xC80`. The
   guide warns off texture and UI animation explicitly - treat as lower priority and
   timebox it.
3. **Intermittent drops to 30fps** for a couple of seconds, then recovery, with no change
   in game speed. Most likely inherent: at stride 1 the loop has one vblank to finish, and
   any overrun costs a whole frame. The user reports the same behaviour emulating BT3 on
   ARM hardware, which supports "inherent to running this engine at 60" rather than a
   defect in the patch.

### Register-naming hazard

Keystone assembles MIPS in **n64 register naming**, where `$t1` is register **13**, not 9.
Writing `$t0`/`$t1` in safe-zone code silently targets the wrong registers and produces a
patch that assembles cleanly and behaves randomly. **All safe-zone assembly in this repo
uses numbered registers (`$8`, `$9`, `$2`).** Always disassemble the result and check the
register numbers before trusting a trampoline.

---

## Input subsystem map (2026-08-22)

Located by save-state diffing with the game **paused** while holding X - pausing was the
user's suggestion and it is much cleaner than diffing during play, because almost nothing
else drifts between captures.

### The pad block

Base `0x00333800`, two pad slots at stride `0x1C0`:

| Offset | Address (slot 0) | Held X | Released | Meaning |
|---|---|---|---|---|
| `+0x01C` | `0033381C` | `817FBFFF` | `817FFFFF` | raw libpad word, **active low** (CROSS = `0x4000`) |
| `+0x028` | `00333828` | `000000FF` | `00000000` | pressure / pressed flag |
| `+0x148` | `00333948` | `00004000` | `0` | current buttons, active high |
| `+0x14C` | `0033394C` | `00004000` | `0` | previous buttons |
| `+0x150` | `00333950` | - | - | newly pressed = `current & ~previous` |
| `+0x154` | `00333954` | `00004000` | `0` | auto-repeat result |
| `+0x158` | `00333958` | `1` | `20` | auto-repeat countdown |
| `+0x19C` | `0033399C` | `20` | `20` | initial repeat delay, in frames |
| `+0x1A0` | `003339A0` | - | - | repeat rate, in frames |

`FUN_00122A38` (battle loop call **[9]**) is the pad update: it calls the libpad wrappers
`FUN_00296090` / `FUN_00295FB8`, normalises both analog sticks, folds stick directions
into the button mask as bits `0x10000`-`0x800000`, then computes the edge and repeat
state. It loops over both pads (`i < 2`, `puVar5 += 0x1C0`).

`FUN_002577B0` is the **auto-repeat timer**, not a double-tap detector:

```c
int AutoRepeat(int cur, int newpress, int *counter, int *prev, int delay, int rate)
{
    int out = 0;
    if (cur == *prev) {
        if (cur != 0) {
            if (--(*counter) < 0) { *counter = rate; out = cur; }
            goto end;
        }
        *prev = 0;
    } else *prev = cur;
    *counter = delay;              // 20 frames
end:
    return newpress ? newpress : out;
}
```

Both `delay` and `rate` are frame counts read from memory (`+0x19C`, `+0x1A0`), so menu
repeat runs twice as fast at 60fps. They are set through a setter at `FUN_002577F4`
(`sw $a0, -4($v0)`), which is a clean hook point if we choose to double them.

### FAILED EXPERIMENT - gating the pad update every other frame

Hooked call [9] (`0012BC64`) through a safe-zone trampoline so `FUN_00122A38` ran on
alternate frames only, leaving everything else at 60Hz.

**Result: no improvement to fighting input, and the pause menu became worse - double
speed and unusable.** Reverted.

Why it fails: skipping the update leaves `+0x150` (newly pressed) latched at its previous
value, so a single press is visible as a fresh edge on two consecutive frames and the
60Hz consumer acts on it twice. Slowing the *read* also cannot help a consumer that
counts frames itself - the parser still runs at 60Hz over a now-stale view.

**Conclusion: the input defect is in the consumers, not the pad read.** Any fix must
either slow the consumers' frame counting or widen their frame windows; it must not slow
the pad read.

`FUN_00122DB0` is the accessor other code uses (`FUN_001230A8(pad, DAT_00333948[pad*0x70], out)`),
and it has **zero direct callers** - dispatched indirectly, so the consumers cannot be
found by static xref. Finding them needs a different approach: a write-watch on the
move-buffer, or hooking `FUN_001230A8` and logging callers via `$ra`.

### Still open

- **Double-tap grab and quick sequences.** The move parser is frame-counted and has not
  been located yet. Next step: hook `FUN_001230A8` in the safe zone to record `$ra` into
  a scratch buffer, read it back over PINE, and identify the real consumers.
- **Menu auto-repeat.** Tractable right now by doubling `+0x19C` / `+0x1A0` via the
  `FUN_002577F4` setter. Worth doing as a standalone improvement.
- **Sprite / UV animation** (mouth movement, Kamehameha beam) still runs at double speed.
- **Intermittent 30fps dips**, believed inherent to the frame budget.

### Input API, traced by runtime caller logging

Static xrefs were useless here (the accessors have zero direct callers), so a logging
trampoline was hooked into each accessor: it writes `$ra` into a 64-entry ring at
`0x000F0210`, replays the displaced instruction and jumps back. Reading the ring over
PINE after a couple of seconds names the real callers. `tools/probe-loop.py` style, but
for call sites rather than call gating.

Three sibling accessors, each tail-calling `FUN_001230A8` (`return (mask & test) != 0`):

| Function | Reads | Meaning | Callers observed |
|---|---|---|---|
| `00122DB0` | `+0x148` | `IsHeld(pad, mask)` | **25**, all inside `FUN_002574F0` |
| `00122DE0` | `+0x150` | `IsNewPress(pad, mask)` | **0** |
| `00122E10` | `+0x154` | `IsRepeat(pad, mask)` | **0** |

So the two edge-detecting wrappers are dead code. Everything goes through `IsHeld`, and
only `FUN_002574F0` calls it.

`FUN_002574F0(pad)` is the **input remapper**: it queries ~25 raw bits and folds them into
the game's own action bitmask (CROSS `0x4000` -> internal bit 9 `0x200`, and so on,
including the four analog-stick directions at `0x100000`-`0x800000`). It then maintains
the internal input state at `0x00333988 + pad*0x38`:

```c
prev = internal_cur[pad];
internal_cur[pad]      = cur;
internal_newpress[pad] = cur & ~prev;
internal_repeat[pad]   = AutoRepeat(cur, cur & ~prev, &counter, &prev2, delay, rate);
```

| Address | Meaning | Readers |
|---|---|---|
| `00333988` | internal current | 3 |
| `0033398C` | internal newly-pressed | **42** |
| `00333990` | internal auto-repeat | 3 |
| `0033399C` / `003339A0` | repeat delay (20) / rate (1) | the repeat timer |

### FIXED - menu auto-repeat

`FUN_002577F8` is `SetRepeat(delay, rate)`. Hooking its entry to double both arguments
restores menu scrolling to its real-time speed at 60fps. Confirmed by the user: "whatever
you did last fixed the menu". Now shipped in the patch as the third group.

### Still unsolved - combat input

Quick-succession moves (double-tap X grab, combo strings) remain unreliable. What is now
ruled out:

- It is **not** the pad read rate - gating that made things worse, not better.
- It is **not** `IsNewPress`/`IsRepeat` - those wrappers are never called.
- It is **not** the auto-repeat timer - that is fixed and only affected menus.

The 42 readers of `internal_newpress` are mostly UI code (`00119FB4`-`0011E1E8`), with a
few in gameplay ranges (`002145D4`, `0022F9F8`, `0025B1DC`, `002BE348`). None of them
consult a frame-counted history at the point of read, so the double-tap window must live
further in, in per-character move state rather than the shared input block.

Next approach if this is picked up again: put the logging trampoline on the gameplay-range
readers to find which one runs during a fight, then look for a countdown in the character
struct that resets on a press - the same shape as the `+0x158` repeat counter, but
per-fighter.

# BT3 60fps - findings log

Running record of everything established about Dragon Ball Z: Budokai Tenkaichi 3
(SLUS-21678, CRC 428113C2). Shared memory between the Analyst and Interpreter roles.
Newest sections at the bottom.

## STATE OF PLAY - read this first

**Working, shipped in `patches/428113C2.pnach`, all four groups verified live over PINE
and confirmed by the user:**

| group | what it does |
|---|---|
| `60FPS - battle` | battle loop stride 2 -> 1 at `0012BCE4`. The whole 60fps change |
| `60FPS - animation clock` | halves the animation clock itself in `FUN_0024D410` (supersedes `60FPS - animation rate`, which only halved rates written through `FUN_001C44F8`) |
| `60FPS - input repeat timing` | doubles the menu auto-repeat delay/rate via `FUN_002577F8` |
| `60FPS - input timing` | halves the 128 per-button frame counters in `FUN_001D3C10` |
| `60FPS - aura update rate` | runs the ki aura's update on even frames only while still drawing it every frame, at `FUN_00164860` |
| `60FPS - airborne motion` | halves the displacement and the ramp of `pos += dir * speed`, at `FUN_001DE000` |
| `60FPS - airborne vertical` | the same for `pos.y += vy`, at `FUN_001DED78` |
| `60FPS - airborne residual` | halves the post-hit slide and its decay epsilon, at `FUN_001DFD88` |

Game speed, animation, menus, grabs, combos and quick-succession input are all correct.

**A fifth group, `60FPS - effect rotation`, is also shipped and enabled - and it is
wrong. Revert it.** It was deployed 2026-08-22 without ever being confirmed by the user.
On 2026-08-24 its target was frozen outright (all ten phase stores nopped, phases verified
motionless for 150 frames) and the user reported **no visible change at all**, so it
compensates something invisible. It is also incomplete on its own terms - four of the
eleven per-tick constants in that function. See "The ki aura at 2x" at the bottom.

**Read "The engine has no timestep" further down before anything else.** The
game has no delta anywhere; it is a fixed 30Hz tick loop now ticking at 60Hz, so
*everything* is 2x until it is individually halved. Nothing self-corrects.

**FIXED 2026-09-04: airborne motion.** Three more groups are shipped -
`60FPS - airborne motion`, `60FPS - airborne vertical`, `60FPS - airborne residual`.
Airborne movement never went through the skeleton at all, which is why every attempt
aimed at root motion failed. See "Airborne motion, solved" at the bottom for the full
derivation and the numbers.

The short version: the position round-trip through the root bone is real, and it is how
*ground* movement works, but during a launched flight the root delta is exactly `0.0000`
every tick while the fighter still moves. The airborne displacement comes from three
separate per-tick channels on the fighter itself, all of them uncompensated:

| routine | what it adds per tick |
|---|---|
| `FUN_001DE000` | `pos += dir(+0x90) * speed(+0xA8)` |
| `FUN_001DED78` | `pos.y += vy(+0xAC)` |
| `FUN_001DFD88` | `pos += residual(+0x80)`, then shrinks it by a fixed epsilon |

Each has a *rate* as well as a *value*, and both halves need halving. The first two get
their value from `FUN_001DBFF8(current, target, step)`, a move-toward-by-at-most-step
helper; halving only the applied displacement leaves the ramp and the decay running at
double rate, so a knockback ends in half the real time.

**Do not re-open these, they are settled by measurement, not by argument:**

- **It is step SIZE, not step COUNT.** Call counters on the gameplay path read *identically*
  on the ground and in the air.
- **The ki aura is not a second bug.** It tracks a character whose motion was 2x.
- **The render chain is followers all the way down.** `fighter+0x15A0` <- `model+0x970`
  <- `bone[0]+0x40`. Do not walk it again; it is mapped in full below.
- **Root motion is the ground channel only.** The 2026-09-02 halve-root-motion experiment
  failed because it halved a channel that reads zero in the air.

**Still imperfect:** circling an opponent (holding the stick sideways) now cruises at about
0.80 of its 30fps speed, where before the fix it was 1.91. Its speed ramps toward a target
that is itself evolving, and the target evolves more slowly under the patch. Everything
else measures between 0.95 and 1.05. See the open question at the end of that section.

**FIXED 2026-08-24: the ki aura.** See the milestone at the bottom. The lever was a
pass that runs too often, not a constant - `vtable[0]` in this engine is update AND draw,
so the hook skips the update half on odd frames and falls through to the draw.

**Superseded - the ki aura, now fixed.** It was the user's oldest open report, and the one
previous sessions kept mis-answering with `60FPS - effect rotation`. Proven to be an
uncompensated per-tick quantity by the 30fps oracle; five candidate systems have now been
eliminated by direct visual test. Read "The ki aura at 2x" at the bottom before touching
it, and **do not trust `tools/findmotion.py`** - its sweep detector was blind (see the
same section).

**Two claims elsewhere in this file are now known to be wrong.** "There is no master
framerate variable" - the effect system has a per-model 60fps flag at `model+0xA40` bit 24,
which is never set. "Three `time += rate` sites exist in the whole binary" - there are 620
in-place float accumulates, 74 of them per-tick countdowns.

**Before doing anything, read "Instrument notes for future agents" at the very bottom.**
Two measurement traps in this codebase produce confident wrong answers.

**Never trust a deploy you have not read back.** The pnach silently wrote one byte per
line for its entire existence because `extended` takes its size from the address's top
nibble. `python tools/apply-live.py --check` is the verification step.

---

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

## The patch was never actually applied - `extended` writes ONE BYTE (2026-08-22)

Every line of the shipped pnach had been writing a single byte since the day it
was written. Found by reading the patch sites back over PINE on a cold boot and
comparing them to what the file asks for:

| site | wanted | actually in RAM | |
|---|---|---|---|
| `0012BCE4` | `24040001` | `24040001` | correct **by luck** - only the low byte differs from the original |
| `001C450C` | `0803C010` | `E4540C10` | original `E4540C80` with its low byte overwritten by `10` |
| `002577F8` | `0803C020` | `3C020020` | original `3C020033`, low byte overwritten by `20` |
| `000F0048` | `4604A102` | `00000002` | only `02` landed |
| `000F004C` | `E4440C80` | `00000080` | only `80` landed |

### Why

`extended` does not mean "32-bit write". It selects the raw PS2 cheat-code
format, in which **the top nibble of the address is a size selector and is not
part of the address**: `0` = byte, `1` = halfword, `2` = word. Every address in
this project is a bare EE address beginning with `0`, so every line became a
byte write.

The user's own pre-existing 60fps code had it right all along -
`patch=1,EE,20264DBC,extended,10000008` - and that leading `2` is the whole
difference. It was read as part of the address rather than as a size prefix.

### What that actually did to the game

- **The stride patch worked by coincidence.** `24040002` -> `24040001` differs
  only in the low byte, so the battle loop really did run at 60fps. That is why
  the patch looked half-alive.
- **Neither trampoline ever existed.** The safe zone held a handful of stray
  bytes, never instructions, so the animation halving and the repeat fix were
  simply absent. Hence "everything is 2x" on a cold boot.
- **The byte write corrupted the two hook sites.** `001C450C` went from
  `swc1 $f20, 0xC80($v0)` to `swc1 $f20, 0xC10($v0)`: the animation-rate setter
  was storing into the wrong field of the fighter. Animations that were re-set
  by a cutscene came back right, which is exactly the partial self-correction
  the user described. `002577F8` went from `lui $v0, 0x33` to `lui $v0, 0x20`,
  pointing the repeat setter at the wrong megabyte of RAM - the likely cause of
  the hang after the intro video.

### Why it looked like it worked yesterday

The milestone was validated over **PINE**, which issues genuine 32-bit writes.
The pnach was generated afterwards and deployed, but never verified from a cold
boot. Live-tested is not deployed-tested.

**Rule: after every deploy, read the patch sites back over PINE and compare to
the file.** `Pnach.validate()` now refuses this class of bug outright, and the
deliverable uses type `word`, whose semantics do not depend on the address.

## SOLVED - combat input timing is 128 frame counters (2026-08-22)

Confirmed by the user: "it works! input is better".

Combat never reads the shared input globals at `0x00333988` - it keeps its own
per-fighter copy. `FUN_001D4A70` maintains it at **`fighter+0x570`**:

| offset | meaning |
|---|---|
| `INPUT+0x000` | raw pad buttons, copied from `pad+0x148` |
| `INPUT+0x1CC` / `+0x1DC` | current mask A / B |
| `INPUT+0x1D0` / `+0x1E0` | previous mask A / B |
| `INPUT+0x1D4` / `+0x1E4` | newpress = `cur & ~prev` |
| `INPUT+0x1D8` / `+0x1E8` | released = `prev & ~cur` |

That is why every reader found on the shared globals turned out to be UI.

### The timing system

`FUN_001D4A70` ends by calling `FUN_001D3C40(ring, cur, newpress, released)`
twice - `fighter+0x780` for button set A, `fighter+0x820` for set B. Each ring
is 4 x 32 bytes, and `FUN_001D3C40` loops over all 32 button bits calling
`FUN_001D3C10` four times per bit:

| ring slot | condition | meaning |
|---|---|---|
| `+0x00+bit` | `cur & bit` | frames held |
| `+0x20+bit` | `!(cur & bit)` | frames released |
| `+0x40+bit` | `!(newpress & bit)` | **frames since last press - the double-tap window** |
| `+0x60+bit` | `!(released & bit)` | frames since last release |

```c
void FUN_001D3C10(int cond, signed char *counter)   // 12 instructions
{
    if (cond == 0) { *counter = 0; return; }        // beql, reset in the delay slot
    if (*counter < 100) *counter += 1;              // saturating
}
```

**128 counters, all counting frames.** At 60fps every button window - double
taps, charges, hold detection, combo links - expired in half its real time.
That is why input felt uniformly unresponsive rather than one move being
broken, and it is exactly the frame-window theory, confirmed.

### The fix

One hook. `FUN_001D3C10`'s increment path only runs on even frames, restoring
the original 30Hz counting rate. The **reset is deliberately left alone** so
"pressed this frame" still reads zero immediately - halving that too would have
added a frame of input latency.

Hook at `001D3C18` (`lb $v0, ($a1)`), resume at `001D3C20`.

**Do not hook `001D3C10` itself.** It opens with `beql $a0, zero` whose delay
slot is `sb $zero, ($a1)`. A likely branch executes its delay slot only when
taken; a plain `j` always executes it, so hooking the entry would zero every
counter on every call instead of halving it. `live.delay_slot_hazard()` now
refuses this, and refuses displacing any branch or jump.

### How it was found

Offset-scanning `.text` for struct field offsets produced only false matches -
`0x1470` resolved to a global at `0x002FEC20` holding `0x80808080`, nothing to
do with the fighter. **Offsets are not unique across structs.** What worked was
following the code: `FUN_001DC2A0` (`GetPadForFighter`) led to the fighter's own
input block, whose update function ends in the history recorder.

### Capture technique notes

- A whole-struct read is **1408 words and not atomic**. Samples tagged frame N
  can contain data from N+1, which showed up as nine impossible "two X presses
  one frame apart". Frame-precise conclusions need the narrow `--watch` mode
  (a handful of words per sample); the wide trace is for finding candidates.
- Arm a capture on a real button press. A fixed-timer capture is half over
  before the instructions have been read - the first 60-second trace caught one
  countdown in a whole minute for exactly that reason.
- Save raw captures. Re-analysing offline beats asking the player to replay the
  session for every new hypothesis.

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

## The remaining 2x is AIRBORNE PHYSICS, not effects (2026-08-22)

> **PARTLY SUPERSEDED (2026-09-02).** "Position integrated per loop iteration" was a
> guess and no such integrator exists. The correct/wrong table at the top is still right.


The user's observation that reframed it: **everything wrong is in the air.**

| correct | wrong |
|---|---|
| ground idle | air idle |
| general fighting, grabs, rush blasts | knockback flight after a heavy smash |
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
correct.** Air idle, knockback flight after a heavy smash, falling after a stun, ki blast
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

## Instrument notes for future agents

**Two measurement traps cost real time in this session. Both produce confident wrong
answers.**

1. **Whole-struct captures tear.** A fighter is 1408 words and PINE cannot read it
   atomically, so a sample tagged frame N can contain data from N+1. This produced
   (a) nine impossible "two X presses one frame apart", and (b) a completely bogus
   "+2 per frame" reading on counters that actually step +1 - dropped frames made
   consecutive samples two game frames apart. **Frame-precise conclusions require the
   narrow `--watch` mode** (a handful of words per sample). The wide `--trace` is for
   finding candidates only.
2. **Offsets are not unique across structs.** Scanning `.text` for `lw rX, 0x1470(rY)`
   found a global at `0x002FEC20` holding `0x80808080`, nothing to do with the fighter.
   Match the whole *idiom* instead (load / add immediate / store back to the same
   offset), or confirm the base register's provenance.

Other hard-won rules:

- **Arm captures on a real button press** (`--armed`). A fixed-timer capture is half over
  before the instructions have been read; the first 60-second trace caught one countdown
  in an entire minute for exactly that reason.
- **Save raw captures** (`--save`, then `tools/countdown.py`). Re-analysing offline beats
  asking the player to replay a session for every new hypothesis.
- **Verify a deploy by reading it back over PINE.** See the `extended` byte-write section:
  the patch was silently writing one byte per line for its entire existence.
- **`ps2ee/live.py` refuses branches and likely-branch delay slots.** Trust it. Hooking
  `FUN_001D3C10`'s `beql` entry would have zeroed every input counter instead of halving
  them, and hooking function prologues at random is what crashed the emulator earlier.
- **Revert anything the user has not confirmed.** Three effect experiments and the
  smoothing constant were all backed out; `tools/apply-live.py --check` plus a stock-value
  check on the experiment sites is how the tree was left clean.

## The engine has no timestep - what "2x" actually means (2026-08-22)

This supersedes the earlier framing of `0012BCE4` as a "battle loop stride".

`0012BCE4` is not a stride. It is the **delay slot of `jal 0x102060`**:

```
0012BCE0  jal   0x102060
0012BCE4  addiu $a0, $zero, 2      <- our patch makes this 1
```

`FUN_00102060(n)` is the end-of-frame routine: it presents, waits **n vblanks**
(passing `n` on to `FUN_0023D160` and `FUN_00264D98` - the same `0x00264DBC`
the circulating patch pokes), and bumps the frame counter at `0x00331D64`.

So the change is purely "wait one field instead of two". **Nothing in the game
receives a timestep.** Proof: the data segment contains no `1/30`, `1/60`,
`30.0` or `60.0` float anywhere (`work/findconst.py`). `FUN_0012BBD0` is a flat
list of about twenty subsystem `jal`s with no delta argument between them.

**Therefore every per-tick quantity in the game runs at 2x real speed, and the
only things that are correct are the ones we have explicitly halved.** Nothing
self-corrects. This is the single most important fact for anyone continuing.

### What that makes the remaining work

| symptom | class | fixed by |
|---|---|---|
| overall pacing | vblank wait | shipped |
| skeletal animation | `time += rate` | shipped |
| input windows | `n++` per tick | shipped |
| menu auto-repeat | `n++` per tick | shipped |
| aura, impact effects | animation clock on non-fighter models | `60FPS - animation clock` |
| ki blast + beam travel | procedural motion | open |
| beam duration | `n--` per tick | open |
| airborne motion, knockback, falling | procedural motion | open |
| camera convergence (`FUN_00122168`) | per-tick lerp | open, nobody has complained |

### Battle-loop subsystem map

`work/subsystems.py` walks the call tree under each top-level `jal`:

| call | fns | contains |
|---|---|---|
| `0012B570` | 737 | input, camera, 3 effect fns |
| `001C2AA8` | 251 | input, camera, 3 effect fns |
| `00212990` | 230 | Vec4Add, 1 effect fn |
| `001BB620` | 213 | Vec4Add, 6 effect fns |
| **`0012B6E0`** | **1005** | **physics, input, camera, 20 effect fns - the gameplay update** |
| `0012B9C0` / `0012B7F8` | 487 / 438 | the two branches of the round-state check |
| `00102060` | 198 | present + vblank wait |

## The animation system, fully mapped

The controller lives at **`model + 0xB40`**:

| field | meaning |
|---|---|
| `+0x004` | length, in animation frames (float) |
| `+0x134` | mode: 0 stopped, 1 play-once, 2 loop |
| `+0x138` | current time (float) |
| `+0x13C` | previous time (float) |
| `+0x140` | rate, frames advanced per tick - this is `model+0xC80` |

**BT3's animations are authored at 60Hz and the stock rate is `2.0`.** Live proof
with the shipped patch on: `time=20.0 prev=19.0 rate=1.0` - our setter hook has
already turned the stock 2.0 into 1.0, and the step really is one frame per tick.

`FUN_0024D410(model)` is the clock. Three `time += rate` sites exist in the whole
binary and there are no others:

| site | which |
|---|---|
| `0024D448` | play-once (clamps to length, then sets mode 0) |
| `0024D478` | loop (wraps to 0) |
| `001D37C8` | the `entity+0x1330` channel, `FUN_001D378C` |

Only four instructions touch `+0xC80` at all: the setter `001C450C` (what we
hooked), a second setter at `0024D034`, and two getters `001C4710` / `00207CA0`.

### Why the clock beats the setter

`[60FPS - animation rate]` only halves rates that something explicitly writes
through `FUN_001C44F8`. A model whose rate is defaulted, or written by the other
setter, keeps its stock value and runs at 2x - which is the likely cause of
"the aura is always double speed even when the character animates correctly".

Halving at the clock is correct **whatever the authored rate is**: a 2.0 model
runs 120 anim-frames/s at 60Hz instead of 60, and a 1.0 model runs 60 instead of
30. Both are exactly 2x, so both want the same halved step.

`[60FPS - animation clock]` hooks all three step sites, plus both getters so the
three call sites that read the rate still observe the old halved value.
**Enable one group or the other, never both** - together they give quarter speed.

## Bounding the motion search

Two scans that had not been done, both of which shrink the remaining problem:

- `work/vecacc.py` - `Vec4Add`/`Vec3Add` calls where destination == first source,
  i.e. the `x += y` idiom, scoped to the 1042 functions under `0012B6E0`.
  **Only 17 exist**, in `001C6920`, `001D6580`, `001D6C08`, `001DF210`,
  `0024A4B8`, `00250DE8` (5) and `00251A48` (6). The ones checked so far
  accumulate into stack temporaries via the matrix library, so they are camera
  or spline code, not entity motion.
- `work/vuacc.py` - a hand-written R5900 COP2 decoder looking for in-place
  `lqc2 ... sqc2` on the same struct field. **There are none.** All twelve hits
  are the 4x4 matrix load/store helpers at `00120B80`, `001212D8`, `0012136C`
  and `00121404`. So no motion is integrated in inline SIMD; it all goes through
  the six-function vector library by pointer, and capstone's COP2 blind spot
  does not hide an integrator after all.

`model+0x970` is never written by a `sw`/`sqc2` in gameplay code - the only
`addiu rX, rY, 0x970` sites that pass it as a destination are the model
initialiser `FUN_0024E238` and the copy at `FUN_001D7414`. It is written through
a pointer handed to the vector library, so a runtime write breakpoint is still
the only way to catch the writer.

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

## A/B-ing a shipped `patch=1` group on a live game (2026-08-25)

The aura fix is now confirmed by direct comparison, not just by "it looks right": with the
patch neutralised the user saw the 2x aura return, and restoring it brought the correct
speed back. **User-confirmed: "the patch definitely worked."**

Getting there needed a technique worth keeping, because the obvious approach does not work.

### You cannot disable a `patch=1` group by poking memory

`patch=1` means PCSX2 re-applies the group **every frame**. Writing the stock instruction
back over `00164888` succeeds - and is overwritten within two frames. Measured, not assumed.
Editing the pnach does not help either without a patch reload, which costs the battle.

### Jump over the hook from an address the cheat engine does not own

The cheat engine only rewrites the words the group lists. Everything else is ours. So hook
*earlier* in the same function and jump past the patched instruction entirely:

    00164880  j 000F0800          (was: sd $s5, 0x28($sp))
    00164884  sd $ra, 0x38($sp)   delay slot, runs as normal
    000F0800  sd $s5, 0x28($sp)   replay displaced
    000F0804  lw $s2, 0x38($s6)   what 00164888 held before the patch
    000F0808  addiu $s3,$s2,0x64  0016488C
    000F080C  ...bump a pass counter at 000F0830...
    000F081C  j 00164890          full update, unconditionally

`00164888` stays patched and keeps being re-applied; it is simply never reached.
`work/aurabypass.py` does this with `--off` / `--on`.

**The displaced instruction runs after the delay slot, not before it.** That reorder is only
safe here because `00164880`/`00164884` are independent register saves. Check that before
picking a hook site.

### Make the probe self-verifying

The trampoline bumps a counter so the state is a measurement, not an opinion:
**120 passes/sec at 60Hz** with the bypass in - two aura nodes, one per fighter, each
advancing every frame, which is exactly the original bug. With the patch in force it is 60.
A reading of 0 means the aura is not on screen and the test is telling you nothing - worth
checking before asking the user to judge anything.

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

## 2026-09-04 - PCSXROO: the emulator became scriptable

Every earlier session drove PCSX2 through PINE, which can read and write memory and
nothing else. Breakpoints meant asking the user to set them in the GUI and read the
registers back by screenshot; getting into a fight meant asking the user to play; testing
a patch meant a full quit and relaunch, because PCSX2 reads its cheat file only at boot.

`Documents/GitHub/pcsxroo` is a PCSX2 fork that exposes the whole debugger over a loopback
JSON socket. Read `docs/pcsxroo/agent-guide.md` there first. What it changes for this
project:

- **Breakpoints and watchpoints without a human.** `mc add --on write` plus the stop's
  `pc` and `ra` is the technique that solved this, and `tools/writers.py` wraps it.
- **Frame-precise capture.** `frame-advance 1` steps exactly one vsync, so a per-frame
  delta is a real per-frame delta. Every earlier capture polled a frame counter over PINE
  and lost frames on any host hiccup, which silently halves the quantity being measured.
- **`patch.reload` re-reads the pnach files**, so a patch experiment costs seconds instead
  of a reboot.
- **Input injection**, so the harness can create the situation it wants to measure - a
  launched opponent, a sustained flight - reproducibly.
- **Screenshots**, which are the only way to be sure the numbers describe the situation
  you think they do.

`ps2ee/roo.py` is the client. Three of its wrappers exist because the raw behaviour
silently corrupts experiments, and each cost a wrong conclusion before being found:

1. **`loadstate` pauses first.** A load into a running VM leaves the game executing while
   the reply comes back, and the number of frames lost that way varies per call. Two runs
   of one experiment then start from different states. Loading into a paused VM restores
   bit-identically - verified by loading three times and comparing positions.
2. **`input.release` only queues.** The hook that writes the pad runs on frames the VM
   executes, so a release issued while paused never lands. The *next* state load then
   starts with the previous test's button held for one frame, which is enough to throw a
   punch. `flush_input()` releases and advances, and it has to be called **before** the
   load, not after - the contaminated frame is the first frame after the restore. This
   produced a reference measurement 65% too large, once, silently.
3. **`screenshot` needs a backslash path.** A forward-slash path is accepted, reports
   `queued`, and no file ever appears.

**A bug in PCSXROO itself, found and fixed here** (branch `fix/frame-advance-input` in that
repo): `VSyncStart` calls `VSyncOnCPUThread` before `PollInputOnCPUThread`, and
`VSyncOnCPUThread` is where frame advance pauses the VM. The input hook returned early
unless the VM was Running, so injected input was dropped on the final frame of every
advance - and an advance of one frame is nothing but a final frame. `input set` followed by
repeated `frame-advance 1` therefore held the button for exactly zero frames, while the
same input over one bulk `frame-advance 120` worked. A stepped capture recorded the game
ignoring the pad and looked entirely plausible. Allowing `Paused` is safe: the hook's only
caller runs while the VM is executing, so it is never reached during an idle pause.

## 2026-09-04 - the 30fps oracle, mechanised

The game at 30fps is correct by definition, so the measurement is: the same save state,
the same scripted input, the same number of vsyncs, once with every compensation removed
and once patched. Equal vsync counts mean equal real time, which is what "twice as fast"
is a claim about.

`tools/patchctl.py` makes the "compensation removed" half possible without a reboot. Two
things had to be worked out:

- **`patch.reload` re-reads the pnach files but not the enabled list.** That list comes
  from the settings loaded at boot, so editing the game ini mid-session achieves nothing.
  Renaming a group in the pnach does: a group whose header no longer matches an enabled
  name is simply not applied. `patchctl` appends ` [off]` to disable.
- **Removing a patch does not undo it.** `patch=1` lines are rewritten every frame while
  active, and when the group goes away PCSX2 just stops writing - the last value it wrote
  stays in RAM. So disabling also has to put the original words back, taken from the boot
  ELF; addresses outside any ELF segment are the trampoline scratch zone, whose original
  content is zero. All 109 words verified by readback.

Because the ini's enabled list is frozen until a restart, it now carries the names of
groups that do not exist yet, so a new experiment does not cost a reboot.

The measurement tools:

| tool | question it answers |
|---|---|
| `tools/traj.py compare` | how far did it travel in the same real time? |
| `tools/traj.py ticks` | is this channel's *per-tick* step the same at both rates (uncompensated) or halved (already fixed)? |
| `tools/traj.py speed` | what is the speed, in units per second, at the same wall-clock offset? |
| `tools/speedtest.py` | the acceptance test: one ratio per situation, 1.00 correct, 2.00 the bug |

The `speed` verb earns its place. Everything else compares distances, and a distance is
the integral of the thing under test: two runs whose speeds match exactly still show
different distances if one entered a ramp a fraction of a second earlier, and a run that
is genuinely 20% slow looks fine over a window that starts later in the same ramp.

`tools/mkstate.py` builds the save states an A/B starts from. The launch itself runs at
whatever rate is under test, so it cannot be inside the measured window - the state has to
be cut afterwards, with the victim already in the air and its momentum baked in.

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
irrelevant. The target is therefore evolving more slowly under the patch. The likeliest
reason is that the target is computed from something the patch halves: `fighter+0x50` is
the previous tick's displacement and is now half its old value, and any target derived
from observed velocity inherits that. **Next step if this is worth chasing: a read
watchpoint on `fighter+0x50` during a sustained sideways hold, and a breakpoint on
`FUN_001DE000` reading `f12` and `f13` - target and step - to find which of the 17 callers
drives it.**

It is a mild slowness against a former 91% overspeed, so it is a refinement, not a defect.

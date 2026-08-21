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

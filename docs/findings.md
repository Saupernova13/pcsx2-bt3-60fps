# BT3 60fps - findings log

Running record of everything established about Dragon Ball Z: Budokai Tenkaichi 3
(SLUS-21678, CRC 428113C2). Shared memory between the Analyst and Interpreter roles.
Newest sections at the bottom.

## STATE OF PLAY - read this first

Last revised 2026-09-08. **20 groups ship**, in `patches/428113C2.pnach` and
exported to `releases/latest/`.

**v13, v14 and v15 are confirmed in play by the user, 2026-09-08.** The pursuit
stomp, the Cell Perfect Barrier camera, and the mouths - cut-in and pre-fight
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
| `60FPS - knockback flight` | doubles the three launch durations a heavy smash puts someone into, `FUN_001E9590` |
| `60FPS - pursuit timing` | the five frame counts and the intercept lead behind the Circle pursuit stomp |
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
   converted with a hard-coded 30. Only `tween duration` qualifies so far.

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
| Transformations run a few hundred ms **long** | Opposite sign, so a different cause. Untouched |
| ~~Pre-fight intro: mouths do not move at all~~ | **FIXED** by `mouth clock`, confirmed in play 2026-09-08. It was the same clip player after all, and it was a speed problem - the track ran out before the intro's first line. The old "not a speed problem" reading was wrong |
| ~~Death of an ordinary character: camera revolves too fast (item 3)~~ | **Solved**, reported by the user 2026-09-08 as fixed by earlier work. Never measured; closed on play |
| ~~Character switch: the sky stops rotating (item 5)~~ | **Solved**, reported by the user 2026-09-08. Never measured; closed on play |
| Death by a body-erasing attack: camera too fast, cuts weirdly (item 2) | **ASSUMED solved\*** - not checked by anyone. The user expects it to have gone with items 3 and 5. Asterisked deliberately: nothing has verified it |
| The Galick Cannon fade to white ends early (item 7b) | Still live, re-confirmed by the user 2026-09-08. A scripted-sequence beat that `sequence wait` should have moved and did not |
| **Real-time blast travel speed** (item 1) | **NOT solved**, confirmed by the user 2026-09-08: blasts still travel way too fast. Never fixed - `airborne motion` and friends fixed the FIGHTER's position integration, and projectiles were only ASSUMED to share that path. `ki blast + beam travel: procedural motion, open` has stood since 2026-08-22 |
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
| ki blast + beam travel | procedural motion | **still open 2026-09-08** - see the note below |
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

## 2026-09-05 - the tween system: every ease in the game ran at double speed

Sweeping for words that **step twice as far** had run out of road. The metric that
found this asks a different question - which words **reverse direction twice as
often** in the same amount of real time. An animation at double speed has to, and
unlike a step size a reversal count needs no magnitude and no alignment between
the two runs, so it survives the state divergence that had been drowning every
positional field in noise.

### Three ways to get the reversal count wrong

Each of these was found by getting it wrong first, and each one alone is enough to
make the scan useless.

1. **Sample both rates on the same real-time grid, with the same number of
   samples.** Reading every vsync gives the 60fps run twice as many looks at the
   same two seconds, and twice as many looks at a noisy word find twice as many
   reversals whatever its speed. Sampling every second vsync in both fixes it, and
   is also exactly one sample per tick at 30fps so nothing is read twice there.
2. **Check the words are actually floats.** The two ~24 KB regions at `0x006E9000`
   and `0x007E9000` are DMA and GIF packet data. Read as floats they are denormal
   zeros punctuated by values like `2.5e30`, and their sign flips mean nothing.
   They accounted for almost the entire first result.
3. **Start from a state that needs no input** - `tools/mkstate.py airidle`.

Unfiltered the scan reported 6792 words at 2x. With the grid fixed and
non-floats excluded: 657, and the top six were unmistakable.

### The tell

Two copies of one small structure, at `0x01879368` and `0x018795F4`, sampled every
second vsync during an airborne idle:

```
01879370   30fps   0.000  0.333  0.667  1.000  0.667  0.333   period 12 vsyncs
           60fps   0.667  0.667  0.000  0.667  0.667  0.000   period  6 vsyncs
```

A triangle wave, ping-ponging 0 to 1 and back in steps of one third, at exactly
double the frequency. `+0x00` is a 1,2,3 phase index, `+0x04` the direction,
`+0x0C` the endpoint. A write watchpoint named `FUN_00267B00`, and its
constructor sits just above it.

### The bug

`FUN_00267AC8(obj, seconds, from, to)` builds a linear tween:

```
00267AC8  lui   at, 0x41F0        ; 30.0
00267AD4  mul.s f12, f12, f00     ; obj+0x08 = seconds * 30    frames remaining
00267AD8  swc1  f13, 0x10(a0)     ; obj+0x10 = from            current value
00267AE0  swc1  f14, 0x14(a0)     ; obj+0x14 = to              target
00267AF0  div.s f00, f00, f12     ; obj+0x0C = span / frames   step per call
```

and `FUN_00267B00` advances it exactly one step per tick, decrementing the frame
count by 1.0 and clamping at the target.

**The 30.0 is the game's frame rate written into the arithmetic.** A caller asks
for a duration in seconds; the constructor converts it to ticks assuming 30 ticks
per second. At 60fps the stepper is called twice as often against a duration still
counted in 30Hz frames, so every tween finishes in half the time it was authored
for. This is the same class of defect as everything else here - a per-tick
quantity with no timestep - but it is the first one found in a *general-purpose
service* rather than in a particular behaviour, which is why it survived so long:
it is not the aura's bug or the animation system's bug, it is every ease, pulse,
fade and blend in the game at once.

One word repairs both halves, because both derive from the same constant:

    patch=1,EE,00267AC8,word,3C014270 // lui $at, 0x4270   30.0 -> 60.0

60.0 doubles the frame count and halves the step together.

### Verification

Through the shipped pnach group, not a memory poke, from the identical
airborne-idle state:

| preset | word at `00267AC8` | tween period |
|---|---|---|
| `off` (the 30fps oracle) | `3C0141F0` = 30.0 | 12 vsyncs |
| `air` | `3C0141F0` = 30.0 | **6 vsyncs** |
| `tween` | `3C014270` = 60.0 | 12 vsyncs |

No regression: dash 0.988 and launched-opponent coast 0.985, both unchanged from
before the group existed.

### What this does not yet explain

The reversal scan still finds 191 real-float oscillators at 2x outside the display
packets, about a hundred of them in the effect pool at `0x0198F000`-`0x0199A000`.
Some of that is an artifact of the method rather than a defect: **a save state cut
before the fix contains tween objects whose `step` was already computed from the
30Hz constant**, and those keep running fast until something rebuilds them, which
in a two-second window most long tweens never do. The ping-pong pair rebuilds
every six ticks, which is exactly why it was the clearest signal in the sweep.

Two dead ends worth not repeating, both ruled out by measurement from the
identical-state oracle:

- **The per-tick timer pool** at `0x018768A8`-`0x0187C6F8` is dead-clean 2.000 on
  values like `0.5 -> 1.0` and `25.60027 -> 51.20022`, and it is the countdown
  field of these same tween objects. It stays at 2.000 *after* the fix and that is
  correct - the duration is now legitimately twice as many frames. Counting
  "words at 2x" is the wrong success measure for this bug; the value field is what
  has to come back to 1.0, and it does.
- **The same pool is just as busy on the ground** - 341 moving words and 65 at 2x,
  against 334 and 51 in the air - so it was never going to be an air-specific
  defect on its own.

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

## 2026-09-05 - ki blasts are cut short: four hypotheses, all wrong

Reported by the user: ki blasts (Kamehameha and friends) last a shorter time and
land fewer hits at 60fps, and in ultimate-attack cutscenes the *blast* runs at
double speed while the bone and mesh animation plays correctly - so the energy
ball forms too fast and the sequence "ends early".

**Not solved.** What follows is what was measured and ruled out, so the next
attempt does not repeat it.

### The instruments

Two globals hold the combo readout, found by intersecting two moments whose
on-screen values were known (1760 at one frame, 2310 eight frames later):

    0033371C   combo damage
    00333724   hit count

`00331D64` is the frame counter, which rose by exactly 8 over those 8 vsyncs and
so confirms 60fps ticks once per vsync.

Save states, all captured live from the user's own session:

    slot 6   mid-Kamehameha, beam on screen, captured patched
    slot 7   the ultimate just started, camera on Goku, ball not yet formed, patched
    slot 8   the same moment of the same ultimate, captured UNPATCHED at 30fps

### A contaminated measurement, and the state that fixed it

From slot 7, running the two arms against each other, the ultimate's damage
landed at vsync 128 patched and vsync 200 unpatched - apparently a large real
difference. **It was an artifact.** Slot 7 was captured with the patch running,
so every tween already in flight carried a step computed from the fixed 60.0
constant; replayed unpatched those tweens run at *half* speed and stretch the
sequence. A state captured under one configuration cannot serve as the reference
for the other whenever the patch changes stored data rather than only code.

Asking the user to capture the same moment with the patch off gave slot 8, and
measuring each state in the configuration it was captured in:

| state | configuration | beam bright until |
|---|---|---|
| slot 8 | unpatched 30fps | vsync 152 |
| slot 7 | patched 60fps | vsync 160 |

**The ultimate's overall duration is not halved.** Frames captured at matched
vsyncs in the two arms show the same body pose, the same camera and the same QTE
prompt at vsync 60.

### Ruled out

- **The sequence length.** 152 vs 160 vsyncs, above.
- **The beam's remaining life.** From slot 6, frame-exact brightness gives 64
  vsyncs unpatched against 62 patched.
- **The blast node's own lifetime.** `FUN_0017C8F4` runs a duration down at
  `0017C99C` by exactly 1.0 a tick, from the `1.0` at `0017C990` - a genuinely
  uncompensated per-tick timer of precisely the shape being hunted, in a node
  type neither the aura nor the particle gate covers. Halving it changed nothing
  the user could see. Worth knowing it exists; it is not this bug.
- **Ki drain.** No word behaves like a gauge emptying during a beam. The
  candidates near `0031C118`-`0031C158` read ratio 0.96 - correct - and the one
  that moves (`0031C128`) wobbles rather than draining, at ratio 1.39.
- **An earlier claim, withdrawn.** A ki barrage was reported here as delivering
  its hits "in half the real time". That came from sampling on a 10-vsync grid;
  at 2-vsync resolution the last hit lands at vsync 12 unpatched against 10
  patched, a factor of 1.25, and the move is front-loaded enough that most of its
  hits land before sampling begins. It is not evidence of anything.

### What the next attempt should do differently

Every measurement above looks at *duration*. The user's description is about a
blast that stops early, which duration should capture - and does not. Two
readings survive:

1. The affected quantity is not on any clock that was watched. A beam in this
   game may persist while a resource lasts rather than while a timer runs, and no
   such resource has been located yet.
2. The situations are not the same situation. Slots 7 and 8 are different
   battles - different health, different blast stock, different positions - and
   only the *phase* of the move is comparable between them, not the outcome.

The cleanest experiment not yet run: have the user fire **the same beam twice
from one save state**, once with the patch and once without, capturing a state
immediately before the input in each case, and compare the hit count. Hit count
is the thing the user actually reports losing, and it is a single integer that
needs no alignment between runs. Everything measured so far has been a proxy for
it.

## 2026-09-05 - ki blasts, reproduced at last: 28 vsyncs against 16

The previous section recorded four wrong hypotheses about this bug and, worse, a
measurement that had to be withdrawn. The thing that broke the deadlock was not
a better hypothesis - it was being able to fire the move on demand.

### Ask the game for the controls

Guessing the control scheme cost most of a session. Every "modifier + button"
probe returned the same result for `L1`, `L2` and `R2`, which looked like proof
the shoulder buttons were not reaching the game - but `tools/padcheck.py` shows
all four reaching it perfectly. The probes were identical because the *move* was
identical: the modifier was right and the assumption about which button ran the
Kamehameha was wrong.

**The game documents itself.** Pause, choose *View Skill List*, and the panel
lists the character's Special Attacks with the stock each costs, drawing the
input for the highlighted one at the bottom:

| move | input | stock |
|---|---|---|
| Wild Sense | L2 + Circle | 2 |
| Now I'm Mad! | - | 3 |
| **Super Kamehameha** | **L2 + Triangle** | **3** |
| Meteor Smash | - | 3 |
| **Angry Kamehameha** (ultimate) | - | 4 |

One screenshot answered what a dozen input probes could not.

### Script input in ticks, not vsyncs

The first A/B with the correct input still failed, and failed silently: at 30fps
the move never came out at all, so the reference run measured an empty screen.
The input script was written in vsyncs - 20 held, 6 pressed - which is 20 and 6
ticks at 60fps but only 10 and 3 at 30fps, too short to register. Lengthening it
to 48 and 16 vsyncs makes the move fire at both rates. **A scripted input has to
be long enough in TICKS at the slower rate**, and a run has to check the move
actually happened rather than assume it.

### The measurement

`tools/blasttest.py`. Same save state, same scripted input, same vsyncs:

| configuration | damage | hits | beam on screen |
|---|---|---|---|
| unpatched 30fps | 8520 | 6 | **28 vsyncs** (8..32) |
| patched 60fps | 8520 | 6 | **16 vsyncs** (8..20) |
| battle group only | 8520 | 6 | 16 vsyncs |

The beam is on screen for roughly half as long, and the way the damage arrives
is the tell: unpatched it *ticks out* - 1520, 4260, 7100, 8520 over about twelve
vsyncs - while patched the whole 8520 lands at once. That is the reported "cut
short, fewer hits", measured.

**Battle-group-only reproduces it exactly**, so no group in the patch causes
this and none compensates it. It is a missing compensation, not a regression.

### The beam is FUN_00186250

A sweep during the beam for words moving the same amount per tick at both rates
- excluding the tween pool, whose countdowns legitimately read 2x - pointed at
`01A0D4D0`, `01A0D764` and `01A36xxx`. Write watchpoints on those land in the
`00183xxx`/`00184xxx` module, whose caller is **`FUN_00186250`: a vtable entry
at `002C3EF4`, no direct callers**, the same shape as the ki aura's
`FUN_00164860` and the particle node's `FUN_00168084`.

Gating that function wholesale on frame parity stretches the beam from 16 vsyncs
to 56 and drops the damage to zero, so it is unquestionably the beam - but a
blanket gate is not the fix, because the same call does the hit detection.

### Eliminated

Every `lui $at, 1.0` in `FUN_00186250`, tested one at a time against the harness,
all leaving the beam at 16 vsyncs:

    001863BC   0018672C   001867C8   00186810   00186850   00186890   001868CC

`001867C8` feeds a countdown at `+0x1F8`; `00186810` feeds a counter at `+0x20C`
compared against a limit at `+0x210` that calls `FUN_00182DE0` - which looks
exactly like a hit-cadence timer and still is not it. Also eliminated earlier:
`FUN_0017C8F4`'s per-tick lifetime at `0017C990`.

### Where to pick this up

The harness is the asset: `tools/blasttest.py` turns any candidate into a
two-minute yes/no, with `--pokes label=ADDR:WORD`. The target is confirmed. What
is not yet known is which channel inside `FUN_00186250` sets how long the beam
lives - it is not any of its seven `1.0` constants, so it is likely a duration
read from the move's data table and stepped somewhere else, or a stage counter
whose threshold rather than whose step is the per-tick quantity.

The next thing to try is a write watchpoint on the beam object's own fields
during the beam - `+0x1F8`, `+0x20C`, `+0x210`, `+0x1F4` - rather than a search
for constants, and to find where the beam decides to end rather than assuming it
counts down.

## 2026-09-06 - ki blasts solved: a hitbox counter authored in ticks

Two sessions had hunted this as "which constant makes the beam short". It was
never a constant. It is a counter, and finding it took abandoning three separate
lines of attack that all looked promising.

### The oracle that made it tractable

Screen brightness had been the measure of a beam all along, and it is a bad one:
a fixed luma threshold catches the launch flash, misses the beam, and resolves to
+/- the sampling step. The damage counter is far better - `0033371C` moves in
exact integers, needs no screenshots, and can be read every single vsync:

| configuration | damage steps | cadence | span |
|---|---|---|---|
| unpatched 30fps | 2840 4260 5680 7100 8520 | every **8 vsyncs** | 32 |
| patched 60fps | the same five values | every **4 vsyncs** | 16 |

Identical damage, identical hit count, exactly half the real time. Uniform 1420
steps. That is the whole bug in one table, and it took two minutes to produce
once the instrument was right. **Reach for the exact integer the game already
maintains before reaching for a picture of the screen.**

### Three wrong turns, and what each one cost

**`FUN_00186250` is a constructor, not an update.** The previous session had it
as "the beam update, confirmed". Breaking on it shows 18 calls clustered in four
frames, each building a 0x40-byte node - and its first act is copying 0x40 bytes
from a template. The real update is `FUN_001866C0`, slot [0] of the same
six-word class descriptor at `002C3EF0`; `00186250` is slot [1]. The descriptor
table at `002C3E00` holds eighteen of these records, and slot [0] is always the
update-and-draw.

**The `seconds * 30.0` family is real, and is not this bug.** The shipped tween
fix was exactly that shape, so enumerating every `lui $at, 0x41F0` in the code
segment seemed certain to find it: 145 sites. Breaking on all of them narrows to
the 33 that execute during a blast, and **none of the 33 changes the cadence** -
tested in two batches and individually. A complete, mechanical elimination of a
whole hypothesis class is worth the twenty minutes it costs.

**A dead field that looked alive.** `+0x1F4` of a beam node visibly counts down
and freezes the instant the beam ends. It is neither: a write watchpoint on it
catches nothing at all, because the pool at `01A2Exxx` is being recycled and the
"countdown" was successive nodes landing on the same address. A value that
changes with no writer is not a clock, it is different memory.

### The actual mechanism

Trace backwards from the symptom instead. The opponent's HP is `018726A4` -
found by scanning all of RAM for words whose change pattern matches the damage
schedule *exactly*, which returns six addresses out of eight million. A write
watchpoint on it names `FUN_001CE630`, whose live call site is `001CBEF4`, and
walking up gives the chain

    FUN_001AFE70  -> 001CD320 -> 001CC588 -> 001CBD70 -> 001CE630 (apply damage)

with `FUN_001AFE70` called **every frame** and everything below it only every
fourth. The gate is inside it, and it is not a float anywhere:

    H = [obj+0x60]                    the live hitbox
    D = [[obj+0x64]+0x24]             the move's data record
    H[0x0A]   tick counter, ++ once per frame by FUN_0012E7C8 at 001AFE98
    D[0x0B]   the hit interval, AUTHORED IN TICKS
    H[0x0B]   hits landed so far
    D[0x0A]   the maximum number of hits

A hit lands when `H[0x0A] >= D[0x0B]`, which resets `H[0x0A]` to zero; the attack
ends when `H[0x0B] > D[0x0A]`. **One counter paces both the cadence and the
duration** - hits arriving twice as fast spend the hit budget in half the time -
which is why the beam was short *and* felt like fewer hits. The designers wrote
these intervals as tick counts, so there is no constant to scale.

### The fix

`FUN_0012E7C8` has exactly one caller and `H[0x0A]` is read and reset only inside
`FUN_001AFE70`, so gating that single call on frame parity is as narrow as a fix
in this project gets. Single-hit attacks cannot regress: the `blez` at `001AFF08`
short-circuits while no hits have landed, so the first hit of any attack is never
delayed.

### Still open: the launch flash

The visual white-out is a separate channel and is **not fixed**. It lasts 8
samples at 30fps and 4 at 60 on a 3-vsync grid - **12 ticks either way** - so it
is a per-tick effect-node lifetime of the `seconds * 30.0` family after all, just
not one that touches damage. Doubling the 22 such sites that fire during a blast
restores most of it (21 vsyncs against the oracle's 24); doubling all 31 sites
that structurally convert seconds to a stored frame count makes it *worse*, so
they interfere and the set is not simply additive.

That is where it stands, and it deliberately was not shipped: tuning twenty-two
simultaneous constants against mean screen luma is how you get a change that
measures well and looks wrong. The next attempt should bisect the 22 against the
brightness curve, one class at a time, and confirm each in play.

## 2026-09-06 - the fix that measured right and looked like nothing

The hit-cadence fix above is real and the user saw no change at all from it, and
that is worth recording as plainly as the fix itself. It moves *when* damage is
applied - 8 vsyncs apart instead of 4 - while leaving the hit count, the total
damage and every drawn frame identical. Nothing about it is visible unless you
are reading the combo counter. **A quantity being provably wrong does not make it
the quantity the player is complaining about.**

What the player sees is the effect, and the effect is drawn by two node classes:
the beam core at descriptor `002C3EF0` and the flare that follows it at
`002C40F0`. Each update carries half a dozen coupled per-tick channels - start
delay, emit countdown, a geometry cadence driving the segment builders
`FUN_00182DE0` and `FUN_0018322C`, lifetime, stagger, fade - all compared against
each other, which is why every single-constant test came back clean. Both open
with a call to `FUN_0012D1D0` and a branch that skips the whole update while
still reaching the draw, so parity into that branch is the same fix the aura and
the particles already use. The flare's skip is a *likely* branch, so its delay
slot has to be nopped and replayed only on the taken path.

    flash on screen        off 30fps   gates off   gates on
                            30 vsyncs   12 vsyncs   24 vsyncs

Twelve to twenty-four is exactly the doubling a parity gate should produce, and
the two-humped curve - the charge, then the fire - comes back; at 60fps the two
humps had merged into one.

### Two instrument failures worth remembering

**Poking a stock value back does not disable a group.** The three-way comparison
first came back with the gated and un-gated arms byte-for-byte identical, because
PCSX2 rewrites every `patch=1` line each frame and had simply put the hooks back.
This is already written down in this document and it still cost a run. Toggle by
group through `patchctl`, never by poke.

**The 30fps arm drifts between boots.** The same `off` measurement gives 21, 27
and 30 vsyncs on different launches while being bit-identical when repeated
inside one session. Only ever compare arms measured in the same session.

## 2026-09-06 - the blast sequence, found by bisecting code instead of constants

Two fixes shipped before this one measured correctly and changed nothing the
player could see. Both were developed against a scripted Super Kamehameha from
slot 1 - a move that turns out **not to exhibit the bug at all**: 6 hits and 8520
damage at both rates, with the beam only marginally shorter. Everything tuned
against it was tuned against a case that was already fine.

**Reproduce the case the user described, not a convenient one.** From the user's
own capture of the Angry Kamehameha, photographed in real time, the difference is
obvious: the camera cuts back to the fight at 2.1s unpatched and 1.4s patched.

### Two instruments that were lying

**A screenshot needs a running VM, so frame-advance plus screenshot cannot time
anything.** Each sample let the game run about five uncontrolled ticks - the
first one after a load slipped 181. Every "vsync" label on the earlier brightness
curves was fiction. The fix is to stop stepping: let the emulator run free and
sample on the wall clock, so each frame is a real instant and two runs at
different frame rates line up on real time.

**A counter read mid-climb is not a result.** The frames showed 8 hits at 30fps
against 6 at 60fps, which looked like the reported "does less hits". Both runs
end at 8 hits and 16640 damage; the combo readout was simply caught part-way up.
Hit count and damage are identical at both rates, in every case measured.

### The decomposition that pointed the way

The cut happens 79 ticks in at 30fps and 107 at 60fps - neither equal in time nor
equal in ticks. Solving `T + N/30 = 2.47` and `T + N/60 = 1.66` gives `T = 0.85s`
correctly compensated and `N = 49` ticks not compensated at all. A mixed
sequence, which is why every whole-sequence measurement looked ambiguous.

### Bisecting the code

Searching for the constant failed repeatedly - it is not a constant. What worked
was gating a call on frame parity and asking one question of the picture: *did
the camera cut move?* One screenshot per candidate, each probe from the same
state so nothing accumulates.

    0012B700 -> FUN_0012CB60 -> 0012CB84 -> FUN_001AD150

`FUN_001AD150` is the scene-graph walker: for every node it loads the class at
`[node+0x28]` and calls `vtable[0]` through a single indirect call at `001AD188`.
Gating that call for a *range of vtable addresses* turns "which class?" into a
binary search, and the range narrows to one: **vtable `002C3940`, update
`FUN_001587B8`** - an action/state controller, not a renderer, whose per-tick
counter at `+0x14` is advanced at `001589D0`. Nothing is drawn from it, so gating
costs no frame.

    camera cut      unpatched 30fps   patched   with the gate
                          2.1s          1.4s        2.0s

The normal-battle blast schedule is byte identical with and without it.

### A trampoline bug worth recognising

The first range sweep answered "delayed" for every range including disjoint ones.
The cause was a branch offset off by two instructions, so classes *below* the
range fell into the parity check as well and everything was gated. **When a
bisection reports the same answer for disjoint halves, suspect the instrument
before the hypothesis.**

## 2026-09-06 - gating an effect update deletes the beam, and how that was found

v5 shipped two groups together and broke rendering: the ultimate drew no beam at
all, the Super Kamehameha drew its charge but no output beam, and a half-built
charge effect stayed **stuck to the character's hands** after the move ended.

### Why gating was wrong here

The ki aura and the particle system are both fixed by gating their update on
frame parity, so gating the blast's effect classes looked like the same move. It
is not. **These updates rebuild the beam's geometry every frame.** Skipping one
does not slow the beam down, it leaves nothing to draw that frame - and because
the lifetime countdown lives in the same skipped block, a node that should have
expired never does. That is the stuck effect, exactly.

The correct fix is to halve every per-tick step instead: 1.0 becomes 0.5 at all
six sites in the beam core `FUN_001866C0` and all thirteen in the flare
`FUN_001961A0`. The geometry is still rebuilt on every frame, and all the
channels move together - which is the whole point, because they are compared
against each other. **Halving any ONE of them does nothing at all**, which is why
every single-constant test across three sessions came back clean and why the
pattern was invisible until they were changed as a set.

    Super Kamehameha, beam on screen (real time, game running free)
      unpatched 30fps   0.6s .. 3.0s
      60fps, no fix     0.6s .. 1.75s
      60fps, halved     0.6s .. 2.9s

### The measurement that was lying about the gate

The gated version *measured* as an improvement - mean screen luma stayed high
for longer. It stayed high because the stuck effect was still on screen. **A
brightness metric cannot tell a longer beam from a leaked one**; the frames had
to be looked at. Every brightness result in this project that was not confirmed
by looking at the picture should be treated as suspect.

### Blaming the wrong half of a pair

Both groups were withdrawn together because both shipped together. Re-measured
separately on the corrected patch, the sequence gate turned out to be innocent:
it draws nothing, so it has no geometry to skip, and it costs the beam nothing
(0.6s..2.9s with it, the same without) while moving the ultimate's camera cut
from 1.4s to 2.0s against a 2.1s target. **When two changes ship together and
only the pair is measured, a good change can be discarded on the evidence
against the bad one.**

## 2026-09-06 - the charged blast is a different code path, and SEQ kills it

The sequence gate was withdrawn, restored as "innocent", and then withdrawn
again for good. The restore was wrong, and the reason is worth more than the
fix: **it was cleared using an uncharged tap of the move, which never exercises
the charge path at all.**

A Super Kamehameha can be tapped or charged - hold Triangle, get a BOOST!
prompt, release to fire a bigger beam. Every automated test in this project
tapped it. Charged, with the sequence gate enabled:

| configuration | hits | damage | beam on screen |
|---|---|---|---|
| unpatched 30fps | 6 | 12120 | 0.3s .. 2.6s |
| shipped groups only | 6 | 13680 | 0.3s .. 1.3s |
| + blast effect duration | 6 | 13680 | **0.3s .. 2.7s** |
| + blast sequence rate | 5 | **1520** | **nothing renders** |

The move still fires - banner, BOOST! prompt, correct firing pose, correct
controller rumble, correct duration - and draws nothing and deals nothing. The
gated controller is what SPAWNS the effects, so gating it at half rate loses the
spawn entirely on the charge path.

**Both withdrawn groups failed the same way for the same reason: an effect that
is gated is an effect that does not get built.** One skipped the geometry
rebuild, the other skipped the spawn. Gating is the right fix for a system that
only advances state; it is never the right fix for one that constructs
something every frame.

### What that says about test inputs

A scripted input exercises exactly one path. This one tapped a button that the
player holds, and three sessions of measurements inherited that blind spot -
including the measurement that "cleared" a group which breaks the game outright.
When a move has a charge, a level, or a direction, the script has to cover it,
and the user's description of how they play it is the specification.

## 2026-09-06 - what is left, and what has been ruled out on it

Shipping state after the charged-blast regression was fixed: rendering is
correct on both moves, the beam's damage window matches the unpatched game
exactly, and the beam's visible duration is restored by halving the effect
nodes' per-tick steps. **The ultimate's cinematic is still paced in ticks and
cuts back to the fight early**, and that is stated in the released file's header.

### The decomposition, for whoever picks this up

The camera cut lands 79 ticks in at 30fps and 107 at 60fps - neither equal in
real time nor equal in ticks. Solving the pair gives about **0.85s that is
correctly compensated and about 49 ticks that are not**. Only that 49-tick piece
needs fixing.

### Ruled out, with the evidence

- **Gating the controller class** (vtable `002C3940`, `FUN_001587B8`). It does
  pace the cut correctly - 1.4s becomes 2.0s against a 2.1s target - and it is
  unshippable: it costs the *spawn*, so a charged blast renders nothing and
  deals 1520 damage instead of 13680. Worse, the pacing it produces looks like a
  side effect rather than a mechanism: gating each of its three calls
  individually (`0012CE88`, `00158F00`, `00158C70`) changes the timing not at
  all, so what actually moved the cut was leaving the node's "processed this
  frame" bit `0x10` set at `001587DC`. A fix that works by accident is not a fix.
- **The sequence counter** at `+0x14`, advanced at `001589D0` - the only per-tick
  increment in `FUN_00158980`. Halving it changes nothing.
- **`FUN_00158980`'s call site** at `00158818`, and **`FUN_00158C70`'s** at
  `00158804`. Neither moves the cut.
- **Constants.** The whole `00158000..00159400` module contains no `1.0` and no
  `30.0` float constant at all; it is an integer state machine.
- **The charge meter.** `0031C4AC` fills at +6.0 a tick at 30fps and +3.0 at
  60fps - **+180 a second either way**, and it reaches its cap in the same real
  time. Its timestep `0031C4F0` is tween-driven and equally correct. The charge
  is not what runs fast.

### The one lead not yet followed - followed on 2026-09-07, and wrong

`FUN_00158F00` decides whether the sequence advances by asking whether an
animation is still playing (`FUN_00206C20`, on `[obj+0x24]` and the bytes at +4
and +5). The guess was that the cinematic waits on an animation whose clock the
patch does not fix.

**It does not.** `FUN_00206C20` is not an animation query at all - it compares a
character id against the ranges 0x12D..0x130 and 0x139..0x13C. And the animation
clock *is* correct inside the cinematic: Goku's model advances `+0x138` by 2.0 a
tick unpatched and 1.0 a tick patched, and every clip that ends naturally ends
at the same real time in both arms.

The wait is in `FUN_00158980`'s sibling `FUN_00158850`, and it is an integer
countdown, not an animation. See "the two clocks behind everything the game
stages" below.

## 2026-09-07 - the user's full defect list

Everything below is the user's own observation of the shipped patch in normal
play, recorded verbatim in substance so no item gets lost between sessions.

### Still wrong, and running fast

| # | What the player sees |
|---|---|
| 1 | Blasts end too fast and travel too fast - **including explosive waves** |
| 2 | Death by a body-erasing attack: the camera moves around the victim too fast and cuts weirdly |
| 3 | Death of an ordinary character: the camera revolves around the corpse too fast |
| 4 | Camera is still too fast in some attack animations - Perfect Barrier named |
| 5 | Character switch: the sky stops rotating about a second in |
| 6 | Pre-fight intro: mouths do not move at all; some intro animations are too fast or too slow for the camera |
| 7 | Vegeta's scouter "Final Galick Cannon": the start animation's mouth movement finishes early, and after the rush sequence the fade to white ends too early, revealing the animation still playing behind it |

### Running slow - overcompensated

| # | What the player sees |
|---|---|
| 8 | Cell's Perfect -> Super Perfect transformation lasts roughly 0.3s longer than it should. Frieza final -> 100% likewise. Reads as a consistent transformation overshoot of a few hundred milliseconds. |

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

## 2026-09-07 - the two clocks behind everything the game stages

Three sessions of chasing individual effects ended here: the blasts are not
paced by the effects at all. They are paced by two integer counters, and both
were invisible to every scan run before today because every scan looked for
floats.

### The instrument that found them

`tools/ratediff.py` asks every word in RAM whether it still moves at double
speed: same save state, same input, the same number of **vsyncs** - the same
real time - once unpatched and once patched. A quantity the patch compensates
covers the same distance in both arms; one it misses covers twice as much.
Three snapshots per arm rather than two, because a word that only moves when
its pool is freed and refilled jumps once, while a clock advances the same
amount in each half of the window. That one requirement cut 805 false
candidates to 28 real ones.

Its companion `eventdiff.py` stops both arms at the same **event** instead of
the same time. Whatever a script keeps time by has to read the same at that
instant in both arms, because the event is the same point in the script.

Neither found the answer directly, but between them they said what the answer
was not: no float in the game moves at double speed during an ultimate except
some long-dead tweens. The clocks had to be integers.

### The chain, from the symptom down

The ultimate is one fighter **state**. `FUN_001E23D0` is the state machine: the
current state index lives at `fighter+0x948`, the handler table at `002C4980`,
and the handler is called once a tick with message 2. Save state 8 sits in
state 261, which becomes state 264 (`FUN_001F6518`, the Angry Kamehameha) at
0.42s unpatched and 0.40s patched - the same real time, so the entry is fine.

Inside the state, the animation schedule is fine too. Goku's model at
`008C0E30` advances `+0x138` by 2.0 a tick unpatched and 1.0 a tick patched:
**the animation clock patch is doing its job**, and every clip that ends
naturally ends at the same real time in both arms. What differed was the moment
an external event *interrupted* a clip - and that traced to the fighter's
animation attribute bit 0xA7 (`FUN_001DAC78`, bitfields at `fighter+0x1085` and
`+0x10AD`), set by `FUN_00158980`'s action from a scripted sequence.

### Clock one: the scripted sequence's wait

`FUN_00158850` steps one node of a scripted sequence per tick. A step that is
waiting counts a plain integer down by one - `[node+4]` at `00158914`,
`[node+8]` at `0015894C` - and fires its action when it hits zero. Those waits
are authored in 30Hz frames, so at 60fps every beat the game *stages* rather
than simulates arrives in half its real time: camera cuts, mouth lines, fades,
and the instant an ultimate lets go of its beam.

Counting down on even ticks only moved the Angry Kamehameha's first hit from
124 vsyncs to 161 against an unpatched 191, and every staged beat before the
beam launch now lands within two vsyncs of the unpatched game.

This is the fix the two withdrawn groups were reaching for and getting wrong.
Gating a node's *update* skips its spawn and its draw. Gating only the *wait*
skips nothing.

### Clock two: the fighter state's phase timer

Every state handler keeps a counter in the scratch block the dispatcher zeroes
on entry (`memset(fighter+0x3D0, 0, 0x50)` at `001E247C`), advances it once a
tick, and compares it against a count authored in 30Hz frames. In the held
Super Kamehameha - state 271, `FUN_001F7860` - that is `001F7A00`:

    lw    $v0, ($s0)          # ticks in this phase
    addiu $v0, $v0, 1
    slt   $v1, $v0, $s3       # ... against the authored charge length
    bnez  $v1, skip
    sw    $v0, ($s0)          # delay slot: stored every tick either way

`tools/phasetimer.py` finds all 28 of them by the shape the compiler gives
them: `addiu $sN, fighter, 0x3d8` in the prologue, then `[$sN] += 1` with a
matching load and store. `tools/mkgate.py` writes a trampoline for each that
adds one on even ticks only - an integer cannot be halved, and freezing one
hangs the state.

Held Blast 2, button down throughout, to the first hit: **unpatched 176 vsyncs,
patched-without-this 115, patched-with-this 175.** Same six hits, same 10900
damage, same eight-vsync spacing.

### Why the blanket gate is wrong, and what it cost

Gating all 28 broke ordinary melee: the fourth hit of a mashed rush lands at
122 vsyncs unpatched, 114 with the rest of the patch, and never within five
seconds with all 28 gated. Some of these counters are clocks and some are
levels - a combo index, an input window - and the ones that are levels must not
be slowed. They have to be selected by measurement, not by shape.

### Which of the 28 to gate, measured one at a time

Two oracles, both counted in vsyncs so they mean real time at either rate: a
held Blast 2 to its first hit (unpatched 176, patched-without 115) and the
fourth hit of a mashed rush (unpatched 122, patched-without 114). Each site was
gated alone and scored on both.

| Site | charge | melee 4th | verdict |
|---|---|---|---|
| `001F7A00` | **175** | 114 | the held charge itself - state 271 |
| 21 others | 115 | 114 | neutral here; same shape, other states |
| `001F1C74` | 105 | 114 | cuts the charge short |
| `001F31C0` | 115 | never | costs the rush its fourth hit outright |
| `001FBF28` | 115 | 160 | slows the rush |
| `001FCE34` | 65 | 214 | breaks both |
| `001FF9A8` | 111 | 138 | slows both |
| `001FFC10` | 66 | 215 | breaks both |

Those six are excluded. The remaining 22 leave both oracles where the rest of
the patch leaves them and fix the one they are supposed to fix.

### A trap: shrinking a live group leaves its hooks in RAM

`patchctl` restores the original word for every address it can see in the
pnach. Rewrite a group with **fewer** addresses than it had a moment ago and
the addresses that were dropped are no longer in the file, so nothing restores
them - the game keeps jumping into a trampoline that is no longer being
maintained. That produced twenty minutes of unreproducible measurements: the
unpatched arm read 176, then 65, then 112, then no hit at all. Restarting the
emulator fixed it instantly. **Shrink a group and restart, or measure nothing.**

### A second trap: loading the state *after* disabling the patch

`realclock.py` loads the save state, applies the preset, then loads the state
again so the patch is live from the first frame. That is right for turning a
group **on** and silently wrong for turning it **off**: the save states were
captured while patched, so their RAM image contains the patched words, and the
second load puts them straight back after `patchctl` has just restored the
originals. The unpatched arm is then not unpatched.

It reads as a plausible result rather than an error. The "30fps" run measured
181 ticks in six seconds one way and 362 the other - the give-away is that the
unpatched game can only ever tick 30 times a second. **Check the tick rate of
the unpatched arm in any real-time measurement**; 60 ticks a second means the
patch is still in RAM.

Order that works: load the state, apply the preset, run. Never load again after
applying.

## 2026-09-07 - MILESTONE: the blasts keep their real timing

Shipped as `releases/v9-scripted-clocks/` and deployed to the user's PCSX2: 17
groups, 424 patch lines, validated. The two new groups are `60FPS - sequence
wait` and `60FPS - state phase timers`.

### Confirmed in play, not by frame stepping

The instrument that matters here is `rtcharge` - the game running free at 100%
speed at both rates, the button going down on the wall clock, the opponent's HP
polled on the wall clock. That is the same clock the player is sitting through.
Held Super Kamehameha from save state 1, L2 for half a second and then L2 +
Triangle held down:

| | unpatched 30fps | patched 60fps |
|---|---|---|
| ticks in six seconds | 181 | 363 |
| the six hits land at | 2.92 3.05 3.19 3.32 3.45 3.59 s | 2.89 3.02 3.15 3.29 3.42 3.55 s |

A 24-frame filmstrip of the same two runs matches shot for shot to within one
0.3s frame: title card, charge ball, lightning, spikes, the beam, the white
flash, 12420 damage, and the aura afterwards. Nothing sticks to Goku's hands and
nothing fails to render.

The frame-stepped oracle agrees: first hit at 176 vsyncs unpatched, 115 with the
rest of the patch, **175** with this. Six hits, 10900 damage and eight-vsync
spacing in all three.

### No regression

| check | unpatched | patched |
|---|---|---|
| mashed rush, three seconds | 4 hits / 2160 damage | 4 hits / 2160 damage |
| the rush's fourth hit lands at | 122 vsyncs | 114 vsyncs |
| forward walk, two seconds | 1.45 units | 1.50 units |

### The ultimate, and where it stands

The Angry Kamehameha from save state 8, to its first hit: 191 vsyncs unpatched,
124 with the rest of the patch, **161** with `sequence wait`. Every staged beat
before the beam launch now lands within two vsyncs of the unpatched game - the
title card, the arm, the ball, the camera cut, the release. What is left is the
flight itself: 27 game ticks in both arms, which is half the real time.

That last half second is not an integer tick counter and not a per-tick float
step. Both classes were enumerated statically and swept exhaustively:

| class | how many | how they were tested | result |
|---|---|---|---|
| integer `field += 1` / `-= 1` | 513 binary-wide, 91 executing during the flight | gated to even ticks one at a time | none moves the first hit; eight break it outright |
| float `field += 1.0` | 140 binary-wide, including hoisted constants | all halved together | no change |
| the fighter state's own phase timer | reaches 28 at the hit in **both** arms | gated | no change - it is a passenger, not the driver |
| the beam node's own clocks (`FUN_00184BD8`, `+0xA8` age against `+0xAC` life) | the whole function's hoisted 1.0 halved | gated and halved | no change |

Whatever schedules that hit is neither. The next thing to try is the collision
itself: `001CE8DC` applies the damage, called from `001CE888`; walking up from
there to whatever decides the hitbox has arrived is the remaining thread.


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

## 2026-09-07 - WITHDRAWN: blast flash duration, and a probe left live in RAM

`[60FPS - blast flash duration]` (one word at `0017D940`, repointing the load
at the pool's 1/60) is **withdrawn**. The user reported Goku getting stuck in a
loop while it was in force.

### The measurement is still sound; the conclusion drawn from it was not

`[node+0x4E4]` really does drain by exactly 1/30 per tick and expire in exactly
9 ticks at **both** rates - 19 vsyncs unpatched against 10 patched - and the
repoint really does put it back on 19. None of that is in doubt.

What was wrong was assuming an uncompensated duration is therefore safe to
double. **A node that lives twice as long is a node something else may still be
waiting on.** This is the third time this project has hit that shape: gating the
blast effect update leaked a node whose lifetime never expired and stuck it to
the character's hands; gating the sequence controller lost the spawn. Extending
a lifetime is not the inverse of those, it is another way into the same class.

Anything that changes how long an effect node exists now needs a stuck-state
check in play before it ships, not only a duration measurement.

### The process failure, which is the more important half

`tools/sweep.py` and the ad-hoc probes here disable a probe group by renaming it
`[off]` **in the file**, and rely on the next `patchctl.apply` to restore the
original word. The last regression run renamed the group and then called
`resume()` without applying anything, so the repoint stayed in RAM. The session
then reported the change as "needs a restart to load" - true of the *named*
group, false of the word, which was already live in the user's play session.

    live RAM at 0017D940 while the user was playing:  C7818204   (the probe)
    original:                                          C7818A1C

**Renaming a group does not unpatch it. Only `patchctl.apply` does.** A probe
must be followed by an apply, and any claim about what the user is running has
to be a readback, not an inference from the file.

### Not assumed: the loop may predate this

The user notes the stuck loop "has happened a few times", so it is not
established that this change caused it - only that the change was live and is
the obvious suspect. It is worth reproducing against the shipped 17 on its own.

## 2026-09-07 - the stuck loop: what is actually known, and what was misread

The user reported Goku "bugging out" in a loop, and says it has happened a few
times. Observed directly on screen, not inferred.

### Established

| | |
|---|---|
| Fighter state | **157**, handler `FUN_001E6DC8` from the table at `002C4980` |
| Pending state | `0xFFFFFFFF` - nothing queued, so there is no transition to take |
| Pad | `0x00000000` on every sample - **no button held**, so not a stuck injected input |
| Animation | still cycling; the game ticks normally at 60/s. Not a freeze, a trapped state |
| Opponent | off camera entirely |
| Recovery | reloading a save state clears it completely |

### Misread, and worth recording as a caution

`fighter+0x3D8` read 0 and never advanced, and this was called the bug. **It is
not.** The same field reads 0 in a perfectly healthy idle (state 11). A zero
there carries no information at all, and the reading was made because a zero was
wanted, not because it distinguished anything. Any future use of that field as
evidence has to compare it against a healthy state in the same situation first.

### Not established

The cause. Two facts sit next to each other and neither implies the other:

- `001E6F40` - one of the 22 gated sites in `[60FPS - state phase timers]` -
  lies inside the range of `FUN_001E6DC8`, the handler he is trapped in.
- Removing that group live did **not** free him.

The second does not clear the group. Restoring an instruction cannot rewind a
state machine that has already parked, which is the same lesson the withdrawn
flash-duration change taught an hour earlier: **the bad state is in RAM, and
code changes do not undo it.** Whether the gate is what puts him into 157 with
no pending state can only be answered by reproducing from a clean state, with
the group on and off.

### The reproduction that is needed

The trap was reached during ordinary play, so the sweep oracles - a held charge
and a mashed rush - do not cover whatever leads into it. What is needed is the
sequence of moves the user was performing. State 157 is not one of the states
this project has identified (264 = ultimate, 271 = held Super Kamehameha), so
naming it is the first job.

## 2026-09-07 - the pursuit stomp, and five frame counts in one chain

The user reported it precisely: hold Square with Up to launch someone with a
heavy smash, then tap Circle and Goku teleports above them and stomps them into
the ground. **At 30fps he lands it every time. At 60fps he never does** - and
the stomp comes down "sort of awkward diagonal" instead of straight.

### The reproduction

Save state 9 (both fighters at melee range), hold `Square` + `Up` - the real
d-pad, not the stick - and the charge releases itself after about 114 vsyncs.
The victim is fighter 1; HP is at `fighter+0x9E4`. Then wait a fixed number of
**vsyncs** - real time, the same in both arms - and tap Circle for 8.

Swept over nine press delays from 5 to 45 vsyncs:

    delay:          5    10    15    20    25    30    35    40    45
    off  (30fps):  54    49    44    39    34    31    30    29    30
    full (16 grp): MISS  MISS  MISS  MISS  MISS  MISS  MISS  MISS  MISS

Nine out of nine. This is the first bug in the project with a clean, total,
deterministic A/B, and it is worth saying why: **no button is pressed inside the
measured window.** Both the launch and the pursuit are triggered before it, and
the window only watches HP and positions. Every earlier attempt to measure this
failed because a press duration is asymmetric - 8 vsyncs is 4 ticks at 30fps and
8 at 60 - and that bias contaminated the result. Waiting in vsyncs and measuring
in vsyncs removes it entirely.

### What was NOT wrong

The user's own diagnosis was that the victim "flies back too fast". **It does
not.** Measured over the launch, the victim's motion in real time:

    off  (30fps)  (218, -139, 100) units/s
    full (60fps)  (219, -139, 100) units/s

and its position matched the 30fps arm to within 0.15 units at the same real
time, 50 vsyncs after impact. The airborne groups do their job. So does the
dive: once it starts, Goku descends at (126, 382, 58) u/s against 30fps's
(129, 392, 59). Both sides of the collision were already correct.

A reasonable guess, and the data ruled it out. Worth recording, because the
instinct to fix what the report names would have gone straight past this.

### What was wrong: five frame counts, in one chain

Every defect found is the same shape - a duration authored in 30Hz frames -
and every one of them had to be fixed or the stomp still missed.

**1. The launch flight.** `FUN_001E9590` (states 213, 214, 223) counts
`fighter+0x3D8` down once a tick from a per-move value: 50 for the D5 smash, 15
for D6, 32 for DF. Measured, state 213 ended at **tick 52 in both arms** - 104
vsyncs at 30fps, 52 at 60. The victim dropped out of the constant-speed launch
and into the gravity tumble in half its real time.

Note that `[60FPS - state phase timers]`, the withdrawn group, does **not**
cover this. `withphase` produced a byte-identical state sequence to `full`. The
28 sites that group gates are a different set; this counter was never in it.

**2. The pursuit windup.** `FUN_001F30E0` (state 43) holds for 6 ticks before
firing the teleport, with a cosmetic effect starting at 4.

**3. The rise.** `FUN_001F3668` (states 47, 48) computes a target once, stores
`(target - pos) * 0.25` at `fighter+0x400`, adds it once a tick, and exits at
exactly 4. Four quarter-steps, so halving the step and doubling the count leaves
the endpoint **identical** and changes only the duration.

**4. The dive stall.** `FUN_001E7408` (states 146, 155, 171): after 20 ticks of
diving, the horizontal speed is halved *every tick*. At 60fps that arrived
before the dive could close, and Goku visibly slid to a stop in mid-air with his
phase counter pinned at 21.

**5. The intercept lead - the one that actually decided it.**
`FUN_001DE8A8` computes

    target = foePos + foeVel * param_4

where `foeVel` is **per tick** and `param_4` is a lead in **ticks**. Broken at
the call site with a breakpoint, the raw prediction relative to the victim was

    off  (87.51, -55.56, 40.02)      param_4 = 12.0
    full (43.75, -27.78, 20.02)      param_4 = 12.0

exactly half, because the velocity is correctly halved and the tick count is
not. That is the whole bug in one line: Goku aims where the victim will be in
`param_4/60` seconds instead of `param_4/30`.

The consequence is geometric, and it is exactly what the user saw. At the moment
the dive begins, Goku minus victim:

    off   (+18.0, -129.1,  +8.2)     ahead of them - the dive falls onto them
    full   (-9.7, -119.4,  -4.4)     behind them  - the dive has to chase

**The dive does not track.** It is a fixed-velocity plunge that works because
the victim runs into it. Being 28 units behind at the start is unrecoverable,
and chasing is what makes it look diagonal.

### The fix, and why it is shaped this way

Nine words, two groups. `[60FPS - knockback flight]` doubles the three launch
durations; `[60FPS - pursuit timing]` doubles the two windup counts, the rise
(step *and* length), the dive stall, and the lead.

Two choices worth defending:

- **The launch timers are doubled, not gated.** A parity gate is the other fix
  shape for an integer clock, and it is what `[60FPS - state phase timers]` did
  before it was withdrawn over the state 157 trap. Doubling the authored value
  leaves the counter decrementing every single tick, so it cannot leave a
  fighter parked in a state the way a gate might. Given the trap is still
  unexplained, that margin is worth having. `FUN_001E9590` also serves only
  three states, and none of them is 157 (`FUN_001E6DC8`).
- **The lead is doubled inside the solver, not at the call site.** `param_4` is
  built as `fVar7 + 4.0 + fVar5` with a per-move `fVar7`, so doubling the
  literal 4.0 corrects only the move whose `fVar7` is zero - and this move's is
  8.0, which is why changing 4 to 8 moved the target a third of the way and no
  further. One word inside `FUN_001DE8A8` turns `mov.s $f12,$f20` into
  `add.s $f12,$f20,$f20` and doubles the whole lead. The function has exactly
  one caller, so nothing else is touched.

### Result

    delay:          5    10    15    20    25    30    35    40    45
    off  (30fps):  54    49    44    39    34    31    30    29    30
    full + fix:    53    48    43    38    33    28    28    29    28

Nine out of nine, within one to three vsyncs of the 30fps arm at every delay.
Confirmed in play with the VM running free and the pad driven on the wall clock
(`tools/stomptest.py`): the stomp connects 1.08s after the smash against 30fps's
1.20s, and the contact sheet shows the second hit and the ground impact.

No regression: the charge oracle (99 vsyncs) and the ultimate oracle (161) are
unchanged to the vsync by these nine words.

### A metric that lied, recorded so it is not trusted again

The first several runs scored "closest approach over the whole window" and it
sat at exactly 7.2 no matter what was changed - the same insensitivity that
killed the previous session's harness. The reason is mundane: the closest
approach happens at the **teleport**, not during the dive, so the number
measured the teleport placement and was blind to everything after it. The HP
drop was the only honest signal. A metric that does not move when the thing it
scores obviously moves is broken, not stable.

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
at 60fps. Slot 9 was captured *unpatched* and is immune, which is why the pursuit
stomp measured on it is unaffected, and the deterministic memory trace was written
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

    arm             charge   melee  ultimate   pursuit stomp
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
- **v13's pursuit stomp** has still not been play-tested.

The v15 half that remains unverified is the *second* track object, `009212F0`,
which drives the radial speed-line effect in Goku's ultimate. It changed on 90 of
170 vsyncs and the hit schedule did not move, so it is the same correction for
the same cause - but nobody has looked at whether that shot reads better.

## 2026-09-08 - the EmuDeck install was running the working pnach

The user, after a session of confirmations: "I just booted up my PCSX2 emudeck
install, and everything is broken beyond belief."

It was, and it had nothing to do with any fix. The install was running
`patches/428113C2.pnach` - the **working** file - with every group in it enabled:

| group | what having it on does |
|---|---|
| `60FPS - animation rate` | superseded by `animation clock`. **Both on = QUARTER speed animation** |
| `60FPS - EXPERIMENT halve root motion` | deliberately breaks ground movement. That is what it is for |
| `60FPS - blast effect rate` | WITHDRAWN: gating skips the geometry rebuild, so the beam is not drawn |
| `60FPS - blast sequence rate` | WITHDRAWN: skips the controller step that SPAWNS the effects, so a charged blast renders nothing and deals no damage |
| `60FPS - state phase timers` | WITHDRAWN: the state 157 trap |

Quarter-speed animation, no beams, broken ground movement and a state trap, all
at once. Every one of those is a documented, deliberate hazard; they were simply
all switched on together.

### How, and why it went unseen for days

`deploy.py` enabled **every group in whatever pnach it was handed**:

    groups = args.only if args.only else [g.name for g in source.groups]

`export.py` exists precisely to drop those five, and `releases/latest/` has
always been correct. The working pnach had been deployed instead, at least as
far back as 2026-09-05 judging by `work/cheat-backups/`.

It went unseen because **every measurement in this project runs against
PCSXROO**, which reads a different cheats directory and a different per-game ini.
The dev instance was correct throughout; the user's actual install was not. Two
emulators, two configs, and only one of them was ever being tested.

Two guards now, both cheap:

- `config.NEVER_SHIP` holds the five names once. `export.py` drops them and
  `deploy.py` refuses to enable them, printing the `releases/latest/` command
  instead. `--only` still selects a subset; `--force-development` overrides.
- `patchctl --status` names any group missing from PCSXROO's own enable list,
  which is the mirror-image failure found earlier the same day.

### What the confirmations actually settled

`v13`, `v14` and `v15` all confirmed in play: the pursuit stomp after a heavy
smash, the Cell Perfect Barrier camera, and the mouths.

**The pre-fight intro mouths are fixed too**, which retires a wrong reading. That
row had said "not a speed problem" since the first defect list, on the strength
of the symptom alone - mouths that never move at all, rather than mouths that
stop early. It was never A/B'd, and it was wrong: same clip player, same 2.0 rate
a tick, and the track simply ran out before the intro's first line. The lesson is
the ordinary one - a symptom that looks qualitatively different is not evidence
of a different cause until something measures it.

Still open, and none of it touched by any of this: v12's input-timing flag, the
Galick Cannon fade, the ultimate's beam landing early, transformations running
long, the character-switch sky. The user also reports "some camera angles/speeds
seem off" - separate from the mouth work, and not yet characterised.

## 2026-09-08 - widescreen retargeted from 16:9 to 19.5:9

The user's install runs PCSX2's own `[Widescreen 16:9]`, from
`resources/patches.zip`. They asked for the same thing aimed at the Galaxy S24
Ultra's 3120x1440 panel - 19.5:9, or 2.166667.

The stock patch is three words, and the third gives the rule away:

| address | stock (4:3) | 16:9 | what it is |
|---|---|---|---|
| `002FE4CC` | 1.166667 | 1.555167 | projection scale, 7/6 |
| `002FE594` | 298.6667 | 398.1227 | the same constant x256 |
| `00130BF0` | `lui $at,0x3F40` | `lui $at,0x3F10` | an INSTRUCTION: 0.75 -> 0.5625 |

0.75 is 3/4 and 0.5625 is 9/16, so that immediate is **1/aspect**, and the two
data floats scale by **aspect / (4/3)** - how much the horizontal field of view
widens. The model reproduces the stock patch from first principles: fed 16:9 it
returns `3FC71C72` and `lui 0x3F10`, against the shipped `3FC70FB6` and
`0x3F10`. The immediate matches bit for bit; the float differs only because the
official patch rounded 4/3 to 1.333.

For 19.5:9 the widen factor is exactly 1.625, giving `3FF2AAAB`, `43F2AAAB` and
`lui $at,0x3EEC`. `lui` sets only the top 16 bits, so the last lands on
0.4609375 against an ideal 0.4615385 - 0.13% narrow, about a third of a pixel
across 3120. A trampoline would fix that for no visible gain.

### How far it is verified, and how far it is not

**Verified exactly, at the arithmetic.** `00130BF0` feeds `$f20` two
instructions later (`mtc1` then `mul.s $f20,$f02,$f20`). Breakpointing after
that multiply, with the group off and on:

    4:3     $f20 = 0.6495191
    19.5:9  $f20 = 0.3991836      ratio 0.61458, predicted 0.61458

**Not verified on screen.** No render test this session could distinguish the
aspects - and crucially it could not distinguish the *official 16:9 values*
from stock either. A live poke of the shipped 16:9 constants left the aura's
bounding box identical to 4:3, so the null result is a property of the test, not
of the constants: these are consumed at scene entry, and every quick path
(save-state load, mid-session toggle) shows the projection the state was
captured with. Seeing it needs a battle entered fresh after boot.

Two mistakes worth recording, both from trusting a metric over a check:

- The first scale-fit searched **horizontal** rescale only, over a band that is
  almost entirely flat green field. The objective was degenerate - error at the
  best scale equalled error at scale 1.0 - and it happily reported "no change"
  for every arm. A fit whose objective is flat has not measured anything.
- A frame captured with an extra 30 frame-advances was read as an aspect
  difference. It was aura animation. Arms must run the same number of frames.

### Shipping

`config.OPTIONAL` is a third list beside `NEVER_SHIP`: groups that belong in the
shared file but must not be switched on for the user. `export.py` keeps them,
`deploy.py` installs them and leaves them out of the enable list. A display
preference is not a fix, and this one additionally **conflicts with the stock
[Widescreen 16:9]** - both write the same three addresses every frame, so
whichever the cheat engine writes last wins.

To use it: add `Enable = Widescreen 19.5:9 - S24 Ultra` under `[Cheats]`, delete
`Enable = Widescreen 16:9` from `[Patches]`, restart, and set the display Aspect
Ratio to Stretch against a 19.5:9 output. PCSX2 has no 19.5:9 display aspect, so
at any other output shape this renders a correctly-wide FOV into the wrong box.


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

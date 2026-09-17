# Full Power Smash and the Lightning Attack

Hard Knockback and the Dragon Smash Circle hit, five frame counts in one chain.

## 2026-09-07 - the Lightning Attack, and five frame counts in one chain

The user reported it precisely: hold Square with Up to launch someone with a
Full Power Smash, then tap Circle and Goku teleports above them and stomps them into
the ground. **At 30fps he lands it every time. At 60fps he never does** - and
the Lightning Attack comes down "sort of awkward diagonal" instead of straight.

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
and every one of them had to be fixed or the Lightning Attack still missed.

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
(`tools/stomptest.py`): the Lightning Attack connects 1.08s after the smash against 30fps's
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

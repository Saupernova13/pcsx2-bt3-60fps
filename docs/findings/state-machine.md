# The fighter state machine and the stuck loop

Phase timers inside fighter states, and the state 157 trap.

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

## 2026-09-16 - ten user reports, and the state 157 trap explained by reading

Ten issues were filed against the published patch (#4-#13). They are not ten
bugs. Sorting them by mechanism rather than by what the player was looking at
gives four systems, and two of the four already had a group written for them.

| # | report | system |
|---|---|---|
| 4 | ki charges and drains too fast | discrete game logic on the tick |
| 6 | the perfect smash cue comes early | fighter state phase timers |
| 12 | fighters taunt almost at once | fighter state phase timers |
| 5 | Hercule's ki blasts too fast | spawned projectile travel |
| 8, 13 | speed lines, Special Beam Cannon twirl | effect animation |
| 9, 11 | blimp, helicopter, wind | stage ambient animation - suspected, NOT confirmed |
| 7, 10 | Cell's and Vegeta's transformations break | uncompensated cinematic - see the #7 section below |

Items 7 and 10 are the only two where the patch makes the game *worse* than the
30fps game rather than faster than it; everything else is something the patch
never reached.

### The scene the reports needed, and how to get one without a controller

Every earlier A/B ran from a hand-made save state, and none of the ten reports
happens in one. They need particular stages and particular characters, which
meant driving the game's own menus over the debug server's pad injection.

That works, and is worth writing down because it removes the standing limit on
what can be tested:

- **Hold each press for 8 frames.** Three frames is under the menu's sampling
  and four presses out of five are simply not seen. This cost several passes.
- The in-battle **pause menu** reaches `COM Settings` (`Stand` makes the
  opponent passive, which is the clean oracle this project always wanted),
  `Return to Character Select` and `Return to Main Menu`. Exiting a battle
  asks `EXIT?` with **No** preselected.
- Character select is a grid: `Down` moves a whole row, so a character is a
  couple of presses away rather than twenty.
- Input held from before the `Fight!` banner is ignored. An action test needs a
  state cut after it, not at the match start.

`work/state-backups/rocky-cell-match-start.p2s` came out of that: Cell (1st
Form) on Rocky Area - Evening, saved the first frame the battle manager is
non-null, so the *opening seconds* of a match are testable for the first time.

### Issue #12, the taunt: the mechanism, exactly

`FUN_001EE968` is the handler for state 11, the idle. Its prologue takes the
phase-timer pointer (`addiu s3, s0, 0x3D8`) and at `001EEBAC`:

    lw    v0, (s3)
    addiu v0, v0, 1
    slti  v1, v0, 0x5B        # 91 frames, authored at 30Hz
    bnez  v1, skip
    sw    v0, (s3)
    jal   FUN_001E0290
    li    a1, 0x43            # state 67 - the taunt

So a fighter left alone taunts after 91 frames, and at 60fps that is 91 ticks
instead of 91 frames: half the real time. The report is exact.

`001EEBAC` is one of the 22 sites in `[60FPS - state phase timers]`, the group
withdrawn on 2026-09-07. Measured from the match-start state, timing the
fighter's own counter rather than only the state it lands in:

| arm | counter starts | taunts | counting took |
|---|---|---|---|
| unpatched 30fps | vsync 198 | 378 | **180 vsyncs** |
| shipped v23 | - | 248 | ~90 |
| v23 + phase timers | vsync 158 | 338 | **180 vsyncs** |

The group fixes the timer **exactly** - 180 vsyncs is 91 frames at 30Hz, in both
arms. What it does not fix is that the counter *starts* 40 vsyncs early, 158
against 198. That is a separate defect in whatever the pre-fight sequence does
between the manager coming alive and the fighter reaching idle, and it is the
whole of the residue in the last row. It is not the taunt timer.

**Correction, 2026-09-28:** the early start is not in the game. It comes from
`rocky-cell-match-start.p2s`, which is cut on the battle's first frame, after
the game has set up the match with unpatched code (a tween at `0x0031C6B0`
takes the same steps per tick in every arm). In a match reached through the menus
with every open fix on, counted from the battle manager's first frame, input
goes live at v169 at 30fps and v170 at 60fps, and the fighter taunts at v349
and v351. See `docs/rig.md`, "Cutting a state worth keeping".

### The state 157 trap: an index gated as if it were a clock

The group was withdrawn because the user was trapped in state 157 with no
pending transition, and that was never reproduced under control. It does not
have to be reproduced. It can be read.

`FUN_001E6DC8` **is** state 157 - the handler in the table at `002C4980` for
index 157 - and 15 call sites hand over to it, almost all inside the blast and
ultimate states, so it is the recovery those moves end in. One of the 22 gated
sites, `001E6F40`, is inside it:

    001E6EF4  lb    v0, 8(s2)      # N, the table's entry count
    001E6EF8  lw    v1, (s3)       # i
    001E6EFC  addiu v0, -1
    001E6F00  slt   v1, v0         # exit test: i >= N-1
    ...
    001E6F18  lw    v0, (s3)       # i
    001E6F24  sll   v0, v0, 1      # i*2
    001E6F2C  addu  v0, s2         # &table[i]
    001E6F34  lh    a1, 6(v0)      # table[i]
    001E6F30  jal   FUN_001C48B8   # is this entry done?
    001E6F38  beqzl v0, skip       # no - leave i alone
    001E6F40  lw    v0, (s3)       # <-- THE GATED SITE
    001E6F44  addiu v0, v0, 1
    001E6F4C  sw    v0, (s3)

`(s3)` here is **an index into a table, not a count of frames**. There is no
compare against an authored frame count anywhere near it; the bound is `N` read
out of the object, and the value is scaled, added to a base and loaded through.
Gating it makes state 157 consume its table at half rate, and because the
advance is already conditional on `FUN_001C48B8`, an entry that finishes on an
odd tick advances the index by nothing at all. A state that cannot reach
`i >= N-1` cannot leave. That is the trap, in the shape the report described:
animation still cycling, nothing queued, cleared only by reloading.

This is the failure the group's own note warned about - "some of these counters
are clocks and some are levels... the ones that are levels must not be slowed" -
and the six levels already excluded were found by measurement against a held
Blast 2 and a mashed rush. Neither oracle ever enters state 157, so this site
was never eligible to be caught that way.

### The audit that should have been run in the first place

Classifying all 22 gated sites out of the boot ELF - a clock being a compare
against an authored count, an index being scale, add, load through:

| verdict | sites |
|---|---|
| clock | 21 - compared against 91, 151, 61, 16, 12, 8, 6, or a charge length in a register |
| **index** | **1 - `001E6F40`, and it is the only one** |

Four of the 21 needed a wider window to classify (`001F3320`, `001F7A00`,
`001F9D48`, `001FBBD0`); all four increment and store with no indexing, and
`001F7A00` is the held-charge clock already validated by measurement on
2026-09-07.

`001E6F40` and its trampoline are out of the group, which now gates 21 sites in
210 lines. The taunt measurement is **unchanged** by the removal - 180 vsyncs
either way - so dropping that site cost the fix nothing.

**Not verified:** the trap itself, which was never reproducible and still is
not. The case that this site is its cause is a reading of the code, a strong
one, but a play test is what would close it.

### Issues #9 and #11, the stage: a claim made and withdrawn the same day

**This section originally reported that Rocky Area carries ~1200 uncompensated
animated fields and that this was the stage's ambient animation - the system
behind the wind and the World Tournament aerials. That was wrong, and the error
is worth keeping rather than deleting.**

What happened: `tools/export.py` was never involved, but the save state was. The
scan attributed to "Rocky Area" was run against a slot that did **not** hold the
Rocky Area scene. `savestate --slot 10` exits 1 - slots are 0-9 - and the helper
that cut the state captured the CLI's output without checking its return code,
so it reported success. `sstates/` already held a `.10.p2s` from an older
session, and that file, a Goku vs Teen Gohan fight on the grassy stage with both
auras lit, is what got copied into the slot and measured.

Re-run against the genuine Rocky Area scene, cut and confirmed by screenshot:

| scene | steady movers | still 2x |
|---|---|---|
| grassy stage at night (slot 1), Buu vs Vegeta | 45 | 25 |
| **Rocky Area - Evening, Cell vs Gohan** | **32** | **27** |
| the mis-attributed scene: grassy, Goku vs Gohan, both auras lit | 1453 | 1257 |

Rocky Area is ordinary. There is **no evidence of a stage ambient animation
system running at double speed**, and #9 and #11 are no better understood than
before. The candidates on Rocky Area are the same two families seen everywhere:
the fighter and manager block around `01870000`, and tween counters - both of
which read 2x by design, for the reason in the next section.

What the mis-attributed scene does say, now that it is labelled correctly, is
that **an effects-heavy scene carries ~1200 uncompensated animated fields** in
`006Bxxxx`-`007Exxxx`, outside the fighters (`018706C0`, `01871CC0`) and their
models (`008C02F0`, `008C1970`), arranged as an array of identical objects with
three animated fields each. Two lit auras is the difference between that scene
and the quiet ones. That makes it a lead for the **effect** cluster - #8's speed
lines and #13's Special Beam Cannon twirl - not for the stage. It is not yet
attributed to anything: a write watchpoint on one field lands in a constructor
(`00121394`, from `00123650`, which allocates 0xE0 bytes and initialises three
sub-objects), which is the allocation rather than the per-tick update, and
memchecks do not observe every write path, so that silence is not proof.

The lesson is cheap and general: **a save state is an input to the measurement,
and an unverified input makes a confident wrong answer.** Check the return code,
then load the state and look at it. One screenshot would have caught this before
the analysis ran. It is written up in [`rig.md`](../rig.md) as trap 3.

### A caution about reading a rate scan

`ratediff` scores a quantity 2x when it covers twice the ground per second, and
that is the right test for a position, an angle or a phase. It is the **wrong**
test for a frame counter, which the patch compensates by doubling the count it
is measured against rather than by halving its step: a correctly fixed counter
still reads 2x. The global frame counter at `00331D64` reads 2x by design, and
so does every tween the tween-duration group already fixed. Only world
quantities can be read straight off the report.

### Issue #7, Cell's transformation: reproduced, and it is not a regression

**Correction to the triage table above.** #7 and #10 were listed as REGRESSIONS,
on the reasoning that a broken transformation is the patch making the game worse
rather than faster. For #7 that is measurably wrong, and #10 is untested.

The scene: `work/state-backups/rocky-cell-match-start.p2s` advanced past the
`Fight!` banner, Cell 1st Form on Rocky Area - Evening. **`R3` transforms** -
transformations cost blast stock, not ki, and Cell carries 3 against a cost of
2. The move puts the fighter in **state 239** (`FUN_001FE960`), which it is
still in 700 vsyncs later, so 239 is the second form rather than the cinematic.

#### Turning "it looks broken" into a number

A desynchronised cinematic cannot be scored by duration - both arms enter 239 at
vsync 10 and neither leaves. What differs is *what is on screen at a given real
time*, so the metric is the mean absolute pixel difference against the unpatched
arm at four fixed vsyncs (210, 252, 336, 420), each arm frame-stepped from the
same state. It is exactly reproducible: the unpatched arm scores **0.00** against
itself.

At 210v and 252v the 30fps game shows Android 17 and then Cell; the patched game
shows **empty desert**. By 420v the patched arm carries a large red polygon
artifact. That is the user's "missing models and camera issues", and the patched
cinematic runs roughly 126 vsyncs *behind* the 30fps one - late, not early.

#### Which group does it: none of them

| group set | drift |
|---|---|
| unpatched 30fps | 0.00 |
| `60FPS - battle` alone | **51.29** |
| `60FPS - battle` + `animation clock` | 25.05 |
| `60FPS - battle` + `aura update rate` | 50.95 |
| `shipped` (5 groups) | 24.80 |
| `nofx`, `noseqwait2`, `nopursuit`, `nocamera` | 24.50 |
| `nomouth` | 24.22 |
| `full` (28 groups) | 22.11 |

**The base 60fps switch breaks it on its own**, the animation clock recovers
about half, and every other group in the patch - sequence wait, camera pacing,
mouth clock, the phase timers - moves it by less than three points between them.
So this is an uncompensated system in exactly the same sense as everything else
this project has fixed. Nothing regressed; the cinematic was never covered.

#### Why the usual instrument finds nothing

`ratediff` across the transformation window, holding `R3`, reports 28 words still
at 2x, and all of them are the families that read 2x by design - the tween
counters stepping -1.0 a tick and the manager block around `01870000`. There is
no world quantity running at double speed here.

That is consistent with what the pictures show. The defect is not a value moving
too fast; it is **beats firing in the wrong order or at the wrong moment** - a
model that has not spawned when the camera cuts to it. A rate scan cannot see
that. `tools/eventdiff.py`, which stops both arms at the same *event* rather
than the same time, is the instrument for it, and that is the next step.

State 239's handler does carry a phase timer at `001FEB3C`, counting to `0x3D`
(61 frames), and it is one of the 21 sites the reinstated phase-timer group
gates. Gating it is worth 2 points of the 25 and no more, so the 61-frame beat
is one of several and not the one that matters.

#### Not established

- #10 (Vegeta Scouter's Great Ape transformation) has **not** been tested. It is
  a transformation cinematic too, so the same class is likely, but "likely" is
  what the triage table already got wrong once.
- What actually paces the cinematic. The measurement above says which groups do
  *not* fix it, which is not the same as knowing what would.

## 2026-09-21 - #39 reproduced: state 93, and four phase numbers gated as clocks

The user saved a state in the freeze on their EmuDeck install, running v24
exactly (its patch lines match `patch/428113C2.pnach` line for line). PCSXROO
refuses a v2.5.274 state, so `tools/transplant.py` carried its EE memory into a
running battle and wrote it back out as a native state.

### What the fighter is doing

| | |
|---|---|
| Fighter | P1, Super Saiyan Goku, standing on a raised pipe (y = -338) |
| Fighter state | **93**, handler `FUN_001E5CE8`, shared by states 90-93 |
| Pending state | `0xFFFFFFFF` |
| Phase `fighter+0x3D8` | **0**, never moves |
| Sub-counter `fighter+0x3DC` | 0, 1 ... 7, 0, 1 ... every tick, forever |
| Picture | the model is drawn on some frames and missing on others |

`FUN_001E5CE8` switches on `fighter+0x3D8`, values 0 to 3. Phase 0 is an 8-tick
loop on the sub-counter: it restarts the pose at 1, sets it again at 2, and at
8 resets the sub-counter to 0 and leaves through `001E6060`, which adds one to
the phase. `001E6060` was one of the 21 sites `[60FPS - state phase timers]`
gated. If the loop ends on an odd tick, the phase is not advanced and phase 0
runs again. The loop is 8 ticks long, so it ends on an odd tick every pass after
that. Traced on the user's state, 40 ticks: phase 0 throughout, the sub-counter
wrapping at frames 13109, 13117, 13125 and so on, all odd.

This is the state 157 trap again, not a new mechanism. It is a phase number
gated as if it were a clock, and the loop feeding it has an even period.

### The audit that missed it

The 2026-09-16 audit called 21 of the 22 sites clocks, "each compared against an
authored count". Four are not compared against anything. Each adds one and
branches away:

| site | handler | states | what it is |
|---|---|---|---|
| `001E6060` | `FUN_001E5CE8` | 90-93 | phase 0 -> 1, after the 8-tick loop |
| `001F3320` | `FUN_001F3270` | 44 | phase 0 -> 1, once |
| `001F9D48` | `FUN_001F97F8` | 301-303, 313-315 | phase 1 -> 2, once `FUN_001D6360` reports ready |
| `001FBBD0` | `FUN_001FBA90` | 260 | phase 0 -> 1, once `FUN_001D6360` reports ready |

`001F9D48` and `001FBBD0` are the same shape as `001E6060`. Each advance is
conditional, and on an odd tick it is simply lost. Whether the condition holds
on the next tick decides whether that is a one-tick delay or another trap.
`FUN_001D6360` reads a flag on a global object, and `FUN_001D63D8`, called in the
same branch, sets that object's state to 4. Nobody has checked whether the flag
survives, and the fix does not need to know.

The test that separates the two is mechanical and needs no judgement. A clock
is compared against its bound on the instruction straight after the add
(`slti`/`slt` on the same register). An index is not. Run over all 28 sites
`phasetimer.py` finds:

| verdict | sites | gated |
|---|---|---|
| clock | 21 | 17. The other 4 (`001F1C74`, `001FCE34`, `001FF9A8`, `001FFC10`) were excluded by measurement as input windows |
| index | 7 | none now. `001E6F40`, `001F31C0` and `001FBF28` were already out; the four above leave |

The test agrees with every exclusion made by measurement that was an index,
and with every clock that was kept. It is necessary, not sufficient: a clock
can still be an input window that must not be slowed.

### The fix, and how it was checked

The four gates and their trampolines are removed, and the group now writes the
game's own instruction back at each site. A save state cut under v24 still holds
the old hooks in RAM, and without those four lines it would keep them until the
next boot.

| arm, from the user's own state | result |
|---|---|
| v24 | phase 0 for as long as it was watched; model strobing in consecutive screenshots |
| v24, `001E6060` restored by hand | phase 1 on the next pass, 2, 3, then idle (state 11) 68 ticks later |
| the exported fix, state loaded with no hand edits | the hook is overwritten on the first vsync; idle 69 ticks later, model drawn every frame |

The exported patch differs from v24 only in this group, 557 patch lines down
to 521.

### Not established

- **Which move enters states 90-93.** Offensive Vanishing (`Circle` + a
  direction mid-rush) is states 32-35, and a Step-In, a Dragon Dash, a Z-Burst
  Dash, a jump and a landing from flight do not enter 90-93 from Rocky Area
  either. The four variants each pick a pose set (`0x5F`, `0x62`, `0x65`,
  `0x68`), and phase 2 moves the fighter by a distance built up in phase 0
  (`fighter+0x3E8`). #39's first report was SSJ2 Teen Gohan mid-combo.
- **Phase 0 still runs at double speed.** The 8-tick sub-counter is a clock of
  its own, `fighter+0x3DC`, and nothing compensates it, so phase 0 takes 133ms
  instead of 267ms. That is a timing error, not a freeze, and it is not this
  fix.

## 2026-09-30 - issue #115: a rushing Blast 2's time limit is seconds * 30

An audit of the 145 `lui $at, 0x41F0` sites. 80 of them run somewhere in the
rig's scenes (9 of those patched by now), found by breaking on all of them over
26 scenes. `001F9260` is one that no group covered.

### The limit

`FUN_001F8C00` is the handler of fighter states 284-289 (the state table has it
at `002C4DEC`-`002C4E00`): the rush of a rushing Blast 2. For the animations in
which the fighter is closing on the opponent it runs, once a tick:

    001F9240  lw    $v0, 0($s6)          fighter+0x3DC
    001F924C  addiu $v0, $v0, 1
    001F9258  jal   FUN_00210E28         params+0x1C of this blast: seconds
    001F925C  sw    $v0, 0($s6)
    001F9260  lui   $at, 0x41F0          * 30.0
    001F926C  c.olt.s $f0, $f20          limit < counter: the rush is over

`fighter+0x3D8`, next to it, counts 16 ticks of being in range and is one of
the clocks `[60FPS - state phase timers]` gates. `+0x3DC` is not gated.

### Measured

Cell 2nd Form's Drain Life has a limit of 1.5 s. Save state 7 is a 1P vs 2P
match against Ultimate Gohan; the scene backs Cell away with `Down` under the
30fps words until the two are a set distance apart, waits 60 vsyncs, applies the
arm under test and fires `L2 + Up + Triangle`. The stage wall stops him at 780
units.

| start distance | 30fps | 60fps before | with `001F9260` at 60.0 |
|---|---|---|---|
| 309 | grab v110, counter 10 | grab v109, counter 20 | grab v109, counter 20 |
| 510 | grab v130, counter 20 | grab v130, counter 41 | grab v130, counter 41 |
| 609 | grab v142, counter 26 | gives up v140 at 46, 72 units short | grab v141, counter 52 |
| 701 | grab v152, counter 31 | gives up v140, 164 short | grab v151, counter 62 |
| 780 | grab v160, counter 35 | gives up v140, 243 short | grab v159, counter 70 |

`[60FPS - rushing Blast 2 time limit]` is that one word.

### Left alone

- **`FUN_001F7DE8`, states 275-277.** The same comparison at `001F8398`, against
  `fighter+0x3D8` and with the limit less one. None of the seven blast inputs
  from any of the ten save states enters those states, so there is nothing to
  measure a change against.
- **The limit itself.** 30fps would run out at about 940 units by the counter's
  pace; the wall is at 780.

### The rest of the audit

Read and found already covered: the meter functions that divide by 30
(`FUN_001C3A20` and its three siblings, `FUN_0020F070`, `001E1AF8`) are all
called from the economy `[60FPS - meter economy]` gates; the combo record's
display timer (`001CE920`, `001CE994`, victim+0xD48) counts down every second
vsync in both arms; the camera shot length at `001C7944` feeds the countdown
`[60FPS - camera pacing]` gates; `001C4550` sets the animation step that
`[60FPS - animation clock]` halves when it is read.

Found and fixed under their own issues: the blast ramps (#109), the arc effect
class (#111), and the fourth word of `[60FPS - effect rotation]` (#113).

Inside an effect class whose update a group already runs at 30Hz, so taken as
covered without a measurement of their own: the sprite class (`00182F14`,
`00183034`, `0018352C`, `00183A54`, `00186358`, `0018637C`, `001865F0`), the
spiral (`00188128`, `0018883C`, `0018A484`, `0018BFD4`), the swirl (`00190EF8`,
`001917B8`, `001918B4`, `00191910`), the lightning (`0017C824`), the rays
(`001689EC`, `0016971C`), the sparks (`0017DD9C`) and the track class
(`0019DAFC`).

Checked on 2026-10-02:

| site | what | verdict |
|---|---|---|
| `00210064` | ki blast turn rate | fixed under #117 |
| `0021015C` | ki blast life in ticks, `node+0x5B4` | counted by `[60FPS - projectile life]` |
| `00211584` | `fighter+0xE40`, the post-cinematic timer | counted by #35's combat timers |
| `002115CC` | beam duration in states 272-274 (`FUN_001F7860`) | its counter's load is gated |
| `0021277C` | a Blast 1's effect length (`params+0xA0`) | read by the paralysis and Solar Flare code, both counted in real time |
| `001795D4`, `00179B9C` | called only from the lightning class | gated with it |
| `00192EF4` | called only from the swirl class | gated with it |
| `001A11E0`, `001A1738` | called from the beam-impact burst class | gated with it |
| `00245794` | `FUN_00245740` makes one of ten objects that `FUN_002454E0` updates once a tick: a life in ticks (`+0x08`, seconds * 30) and values that grow and fade over it | **runs at double speed**: a ki charge's object lives v164-v209 at 30fps and v164-v188 in the build. With the pool switched off the picture loses a faint ring round the charge, a 2.7 mean pixel change. Fixed under #137: it is the Max Power shockwave. |

Not checked yet: `001374E0`, `0014B284`, `0014B638`, `0014BA5C`, `0014C06C`,
`0014D708`, `00160168`, `0016A2D4`, `0019522C`, `00195514`, `00195F90`,
`00195FB4`, `00196070`, `0019A9C4`; the 64 unpatched sites that never ran in a
rig scene; and `FUN_001DC4C0`, which adds seconds * 30 to a battle counter
(`battle+0x1C`) only in game modes 4 and 0x1B.

## 2026-10-09 - issue #137: the Max Power shockwave

The ring object at `00245794` in the table above. Holding `L2` with Goku
(Early) at full Ki fills the Max Power gauge at about v164, and `FUN_00175F40`
makes one ring through `FUN_00245740`. Drawn, it warps the background in a band
that spreads out from the fighter: photographed at 30fps with and without the
pool's draw (`FUN_00245668` returning at once), the rocks behind Goku bend
along the ring.

| what | where |
|---|---|
| the pool | 10 objects of `0x470` bytes at `**(gp-0x566C)`; the counts of live ones at `+0xA4` / `+0xA8` of the header |
| update, once a tick | `FUN_002454E0`, from `FUN_002456E8`, which skips it while paused and always calls the draw |
| one object's tick | `FUN_00244E20` |
| the maker | `FUN_00245740`, 7 call sites |

`FUN_00244E20` per tick: life `+0x08` -= 1 (gone at 0); radius `+0x0C` += speed
`+0x10` while the radius is at most 600; speed += `+0x14`; width `+0x18` +=
`+0x1C`; and while the life is at most 6, alpha `+0x20` += `+0x24` (clamped at 0).
The maker sets life = seconds * 30.0 (`00245794`), `+0x14` = -(speed * 0.3) /
life and `+0x1C` = (width * 3.2) / life, and the alpha 0.502 and its step -0.0837
(`gp-0x5C50`, `gp-0x5C4C`).

`[60FPS - max power shockwave]` scales the ring where it is made. Life doubles,
which halves both divided steps; the starting speed and the slow-down's
numerator are halved as well, so the speed is halved and the slow-down
quartered, as a per-tick and a per-tick-squared quantity must be. The fade
starts 12 ticks from the end and its step is halved in `.data` (one reader).

| Goku (Early), from the cheat file | 30fps | 60fps before | with the group |
|---|---|---|---|
| ring alive | v164-v209, 46 vsyncs | v165-v187, 23 | v165-v211, 47 |
| radius 10 vsyncs in | 68 | 113 | 63 |
| radius at mid-life | 122 | 122 | 121 |
| radius at the end | 208 | 208 | 211 |
| fade, 0.50 to 0 | over 14 vsyncs | gone before it starts | over 14 vsyncs, in half-steps |

A 30Hz gate on `FUN_002454E0` gives the same curve and was tried first. It was
not kept: the draw renders any live object without checking it has had its
first update, and `FUN_00244D00` hands out a slot without clearing it, so a
ring made on an odd tick would be drawn for one frame with its slot's previous
vertices.

A trap met on the way: in this scene two identical 60fps runs photograph
differently at the same vsync although their RAM is identical, so the ring
could not be isolated by photographs at 60fps. The 30fps arm photographs
reproducibly. The comparison above is read from RAM.

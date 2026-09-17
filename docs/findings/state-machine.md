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

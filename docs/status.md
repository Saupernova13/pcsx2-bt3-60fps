# Build confidence ladder

Which build to trust, and why. Set by testing **in play**, not by measurement.
Newest at the top. `patch/428113C2.pnach` currently holds **v23**.

What every version changed and discovered, v01 through v23, is in
[`versions/`](versions/README.md). This page is only about which build to trust.

> **\*** means fixed and verified by measurement against the 30fps oracle -
> same save state, same input, same number of vsyncs - but **not yet confirmed
> in play by the user**. A star is provisional: nothing is settled here until it
> has been played. **v17, v21, v22 and v23 are starred** (v23 is v22's patch) - v22 half-cleared: the user
> confirmed its duration in play on 2026-09-12, but not yet who wins a clash.

**v16, v18 and v19 are confirmed in play by the user, 2026-09-09.** Ki blast
travel, Buu's Super Kamehameha *and his breath*, and the screen fade - the user
calls these milestones. **v17 is not confirmed**: Frieza's I Might Die This Time rocks still feel
unchanged in play. The measurements say why, and it is not that the fix failed -
see the v17 section. It stays starred.

**v13, v14 and v15 are all confirmed in play by the user, 2026-09-08** - the
Lightning Attack after a Full Power Smash, the Cell Perfect Barrier camera, and the
mouths, in the cut-in AND in the pre-fight intro. v14's star is cleared.
None of it touches v12's input-timing flag, which still stands.

> **Deploy `patch/428113C2.pnach`, never `wip/working.pnach`.** The working
> pnach carries five groups that must never be enabled, and `deploy.py` used to
> turn on every group in whatever file it was given. The user's EmuDeck install
> had been running all 24 of them - quarter-speed animation, no beams, broken
> ground movement, the state 157 trap - since at least 2026-09-05, while every
> test ran against PCSXROO. `deploy.py` now refuses them.

| Build | Groups | Confidence | Ultimate Blast | Notes |
|---|---|---|---|---|
| `v23-known-issues-refresh` | 26 | **DURATION CONFIRMED IN PLAY, OUTCOME NOT YET\*** | correct | Patch lines identical to v22. The shipped header's KNOWN NOT FIXED list gains v22's own gap - the CPU ends a little weak in a Beam Struggle - which had been written in after v22 was tagged |
| `v22-beam-clash` | 26 | **DURATION CONFIRMED IN PLAY, OUTCOME NOT YET\*** | correct | Adds `beam clash` - the whole beam-clash contest is counted in ticks, so at 60fps it played in half its real time (2.17s against 4.34s) while the CPU's synthetic stick rotated once per tick. The winner flipped. Now 4.30s, and the player's count matches the 30fps game exactly |
| `v21-rush-struggle` | 25 | **FIXED, NOT YET PLAY-TESTED\*** | correct | Adds `rush struggle` - the CPU's synthetic stick rotates once per tick, so at 60fps the AI out-rotated the player twice as fast and the winner of a clash flipped |
| `v20-known-issues-refresh` | 24 | **CONFIRMED IN PLAY** | correct | Patch content byte-identical to v19. The shipped header's KNOWN NOT FIXED list had gone stale - it still named the intro mouths and the transformation overshoot, both fixed and confirmed |
| `v19-screen-fade` | 24 | **CONFIRMED IN PLAY** | correct | Adds `screen fade` - the game's fullscreen fade service counted its phases in 30Hz frames, so every fade in the game ran in half its real time |
| `v18-beam-object-travel` | 23 | **CONFIRMED IN PLAY** | correct | Adds `beam object travel` - Buu's Super Kamehameha and its class crossed the gap at 2x |
| `v17-blast-object-travel` | 22 | **MEASURED, NOT FELT IN PLAY\*** | correct | Adds `blast object travel` - the rocks of Frieza's I Might Die This Time and their class crossed the gap at 2x |
| `v16-projectile-travel` | 21 | **CONFIRMED IN PLAY** | correct | Adds `projectile travel` - ki blasts crossed the ground at 2x speed. The first fix here that changes how the game PLAYS |
| `v15-mouth-clock` | 20 | **CONFIRMED IN PLAY** | correct | Adds `mouth clock`. Confirmed 2026-09-08; inherits v12's flag |
| `v14-camera-pacing` | 19 | **CONFIRMED IN PLAY** | correct | Adds `camera pacing`. Confirmed 2026-09-08, star cleared; inherits v12's flag |
| `v13-pursuit-stomp` | 18 | **CONFIRMED IN PLAY** | correct | Adds the two pursuit groups. Confirmed 2026-09-08; inherits v12's flag |
| `v12-restore-sequence-wait` | 16 | **FINE, FLAGGED** | correct | Carries the input-timing flag below |
| `v11-back-to-v8-set` | 15 | **DEFINITELY FINE** | **ends early** | The known-good baseline. Fall back here |
| `v10-withdraw-phase-timers` | 16 | superseded | correct | Identical group list to v12 |
| `v09-scripted-clocks` | 17 | **DO NOT USE** | correct | State 157 trap |
| `v08-blast-duration-only` | 15 | fine | ends early | Same group list as v11 |
| `v07-blasts-fixed` | 16 | superseded | - | Contained the withdrawn sequence-rate gate |
| `v05`, `v04` | 16, 15 | **DO NOT USE** | - | Withdrawn: gating deleted the beam |

## v11 - DEFINITELY FINE

The baseline. Confirmed in play: no state 157 trap.

**Its known tradeoff is accepted, not a defect.** The Ultimate Blast ends
early, because `[60FPS - sequence wait]` is absent. Do not re-open that as a bug
against this build - it is the price of the build.

Fall back here if anything later misbehaves.

## v12 - FINE, WITH A STANDING FLAG

Confirmed in play: no trap, and the ultimate's cinematic and charge are correct
again. Differs from v11 by exactly one group, `[60FPS - sequence wait]`.

> **FLAG: POTENTIAL INPUT TIMING ISSUE.**
> This build and **every build from here forward** may carry an input timing
> problem. Reported by the user, currently unconfirmed and uncharacterised.
> Every later build inherits this flag until it is explicitly cleared by
> testing. If input feel is ever in question, compare against v11 first.

## v13 - the Lightning Attack

Adds `[60FPS - knockback flight]` and `[60FPS - pursuit timing]` to the v12 set.
Fixes the Full Power Smash into a Lightning Attack, which missed at 60fps and
landed every time at 30. Five separate durations authored in 30Hz frames, in one
chain; see findings/smash-and-lightning-attack.md for the derivation.

Verified by automated test, not yet by the user:

- Nine press delays from 5 to 45 vsyncs. Before: 0 of 9 connect. After: 9 of 9,
  within 1-3 vsyncs of the 30fps arm at every delay.
- Confirmed with the VM running free and the pad on the wall clock
  (`python tools/stomptest.py --presets off nopursuit full`), which is a
  different instrument from the frame-stepped sweep and agrees with it.
- The charge and ultimate oracles are unchanged to the vsync, so nothing that
  already worked moved.

`nopursuit` is the 16-group v12 set, kept as a named preset so this can be
switched off without editing anything.

**It inherits v12's input-timing flag** - nothing here clears it.

## v14 - camera pacing

One group, `[60FPS - camera pacing]`, and it is not a Cell fix - it is the
camera system. `FUN_001C69C8` updates every camera in the game and lerps its
euler angles toward a per-tick target; both the blend rate (`$f20`, a flat 0.20
a tick) and the scripted camera-move countdown (`fighter+0x558`, a length in
`fighter+0x55C` authored in 30Hz frames) are per-tick and were uncompensated.

Mean absolute camera orientation error against the 30fps arm, Cell's Perfect
Barrier, shot 1: **22.96 degrees -> 1.52**. Peak 89.3 -> 4.2. Halving the blend
alone gives 12.84 and gating the move alone 14.01, so **neither half is a fix on
its own** and `nocamera` (the 18-group v13 set) is kept as a named preset for
diffing.

Global, measured rather than assumed: on Goku's ultimate from save state 8,
which takes no input at all, mean error goes 5.00 -> 1.93 and peak 14.6 -> 0.7.

Confirmed by contact sheet at 0.12s on the wall clock: the fixed arm matches the
30fps arm tile for tile through the orbit, where unpatched 60fps is a beat ahead.

No regression - charge 99, ultimate 161, Lightning Attack still connects, and the
**ordinary** battle camera improves from 3.71 to 2.88 degrees rather than going
sluggish.

**It inherits v12's input-timing flag** - nothing here clears it.

Also in this build: `movieshot.py` and `stomptest.py` no longer reload the save
state after applying a preset. Save state 4 was captured while patched, so that
reload put `[60FPS - battle]` back and the "30fps" arm ran at 60fps. Slot 9 was
captured unpatched, so the v13 pursuit results are unaffected.

## v15 - mouth clock

Adds `[60FPS - mouth clock]`: two hooks, at `0024ED2C` and `0024F3D4`, halving
the per-tick rate of the game's **second** clip player. That player drives the
keyframe tracks a scripted cut-in uses - the mouth among them - and its rate is
2.0 a tick, so at 60fps a track burned its keyframe array in half the real time
and held the last key.

Measured per vsync on Vegeta (Scouter)'s Final Galick Cannon, save state 3, on a
frame-advance film aligned to the first vsync of state 287:

| arm | transitions | first | last | span |
|---|---|---|---|---|
| 30fps unpatched | 10 | v43 | v163 | 2.00s |
| 60fps, v14's 19 groups | 12 | v43 | v115 | 1.20s |
| 60fps, this build | 14 | v43 | v167 | 2.07s |

5.00 open/close transitions a second against 10.00 - exactly 2x - and with the
group the final phrase, which v14 skips entirely, plays again. Every one of the
unpatched arm's ten beats lands within two vsyncs.

No regression: `hitclock.py --baselines` is byte-identical with the group on,
neither hook fires at all in ordinary battle, and the whole-frame difference from
the 30fps reference over the Vegeta cut-in is unchanged at 3.46.

It does change Goku's ultimate, on 90 of 170 vsyncs: the second track object
drives that shot's radial speed-line effect, which was running at 2x for the same
reason. The hit counters land on identical vsyncs either way, so the schedule is
untouched - but this half is **not independently verified as an improvement**,
only as the same correction for the same cause. Worth a look in play.

**Confirmed in play by the user, 2026-09-08.** It still inherits v12's
input-timing flag, which nothing here clears.

## v16 - projectile travel

`[60FPS - projectile travel]`, one hook at `00176A2C`. The effect-node update
steps `pos += vel * step` once a tick with no delta-time term, and for a plain ki
blast that step is 27.7778 units a tick in BOTH arms - so every projectile
crossed the ground at exactly double speed at 60fps.

Measured from training-mode scenes at three ranges, timing flight by the
opponent's reaction, and fitting flight = fixed + gap/speed:

| gap | 30fps | 60fps before | 60fps after |
|---|---|---|---|
| 420 | 58 vsyncs | 42 | **57** |
| 657 | 76 | 51 | **74** |
| 842 | 88 | 57 | **87** |

The travel term is 2.000x and the fix puts every range within two vsyncs of the
unpatched game. Verified as shipped from the pnach, not only as a live poke.

**This is the first fix in this project that changes how the game plays rather
than how it looks** - a blast at double speed halves the time to dodge it.

Two limits, both stated rather than hidden. It does **not** cover Buu's charged
`L2+Up+Triangle`, whose projectile this integrator never touches - there is a
second mover, not yet found. And Frieza's "I might die this time" is untested.

**Confirmed in play by the user, 2026-09-09.** The star is cleared. Verified
against the 30fps oracle at three ranges, as shipped from the pnach, and now in
normal play. **Inherits v12's input-timing flag.**

## v17 - spawned projectile flight

Adds `[60FPS - blast object travel]`. The rocks of Frieza's I Might Die This Time - and everything
else on the same object class - advanced `position += direction * 37.037` per
**tick**, identical in both arms, so they crossed the gap in half the real time.
The fix hooks the one `Vec3Add` both code paths converge on and halves the
advance.

Verified as shipped from the pnach, at three ranges, against the 30fps oracle:
impact moved 103 -> 106, 113 -> 124, 118 -> 134 against 30fps's 110 / 128 / 137.
Inert at idle and for plain ki blasts, so it cannot double-compensate with
`[60FPS - projectile travel]`. Buu's Super Kamehameha is untouched by it, vsync for
vsync - that beam is a different subsystem and is still unfixed.

**It stays starred. The user played it on 2026-09-09 and felt no difference.**

That is not the fix failing - it is the fix being invisible, and the numbers
predicted it. The move is `pre-launch + gap / speed`, and at 30fps the summon
phase alone is **103.2 vsyncs**, with the rocks crossing at 18.75 units/vsync:

| gap | travel share of the move | what the fix can move |
|---|---|---|
| 125 | 6.7 of 110 vsyncs - **6%** | 102 -> 106, **4 vsyncs (67 ms)** |
| 474 | 25.3 of 128 - 20% | 113 -> 124, 11 vsyncs |
| 628 | 33.5 of 137 - 24% | 117 -> 134, 17 vsyncs (0.28 s) |

At the range anyone actually fights at, the rocks are **94% summon animation**,
and halving the travel error moves the impact by a seventeenth of a second.
Nobody could feel that. The measurement was sound and so is the user's report.

**What is left to feel is the summon phase itself**: 98.3 vsyncs at 60fps
against 103.2 at 30, ~5 vsyncs fast, uncompensated, and the same ~5-vsync
pre-launch defect seen on Buu's Super Kamehameha in v18. That is the part of this
move a player can see, and it is not fixed. **Inherits v12's input-timing
flag.**

## v18 - beam object travel

Adds `[60FPS - beam object travel]`. Buu's Super Kamehameha runs on a sibling of
the rock class - `FUN_00155C5C`, `position(+0x60) += delta(+0x80)` - with the
same 37.037 per-tick delta, set once at launch and identical in both arms. The
fix hooks the one `Vec3Add` at `00156004` that both code paths converge on.

Verified as shipped from the pnach at two ranges: hit moved 44 -> 45 at gap 86
and 59 -> 76 at gap 657, against 30fps's 50 and 81. The travel component paces
18.42 units/vsync in both arms, an exact match; the residual ~5 vsyncs is the
pre-launch animation, a separate defect.

Inert at idle, for plain ki blasts and for Frieza's I Might Die This Time rocks - those re-measure at
v124, unchanged - so it cannot double-compensate with v16 or v17.

**Confirmed in play by the user, 2026-09-09.** The star is cleared. The user
also confirms **Buu's breath attack** is fixed by this group - a move that was
never measured, and evidence the hook sits on the class rather than on the one
blast it was found through. **Inherits v12's input-timing flag.**

## The state 157 trap

Goku parks in fighter state 157 (`FUN_001E6DC8`), an airborne dash/flight state,
with pending state `0xFFFFFFFF` - no queued transition - and no button held. The
game keeps ticking normally; only that fighter is trapped. A save-state reload
clears it.

Seen on v9 (17 groups). Not seen on v11 (15) or so far on v12 (16). The group
that differs and is out of both is `[60FPS - state phase timers]`, which is the
only group that gates counters **inside the fighter state machine** and whose 28
sites were all validated against two **grounded** oracles - a held charge and a
mashed rush. No airborne state was ever tested, and the trap is airborne.

That is a strong circumstantial case, not a proof. It was never reproduced under
controlled conditions.

## v19 - screen fade

Adds `[60FPS - screen fade]`, two words. `FUN_00172810` is the game's fullscreen
fade service - a colour, a fade-in, a hold and a fade-out - and its init at
`FUN_00172718` takes durations in **seconds** and multiplies by a hard-coded
30.0. The same defect as the tween constructor at `00267AC8`, in a second
general-purpose service. One word makes it 60.0, which doubles all three phase
counts and their divisors together, so the blend curve is unchanged and only its
rate halves. The 180-tick hold cap at `001728C8` is a separate literal.

That the callers speak seconds is read straight out of the ELF: the static
descriptors at `002ECCC0` and `002ECCF0` hold 0.5 / 1.0 / 0.5 and 1.0 / 0 / 1.0
seconds. So this fixes every fade in the game at once, not one move's flash.

Verified as shipped from the pnach on Vegeta (Scouter)'s Final Galick Cannon,
save state 3, filmed per vsync on mean luma:

| arm | full white | lifts at | scene behind it |
|---|---|---|---|
| 30fps oracle | v446..v495 | v508 | mean 170 |
| 60fps before | v437..v460 | v476 | **mean 90 - the animation, exposed** |
| 60fps after | v443..v491 | v504 | mean 168 |

The fall is value-for-value the 30fps curve over the same 28 vsyncs. On the node
itself the durations go 15/30 frames to 30/60 and the blend step 1/15 to 1/30.

No regression: the ultimate's eleven state transitions land on identical vsyncs
with the group on and off, so the fade moves no beat. Frieza's I Might Die This Time rocks and Buu's
Super Kamehameha construct no fade node at all, so it cannot touch them.

**Confirmed in play by the user, 2026-09-09.** The star is cleared. The
Galick Cannon's white flash now covers what it exists to cover. **Inherits
v12's input-timing flag.**

## Fixed somewhere between v13 and v19, by nothing anyone aimed at it

On 2026-09-09 the user reports that **transformations** and **explosive waves**
are both correct in play. Neither was ever worked on:

- **Transformations ran ~0.3s LONG** (item 8: Cell Perfect -> Super Perfect,
  Frieza final -> 100%). The only defect on the list with the opposite sign.
  Never investigated, never had a group written for it.
- **Explosive waves** (the second half of item 1) were never separately checked
  after the travel work; the three movers were measured on ki blasts, rocks and
  Buu's Super Kamehameha only.

The explosive wave is plausibly `[60FPS - projectile travel]` or one of the two
object movers reaching a fourth caller, which is what a class-level hook is for.
**The transformation overshoot has no candidate mechanism at all** - nothing in
v13..v19 lengthens or shortens a transformation, and the fixes that landed in
that window all make things *slower*, which is the wrong direction for an
overshoot.

Recorded as fixed because the user played it. **Recorded as unattributed
because it is: an unattributed fix can regress without anyone knowing why.** If
a transformation ever runs long again, this is the note to come back to.

## v24 (proposed) - the smash charge

Adds `[60FPS - smash charge]`, one data word. Closes issue #6: a smash attack
charges in half the real time at 60fps, and the Perfect Smash - releasing on the
exact moment level 3 is reached - gets half as long to do it in.

`FUN_001E33E0` adds `gp-0x6D80` (`002FD4F0`, 0.0444444 = 1/22.5) to the charge
every tick. One reader, so it is halved in data. All eleven charge states use
it: 71-76, the six Smash directions, and 83-87.

| Cell, Rocky Area, Square held | charge fills in | Perfect Smash accepted on |
|---|---|---|
| unpatched 30fps | 44 vsyncs | **2 vsyncs** |
| v23, no gate | 22 vsyncs | 1 vsync |
| **v23 + this group** | **44 vsyncs** | **2 vsyncs** |

The charge is not merely the same length - it is the same sequence, 0.04 0.09
0.13 ... 0.98 1.00, sample for sample against the 30fps arm. The window was
measured by releasing on each vsync in turn with a breakpoint on the grant at
`001E4810`.

**Not confirmed in play.** Only the neutral Smash was tested, on one character.

## v20 - the shipped header caught up

**No patch change.** The patch at the `v20-known-issues-refresh` tag has the
same 25 groups and the same 279 patch lines as v19, verified line for line.

What changed is the `KNOWN NOT FIXED` block the shared file carries at the top,
which is the only documentation most people who use this patch will ever read.
It was still telling them the pre-fight intro's mouths do not move (fixed in
v15, confirmed 2026-09-08) and that transformations run long (confirmed fixed
2026-09-09). It now names what is actually left: the ultimate's beam, the fast
summon phase on Frieza's I Might Die This Time rocks and Buu's Super Kamehameha, the intro animation
pacing, and the never-re-checked camera on a body-erasing death.

Cut as its own version rather than rewriting v19 in place - a release is a
record, and v19's file stays as it shipped.

## v21 - the Rush Struggle

Two rush attacks collide, both fighters enter state 250, the game counts hits
into `fighter+0xE50` and at `001D945C` picks whoever has more. All of it is
authored in ticks. A player's hands do not speed up with the tick rate; the
AI's do - `FUN_001D4370` branches on **`fighter+0x1278`**, the game's own
human/AI flag, and feeds an AI fighter synthetic input whose stick snaps
through cardinal directions once per tick.

Driving both sticks at a true 5 rotations a second, per vsync so the hand speed
is identical in both arms: **30fps ends 66-59 to the player, unpatched 60fps
ends 53-47 to the CPU.** The outcome flips - this is the first defect found in
this project that decides who wins a fight.

The fix gates only the AI's rotation, on even ticks, using that flag. Swept
across hand speeds the winner matches the 30fps oracle at 2, 5 and 8 rotations
a second; 3.5 is a coin flip in the oracle itself (55-57).

The struggle still runs in 1.63s rather than 2.95s, so the counts read low - the
88-tick duration is a separate defect and does not affect who wins.

**Starred pending the user's own play-test.** **Inherits v12's input-timing
flag.**

## v22 - the Beam Struggle

Two beams collide and both players rotate their sticks. There is no counter on
screen, so this was measured against the game's own internals: rotations land in
`fighter+0xE4C`, and an event manager, `FUN_001D8E50`, runs the contest one call
per tick - 30 ticks of each fighter's introduction, 46 in which a tug moves one
step per tick toward whoever leads, 16 to show the result, then a few to drive
it out. The sign of the tug picks the winner.

Every part of that is authored in ticks, so at 60fps the clash played in **half
its real time** while a human's hands did not speed up and the CPU's synthetic
stick did. From the user's own save state, both sticks turned at a true 5
rotations a second: **30fps ends 91-88 to the player, 60fps ended 61-62 to the
CPU.** The outcome flipped.

The fix doubles every phase length so each phase lasts its 30fps real time,
halves the clash point constant so the point lands exactly where 30fps puts it
(and now moves smoothly every frame rather than in 30Hz steps), and gates the
AI's rotation to every other tick through the game's own human/AI flag. The
player's input is untouched.

Verified against the 30fps oracle with the 60fps base patch alone, where the AI
behaves tick for tick as it does at 30fps: **72-72 idle, 91-86 at 5 rotations a
second, over the same 4.3 seconds.**

**Known gap:** with every group enabled the CPU ends 10-18% below the 30fps
game, because the correct beam travel speed changes where the clash forms and
the AI reacts to that. At 3.5 rotations a second - a near-tie the 30fps game
gives the CPU 73-75 - this build gives it to the player 73-69. Every other speed
tested picks the 30fps winner.

**Play-test, 2026-09-12:** the user played a Beam Struggle from their own save with
v22 installed and confirmed the duration - "it indeed was fixed in terms of
duration". The outcome is still unreported, so the star stands.

**The player's input rate is deliberately untouched.** The gate is AI-only, so a
human's stick is still read every tick, 60 times a second. Below about 7.5
rotations a second that is indistinguishable from 30fps - the counts are
identical, 55/55, 73/73, 91/91 - and above it the 60fps build counts crossings
the 30fps game aliases away. Matching the original exactly would mean throwing
away input the player can feel themselves giving. See docs/findings/struggles.md.

## v23 - the shipped header caught up with the Beam Struggle

**No patch change.** The patch at the `v23-known-issues-refresh` tag has the
same 27 groups and the same 313 patch lines as v22; only comments differ.

v22 was tagged before its known gap - the CPU ending 10-18% low in a Beam Struggle -
was written into the `KNOWN NOT FIXED` block, so the file people installed never
mentioned it. v23 is that file. Its confidence is v22's, star and all.

It is the first version published as a GitHub Release, with the patch attached.

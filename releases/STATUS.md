# Build confidence ladder

Which build to trust, and why. Set by testing **in play**, not by measurement.
Newest at the top. `releases/latest/` currently holds **v16**.

**v13, v14 and v15 are all confirmed in play by the user, 2026-09-08** - the
pursuit stomp after a heavy smash, the Cell Perfect Barrier camera, and the
mouths, in the cut-in AND in the pre-fight intro. v14's star is cleared.
None of it touches v12's input-timing flag, which still stands.

> **Deploy `releases/latest/`, never `patches/428113C2.pnach`.** The working
> pnach carries five groups that must never be enabled, and `deploy.py` used to
> turn on every group in whatever file it was given. The user's EmuDeck install
> had been running all 24 of them - quarter-speed animation, no beams, broken
> ground movement, the state 157 trap - since at least 2026-09-05, while every
> test ran against PCSXROO. `deploy.py` now refuses them.

| Build | Groups | Confidence | Ultimate's blast | Notes |
|---|---|---|---|---|
| `v16-projectile-travel` | 21 | **FIXED, NOT YET PLAY-TESTED\*** | correct | Adds `projectile travel` - ki blasts crossed the ground at 2x speed. The first fix here that changes how the game PLAYS |
| `v15-mouth-clock` | 20 | **CONFIRMED IN PLAY** | correct | Adds `mouth clock`. Confirmed 2026-09-08; inherits v12's flag |
| `v14-camera-pacing` | 19 | **CONFIRMED IN PLAY** | correct | Adds `camera pacing`. Confirmed 2026-09-08, star cleared; inherits v12's flag |
| `v13-pursuit-stomp` | 18 | **CONFIRMED IN PLAY** | correct | Adds the two pursuit groups. Confirmed 2026-09-08; inherits v12's flag |
| `v12-restore-sequence-wait` | 16 | **FINE, FLAGGED** | correct | Carries the input-timing flag below |
| `v11-back-to-v8-set` | 15 | **DEFINITELY FINE** | **ends early** | The known-good baseline. Fall back here |
| `v10-withdraw-phase-timers` | 16 | superseded | correct | Identical group list to v12 |
| `v9-scripted-clocks` | 17 | **DO NOT USE** | correct | State 157 trap |
| `v8-blast-duration-only` | 15 | fine | ends early | Same group list as v11 |
| `v7-blasts-fixed` | 16 | superseded | - | Contained the withdrawn sequence-rate gate |
| `v5`, `v4` | 16, 15 | **DO NOT USE** | - | Withdrawn: gating deleted the beam |

## v11 - DEFINITELY FINE

The baseline. Confirmed in play: no state 157 trap.

**Its known tradeoff is accepted, not a defect.** The ultimate's blast ends
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

## v13 - the pursuit stomp

Adds `[60FPS - knockback flight]` and `[60FPS - pursuit timing]` to the v12 set.
Fixes the heavy smash into Circle pursuit stomp, which missed at 60fps and
landed every time at 30. Five separate durations authored in 30Hz frames, in one
chain; see findings.md for the derivation.

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

No regression - charge 99, ultimate 161, pursuit stomp still connects, and the
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

**Starred pending the user's own play-test**, like v14 was. Verified against
the 30fps oracle at three ranges and as shipped from the pnach, but not yet
seen in play. **Inherits v12's input-timing flag.**

## v17 - spawned projectile flight

Adds `[60FPS - blast object travel]`. Frieza's summoned rocks - and everything
else on the same object class - advanced `position += direction * 37.037` per
**tick**, identical in both arms, so they crossed the gap in half the real time.
The fix hooks the one `Vec3Add` both code paths converge on and halves the
advance.

Verified as shipped from the pnach, at three ranges, against the 30fps oracle:
impact moved 103 -> 106, 113 -> 124, 118 -> 134 against 30fps's 110 / 128 / 137.
Inert at idle and for plain ki blasts, so it cannot double-compensate with
`[60FPS - projectile travel]`. Buu's charged blast is untouched by it, vsync for
vsync - that beam is a different subsystem and is still unfixed.

**Starred pending the user's own play-test.** **Inherits v12's input-timing
flag.**

## v18 - beam object travel

Adds `[60FPS - beam object travel]`. Buu's charged blast runs on a sibling of
the rock class - `FUN_00155C5C`, `position(+0x60) += delta(+0x80)` - with the
same 37.037 per-tick delta, set once at launch and identical in both arms. The
fix hooks the one `Vec3Add` at `00156004` that both code paths converge on.

Verified as shipped from the pnach at two ranges: hit moved 44 -> 45 at gap 86
and 59 -> 76 at gap 657, against 30fps's 50 and 81. The travel component paces
18.42 units/vsync in both arms, an exact match; the residual ~5 vsyncs is the
pre-launch animation, a separate defect.

Inert at idle, for plain ki blasts and for Frieza's rocks - those re-measure at
v124, unchanged - so it cannot double-compensate with v16 or v17.

**Starred pending the user's own play-test.** **Inherits v12's input-timing
flag.**

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
with the group on and off, so the fade moves no beat. Frieza's rocks and Buu's
charged blast construct no fade node at all, so it cannot touch them.

**Starred pending the user's own play-test.** **Inherits v12's input-timing
flag.**

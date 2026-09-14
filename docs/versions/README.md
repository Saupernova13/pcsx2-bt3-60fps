# Version history

Every version of the patch: what it changed over the one before it, and what was
discovered on the way. Each note is written from the release file at its tag, the
commits that produced it, and the findings log of the time.

**The patch to install is always [`patch/428113C2.pnach`](../../patch/428113C2.pnach).**
Every version below is also a git tag, and each note ends with the command that
recovers that version's file.

| version | date | groups | what it did | confidence |
|---|---|---|---|---|
| [`v01`](v01-60fps-input-fixed.md) | 2026-08-22 | 4 | 60fps battles: animation rate, menu repeat and the 128 combat input counters | confirmed working |
| [`v02`](v02-airborne-and-hover.md) | 2026-09-05 | 13 | animation clock, the ki aura, particles, tweens, four airborne channels and the hovering idle | aura and hover confirmed in play |
| [`v03`](v03-blast-hit-cadence.md) | 2026-09-06 | 14 | multi-hit blasts land their hits at the real rate | superseded |
| [`v04`](v04-blast-effect-rate.md) | 2026-09-06 | 15 | gated the blast effect update - deleted the beam | **do not use** |
| [`v05`](v05-blast-sequence-rate.md) | 2026-09-06 | 16 | gated the ultimate's sequence controller - kills charged blasts | **do not use** |
| [`v06`](v06-blast-effect-duration.md) | 2026-09-06 | 15 | withdrew both gates; halved all nineteen blast effect steps instead | superseded |
| [`v06b`](v06b-withdraw-broken-blast-groups.md) | 2026-09-06 | 14 | the withdrawal alone - v03's group list | superseded |
| [`v07`](v07-blasts-fixed.md) | 2026-09-06 | 16 | restored the sequence gate, wrongly believed innocent | superseded |
| [`v08`](v08-blast-duration-only.md) | 2026-09-06 | 15 | withdrew the sequence gate for good | fine, ultimate ends early |
| [`v09`](v09-scripted-clocks.md) | 2026-09-07 | 17 | scripted-sequence waits and fighter state phase timers at 30Hz | **do not use** - state 157 trap |
| [`v10`](v10-withdraw-phase-timers.md) | 2026-09-07 | 16 | withdrew state phase timers | superseded |
| [`v11`](v11-back-to-v8-set.md) | 2026-09-07 | 15 | withdrew sequence wait too - v08's group list | **definitely fine** - the baseline |
| [`v12`](v12-restore-sequence-wait.md) | 2026-09-07 | 16 | restored sequence wait | fine, flagged |
| [`v13`](v13-pursuit-stomp.md) | 2026-09-07 | 18 | the heavy smash into Circle pursuit stomp lands at 60fps | confirmed in play |
| [`v14`](v14-camera-pacing.md) | 2026-09-08 | 19 | every camera paced by real time | confirmed in play |
| [`v15`](v15-mouth-clock.md) | 2026-09-08 | 20 | cut-in mouths and keyframe tracks at real speed | confirmed in play |
| [`v16`](v16-projectile-travel.md) | 2026-09-09 | 22 | ki blasts travel at real speed; optional 19.5:9 widescreen | confirmed in play |
| [`v17`](v17-blast-object-travel.md) | 2026-09-09 | 23 | spawned projectiles like Frieza's rocks travel at real speed | measured, not felt\* |
| [`v18`](v18-beam-object-travel.md) | 2026-09-09 | 24 | beam objects like Buu's charged blast travel at real speed | confirmed in play |
| [`v19`](v19-screen-fade.md) | 2026-09-09 | 25 | every fullscreen fade in the game at real speed | confirmed in play |
| [`v20`](v20-known-issues-refresh.md) | 2026-09-09 | 25 | no patch change - the shipped known-issues header refreshed | confirmed in play |
| [`v21`](v21-rush-struggle.md) | 2026-09-10 | 26 | the CPU can no longer out-rotate the player in a rush struggle | not yet played\* |
| [`v22`](v22-beam-clash.md) | 2026-09-12 | 27 | the beam clash paced in real time, and the CPU's rotation gated | duration confirmed\* |

Group counts are the groups in each release file. From v16 on, one of them is the
optional 19.5:9 widescreen group, which ships switched off.

## Reading the lineage

The list is not a straight line, and the notes say why:

- **v06 and v06b are siblings**, cut in the same commit: v06 is the fix, v06b is the
  withdrawal alone.
- **v07 builds on v06**, not v06b.
- **v08 and v11 have identical group lists**, as do **v10 and v12** - v09 to v12 is a
  rollback and roll-forward to isolate the state 157 trap.
- **v20's patch is byte-identical to v19's**; only the shipped header changed.

A \* marks a build measured correct against the 30fps game but not yet confirmed in
play. Per-build confidence is kept current in [`status.md`](../status.md), and the
full derivation of every group is in [`findings.md`](../findings.md).

## Adding a version

`tools/export.py --release NAME` refuses to run until `docs/versions/NAME.md` exists.
Write the note first - what the version changes over the last one, and what was
discovered - then cut the release and tag it. See [`releases.md`](../releases.md).

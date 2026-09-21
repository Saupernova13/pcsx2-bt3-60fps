# BT3 60fps - findings

The findings log, split by topic. Every section of the original
`docs/findings.md` is in exactly one file below, unedited and in its original
order. `tools/split_findings.py` does the split and checks nothing was lost.

| topic | covers | sections |
|---|---|---|
| [State of play and the user's reports](state-of-play.md) | The running summary, the user's defect lists and every play-test. | 5 |
| [The engine, the frame routine and the first 60fps patch](engine.md) | How BT3 runs a frame, where 60fps comes from, and the early probes. | 13 |
| [Tooling, the rig and the measurement method](tooling-and-method.md) | Instruments, the 30fps oracle, and how a shipped group is A/B'd. | 5 |
| [Input timing](input.md) | The input subsystem and the combat input counters. | 2 |
| [Airborne motion, gravity and the hovering idle](airborne-and-hover.md) | Flight, gravity, the airborne idle animation and the hover bob. | 9 |
| [Effects, the ki aura and particles](effects-aura-particles.md) | The effect-node system, the aura, effect rotation and the particle system. | 8 |
| [Tweens, fades and staged sequences](tweens-fades-and-staging.md) | The tween service, the scripted-sequence clocks and the screen fade service. | 4 |
| [Blasts: hit cadence, effects, sequences and Flame Shower Breath](blasts.md) | Blast 2 and Ultimate Blast timing: hit cadence, effect duration, the sequence clock. | 13 |
| [The fighter state machine and the stuck loop](state-machine.md) | Phase timers inside fighter states, and the state 157 and state 93 traps. | 3 |
| [Projectile, rock and beam travel](projectile-travel.md) | The three movers: effect-node projectiles, spawned objects and travelling beams. | 6 |
| [Full Power Smash and the Lightning Attack](smash-and-lightning-attack.md) | Hard Knockback and the Dragon Smash Circle hit, five frame counts in one chain. | 1 |
| [The camera and the cut-in mouth](camera-and-mouth.md) | Camera pacing and the second clip player behind the mouths. | 5 |
| [Rush Struggle and Beam Struggle](struggles.md) | Both stick-rotation contests, their tick clocks and the CPU's synthetic stick. | 2 |
| [Widescreen](widescreen.md) | The widescreen model and every aspect group. | 2 |
| [Stage scenery and ambient animation](stage-and-scenery.md) | The stage scene graph, its keyframe tracks, and the ambient props on them. | 1 |
| [Fighter status timers](status-timers.md) | The per-tick status timer block: paralysis, Solar Flare's lock-off, the combat timers. | 1 |

## The original introduction

# BT3 60fps - findings log

Running record of everything established about Dragon Ball Z: Budokai Tenkaichi 3
(SLUS-21678, CRC 428113C2). Shared memory between the Analyst and Interpreter roles.
Newest sections at the bottom.

> **Note (2026-09-13):** the repo was restructured for publication. The generic
> ps2ee library and 13 tools moved to the PCSXROO repo (now
> `pcsxroo/ps2ee/` and `pcsxroo/tools/` there); this game's knowledge now lives in `tools/game/`. Tool
> names in this log are unchanged and still resolve - the current index is
> [`docs/tools.md`](tools.md). `patches/428113C2.pnach` is now
> `wip/working.pnach`, the install file is `patch/428113C2.pnach`, and
> released versions are git tags, not directories. Sections below keep the
> paths they were written with.

# Ray effects

Newest sections at the bottom.

## 2026-09-29 - issue #103: the Kamehameha's charge rays counted per tick

A breakpoint on each effect-class update that `effect-classes.md` (PR #76)
lists as not examined, over every rig scene, found class `002C3AA8` running only
in Goku's Kamehameha (save state 0, `L2`+`Triangle` held 60 vsyncs): one object.
With its draw disabled (`jr $ra` at `00168DA0`) the long blue-white rays round
the charge ball are gone.

| vtable slot | function | what |
|---|---|---|
| `+0x00` | `FUN_00168C00` | the update |
| `+0x14` | `FUN_00168DA0` | the draw |

The update works on the object at `node+0x38`, once a tick:

| field | what |
|---|---|
| `+0x38` | start delay, -1.0 a tick (`00168C98`); then `FUN_001692F0` starts the rays |
| `+0x48` | life, -1.0 a tick (`00168C70`), then flag 8 |
| `+0x3C` | hold after that, -1.0 a tick (`00168CC8`) |
| `+0x44`, `+0x40` | fade and its length, -1.0 a tick (`00168CF8`); alpha `+0x4C` = fade / length |

In this Kamehameha the hold is 3 and the life and fade are 0, so the rays hold
until the beam sets flag 8, then count 3 ticks and go.

### The fix

The update opens with the game's freeze check, `FUN_0012D1D0` (`00168C2C`), and
skips everything while it answers "frozen". `[60FPS - ray effect rate]` puts a
wrapper at `000F1BF0` that calls the check and ORs in frame parity, and
`00168C2C` calls it instead - the same gate as the swirl (#94), lightning (#96)
and spiral (#101) classes.

### Measured

Every open fix on:

| | 30fps | 60fps before | 60fps with the group |
|---|---|---|---|
| ray object alive | v81-v101, 11 updates | v80-v98, 19 updates | v81-v101, 11 updates |
| hold 3 -> 0 | v97-v101 | v97-v99 | v97-v101 |
| alpha drops to 0 | v103 | v100 | v103 |

With the group the hold and the alpha take the 30fps value at every vsync from
v81 to v104. All 15 smoke moves return to idle.

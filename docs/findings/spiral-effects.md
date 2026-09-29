# Spiral effects

Newest sections at the bottom.

## 2026-09-29 - issue #101: the Special Beam Cannon's spiral ran once a tick

A breakpoint on each effect-class update that `effect-classes.md` (PR #76)
lists as not examined, over every rig scene, found class `002C3F50` running
only in Imperfect Cell's Special Beam Cannon (save state 1, `L2`+`Up`+`Triangle`
for 8 vsyncs): one object, v55-v101. With its draw disabled (`jr $ra` at
`00188258`) the blue spiral trails round the beam are gone.

| vtable slot | function | what |
|---|---|---|
| `+0x00` | `FUN_00187F90` | the update |
| `+0x14` | `FUN_00188258` | the draw |

The update works on the object at `node+0x38`, once a tick:

| field | what |
|---|---|
| `+0x258` | start delay, -1.0 a tick |
| `+0x260`, `+0x264` | fade and its length, -1.0 a tick |
| `+0x250` | age, +1.0 a tick, against a lifetime of `+0x34` seconds times 30.0 (`00188128`) |
| `+0x25C` | a countdown, -1.0 a tick |
| `+0x368` | the spiral's counter, +1 a tick |
| `+0x370` | the spiral's scale, growing a little each tick |
| `+0x39C` | its chain of segments; `FUN_0018A7A0` steps each one's delay and ping-pong phase |

The beam ends the object from outside: at v105 at 30fps and v101 at 60fps,
the beam's own one-tick hand-offs recorded on #13.

### The fix

The update opens with the game's freeze check, `FUN_0012D1D0` (`00187FC0`),
and skips everything while it answers "frozen"; the one call on that path,
`FUN_00189FD0`, registers the object in a table and steps nothing.
`[60FPS - spiral effect rate]` puts a wrapper at `000F1BC0` that calls the
check and ORs in frame parity, and `00187FC0` calls it instead - the same gate
as the swirl (#94) and lightning (#96) classes.

### Measured

Every open fix on:

| | 30fps | 60fps before | 60fps with the group |
|---|---|---|---|
| spiral counter `01A874E8` reaches 24 | v103 | v80 | v104 |
| spiral scale `01A874F0` reaches 1.1 | v101 | v79 | v102 |
| age at the end of its life | 25 | 46 | 23 |

The explosion fills the frame and the beam runs its known few vsyncs ahead, so
a picture score does not move (37.33 either way); the counters are the oracle.
The beam's damage is the same with and without the group (5460). All 15 smoke
moves return to idle.

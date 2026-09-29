# Lightning effects

Newest sections at the bottom.

## 2026-09-29 - issue #96: the transformation lightning ran once a tick

Found by the per-tick RAM hunt on Goten's transformation (save state 8, `R3`
for 6 vsyncs), run again with #95's swirl gate on so the swirl's particles no
longer crowd the list. `01A43908` counted 0 to 25 once a tick in both arms. A
write watch lands at `0017C9F0` in `FUN_0017C8F8`, the update of effect class
`002C3E48` - one of the classes `effect-classes.md` (PR #76) lists as not
examined.

| vtable slot | function | what |
|---|---|---|
| `+0x00` | `FUN_0017C8F8` | the update |
| `+0x14` | `FUN_0017CB60` | the draw, with its own freeze check `FUN_0012D298` |

The update works on the object at `node+0x38`:

| field | what |
|---|---|
| `+0xEA0` | start delay, -1.0 a tick (`0017CA54`) |
| `+0xE9C` | spawn countdown, -1.0 a tick (`0017C99C`); at 0 `FUN_0017C3F0` spawns a bolt and reloads it |
| `+0xEA8` | run counter, +1.0 a tick up to `+0xEAC` (`0017C9F0`), calling `FUN_001798D8` each tick |
| `+0xE94` | life, +1.0 a tick up to `+0xE98` (`0017CA30`), then flag 2 |
| `+0xEA4` | fade after that, -1.0 a tick (`0017CA84`) |

With the draw disabled (`jr $ra` at `0017CB60`) the purple lightning streaks
round Goten are gone.

It runs in Goten's transformation (two objects, v8-v207) and for 3 ticks near
the end of a ki charge (save states 0 and 3); not in the other rig scenes
(Vegeta's and Cell's transformations, GS2's Ultimate, the Present Bomb, a rush,
the Kamehameha, a KO, guard, flight, idle).

### The fix

The update opens with the game's freeze check, `FUN_0012D1D0` (`0017C928`),
and skips everything while it answers "frozen"; the one call on that path,
`FUN_001793E0`, registers the object in a table and steps nothing.
`[60FPS - lightning effect rate]` puts a wrapper at `000F1B90` that calls the
check and ORs in frame parity, and `0017C928` calls it instead - the same gate
as the swirl class (#94) and `[60FPS - thrown object rate]`.

### Measured

Goten, `R3` from save state 8, every open fix on:

| | 30fps | 60fps before | 60fps with the group |
|---|---|---|---|
| first object's run counter, 0 -> 25 | v26-v74 | v18-v42 | v26-v74 |
| its spawn countdown, steps | 73 | 150 | 72 |
| second object's countdown, steps | 17, v170-v202 | 35, v167-v201 | 17, v168-v200 |

With the group the run counter takes the 30fps value at every vsync from v6
to v230. The countdown reloads with random values, so only its step count is
comparable. The second object is created 2 vsyncs early in both 60fps arms,
upstream of this class.

Smoke test with the group on: all 13 moves and a ki charge return to idle, and
so does Goten after his transformation.

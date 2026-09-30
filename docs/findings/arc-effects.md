# Arc effects

Newest sections at the bottom.

## 2026-09-30 - issue #111: the arcs over Explosive Wave counted per tick

Found while measuring the blast ramps (#109). Screenshots of Vegeta (Scouter)'s
Explosive Wave (save state 9, `L2 + Circle`) showed lightning arcs at v43 and
v55 at 30fps and none in the build from v49 on. Breaking on each effect-class
update named class `002C3F80`, one object, in Explosive Wave and in Super 17's
Android Barrier (save state 4, `L2 + Circle`) and in no other rig scene.

| vtable slot | function | what |
|---|---|---|
| `+0x00` | `FUN_0018C4E8` | the update |
| `+0x14` | `FUN_0018C7C8` | the draw |

With the draw disabled (`jr $ra` at `0018C7C8`) the arcs are gone and the sphere
is still there, in both moves. The sphere is not this class.

The update works on the object at `node+0x38`, once a tick:

| field | what |
|---|---|
| `+0x3A4` | start delay, -1.0 a tick (`0018C548`) |
| `+0x3AC`, `+0x3B0` | fade and its length, -1.0 a tick (`0018C590`) |
| `+0x3A0` | age, +1.0 a tick (`0018C618`) |
| `0018C678` | lifetime: `seconds * 30.0`, compared with the age |
| `0018D1C0` | each arc's own counter, +1.0 a tick up to 5 |

Explosive Wave's arcs live 26 ticks. Android Barrier's are ended from outside,
when the barrier ends, so their length is right in the build and only their
animation is fast: the age reads 123 there where 30fps reads 63.

### The fix

The update opens with the game's freeze check, `FUN_0012D1D0` (`0018C524`), and
skips to `0018C758` while it answers "frozen". `[60FPS - arc effect rate]` puts
a wrapper at `000F1C50` that calls the check and ORs in frame parity, and
`0018C524` calls it instead - the same gate as the burst (#82), swirl (#94),
lightning (#96), spiral (#101) and ray (#103) classes.

### Measured

Every open fix on:

| | 30fps | 60fps before | 60fps with the group |
|---|---|---|---|
| Explosive Wave: age 1 -> 26 | v13-v63 | v12-v37 | v13-v63 |
| Explosive Wave: vsyncs v10-v80 with the 30fps age | - | 20 of 71 | 71 of 71 |
| Android Barrier: age when the barrier ends | 63 (v136) | 123 (v134) | 63 (v136) |
| Android Barrier: vsyncs v10-v270 with the 30fps age | - | 3 of 261 | 261 of 261 |
| Explosive Wave: first damage at 39.7 units | v35 | v34 | v34 |

Eight consecutive vsyncs of the gated Explosive Wave (v41-v48) show the arcs in
every frame, changing every second one as at 30fps: the update does not build
the picture. All 15 smoke moves return to idle.

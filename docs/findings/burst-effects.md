# Burst effects

Newest sections at the bottom.

## 2026-09-28 - issue #82: two effect classes that tick their whole update

Goku's Kamehameha (`L2` + `Triangle` held 60 vsyncs, save state 0) still differs
from 30fps by 9-24 in pixel score at the best offset within 4 vsyncs, mostly in
the impact burst. Recording all of RAM per vsync in both arms and keeping the
words with the same values per tick turned up, besides fighter-state toggles
that start with the beam's end, two effect timers:

| word | per tick | writer | class |
|---|---|---|---|
| `01A03634` | 10.0, 9.0, 8.0 ... | `001A2FC8`, `obj+0x114 -= step` | vtable `002C4308`, update `FUN_001A2DD0` |
| `01A8F408` | 1.0, 0.9, 0.8 ... | `0017D98C`, `obj+0x4E8 -= obj+0x4EC` | vtable `002C3E78`, update `FUN_0017D8E0` |

Neither class has a group acting inside it.

### `002C3E78`

`FUN_0017D8E0`, once a tick, on the object at `node+0x38`:

| field | what |
|---|---|
| `+0x510` | start delay, -1 a tick; the update stops here while it is above 0 |
| `+0x514` | flags: bit 1 runs the timer, bit 2 the fade, 4 and 8 end it |
| `+0x4E4` | timer in seconds, -`gp-0x75E4` (1/30) a tick |
| `+0x4E8`, `+0x4EC` | fade and its rate per tick |
| `+0x508` | mode: 0 counts `+0x490` down by `+0x4E0`; 1-3 emit random pieces every tick |

It runs in Goku's Kamehameha from its firing, and in Vegeta (Scouter)'s
transformation from v186: mode 1, a 0.5 s timer, so at 30fps it lives 15 ticks,
30 vsyncs, and at 60fps 15 vsyncs.

### `002C4308`

`FUN_001A2DD0` counts `obj+0x114` down by 1.0 a tick and scales two fields by the
fraction left, and its helpers `FUN_001A0FC0` to `FUN_001A1A40` move its parts once
a tick. They call only vector maths, the random number generator, memset and node
utilities - no tween, animation clock or effect-command runner, which other
groups already pace.

### The fix

Both updates start with the game's freeze check, `FUN_0012D1D0` (`0017D904`,
`001A2E08`), and skip everything while it answers "frozen"; both draw from a
separate vtable slot (`+0x14`: `0017DCB8`, `001A3488`). A wrapper at `000F1A90`
calls the freeze check and ORs in frame parity, and those two call sites jump to
it - the same shape as `[60FPS - thrown object rate]` for `FUN_0012CED0`. Every
channel of both updates then runs at 30Hz.

| every open fix on | 30fps | before | after |
|---|---|---|---|
| Kamehameha: `01A03634` 10 -> 0 | 20 vsyncs | 10 | 20 |
| Kamehameha: `01A8F408` 1.0 -> 0 | 20 vsyncs | 10 | 20 |
| Vegeta: spark timer `+0x4E4` 0.5 -> 0 | v186-v214 | v187-v200 | v188-v216 |

Photographed at every vsync of the burst with the gate: drawn on every frame.

### Why the pictures barely move

Best-match pixel difference against 30fps, Kamehameha, within 4 vsyncs:

| mark | before | after |
|---|---|---|
| v130 | 13.6 | 13.7 |
| v150 | 17.0 | 19.6 |
| v160 | 19.3 | 19.8 |
| v190 | 8.9 | 8.6 |

The beam lands a few vsyncs early at 60fps (at v140 the hit counter reads 6
against 4), the flight residual the shipped header lists, and that dominates the
score. In Vegeta's scene the spark effect is now alive where 30fps has it, but its
random pieces sit elsewhere, which a pixel score counts as a difference (v210: 1.8
without, 3.5 with). The timers are the oracle here.

### Also seen

The Kamehameha's end pose (animation `0x10B`) comes 6 vsyncs early (v141 against
v147), the same "ends about 6 early" the Special Beam Cannon shows in #13. No
counter runs toward it in the window before; it fits the one-tick hand-offs
recorded there.

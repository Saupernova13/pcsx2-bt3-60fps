# Swirl effects

Newest sections at the bottom.

## 2026-09-29 - issue #94: the wind swirls ran their whole update once a tick

Found by recording RAM at every vsync of Goten's transformation (save state 8,
`R3` for 6 vsyncs) with every open fix on, and at every vsync at 30fps, then
keeping the words that take the same value per tick in both. 1,129 words did,
and about 1,100 of them sit in `01A4D000`-`01A57000`: a pool of `0x180`-byte
particles. A write watch on one particle's `+0x118` lands at `00191E9C` in
`FUN_00191D28`, called once a tick from `FUN_00190FE8`, the update of effect
class `002C40C0` - one of the classes `effect-classes.md` (PR #76) lists as not
examined.

| vtable slot | function | what |
|---|---|---|
| `+0x00` | `FUN_00190FE8` | the update |
| `+0x14` | `FUN_00191348` | the draw, with its own freeze check `FUN_0012D298` |

The update works on the emitter at `node+0x38`:

| field | what |
|---|---|
| `+0x68` | start delay, -1.0 a tick (`00191040`); the update stops there while it is above 0 |
| `+0x64` | tick counter, +1.0 a tick (`0019125C`) |
| `+0x3B4`, `+0x3B8` | spawn interval in ticks and particles per spawn: a spawn whenever `+0x64` is a multiple of `+0x3B4` (`001910D4`), each particle turning the emitter by `+0x310`..`+0x318` times `gp-0x7504` |
| `+0x60` | life, -1.0 a tick (`001911C0`) |
| `+0x6C` | a second countdown, -1.0 a tick (`0019121C`) |
| `+0x3C8` | the particle list: `FUN_00191D28` ages each particle `+0x118 += 1.0` (`00191E9C`) and moves it |

With the draw disabled (`jr $ra` at `00191348`) the white wind swirls round
Goten are gone for the whole transformation, and so is the white swirl on the
ground round a fighter charging ki.

### Where it runs

A breakpoint on `00190FE8`, 250-300 vsyncs of each rig scene, every open fix on:

| scene | calls | emitters |
|---|---|---|
| Goten's transformation (save state 8) | 167 | 1 |
| Krillin charging ki (save state 3, `L2` held) | 268 | 3 |
| Goku charging ki (save state 0, `L2` held) | 268 | 3 |
| Vegeta's and Cell's transformations, GS2's Ultimate, the Present Bomb, a rush, the Kamehameha, guard, flight, a KO, idle in every save state | 0 | - |

### The fix

The update opens with the game's freeze check, `FUN_0012D1D0` (`0019101C`), and
skips everything while it answers "frozen". `[60FPS - swirl effect rate]` puts
a wrapper at `000F1B60` that calls the check and ORs in frame parity, and
`0019101C` calls the wrapper instead: the same gate as the burst classes (#82)
and `[60FPS - thrown object rate]`. The whole update runs at 30Hz and the draw,
a separate method, still runs every frame. Nothing the update calls is paced by
another group; no group writes inside `00188000`-`00196000`.

The one call made while frozen, `FUN_001945D0`, registers the emitter in a
table and steps nothing.

### Measured

Krillin charging ki, `L2` held from save state 3:

| | 30fps | 60fps before | 60fps with the group |
|---|---|---|---|
| emitter 1 tick counter | 64 steps, v51-v177 | 122 steps, v48-v169 | 64 steps, v49-v175 |
| emitter 2 tick counter | 69 steps, v51-v187 | 125 steps, v48-v172 | 69 steps, v49-v185 |
| emitter 3 life, 6 -> 0 | v163-v179 | v161-v169 | v161-v177 |

The emitters are created 2 vsyncs earlier than at 30fps in both 60fps arms
(emitter 3 at v161 against v163). That comes from the charge, which starts
them, not from this class.

Goten, `R3` from save state 8: with the group, the swirl emitter's tick counter
(`+0x64`) and spin angle (`+0x58`) take the 30fps value at every vsync from v10
to v70. The emitter is set up a vsync early, at v9 against v10; its first step
is at v26 in both. Without the group they start at v18 and step every vsync.

The particles' random pieces come from different draws in each arm, so a
picture score is no oracle here; the counters are.

Smoke test with the group on: all 13 moves and a ki charge return to idle, and
so does Goten after his transformation (the opponent in that save state is a
live CPU, and its states are the same with and without the group).

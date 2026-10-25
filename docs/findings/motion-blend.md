# Motion blends

Newest sections at the bottom.

## 2026-09-29 - issue #98: the crossfade between motions counted per tick

The animation controller at `model+0xB40` (mapped in
[engine.md](engine.md#the-animation-system-fully-mapped)) has a second clock
besides the clip time `+0x138` that `[60FPS - animation clock]` halves: the
crossfade from the previous motion into the new one.

Found by the per-tick RAM hunt on Krillin's ki blast (save state 3, `Triangle`
for 4 vsyncs): `008C0F74` took 0.833, 0.667 ... 0 once a tick in both arms, and
P1's bone rotations at `00918E80`-`0091A38C` moved with it. `008C0F74` is P1's
model (`008C02F0`) `+0xC84`, the "no crossfade (`+0xC84`)" that #21's notes
checked in Vegeta's transformation, where none ran.

| field (`model+`) | controller `+` | what |
|---|---|---|
| `0xC84` | `0x144` | crossfade weight, 1.0 at the start of a blend, 0 when done |
| `0xC88` | `0x148` | its step per tick |

- `FUN_0024C668(model, seconds)` starts a blend: weight 1.0, step
  `1 / (seconds * 30.0)` (`0024C6A8`: `lui $at, 0x41F0`), or weight 0 for a
  blend shorter than `gp-0x5C2C`. It is the only store to the step.
- `FUN_001C47A8` counts the weight down by the step once a tick (`001C47E0`),
  and a sibling does the same at `001C4420`.
- `[60FPS - animation clock]` hooks `001C4714` and `001C4838` in the same
  code, for the rate getters, but not this countdown.

Some states wait for the blend: Krillin's firing state 174 ends when it does.

### The fix

`[60FPS - motion blend]` makes the setup's 30.0 60.0, so the step halves at its
only source. The blend is sampled at 60Hz over its authored seconds.

### Measured

Krillin's ki blast, one tap, every open fix on:

| | 30fps | 60fps before | 60fps with the group |
|---|---|---|---|
| crossfade 0.833 -> 0 | v19-v29, a step every 2 vsyncs | v19-v24 | v19-v30, a half step every vsync |
| bone `00918E88`, -0.090 -> -0.432 | settles v29 | settles v24 | settles v30 |
| state 174 ends | v31 | v25 | v31 |

With the group the bone passes through each 30fps value one vsync after it
(-0.182 at v22 against v21-v22, -0.266 at v24 against v23-v24 ...), the 60Hz
samples falling between the 30fps ones.

Smoke-test timelines, P1's state changes after the presses:

| case | 30fps | 60fps before | with the group |
|---|---|---|---|
| ki blast, three taps 20 vsyncs apart | 174 from v6, idle at v78 | idle at v24, v48 and v72 between shots | 174 from v6, idle at v78 |
| ki charge, `L2` 200 vsyncs | idle at v216 | v212 | v216 |
| the other 11 moves timed | - | unchanged by the group | unchanged |

The other moves' remaining leads (the fork, Hell's Storm, the Kamehameha's end)
do not come from the blend. Vegeta's and Goten's transformations were only
smoke-tested, not timed. All 15 smoke moves return to idle.

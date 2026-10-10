# Cloth: capes

Newest sections at the bottom.

## 2026-09-28 - issue #92: the cape flutter ran on 30Hz settings

Found by a per-tick hunt that compares each word's **steps** rather than its
values - a phase that started elsewhere never matches value for value, but its
per-tick step does. Over 40 idle ticks of Great Saiyaman 2 (save state 2),
`008C1738` and `008C1778` stepped `+0.1` a tick in both arms. A write watch
lands in `FUN_00250DE8(model, cloth)`, with the cloth piece at `model+0x1420`.

Each piece has three flutter phases, stepped once a tick and wrapped:

    cloth+0x28 += f23 * 0.1      00251120  (gp-0x5BBC)
    cloth+0x2C += f23 * 0.23     00251134  (gp-0x5BB8)
    cloth+0x30 += f23 * 0.27     0025114C  (gp-0x5BB4)

A piece with a parent (`cloth+0x24`) copies the parent's phases less 0.9 instead,
so a cape's three pieces ripple down it. The flutter is built from the sines of
the phases and the model's motion.

The function picks its rate settings on entry (`00250E50`-`00250E90`):

| | normal | model flag `0x01000000` at `+0xA40` |
|---|---|---|
| `f23`, the phase step | 1.0 | 0.5 |
| `f24`, scales a velocity term (`0025120C`, `002512B8`) | 1.0 | 2.0 |
| `f25`, ticks a second (divides a per-tick speed limit at `00251064`) | 30.0 | 60.0 |

So the game has a 60Hz cloth mode of its own. No battle model sets the flag, and
a battle at 60 ticks a second ran the 30Hz settings.

`[60FPS - cape flutter]` takes the 60Hz settings whenever a battle exists: the
`beqz` on the flag at `00250E74` becomes a jump to a wrapper at `000F1B30` - its
delay slot, `lb $s7`, still runs - that goes to the 60Hz settings if the flag is
set or the battle manager (`0x002FEB14`) is non-null. The manager stays live
from a match's first frame through the win pose. Outside a battle nothing
changes.

Of the ten rig save states only GS2's runs the cloth update: three calls a tick,
one per piece of the cape.

| Save state 2, first phase | v100 | v108 | v116 |
|---|---|---|---|
| 30fps | -1.05 | -0.647 | -0.247 |
| 60fps before | -2.23 | -1.43 | -0.63 |
| 60fps with the group | -1.05 | -0.647 | -0.247 |

### Also seen, not changed

- A stage effect class (update `FUN_0014A528`, vtable `002C36B8`; state update
  `FUN_00149870`) steps a rotation at `+0x18` by `rate * 2pi` a tick, plus two
  scrolls at `+0x1C`/`+0x20`, and two instances on Rocky Area step `+0.044` a
  tick in both arms. Halving it measures exact, but switching the class off
  entirely changes nothing in the idle view, so what it draws is not known and
  it is not patched.
- Over the rock faces of Rocky Area a haze changes about twice as much per 10
  vsyncs at 60fps as at 30fps, with `[60FPS - sky scroll]` on. It is not the sky
  scroll, not the class above, and not one of the 33 direct reads of the frame
  counter `0x00331D64` (each selects a frame buffer). Issue #11.

## 2026-10-10 - the slow-chains settings are not a 60Hz mode

BT3-Decompiled names the flag `BOBJ_FLAG_SLOW_CHAINS` ("chains use the half-speed
constants"): a slow-motion setting, not a 60Hz one. `BObjChainB_Step`
(`src/battle/btl_obj_chain.c`) under it scales some per-tick terms and leaves
others, so the first version of the group fixed a standing cape and overdrove a
moving one (`work/tools-scratch/capevis.py`: the angle each cape link travels and
its spread over the same real time).

| Per-tick term | slow-chains setting | at 60fps | the group |
|---|---|---|---|
| node and movement velocity | x `mult` 2 | right | kept |
| idle phase step; swing step when `depthB & 1` | x `scale` 0.5 | right | kept |
| swing step on the other links (`0025138C`) | not scaled | 2x (measured 1.97x) | x `scale`, cave `000F24E0` |
| blend toward the target, `t` 0.1-0.5 (`00251564`) | not scaled | settles 2x as fast | `1 - sqrt(1 - t)` while `mult` > 1, cave `000F24F0` |
| speed cap `1388.9 / fps` (`00251064`, the only reader of `f25`) | fps 60 | the cap halves | fps 30 (`00250E7C`) |
| damping `vel * half * mult` (`0025120C`) | x2 | 2x | half only |
| push / sway decay x0.85 a tick (`BtlObj_DecayPush`, data `002FE67C`, one reader) | - | decays 2x as fast | `sqrt(0.85)` |

Great Saiyaman 2 (`rocky-gs2-vs-standing-gohan.p2s`), 240 vsyncs, cape path vs 30fps, links 0 / 1 / 2:

| | moving (`Up`) | standing | ki charge (`L2`) |
|---|---|---|---|
| 60fps, no group | 0.56 / 0.74 / 0.80 | 2.99 / 1.57 / 1.26 | 1.66 / 1.67 / 1.75 |
| first version | 2.85 / 1.99 / 1.85 | 1.59 / 1.01 / 1.08 | 1.64 / 1.42 / 1.43 |
| this version | 0.95 / 0.97 / 0.84 | 1.50 / 0.82 / 1.00 | 0.98 / 0.91 / 0.99 |

Standing link 0 barely moves: 0.70 rad over 8 s at 30fps, 1.01 with the group
(2.18 without it). The cape's noise source (`BtlObj_ChaosRand`, a logistic map)
advances once per call, so the paths can only match in total, not vsync by vsync.
State timelines of eight moves are identical with and without the new lines.

The decay word is shared with hair (chain A), whose own steps are not compensated:
Ultimate Gohan's hair, standing, travels 0.91 / 0.81 / 0.62 of its 30fps path in
the full build, with and without this group. That is a defect of its own.

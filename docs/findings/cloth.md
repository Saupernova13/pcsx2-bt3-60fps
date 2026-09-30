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

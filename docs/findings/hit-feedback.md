# Hit feedback: camera shake and controller rumble

Newest sections at the bottom.

## 2026-09-28 - issue #80: both counted 30Hz ticks

Found by recording all of RAM at every vsync of Hercule's Present Bomb hit
(`rocky-hercule-vs-standing-gohan.p2s`, `L2` + `Triangle`) in both arms, and
keeping the words whose values are the same per tick in the two - the signature
of a clock no group compensates. Two families came out besides the effects
already fixed: floats at fighter `+0x470` stepping -1/30 a tick, and ints at
fighter `+0x15D8` counting 4, 3, 2, 1, 0.

### The camera shake

A write watch on `+0x470` lands in `FUN_0023F438`. Each camera has four shake
slots: a time left in seconds at `slot+0x00` and a size at `slot+0x10`, filled
by `FUN_0023F3C8`. Once a tick:

    FUN_0023F438:  time left -= gp-0x5D2C (002FE544, 1/30 s); at 0, clear the slot
    FUN_0023F478:  take the slot with the largest size; offset the camera by
                   random draws * min(time left * k * size, cap)

The countdown has three callers: the battle camera at `001C6B60`, measured
once a tick, and two in the camera code at `0023D63C` and `0023D7C4`, not
measured. The constant has one reader, so it is patched in data: 1/30 becomes
1/60.

| Present Bomb, first hit | 30fps | before | after |
|---|---|---|---|
| slot filled with 0.2 s reaches 0 | v117 | v111 | v117 |
| slot filled with 0.3 s reaches 0 | v123 | v114 | v123 |

Not covered: the random offsets. `FUN_0023F478` draws them once a tick into
stack temporaries (`sp+0x30`, `sp+0x40` of the camera update), so at 60fps the
camera jitters every vsync where 30fps jitters every other one. Holding them for
two ticks needs a cache, and three cameras call the generator every frame
(both fighters' and the battle camera), so one saved random-number state is not
enough.

### The controller rumble

A write watch on `+0x15D8` lands in `FUN_001DC5E0`, each fighter's rumble at
fighter `+0x15D0`, called once a tick from `001C2600`:

| field | what |
|---|---|
| `+0x00` | rumble on |
| `+0x04` | large motor strength |
| `+0x08` | large motor time: seconds * 30.0 (`001DC554`), -1 a tick |
| `+0x0C` | small motor time: seconds * 30.0 (`001DC578`), -1 a tick |
| `+0x10` | large motor phase, +1 a tick; sent as strength * (0.75 + 0.25 * sin(phase * k / 30.0)) (`001DC654`) |
| `+0x14` | small motor counter, +1 a tick; the motor is on when bit 0 is clear (`001DC6C0`) |

`FUN_00122E88` adds each call's values into the pad's accumulators
(`0x00333800 + pad * 0x1C0`, `+0x160` and `+0x164`), and `FUN_00122F10` sends
them and zeroes them. That is why the update is not gated: a skipped tick would
send zero and pulse the motors. Instead the three 30.0s become 60.0 and the
small motor toggles on bit 1.

| Present Bomb, first hit | 30fps | before | after |
|---|---|---|---|
| vsyncs with rumble sent to the pad | 10 (v109-v118) | 5 | 11 (v107-v117) |
| the large motor's values | 191, 250, 227, 152, 131 | the same, one a vsync | the same curve, over the same time |

The extra vsync is the send, one tick behind the timer.

### Also seen, not changed

- An 8-entry ring buffer at fighter `+0x570` (write index `+0x910`, reader
  `FUN_001D3DF8`) advances once a tick; it looks like per-tick history, likely
  input. The input groups shipped in v24 were confirmed in play, so it is left
  alone.

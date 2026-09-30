# The HUD: the health bar's drain and shake

Newest sections at the bottom.

## 2026-09-28 - issue #84: the health bar counted 30Hz ticks

Found by recording all of RAM at every vsync of Hercule's Present Bomb against
Ultimate Gohan (`rocky-hercule-vs-standing-gohan.p2s`, `L2` + `Triangle`) and
keeping words that fall steadily: Gohan's displayed health stepped down by the
same amount per tick in both arms. A write watch on it lands in `FUN_0021CD20`,
the health bar update, which runs once a tick. `HUD = *(gp-0x5728)`
(`01876860` in that state) and `HUD+0x24` is the side the call updates.

| field | what |
|---|---|
| `HUD+0x0C + 12*side + 4*slot` | shake slot: tick count (halfword), then amplitude (halfword), three slots a side |
| `HUD+0x28 + 4*side` | displayed health, the red section |
| `HUD+0x30 + 4*side` | real health |
| `HUD+0x1B8 + 24*side` | the bar-break tween, started when the displayed health crosses a 10000 boundary |
| `HUD+0x248 + 4*side` | drain speed, health per tick |

### The drain

While the real health is below the displayed one, each tick:

    gap > 20000: speed = max(speed, 200)     0021CE9C, slti at 0021CEAC
    gap > 10000: speed = max(speed, 150)     0021CEC0, slti at 0021CED0
    gap >  5000: speed = max(speed, 120)     0021CEE8, slti at 0021CEF4
    displayed -= speed, not below the real health
    caught up:   speed = 100                 0021CFD0

At 60 updates a second the red section fell twice as fast. The four speeds and
their `slti` are halved: the same drain per second in steps half the size. The
bar-break check compares the step with the distance to the next 10000, so it
still fires once per boundary.

### The shake

`FUN_0021FA38` and `FUN_0021FA88` fill a side's slots on a hit, from the
damage handler at `00219034`-`002190E8`:

| damage | count | amplitude | slots |
|---|---|---|---|
| 9999 or more | 15 | 3 | 0 and 1 |
| 1000 to 9998 | 10 | 2 | 0 and 1 |
| under 1000 | 5 | 2 | 0 and 1 |
| when `FUN_0020BC00` is true | 8 | 2 | 0 and 2 |

The loop at `0021CD4C`-`0021CE24` runs over the three slots once a tick: while
a count is above 0 it counts it down and gives the slot's sprite
(`*(HUD+8)` + `0x38`, `0xA8`, `0xE0`) a random x and y offset within the
amplitude (`+0x18`, `+0x1C`); at 0 it zeroes them. That loop now runs on even
ticks only, from a wrapper at `000F1AC0` entered in place of the `lw` at
`0021CD44`, so a count and its offsets change every 2 vsyncs, as at 30fps.

`FUN_0021CD20` is not gated as a whole: after the drain it steps the bar-break
tween (`jal 0x267B00` at `0021CE58`), whose duration `[60FPS - tween duration]`
already counts in 60Hz frames. Gating the function would run that tween at half
speed.

### Measured

Present Bomb against Ultimate Gohan, every open fix on:

| | 30fps | 60fps before | 60fps with both groups |
|---|---|---|---|
| red section drains 6360 health | 104 vsyncs | 52 | 105 |
| shake on a 6360 hit (count 10) | 20 vsyncs, new offset every 2 | 10, every vsync | 20, every 2 |
| shake on a small hit (count 5) | 10 vsyncs | 5 | 10 |
| drain step per vsync | 60 (120 a tick) | 120 | 60 |

A hit that lands on an odd tick starts its shake one vsync later than on an
even one, the usual cost of a gate.

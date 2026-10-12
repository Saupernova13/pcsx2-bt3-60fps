# The CPU opponent

The AI update, how often it decides, and what its decisions touch.

## 2026-10-09 - issue #100: the CPU decided once a tick

`FUN_001BB620` is the whole AI, called once a tick from the battle loop at
`0012BC8C`. Per AI fighter (`fighter+0x1278` set) it builds a situation mask
(`FUN_001BFF70`), runs its rules (`FUN_001BAC30`), rolls eight random choices a
tick (`FUN_001BA760`), and writes the CPU's buttons and stick at
`fighter+0x127C` / `+0x1280` / `+0x1284` (`FUN_00208198`). `FUN_001D4370` feeds
those into the fighter's input exactly as a pad's would.

At 60fps it decided 60 times a second, and its mashed buttons flipped every
frame instead of every other one.

### Where it shows: a launched CPU recovers late

A CPU set to stand still is not idle. Launched, it mashes `Down` and a second
button (`0x21`) to recover in mid-air, on one tick and off the next. State 212,
the launched flight (`FUN_001E9218`), holds a loop animation for
`fighter+0xFC8 * 15` ticks. When the loop can end, it recovers the fighter into
state 230 only if a direction is held at that tick (`fighter+0x73C & 0xF0`, or
game mode 4 or `0x1B`). Otherwise it plays the landing animation still in the
air and ends in state 217, then 230, 16 vsyncs and about 50 units later.

Pan's Rush Finish on a standing Ultimate Gohan (`Square` x7, 16 vsyncs apart):

| | 30fps | 60fps | 60fps, AI gated |
|---|---|---|---|
| CPU's mash | 2 vsyncs on, 2 off | 1 on, 1 off | 2 on, 2 off |
| mash at the loop's end | on: state 230 at v166 | off: 217 at v180 | on: 230 at v164 |
| Gohan's flight, state 212 | 44 vsyncs | 59 | 43 |
| Gohan knocked | 229.6 units | 280.5 | 226.2 |

Gohan's flight path is identical vsync for vsync in all three; only the moment
he recovers differs. Devilman's Rush Finish gives 229.9 / 280.7 / 226.4. Without
`[60FPS - throw flight]` (#125) the same scene happened to land near 30fps
(242.6), because the loop ended at a different time.

### The gate

`[60FPS - CPU decision rate]` hooks `0012BC8C` to a wrapper at `000F2000`. It
runs the AI if any of these holds, and returns otherwise:

| condition | why |
|---|---|
| 2 ticks since the AI last ran (frame counter `00331D64`) | 30 decisions a second |
| any fighter's state differs from the state the AI last saw | at 30fps the AI always sees a new state on the next tick; without this, a button chosen for a state that just ended is held into the new one for a tick |
| any fighter in state 250 (Rush Struggle) or 304 (Beam Struggle) | `[60FPS - rush struggle]` and `[60FPS - beam clash]` already pace the CPU's stick by counting its rotation only on even ticks of the state's counter |

The data, the last-run frame and up to four fighter states, sits at
`000F2100`-`000F2113` and is never written by a patch line.

Both extra conditions came from measurements:

- **The struggle bypass.** With a plain even-tick gate, the CPU's Rush Struggle
  hits fell to its automatic 26 at every hand speed. Its stick then steps on
  alternate global ticks, and the struggle groups only count a rotation on even
  ticks of their own counter.
- **The state-change run.** A plain gate started save state 8's fight with the CPU
  jumping (state 15) one vsync after it reached idle, holding a button chosen
  before the state changed. The 30fps game does not do that.

### Measured

| check | 30fps | 60fps before | with the group |
|---|---|---|---|
| Pan's Rush Finish, Gohan knocked | 229.6 | 280.5 | 226.2 |
| Devilman's Rush Finish, Gohan knocked | 229.9 | 280.7 | 226.4 |
| Rush Struggle CPU hits, 0 / 2 / 5 / 8 rot/s | 51 / 51 / 62 / 62 | 49 / 51 / 57 / 57 | 53 / 55 / 60 / 61 |
| Rush Struggle winner at each speed | CPU, CPU, P1, P1 | the same | the same |
| save state 8, the CPU's first decisions | 13, 11, 55, 11, 15, 21, 20, 13, 15, 20 | 13, 11, 15, 21, 20, 13, 15, 21 | 13, 11, 55, 11, 15, 21, 20, 13, 15, 20 |
| P1's state timeline, 8 smoke moves | - | - | identical with and without |

The decision sequence in save state 8 follows the 30fps one; the timings
inside it do not, because the CPU's rolls come from the shared random sequence,
which other systems draw from at a different rate at 60fps. A fight against a
live CPU still diverges from the 30fps fight. That is expected of any change to
when the AI runs, and it is why the struggles and the Rush Finish, where the
CPU's input is mechanical, are the measurements to trust.

Not measured: the Beam Struggle with this group, because the rig has no save
state that reaches state 304. The bypass keeps the AI running every tick there,
which is what the beam clash group was measured with.

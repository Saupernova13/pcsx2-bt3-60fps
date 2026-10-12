# v27 - recovery windows

| | |
|---|---|
| Tag | `v27-recovery-windows` |
| Date | 2026-10-11 |
| Built on | [v26-cinematic-camera](v26-cinematic-camera.md) |
| Groups | 39 (552 patch lines) |
| Confidence | **MERGED AFTER PLAY TEST** - the owner merged #159 on 2026-10-11; both windows measured equal to 30fps in the rig |

## What it changed over v26

One group, two patch lines.

**Recovery windows.** A fighter who is launched upward or blown away can't
recover until the move has run for a set number of frames. The game counted
those frames once a tick, so at 60fps the window opened after half the time and
a launched or blown-away fighter could recover twice as early (#158).

| Group | What ran at double speed | Now |
|---|---|---|
| `recovery windows` | launched (`001E8D00`) and blown away (`001E9994`): recovery allowed after 8 ticks | after 17 ticks, the same time as at 30fps |

| Window opens after | 30fps | v26 | v27 |
|---|---|---|---|
| blown away (charged smash) | 18 vsyncs | 9 | 18 |
| launched (Square x3, Up + Triangle) | 18 vsyncs | 9 | 18 |

The comments in the patch file were also shortened. That changes no patch line.

## What was discovered

The game counts how long a fighter has been in its current move in one
per-fighter counter (`actionFrame`). No group compensated it, so every handler
that compares it to a fixed number runs at double speed. These were found in the
decompiled source:

| Handler | Compare | Status |
|---|---|---|
| launched, blown away | after 8 frames | fixed here |
| vanish dash | 13 and 7 frames | open, no scene triggers it yet |
| moves 0x67-0x69 | 10 frames | open, no scene triggers it yet |
| clash struggle | 16 frames | already covered by `beam clash` |
| lie down | 91 frames | covered by the knockdown fix (#70) |

## Get this version

Download `428113C2.pnach` from the
[v27-recovery-windows release](https://github.com/Saupernova13/pcsx2-bt3-60fps/releases/tag/v27-recovery-windows),
or:

    git show v27-recovery-windows:patch/428113C2.pnach > 428113C2.pnach

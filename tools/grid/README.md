# The 30Hz tick grid (work in progress, issue #127)

At 60fps every one-tick hand-off (a request applied next tick, an event seen next tick, a flag read
next tick) costs 1 vsync instead of 2, so multi-step moves end early. The grid makes the discrete
steps happen on even vsyncs only (the 30fps tick) while motion and animation keep their 60fps
half-steps.

The group is `[60FPS - tick grid]` in `wip/working.pnach`. `grid13.lines` was an earlier prototype, applied in the rig as
`fk-animation clock,smash charge+lines:tools/grid/grid13.lines` (it carries its own copies of those
two groups). Parts:

| Part | Where | What |
|---|---|---|
| A | `001E2430` -> `000F2A00` | state switch and animation requests on even ticks; effect-raised flags 0xA7..0xAB become visible there (`000F2820` defer, `000F2880` flush) |
| B | `001C4858` -> `000F2240` | an animation's end reported on odd ticks |
| S | `001D4A24` -> `000F21C0` | the pad read on even ticks |
| prev | `001C4818`, `001C4988` | prevFrame updated on odd ticks, so an even tick's window is the whole 30fps tick |
| passed | `001C4A08`, `001C4A80` | PassedRatio / PassedFrame answer 0 on odd ticks |
| events | `001C1F54` -> `000F3000` | fighter events: none on odd ticks; on even ticks read half a step ahead (what the 30fps tick shows), hit windows at the real frame |
| items | `00153D68`, `00156134` | the multi-piece item steps on even ticks; the blast item's end timer and decisions on even ticks |
| charge | `001E4610`, `001E4F34`, `001E3404`, `001E4804` | full-charge count in 30fps ticks, whole first charge step, Perfect test back to == 1 |

`bench.py` (run from `work/tools-scratch`) times ten Blast 2 / Ultimate scenes against 30fps.

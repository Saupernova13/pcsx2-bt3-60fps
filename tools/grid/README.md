# The 30Hz tick grid (work in progress, issue #127)

At 60fps every one-tick hand-off (a request applied next tick, an event seen next tick, a flag read
next tick) costs 1 vsync instead of 2, so multi-step moves end early. The grid makes the discrete
steps no button starts happen on even vsyncs only (the 30fps tick) while motion and animation keep
their 60fps half-steps. Every press and release still acts on the vsync it arrives: the pad is read
every vsync, and a switch on an odd vsync goes through when the fighter's input changed on it or the
vsync before.

The group is `[60FPS - tick grid]` in `wip/working.pnach`. `grid13.lines` was an earlier prototype, applied in the rig as
`fk-animation clock,smash charge+lines:tools/grid/grid13.lines` (it carries its own copies of those
two groups). Parts:

| Part | Where | What |
|---|---|---|
| A | `001E2430` -> `000F2A00` | state switch and animation requests on even ticks, or on an odd tick when the fighter's input changed this vsync or the last (pressed / released / command edges, chr+0x744..0x758; last-edge vsync per fighter at `000F2B80`); effect-raised flags 0xA7..0xAB become visible on even ticks (`000F2820` defer, `000F2880` flush) |
| B | `001C4858` -> `000F2240` | an animation's end reported on odd ticks |
| prev | `001C4818`, `001C4988` | prevFrame updated on odd ticks, so an even tick's window is the whole 30fps tick |
| passed | `001C4A08`, `001C4A80` | PassedRatio / PassedFrame answer 0 on odd ticks |
| events | `001C1F54` -> `000F3000` | fighter events: none on odd ticks; on even ticks read half a step ahead (what the 30fps tick shows), hit windows at the real frame |
| items | `00153D68`, `00156134` | the multi-piece item steps on even ticks; the blast item's end timer and decisions on even ticks |
| blend | `001C4420` -> `000F3480` | a new blend's first step whole (`BtlAnim_ApplyBlend`), as on its first 30fps tick |

`gridIgen.py` builds the group's lines from the earlier all-input-on-the-tick version (`python gridIgen.py gridF.lines gridI.lines`). `lat.py` is the input check: for every save slot, input and tick phase, the vsyncs from a press or release reaching the game to the fighter's first state or animation change, against another arm.

`bench.py` (run from `work/tools-scratch`) times ten Blast 2 / Ultimate scenes against 30fps.

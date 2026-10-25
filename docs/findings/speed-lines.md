# Speed lines

Newest sections at the bottom.

## 2026-09-29 - issue #8: the speed lines spawn about 1.66x as often

The pink and yellow radial streaks round a hit in Hercule's Dynamic Mess Em Up Punch (save
state 5, `L2`+`Triangle`) are sprites spawned by the sprite effect class
(vtable `002C3EF0`, update `FUN_001866C0`). Found through the random numbers
they use: over v100-v300, three sites in `FUN_001840A0` (`00184320`, `0018434C`,
`00184380`) draw once per line in the Dynamic Mess Em Up Punch and never in idle.
`FUN_001840A0` is called by `FUN_001853C8`, which `FUN_001866C0` calls at
`001867B4`. With that one call removed, the streaks are gone. They were missed
by the earlier draw-disable test because the class's own draw method does not
draw its sprites.

| | 30fps | 60fps |
|---|---|---|
| lines spawned, v100-v300 | 47 | 78 |
| spawner calls per emitter | 20, 15, 12 | 23, 35, 20 |
| spawn spacing inside a window | 4 vsyncs | 3 vsyncs |

### Why halving the timers was not enough

Each tick the update either spawns - when the countdown `+0x1F8` is at or below
0, and the spawner then reloads it with the emitter's interval (`def+0x64`,
0.99 here) - or counts `+0x1F8` down. `[blast effect duration]` halves that
step and five others in the update (`+0x204`, `+0x20C`, `+0x1F4` life, `+0x1FC`,
`+0x200` window), which keeps each timer's length but not the update's order:

- The spawn tick does not count down. At 30fps a cycle is a spawn tick and one
  countdown tick, 4 vsyncs; with half steps it is a spawn tick and two countdown
  ticks, 3 vsyncs.
- Gating only the spawn call to even ticks fixes the spacing (62 lines), but a
  window (`+0x200`) that closes on an odd tick still lets one more burst through
  on the next even tick; at 30fps the same tick that sets the end flag also
  empties the window.

### The fix

`[60FPS - sprite effect clock]` runs the whole update at 30Hz, as the game does:

- after the freeze check, the branch at `001866F4` goes through a wrapper at
  `000F1C20` that takes the frozen path (`001868E0`) on odd ticks as well;
- each of the six halved steps loads a full 1.0: the `mtc1 $at, fX` after each
  of `[blast effect duration]`'s `lui $at, 0x3F00` becomes
  `lwc1 fX, -0x5798($gp)`, the static pair (1.0, 0.0) at `002FEAD8`. Nothing
  stores to it by `$gp` or by absolute address, and a write watch over eight
  scenes (300 vsyncs each) saw no write.

No word overlaps another group. With this group the six `[blast effect
duration]` words have no effect, and PR #66's gate on the particle stepper
always passes, since the update then only runs on even ticks.

### Measured

Every open fix on:

| | 30fps | 60fps before | 60fps with the group |
|---|---|---|---|
| Dynamic Mess Em Up Punch lines spawned, v100-v300 | 47 | 78 | 47 |
| emitter `01A2E850` spawns | 108, 112, 116, 166 ... (15) | 107, 110, 113, 116, 119 ... (35) | 107, 111, 115, 165 ... (15) |
| GS2's Ultimate hearts, class updates | 24, v135-v253 | 51, v134-v254 | 24, v134-v252 |
| Kamehameha, first four objects' updates | 18, 49, 28, 30 | 39, 100, 52, 58 | 19, 50, 28, 29 |

Every emitter spawns as often as at 30fps, at the same spacing, one vsync
earlier. Dynamic Mess Em Up Punch and Kamehameha damage and both fighters' state
timelines are the same with and without the group. All 15 smoke moves return
to idle.

## 2026-10-09 - the scene above is Dynamic Mess Em Up Punch; Present Bomb too

`L2`+`Triangle` for Hercule is Dynamic Mess Em Up Punch, the name the game
shows and the wiki lists (1 or 6360 damage, chosen at random). The sections
above called it Present Bomb, which is `L2`+`Up`+`Triangle`. Present Bomb, the
move issue #8 names, spawns the same lines while the bomb flies. Calls to
`FUN_001840A0` over v60-v200 from save state 5, `L2`+`Up`+`Triangle`, in the
full test build:

| | 30fps | without `sprite effect clock` | with it |
|---|---|---|---|
| lines spawned | 24 | 32 | 24 |

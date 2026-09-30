# Stage scenery and ambient animation

The stage scene graph, its keyframe tracks, and the ambient props on them.

## 2026-09-16 - issue #9, the stage: a scene graph with its own clock

The report: *"Background Helicopter in world tournament stage moves at double
speed"*. Two earlier attempts at the stage family failed, and both failures are
worth keeping because neither was a measurement error this time.

### Why the earlier attempts found nothing

The 2026-09-16 morning attempt measured **Rocky Area**, and reported ~1200
uncompensated fields before that was withdrawn as the wrong save state. The
corrected re-run found 32 movers on Rocky Area, 27 at 2x, all of them known
read-2x-by-design families.

That answer was right, and the reason is now clear: **Rocky Area has no animated
scenery at all.** A breakpoint on the stage evaluator's own instruction never
fires on that map, in any arm. There was nothing there to find.

`#9` names the World Tournament stage specifically. Built from the menus -
Vegeta (Scouter), `COM Settings -> Stand`, World Tournament Stage - Noon, cut
with every group off and confirmed by screenshot
(`work/state-backups/world-tournament-noon-vegeta.p2s`, slot 4) - the same scan
reads very differently:

| scene | steady movers | still 2x | biggest pages |
|---|---|---|---|
| Rocky Area - Evening | 32 | 27 | the fighter block |
| **World Tournament - Noon** | **1672** | **1254** | `006Dxxxx` 468, `007Dxxxx` 468, `006Cxxxx` 105 |

The fighter block contributes 25 of the 1254.

### Following it to the cause, past two dead ends

A write watchpoint on the biggest family lands in `00121388`/`00121394` - a
`sqc2 vf24-27` block, a bare 64-byte matrix store. The fields are **world
matrices**, the output of the transform pass, exactly the follower-not-cause
trap this log already records for `00121394`.

Breaking on the store and tallying `ra` instead of the address is what got past
it: **`00111610`, 48 hits of 55**, inside `FUN_00111358`, the scene-graph walker.
Still downstream, but it named the system.

The smaller clusters the scan flagged were the way in. `016F1F74` and friends -
nine words, value 0.92, climbing 0.0316 per 50 ticks - watchpoint into
`00123A9C`:

```
00123A88  lwc1  f01, 0x14(s1)     # b
00123A8C  lwc1  f00, 0x14(s0)     # a
00123A90  sub.s f00, f00, f01     # a - b
00123A94  mul.s f00, f00, f02     # * t
00123A98  add.s f00, f00, f01     # + b
00123A9C  swc1  f00, 0x24(s2)
```

That is a keyframe lerp, and `FUN_00123890` around it is the evaluator: given a
time it finds the two keys straddling it and interpolates position and rotation.

### The cause, and the fix

`FUN_00123890` has exactly one caller, `FUN_00115478`, which reads the time from
`node+0x1C` at `00115648` and advances it a few instructions earlier:

```
001153C8  lui   $at, 0x4000       # 2.0f
001153CC  mtc1  $at, f20
00115410  add.s f00, f00, f20     # time += 2.0, once a tick
00115418  swc1  f00, 0x1C(s0)
00115434  c.lt.s f00, f01         # past the end of the track?
0011543C  sw    zero, 0x1C(s0)    # wrap
```

**Two units of track per tick.** Sixty a second at 30Hz, a hundred and twenty at
60Hz. Every animated prop on a map that has them runs at exactly double speed,
and the immediate is the whole of it.

| arm | stage time over 80 vsyncs |
|---|---|
| unpatched 30fps | 94 -> 172, **+78** |
| the 27 groups | 122 -> 280, +158 |
| **+ `lui $at, 0x3F80`** | 92 -> 171, **+79** |

A cropped sky-band picture score moves 6.98 -> 5.69 over the same window; the
whole-frame score barely moves, because two fighters and a stadium crowd
dominate the frame and a blimp does not. The memory figure is the one that
settles it.

### What this does not fix

**Issue #11, the Rocky Area wind, is not this system.** The evaluator never runs on
Rocky Area - Evening, in any arm, from either of the two states cut on that map.
Whatever animates the wind, it is not the stage scene graph, and the rate scans
of that map were telling the truth.

**A note on which issue is which**, because this session got it backwards once
and wrote it into a PR: **#9 is the World Tournament aerials** - "the Blimp and
Helicopter move faster than in the vanilla game" - and **#11 is the Rocky Area
wind**. The user's original list said "the animation of the wind is sped up in
desert sequence", and the desert sequence is Rocky Area, so #11 needs no
clarifying question. Read the issue, not the memory of it.

## 2026-09-21 - issue #52, the clouds: a sky scroll outside the keyframe graph

The report: the clouds still move at double speed after `[60FPS - stage
animation]` fixed the World Tournament blimp and banners.

### Found by rate scan, then by watchpoint

A rate scan of Rocky Area (save state 7, 30fps against v24, 120 vsyncs) leaves
two slow floats at 2x outside the fighters: `01A9AEE0` and `01A9AF28`, stepping
-0.0016 a tick. A write watchpoint lands in a setter (`001A77C0`) called from
`FUN_00135200`, which copies them out of a global object - the pointer at
`gp-0x58BC`, `01A9AC80` in both scenes tested. That object's own update is
`FUN_001350E0`:

```c
sky->u += sky->dir_u * sky->rate;      /* +0x2A8 += +0x2A0 * +0x2B0 */
sky->v += sky->dir_v * sky->rate;      /* +0x2AC += +0x2A4 * +0x2B0 */
/* each wrapped into +/- sky->wrap, +0x2B4 = 4.0 */
```

once a tick, no timestep. `FUN_00135200` draws the layer from `u` and `v`. None of
it is in the stage scene graph `FUN_00115478` walks, so halving that graph's
time step could never reach it.

On the World Tournament the rate is 0.0008, direction (0.871, 0.491).

### The fix

`+0x2B0` is loaded twice, at `0013511C` for `u` and `00135138` for `v`. Each load
becomes a jump to a four-instruction helper (`000F18C0`, `000F18D8`) that loads
it, multiplies by 0.5 and returns past the load. The next instruction, loading
the direction, runs in the jump's delay slot as it ran before. `$f3` and `$at`
are unused in `FUN_001350E0`, and its `ld ra` has already run.

| save state 7, 240 vsyncs | ticks | u moves |
|---|---|---|
| 30fps | 120 | -0.19199 |
| v24 | 240 | -0.38398 |
| v24 + `[60FPS - sky scroll]` | 240 | **-0.19197** |

Photographed on the World Tournament at vsync 400 from the same state, the sky
right of the banners, mean pixel difference against the 30fps frame:

| arm | difference |
|---|---|
| 30fps, a second run | 0.0 |
| v24 | 20.3 |
| v24 + this group | **2.3** |

### A probe that misled, and why it is recorded

Writing a new `u`, `v` or wrap into the object by hand and photographing two
frames later changed **no pixel at all**, on either map, which briefly read as
"this layer is not the clouds". The A/B above says it is. The probe was taken on
a paused VM stepped two frames, and the layer evidently does not pick the new
value up that soon; the arms-at-the-same-vsync comparison is the one to trust.

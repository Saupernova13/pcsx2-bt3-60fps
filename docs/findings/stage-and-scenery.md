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

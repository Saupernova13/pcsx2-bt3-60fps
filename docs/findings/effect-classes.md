# Effect classes and their clocks

Newest sections at the bottom.

## 2026-09-28 - issue #10: two effect classes that count 30Hz ticks

The re-test of the combined build left one thing wrong in Vegeta (Scouter)'s
Great Ape transformation: the energy ball's big flash came 12 vsyncs early. Mean
screen brightness per vsync, from `rocky-vegeta-scouter-standing.p2s` (slot 9),
`R3`:

| event | 30fps | 60fps, every fix |
|---|---|---|
| small flash starts | v69 | v67 |
| big flash | v89 | v77 |
| gap | 10 ticks | 10 ticks |

### Finding the clock: same values per tick in both arms

A rate scan cannot see this kind of defect, and a search for `+1` counters
ending at the flash found nothing. What found it was recording all of RAM at
every vsync in both arms and keeping the words whose values are **identical per
tick** in the two arms over the window (every vsync at 60fps, every second vsync
at 30fps). A clock the patch compensates takes different values per tick in the
two arms; one it missed takes the same ones. Of 42,075 words that changed, 53
matched, and the ones that were not display lists or the frame counter were one
effect's tracks, stepping `+2.0`, `+0.35` and `+90` degrees a tick.

One trap on the way. The most flash-like of them, `01FFE5CC` (128 down to 0 by
16 a tick, then 255 down by 30), is on the **EE stack**. A write watch on it
stops in four unrelated functions within a few frames. A word near the top of
RAM that looks like state at a frame boundary can be the leftovers of whatever
function last used that stack depth.

### The scripted effect tracks - vtable `002C4278`

A write watch on the track clock names `FUN_001AAB40`. The class:

| slot | function | role |
|---|---|---|
| `+0x00` | `FUN_0019DB90` | update: freeze check, then the countdowns and `FUN_001AAB40` |
| `+0x14` | `FUN_0019DD38` | draw, separate from the update |

The effect object is `node+0x38`. It carries up to eight tracks of `0x60` bytes
at `obj+0x08`, and `FUN_001AAB40` advances each of them once a tick:

    track+0x04 += 2 * track+0x18     the track clock: 60Hz frames per 30Hz tick
    track+0x20, +0x24 = rand()       jitter, two draws of FUN_002A9C78 per track
    track+0x30 += track+0x40         spin, through FUN_00121EC0
    track+0x14 -= 1.0                the fade, once the clock passes its end

When the clock reaches its end (`+0x0C`), a track loops back to `+0x00` while its
loop count (`+0x1C`) lasts, or fades. `FUN_0019DB90` itself counts four more down
by 1.0 a tick:

| field | what | set from |
|---|---|---|
| `obj+0x9C` | start delay | a byte of the effect command, `0014EDA0` |
| `obj+0xA0` | hold before the fade | a byte, `0014EDB4` |
| `obj+0xA8` / `+0xA4` | fade remaining / total | a byte, `0014EDC8` |
| `obj+0xAC` | lifetime | seconds * 30.0, `0019DAFC` |

All of them count 30Hz ticks, and no group touched the class. The effects are
created by `FUN_0019D730`, called from the effect-command handler `FUN_0014EBD8`
(`0014ED88`, dispatched from `001507E8`) and from `001A6D5C`.

**The fix.** `FUN_001AAB40` has one caller, `0019DBD4`, and the draw is its own
method, so that call goes through a wrapper at `000F1A40` that runs it on even
ticks only. Clock, jitter, spin and fade then run at their authored 30Hz, drawn
every frame. The four countdowns step 0.5: each test is `<= 0`, so half steps
take exactly twice the ticks.

It runs in Vegeta's transformation (three effects), Goten's (three) and GS2's
Ultimate (a hit spark and one later effect). Measured with every other fix on:

| Vegeta's energy ball | 30fps | without | with |
|---|---|---|---|
| small flash starts | v69 | v67 | v68 |
| big flash | v89 | v77 | v88 |
| frames v70-v130, best match against 30fps | 0 | 8.4-61.2 | 1.0-2.3, one vsync later |

GS2's spark, traced tick by tick: lifetime, fade and track clock equal the 30fps
values on every even vsync, and the effect ends on the same vsync, v146. Gating
the jitter to 30Hz shifts the random draws other effects get, so a random ring in
the same hit looks different from the ungated 60fps run; that is the RNG, not
timing.

### The transformation flash - vtable `002C42D8`

After the ball, the transformation goes white and cuts to the Great Ape. At
30fps the white lasts 22 vsyncs; at 60fps 11. Both arms cut when the fighter's
ticks-in-state reads 14. The same-values-per-tick search over that window
named `019C6FC4`, which is `obj+0x564` of a second effect class:

| slot | function | role |
|---|---|---|
| `+0x00` | `FUN_001A0850` | update: a small phase machine in `node+1` |
| `+0x04` | `FUN_001A0600` | init |

It is created by `FUN_001CF890` for every transformation type in
`fighter+0x12DC`, and flag `0x10` (set by `FUN_001A0DD8` when the fighter's
event bit 1 at `fighter+0x1262` goes up) starts phase 2, the white. Then:

    obj+0x564 += 1.0 a tick     until it passes obj+0x568 = 10.0   (001A06B8)
    obj+0x55C += 1.0 a tick     until it reaches obj+0x560, a byte of the effect's data

**The fix.** Both steps become 0.5. The hold's test is strict
(`c.olt.s limit, count`), so half steps would end it at 10.5, one tick early;
the limit becomes 10.5 and the hold ends at 11.0 after 22 ticks, the 30fps 11
exactly. The end timer's test is `<=`, so its half step alone is exact.

| | 30fps | without | with |
|---|---|---|---|
| Vegeta: white | v405-v426 | v403-v413 | v403-v424 |
| Vegeta: cut to the Great Ape | v427 | v414 | v425 |
| Goten: the hold (phase 2) | v149-v171 | v146-v157 | v146-v168 |

The 2-3 vsync lead is before the hold: the event bit that starts it comes early.
That is the same 3-vsync lead PR #68 leaves on Goten's reveal (issue #67), and
not this class; its source is not traced.

### The map for the next pass

28 vtables have an update slot that calls a freeze check (`FUN_0012D1D0`, or
`FUN_0012CED0`). Found by walking every `jal` to them back to its function's
prologue and looking the function up in the data section. Two of them,
`002C3B38` and `002C3D28`, check it in slot 3 (`+0x0C`) as well; the draw slot
(`+0x14`) of many uses `FUN_0012D298` instead. Which fixes act inside each
update:

| vtable | update | covered by |
|---|---|---|
| `002C3D88` | `FUN_00176980` | `projectile travel`, `projectile life` |
| `002C3DE8`, `002C3E18` | `FUN_00177968`, `FUN_00178A28` | `thrown object rate` |
| `002C3EF0` | `FUN_001866C0` | `blast effect duration`, `sprite effect rate` (PR #66) |
| `002C40F0` | `FUN_001961A0` | `blast effect duration` |
| `002C4278` | `FUN_0019DB90` | `effect track clock` |
| `002C42D8` | `FUN_001A0850` | `transformation flash` |

Not examined yet, and nothing acts inside them: `002C3A00` (`0015E960`),
`002C3AA8` (`00168C00`), `002C3B08` (`0016B168`), `002C3B38` (`0016BAC8`),
`002C3B98` (`00171940`), `002C3C88` (`001732C0`), `002C3CC8` (`00174590`),
`002C3D28` (`001758F8`), `002C3D58` (`00175F40`), `002C3DB8` (`001771D8`),
`002C3E48` (`0017C8F8`), `002C3E78` (`0017D8E0`), `002C3EA8` (`0017F160`),
`002C3F20` (`001876A0`), `002C3F50` (`00187F90`), `002C3F80` (`0018C4E8`),
`002C40C0` (`00190FE8`), `002C42A8` (`0019E308`), `002C4308` (`001A2DD0`),
`002C4338` (`001A3CC8`), `002C4368` (`001A6C58`). Some may be paced by the
animation clock or the tween service and be correct already; each needs its own
look. The aura and the particles are not on this list: their updates do not call
the freeze check, and `aura update rate` and `particle update rate` gate them.

### What is left

- GS2's Ultimate: the fireball on the first hit is 3 vsyncs long at 60fps and
  fills the view, against 4 at 30fps and a smaller orange ball. Not this class;
  one of the unexamined ones above.
- The transformation event lead above: 3 vsyncs on Goten, 2 on Vegeta.

## 2026-10-09 - issue #139: the hit effect, class `002C3F20`

A census of the classes listed above as not examined: every rig scene, idle and
nine moves (ki charge, both Blast 2s, an Ultimate, a rush, ki blasts, a
transformation, a smash), with a breakpoint on each update
(`work/tools-scratch/effcensus.py`). Four ran:

| vtable | update | ran in |
|---|---|---|
| `002C3F20` | `FUN_001876A0` | almost every hit: rushes, smashes, ki blasts, Blast 2s, Ultimates |
| `002C3D58` | `FUN_00175F40` | reaching Max Power Mode; it makes the shockwave of #137 |
| `002C3B38` | `FUN_0016BAC8` | Krillin's Ultimate |
| `002C3DB8` | `FUN_001771D8` | Goten's Ultimate |

None of `002C3A00`, `002C3B08`, `002C3B98`, `002C3C88`, `002C3CC8`, `002C3D28`,
`002C3EA8`, `002C42A8`, `002C4338` or `002C4368` ran in any of them.

`FUN_001876A0`, once a tick unless its freeze check (`FUN_0012D1D0`, at
`001876C0`) says frozen:

- if `+0x545`, `+0x14` -= `+0x54C`;
- for each set bit of `+0x544`, `FUN_00151810` copies the object's position into
  a sub-effect;
- `FUN_001871A8` runs the emitters: for each of 19, `FUN_0014D908` works out the
  start and stop flags (no clock) and `FUN_0014FF90` spawns;
- with flag 1 set (from outside), `+0x550` += 1.0 until it reaches `+0x554`,
  then flag 2, then `FUN_001ADA58` removes it.

The life `+0x554` was 0.0 on a rush hit, so the object ends one tick after its
owner sets flag 1, at v31 at 30fps and v32 at 60fps: the life is the owner's.
What runs per tick is the emission. Calls to `FUN_0014FF90` from `00187284`:

| scene | 30fps | 60fps before | with `[60FPS - hit effect rate]` |
|---|---|---|---|
| Cell (1st Form)'s rush, v8-v45 | 46 | 79 | 46 |
| Krillin's ki blast hit, v12-v70 | 78 | 159 | 78 |
| Cell's smash, v70-v140 | 70 | 115 | 65 |
| Super 17's Hell's Storm, v85-v200 | 424 | 872 | 440 |

The group makes the freeze check report odd ticks as frozen, the shape
`[60FPS - burst effect rate]` uses. Photographed on Cell's rush at v12-v26, the
spark draws in all three arms.

Two more emitter paths showed up in the same counts and are not this class: the
ki blast projectile's own (`001766B8`, 27 calls at 30fps against 37 on the ki
blast hit) and the game objects' (Hell's Storm's bullets, through
`FUN_00155918` and `FUN_0014FF50`: 257 against 410). There are 10 direct callers
of `FUN_0014FF90` and 12 per-object emit helpers that call `FUN_0014FF50`.

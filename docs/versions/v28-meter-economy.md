# v28-meter-economy - DRAFT

| | |
|---|---|
| Tag | `v28-meter-economy` |
| Date | 2026-10-25 |
| Built on | [v27-recovery-windows](v27-recovery-windows.md) |
| Groups | 3 shipped group(s) changed |
| Confidence | **DRAFT - fill this in** |

> **DRAFT.** Every other note on this page is written for a player: what this
> version changes over the last one, and what was discovered on the way. Rewrite
> this before the release PR merges - its merge is what publishes the release.

## What it changed

Shipped groups this version carries that the last release did not:

- `60FPS - ki charge loop`
- `60FPS - max power charge`
- `60FPS - meter economy`

The commits to `wip/working.pnach` it carries since v27-recovery-windows:

- fix(patch): fill ki at its real speed past a charge's first second (f6ab39a)
- docs(patch): name PR #25's buff duration without its group header (e9860c5)
- docs(meter): record that the economy gate also fixes the Blast 1 buffs (56962bf)
- fix(patch): fill the Max Power Mode gauge at its real-time speed (df2f081)
- fix(patch): gate the fighter meter economy to even ticks (2c689b6)

## What was discovered

fix(patch): gate the fighter meter economy to even ticks

This PR fixes your ki filling up and emptying twice as fast as it should at 60fps - including Max Power Mode arriving after half the charging and running out in half the time - and Blast 1 buffs wearing off in half their published time, along with everything else the game hands you "after a second" of standing there.

`[60FPS - meter economy]` gates `FUN_001E16C0` to even ticks at its single call site, `001E2584`. `[60FPS - max power charge]` changes the 30.0 ticks a second in `FUN_0020F000`, which sizes the charge state's per-tick fill of the Max Power gauge, to 60.0. `[60FPS - ki charge loop]` halves the ki the charge state's handler adds itself once a tick after the charge's first second, through a wrapper at `001EB8D4` that alternates the rounding.

| | Before | After |
|---|---|---|
| `+09F8` gained per 60 vsyncs, idle | 210k | 105k, matching 30fps |
| The game's "one second" | 30 vsyncs | 60 vsyncs |
| Ki gained per 10 vsyncs, a held charge after its first second | 7950 | 3975 (30fps: 3975) |
| Charging to Max Power Mode, full Ki | 56 vsyncs | 113 vsyncs (30fps: 112) |
| Max Power Mode draining from full | ~480 vsyncs | ~1020 vsyncs, the 30fps slope |
| Blast 1 buffs (After Image Strike, published 15s) | 7.40s | 14.88s (30fps: 14.88s) |
| Momentum peak after a three-hit rush | 8800 | 16000 (30fps: 15600) |
| Groups | - | `meter economy`, `max power charge`, `ki charge loop` |

## What the function does in one tick

Ki income by two paths, three more gauges, a `fighter+0xD80 -= 400` drain, and
the clock the once-per-second blocks run on:

```c
bVar1 = 0x1d < puVar10[0x4cb] + 1;      /* puVar10[0x4cb] is fighter+0x132C */
puVar10[0x4cb] = puVar10[0x4cb] + 1;
if (bVar1) puVar10[0x4cb] = 0;
...
if (bVar1) { /* the once-a-second blocks */ }
```

Every constant in it is authored per 30Hz frame, and `fighter+0x132C` counting
0..29 is the game's second, so gating the call fixes the rates and the second
together.

## Results

| after 46 vsyncs, Cell on Rocky Area | `+099C` | `+09F0` | `+09F8` | second |
|---|---|---|---|---|
| unpatched 30fps | 94498 | 95520 | 259962 | 14 |
| 27 groups, no gate | capped | capped | 340761 | 7 |
| **27 groups + this gate** | **94498** | **95520** | **259962** | **14** |

| Goku (Early), `L2` at full Ki, first add to 30000 | fill | per tick |
|---|---|---|
| unpatched 30fps | 112 vsyncs | 535 |
| 27 groups + meter economy | 56 vsyncs | 535 |
| **+ max power charge** | **113 vsyncs** | **265** |

| Krillin holding `L2` from 20000 ki, ki per 10 vsyncs | v0-v50 | v50-v180 |
|---|---|---|
| unpatched 30fps | 5425 | 3975 |
| meter economy only | 5425 | 7950 |
| **+ ki charge loop** | **5425** | **3975** |

Equal at every sample over 60 vsyncs, for both fighters. Spending ki on a move
is untouched: that runs on the move's own path, not per tick.

## Also in this PR

| file | change |
|---|---|
| `docs/rig.md` | adds a seventh trap: `launch` attaches to an emulator already holding port 28110, so a new group name can silently never reach the cheat engine |
| `docs/findings/meter-economy.md` | the derivation, the gauge offsets, the two measurement shapes that produce false positives here, the Max Power Mode measurements, Momentum, and the buff countdown |
| `docs/status.md` | v24 (proposed) |

Closes #4
Closes #20

🤖 Generated with [Claude Code](https://claude.com/claude-code)

> Seeded from one merge's body, which may describe only one of the changes
> listed above: #16.

## Get this version

Download `428113C2.pnach` from the
[v28-meter-economy release](https://github.com/Saupernova13/pcsx2-bt3-60fps/releases/tag/v28-meter-economy),
or:

    git show v28-meter-economy:patch/428113C2.pnach > 428113C2.pnach

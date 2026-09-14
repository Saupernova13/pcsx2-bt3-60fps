# v09 - the scripted clocks

| | |
|---|---|
| Tag | `v09-scripted-clocks` |
| Date | 2026-09-07 |
| Built on | [v08](v08-blast-duration-only.md) |
| Groups | 17 (424 patch lines) |
| Confidence | **DO NOT USE** - the state 157 trap |

## What it changed over v08

- Added `[60FPS - sequence wait]`. `FUN_00158850` steps one node of a scripted sequence
  per tick, and a step that is waiting counts a plain integer down at `00158914`
  (`[node+4]`) and `0015894C` (`[node+8]`), both authored in 30Hz frames. It now counts
  down on even ticks only. Unlike gating the node's update it skips no work: the step
  still runs, still spawns and still draws.
- Added `[60FPS - state phase timers]`. Every fighter state handler keeps a counter that
  `FUN_001E23D0` zeroes on entry, advances once a tick, and compares against a count
  authored in 30Hz frames. 22 of the 28 sites now jump to a trampoline that adds one on
  even ticks only; the store still runs every tick, so code reading the counter as a
  level is unaffected. The other six - `001F1C74`, `001F31C0`, `001FBF28`, `001FCE34`,
  `001FF9A8` and `001FFC10` - are levels rather than clocks, a combo index and an input
  window among them.

## What was discovered

- **Two integer clocks sit behind everything the game stages.** Camera cuts, mouth
  lines, fades and the instant an ultimate lets go of its beam wait on the sequence
  counter; how long a Blast 2 charges, how long a recovery lasts and when a beam is
  released are phase timers. An integer cannot be halved and freezing one hangs the
  state, so the shape of the fix is a parity gate on the increment.
- **The blanket gate was wrong.** All 28 phase-timer sites were gated first; scored one
  at a time against a held Blast 2 and a mashed rush, six turned out to be levels, and
  gating them cost an ordinary rush its fourth hit or cut the charge short.
- **Shrinking a live group leaves its hooks in RAM**, because patchctl can only restore
  addresses the pnach still names. That had made the previous measurements
  unreproducible.
- **The user's full defect list** was recorded on 2026-09-07: what was still running
  fast, what was overcompensated and running slow, and what the entries had in common.

## Evidence

- Angry Kamehameha from save state 8, first hit to first hit: 30fps 191 vsyncs, without
  `sequence wait` 124, with it 161. Every staged beat before the beam launch lands
  within two vsyncs of the 30fps game.
- Held Super Kamehameha from save state 1, button down throughout, time to the first
  hit: 30fps 176 vsyncs, without phase timers 115, with all 28 sites 175 - the same six
  hits, damage and eight-vsync spacing in all three. With the final 22 sites, a held
  Blast 2 lands its first hit at 175 against 176, and the rush keeps its fourth hit.
- In free-running real time, the held Super Kamehameha's six hits land at
  2.92/3.05/3.19/3.32/3.45/3.59s at 30fps and 2.89/3.02/3.15/3.29/3.42/3.55s with this
  build. Charge ball, beam, flash and 12420 damage render and land the same in both.

## Still wrong in this build

- **The state 157 trap.** After this release the user hit Goku parked in an airborne
  dash/flight state with no queued transition. `state phase timers` was withdrawn in
  v10 on reasoning, not proof. Do not use this build.
- An ultimate's beam lands its first hit about half a second early: the cinematic up to
  the launch now matches within two vsyncs, and the flight does not.

## Get this version

    git show v09-scripted-clocks:releases/v9-scripted-clocks/428113C2.pnach > 428113C2.pnach

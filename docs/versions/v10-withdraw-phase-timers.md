# v10 - state phase timers withdrawn

| | |
|---|---|
| Tag | `v10-withdraw-phase-timers` |
| Date | 2026-09-07 |
| Built on | [v09](v09-scripted-clocks.md) |
| Groups | 16 (204 patch lines) |
| Confidence | Superseded - identical group list to v12 |

## What it changed over v09

Removed `[60FPS - state phase timers]`.

The user hit a repeatable trap: Goku parked in fighter state 157
(`FUN_001E6DC8`, an airborne dash/flight state) with pending state `0xFFFFFFFF` -
no queued transition - and no button held, recurring after a clean state load.
The group was withdrawn **on reasoning, not proof**. It was the only shipped group
that touched the fighter state machine's counters, which is exactly the mechanism
behind a fighter that cannot leave a state, and all 28 of its sites had been
validated against two **grounded** oracles - a held charge and a mashed rush. No
airborne state was ever tested, and the trap is airborne.

`[60FPS - sequence wait]` was kept: the user confirmed in play that it fixes the
ultimate's cinematic, and it does not touch state transitions.

## What was discovered

- **Blasts keep their real timing in normal play** - confirmed by the user playing
  v09 with the game running free, not by frame stepping.
- **The data segment does contain 1/30 and 1/60**, correcting an earlier claim in
  the log. There are 24 per-tick rates pooled in `.lit4`, each read by exactly one
  instruction.
- **Blast flash duration - found, fixed, and withdrawn before it shipped.**
  `FUN_0017D8C0` drains `[node+0x4E4]` by 1/30 a tick and expires the node in 9
  ticks in both arms: 10 vsyncs at 60fps against 19 at 30. Repointing the load at a
  1/60 the pool already holds put it back on 19 exactly - one word, no trampoline,
  a fix shape available only because the constant lives in `.lit4`. It was reverted
  on the user's report that Goku got stuck in a loop.
- **The process failure mattered more than the fix.** A probe group used to test it
  had written the same word into RAM and was never restored, so the change was live
  in the user's session while it was believed not to be. Extending a node's lifetime
  is not free: a node that lives twice as long is a node something else may still
  be waiting on.
- The stuck loop was recorded carefully as established, misread and not
  established. It was never reproduced under controlled conditions.

## Evidence

After deploy, all 22 hook sites read the stock ELF word and the `000F1000-1318`
trampoline scratch was zero.

## Get this version

    git show v10-withdraw-phase-timers:releases/v10-withdraw-phase-timers/428113C2.pnach > 428113C2.pnach

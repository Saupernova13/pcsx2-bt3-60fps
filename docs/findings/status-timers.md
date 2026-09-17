# Fighter status timers

The per-tick status timer block: paralysis, Solar Flare's lock-off, the combat timers.

## 2026-09-17 - issue #34, the combat timers

Paralysis (#28) exposed a block of per-tick countdowns in the fighter update,
`FUN_001E1D20`. Mapping each timer's arming site back to the state table named
most of them, and exercising the moves SuperCombo describes armed five.

### Which move arms which timer

Save state 4 is Goku (Early) against a standing Ultimate Gohan
(`work/state-backups/rocky-goku-early-vs-standing-gohan.p2s`); a script dashes in
(`Up` + `Cross` until 20 units) and then plays an input. Goku's Rushing
Techniques are, in slot order, Heavy Finish, Kiai Cannon, Flying Kick and Heavy
Finish, so `Square` then `Triangle` is Heavy Finish.

| field | armed by | what it does |
|---|---|---|
| `+0x0D48` | every hit taken; states 250, 252 | combo timer, re-armed to ~32 per hit |
| `+0x1036`, 50 bytes | hits | a used option's byte drops to 0 and climbs 1 a tick, capped at 100 |
| `+0x0FF0` | the end of hitstun or stun (states 189-204) | 14 ticks |
| `+0x0DE4` | the attacker's Ground Slash (states 174-179) | 30 ticks, paused while a state flag holds |
| `+0x0E40` | the attacker after a Blast 2 cinematic (states 298-306, 313-315) | 59 ticks |

The byte array is the shape of SuperCombo's "option anti-repetition system":
options that cannot repeat within a combo, a combo being hits that do not drop
the hit counter.

### Measured

| timer | 30fps | shipped | shipped + `[60FPS - combat timers]` |
|---|---|---|---|
| combo `+0x0D48`, Heavy Finish | 204 | 167 | 198 |
| after hitstun `+0x0FF0`, Heavy Finish | 28 | 14 | 28 |
| repetition byte back to 100 | 198 | 99 | 199 |
| `+0x0DE4`, Ground Slash | 68 | 39 | 69 |
| `+0x0E40`, Frieza's I Might Die This Time rocks from save state 7 | 118 | 59 | 119 |

The combo timer's remaining 6 vsyncs is where the last hit lands: it is
re-armed per hit, and the stun before it is 116 vsyncs at 30fps and 114 at 60fps.

### Delay slots decide the hook shape

- `+0x0D48` and `+0x0E40`: `addiu` then `sw`. A `jal` on the `addiu` would
  store before the helper runs, so the helper stores and the `sw` becomes a
  `nop`.
- `+0x0FF0`: the decrement is in `blez`'s delay slot. The hook is on the next
  instruction, whose helper undoes the `-1` on odd ticks, stores, and replays
  the `dmove`.
- `+0x0DE4`: decrement and store are reached through a `blezl` and a `bnez`,
  both with the work in their delay slots, and every nearby instruction is a
  branch or a call. `001E1FC4`-`001E1FD8` is replayed in a trampoline.
- The repetition loop's helper sets `$ra` past the loop on odd ticks.

### Not established

- **`+0x0FE8` and `+0x0FE4`.** Same countdown shape, armed from hit-reaction
  helpers (`001C9B50`, `001CF220`), and nothing tried here arms them. Guard
  crush and fatigue are candidates; the COM on Stand does not guard.
- **`+0x0D88`**, +1 a tick in states 0x89-0x8C, and **`+0x1580`**, state 4 in one
  game mode, were not investigated.
- **In play.** Whether a combo that drops or connects at 30fps now does the same
  at 60fps was not scripted.

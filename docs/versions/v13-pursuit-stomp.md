# v13 - the pursuit stomp

| | |
|---|---|
| Tag | `v13-pursuit-stomp` |
| Date | 2026-09-07 |
| Built on | [v12](v12-restore-sequence-wait.md) |
| Groups | 18 (213 patch lines) |
| Confidence | **CONFIRMED IN PLAY** 2026-09-08; inherits v12's flag |

## What it changed over v12

Hold Square with Up to launch someone, tap Circle, and Goku teleports above them and
stomps them down. At 30fps it lands every time; at 60fps it never did, and came down
at an awkward diagonal instead. Nine words across two groups, every one doubling a
duration authored in 30Hz frames:

- `[60FPS - knockback flight]`: `FUN_001E9590` counts the launch flight's phase timer
  at `fighter+0x3D8` down from a per-move value in states 213, 214 and 223. Doubled:
  15 -> 30, 50 -> 100 and 32 -> 64 ticks.
- `[60FPS - pursuit timing]`: the rest of the chain - the windup's effect onset 4 -> 8
  and the windup before the teleport 6 -> 12 ticks (`FUN_001F30E0`, state 43); the rise
  (`FUN_001F3668`, states 47 and 48), which adds `(target - pos) * 0.25` once a tick and
  exits at 4, now 0.125 over 8 so the endpoint is identical and only the duration
  doubles; the dive (`FUN_001E7408`, states 146, 155 and 171), whose horizontal speed is
  halved every tick after 20 ticks, now 40; and the intercept lead in `FUN_001DE8A8`,
  doubled inside the solver by one word (`mov.s $f12,$f20` -> `add.s $f12,$f20,$f20`).

## What was discovered

- **Neither side of the collision was at fault.** The victim's flight was already
  correct in real time - (219,-139,100) units a second against 30fps's (218,-139,100),
  its position within 0.15 units 50 vsyncs after impact - and so was the dive. What was
  wrong was five durations in one chain.
- **The lead decided it.** `target = foePos + foeVel * lead`, where the velocity is per
  tick and the lead is in ticks: the raw prediction was (87.5,-55.6,40.0) at 30fps and
  exactly half that at 60. When the dive began, Goku minus victim was (+18.0,-129.1,+8.2)
  at 30fps - ahead - and (-9.7,-119.4,-4.4) at 60 - behind. The dive does not track; it is
  a fixed-velocity plunge that works because the victim runs into it, so starting behind
  is unrecoverable, and chasing is what looked diagonal.
- **Doubled, not gated, on purpose.** A parity gate is the other shape of fix for an
  integer clock, and it is what the withdrawn `state phase timers` did before the state
  157 trap. A doubled countdown still decrements every tick, so it cannot park a fighter
  in a state. `FUN_001E9590` serves only three states, and none of them is 157.
- **Doubling the literal at the call site fixed a third of it.** The lead is built as
  `fVar7 + 4.0 + fVar5` with a per-move `fVar7`, 8.0 for this move, so doubling the 4.0
  moved the target a third of the way. The scale is doubled inside the solver, which
  has exactly one caller.
- **A metric that lied** was recorded, so it is not trusted again.

## Evidence

Swept over nine press delays from 5 to 45 vsyncs: 0 of 9 connected before, 9 of 9
after, within 1-3 vsyncs of the 30fps arm at every delay. Confirmed a second way with
the VM running free and the pad on the wall clock, a different instrument that agrees.
The charge and ultimate oracles are unchanged to the vsync.

## Get this version

    git show v13-pursuit-stomp:releases/v13-pursuit-stomp/428113C2.pnach > 428113C2.pnach

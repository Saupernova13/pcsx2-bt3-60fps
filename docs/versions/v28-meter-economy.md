# v28 - ki, the combat windows, effects and the match clock

| | |
|---|---|
| Tag | `v28-meter-economy` |
| Date | 2026-10-25 |
| Built on | [v27-recovery-windows](v27-recovery-windows.md) |
| Groups | 84 (1277 patch lines) |
| Confidence | **MERGED AT 99%** - the owner merged 44 PRs on 2026-10-25, each at 99% confidence; every changed group ran together in the owner's 2026-10-16 test build |

## What it changed over v27

The biggest version so far: 45 new groups and 2 changed ones, from 42 fix PRs,
plus two docs PRs. Each fix is for something that counted 30fps frames, so at
60fps it ran at double speed or for half its time.

**Ki, Max Power and the smash charge.**

- Ki fills and drains at its real speed, Max Power Mode takes its full charge and
  lasts its full time, and Blast 1 buffs last their published time (#16:
  `meter economy`, `ki charge loop`, `max power charge`).
- Holding Square charges a smash at its real speed. The Perfect Smash release
  window is its full length again, and the Level 3 flash pulses at its real rate
  (#17: `smash charge`, `charge flash`).
- The camera's bob while you charge a smash runs at its real speed (#107:
  `camera bob`).
- The ripple when a fighter hits Max Power Mode grows and fades at PS2 speed
  (#138: `max power shockwave`). The Max Power dash (hold a direction, tap
  Circle) travels its full distance (#163: `vanish dash`).

**Combat timing.**

- The vanish and Z-Counter windows are as long as at 30fps (#65:
  `defence windows`). So is the Auto-Counter stance's Sonic Sway window (#168:
  `sonic sway window`).
- Combos no longer drop, and moves no longer come back twice as soon. The windows
  after hitstun, a Ground Slash and a Blast 2 cinematic last their full time
  (#35: `combat timers`).
- Paralysis (Demon Eye, Psychokinesis, Kaikosen) lasts its full time (#30:
  `paralysis`).
- The freeze when a Z-Counter, a push-stop guard or two colliding smashes land
  lasts as long as on a PS2 (#144: `hit-stop`).
- A knocked-down fighter slides as far as at 30fps and stays down the full 3
  seconds (#70: `knockdown tumble`). Thrown fighters fly as far (#126:
  `throw flight`).
- Fighters blend between poses over their real time, so tapped ki blasts chain
  again (#99: `motion blend`).
- A fighter who loses the lock-on searches for its real time (#136:
  `lock-on search`).

**Blasts and projectiles.**

- Babidi's Demon Eye, and blasts on the same kind of script, reach the opponent
  again (#31: `blast script clock`).
- Ki blasts that miss fly their full range (#59: `projectile life`), and curve at
  their real homing rate, so a sidestep dodges them as on a PS2 (#118:
  `ki blast homing`).
- These all fly at their real speed: Devilman's fork (#61: `weapon object
  travel`), the shots of Super 17's Hell's Storm and Goten's volley (#122:
  `barrage shot rate`), and discs such as Krillin's Destructo Disc (#148:
  `disc travel`).
- A quickly released beam charges and hits as hard as at 30fps, and fires on the
  same frame (#73: `beam charge`).
- Blasts that speed up or grow, such as Explosive Wave, Kaikosen and Android
  Barrier, do so over their real time (#110: `blast ramp clock`).

**Effects.** Each runs at its 30fps speed now:

- hit flashes such as Hercule's Dynamic Mess Em Up Punch (#78: `effect command
  ramp`)
- beam-impact bursts and transformation sparks (#83: `burst effect rate`)
- the wind swirls of a ki charge or a transformation (#95: `swirl effect rate`)
- transformation lightning (#97: `lightning effect rate`)
- the Special Beam Cannon's spiral (#102: `spiral effect rate`)
- the Kamehameha's charge rays (#104: `ray effect rate`)
- speed lines (#105: `sprite effect clock`)
- the arcs over Explosive Wave and the barriers (#112: `arc effect rate`)
- ground dust (#152: `ground dust rate`)
- the power-up glow (#154: `power-up glow rate`)

The second link of a dangling piece, such as Ultimate Gohan's forehead lock,
trails the first as at 30fps (#114 changes `effect rotation`).

**Feedback and the HUD.**

- Screen shake and pad rumble last their full time (#81: `camera shake`,
  `controller rumble`). The shake jitters as often as on a PS2 (#130:
  `camera shake jitter`).
- The health bar drains and shakes for its real time (#85: `health bar drain`,
  `health bar shake`).
- Grunts and shouts repeat no more often than at 30fps (#87: `voice cooldown`).
- Fighters blink at their real rate (#91: `eye blink`).

**The match, menus, story mode and stages.**

- A 60-second Duel lasts 60 seconds (#134: `match timer`).
- A held direction scrolls menus at PS2 speed, both in battle and out (#128
  changes `input repeat timing`).
- Story mode's lines, text, waits and script cameras last their real time (#146:
  `story script clock`).
- Clouds drift at their real speed (#60: `sky scroll`).

The shipped header's "known not fixed" list is corrected (#141). An Ultimate
Blast lands its first hit 2-5 frames early and finishes 6-11 frames early (issue
#127), not half a second early. The camera after a body-erasing KO and the
pre-fight intro now match the PS2, so both come off the list.

**Not in this version.** These are still open, below the 99% bar:

- the cape flutter (#93)
- the CPU's decision rate (#131)
- the ring shot (#150)
- the 30fps tick grid (#170)
- the Rush Struggle rework (#71). `rush struggle` ships as it was in v27.

## What was discovered

- **The game's second is a counter.** Each fighter's meter economy counts 0 to 29
  and fires every once-a-second block when it wraps, so at 60fps "per second"
  came every half second. One gate on that function fixes ki, the gauges, the
  drain and the buffs together, instead of a dozen constants.
- **v27's open `actionFrame` compares are closed.** The vanish dash (13 and 7
  ticks) and the Sonic Sway window (moves 0x67-0x69, 10 ticks) now count to 26,
  14 and 20.
- **The test build was the reference.** v28's exported patch matches the
  owner's 2026-10-16 test build group for group, apart from the five open PRs
  above. No two of its 81 non-widescreen groups write the same address.
- **Three rig traps.** Until 2026-10-12 the rig's `fk` arm ran without the open
  PRs' groups. The EE's FPU has no `c.lt.s` (`0x3C`) form. CPU behaviour has to be
  compared over several start phases. `docs/rig.md` now lists 21 traps.

## Get this version

Download `428113C2.pnach` from the
[v28-meter-economy release](https://github.com/Saupernova13/pcsx2-bt3-60fps/releases/tag/v28-meter-economy),
or:

    git show v28-meter-economy:patch/428113C2.pnach > 428113C2.pnach

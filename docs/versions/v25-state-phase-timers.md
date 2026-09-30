# v25 - the mid-combo freeze

| | |
|---|---|
| Tag | `v25-state-phase-timers` |
| Date | 2026-09-30 |
| Built on | [v24](v24-state-phase-timers.md) |
| Groups | 33 (521 patch lines) |
| Confidence | **FIXED, NOT YET PLAY-TESTED\*** - the freeze was reproduced from the user's own save state and the fix frees it; nobody has played the version |

## What it changed over v24

One group, `[60FPS - state phase timers]`, and nothing else: the released file
goes from 557 patch lines to 521.

**The freeze.** On v24 a fighter could stop dead in the middle of a combo, its
model flashing on and off, until something hit it (issues #39 and #57). The
group gated four sites that are not clocks. They are phase numbers: the number
of the step a state is on. One of them, `001E6060`, is the only way out of an
8-tick loop in states 90-93, so a loop that ended on an odd tick never left.
All four are out of the group.

| | v24 | v25 |
|---|---|---|
| Sites the group gates | 21 | 17 |
| `001E6060` (states 90-93) | gated | the game's own instruction |
| `001F3320` (state 44) | gated | the game's own instruction |
| `001F9D48` (states 301-303, 313-315) | gated | the game's own instruction |
| `001FBBD0` (state 260) | gated | the game's own instruction |

The group writes the game's own instruction back at each of the four sites
rather than leaving them alone, so a save state made while frozen on v24 comes
unstuck when it is loaded on v25.

Measured on the user's EmuDeck save state from the freeze, Super Saiyan Goku in
state 93:

| | what happens |
|---|---|
| v24 | stuck for 517 vsyncs, until the CPU's attack lands |
| v25 | back to idle after 69 ticks, the model drawn on every frame |

## What was discovered

- **A counter is a clock only if the code compares it against a limit.** Of the
  28 per-tick counters in the fighter state machine, 21 are followed by a
  compare (`slti`/`slt`) and count frames. The other 7 are used as a number:
  which step, which table entry. v24 gated four of those 7. The state 157 trap
  of v09 was the same mistake, found one site at a time; this is the rule that
  covers all of them.
- **The freeze came free when the fighter was hit** because a hit forces a new
  state from outside. That is why it looked intermittent in play.

## Known not fixed

Unchanged from v24, less the freeze, plus one item this fix leaves behind:

- **The first step of states 90-93 still runs at double speed.** Its 8-tick
  loop is a clock of its own that nothing compensates, so that step takes 133ms
  instead of 267ms. It is a timing error, not a freeze.
- An ultimate's beam still lands its first hit about half a second early.
- Frieza's rocks and Buu's charged blast still have a ~5-frame pre-launch
  overshoot.
- Some pre-fight intro animations are paced wrong against the camera.
- In a beam clash the CPU ends a little weaker than at 30fps at a middling
  rotation speed.
- Death by a body-erasing attack: the camera has never been re-checked.

## Get this version

Download `428113C2.pnach` from the
[v25 release](https://github.com/Saupernova13/pcsx2-bt3-60fps/releases/tag/v25-state-phase-timers),
or:

    git show v25-state-phase-timers:patch/428113C2.pnach > 428113C2.pnach

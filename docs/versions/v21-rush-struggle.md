# v21 - rush struggle

| | |
|---|---|
| Tag | `v21-rush-struggle` |
| Date | 2026-09-10 |
| Built on | [v20](v20-known-issues-refresh.md) |
| Groups | 26 (291 patch lines) |
| Confidence | **FIXED, NOT YET PLAY-TESTED\*** - inherits v12's flag |

## What it changed over v20

Added `[60FPS - rush struggle]`.

Two rush attacks collide, both fighters enter state 250 (`FUN_001F47C8`) and rotate
their sticks. Hits are counted into `fighter+0xE50` - only `FUN_001E11D0` increments
it - and at `001D945C` the higher count wins. `FUN_001D4370` branches on
**`fighter+0x1278`, the game's own human/AI flag**, and feeds an AI fighter synthetic
input from `+0x127C/+0x1280/+0x1284` instead of the pad, stepping that stick through
cardinal directions once per tick. The fix routes the rotation query at `001F4938`
through a trampoline at `000F1500` that honours it only on even ticks of the state's
own counter, and only for an AI-driven fighter. The player's input is untouched.

## What was discovered

- **The first defect in this project that decides who wins a fight.** A player's
  hands do not speed up with the tick rate; the AI's do.
- **A save state from a newer PCSX2 can be carried to the dev rig as raw memory.**
  The user's install writes savestate format 0x9A55 and PCSXROO reads 0x9A59, but the
  ELF is identical and every pointer absolute, so `transplant.py` writes the source's
  EE RAM and scratchpad over a running battle.
- **The instrument manufactured a defect before it measured the real one.** A pad
  driven on the wall clock caps at about 43 updates a second, which the 60Hz arm
  out-samples and the 30Hz arm cannot. Driving both sticks per vsync from game time
  removed it - and showed the true defect at once.
- **The obvious fix does not work.** Gating every fighter's rotation halves both
  sides and preserves the ratio; the discriminator had to be the AI flag.
- The struggle lasts exactly 88 ticks in every arm, and four candidates for its
  clock were ruled out.
- The 2026-09-09 play-test, recorded at the start of this window: ki blast travel,
  Buu's charged blast and his breath, and the screen fade confirmed as milestones;
  v17 invisible in play for the measured reason; and **transformations and explosive
  waves correct in play - fixed by nothing anyone aimed at them**. Recorded as
  unattributed, because an unattributed fix can regress without anyone knowing why.

## Evidence

Both sticks turned at a true 5 rotations a second: **30fps ends 66-59 to the player,
unpatched 60fps ends 53-47 to the CPU.** Swept across hand speeds:

| rot/s | 30fps | 60fps before | 60fps fixed |
|---|---|---|---|
| 2.0 | CPU 52-39 | CPU 53-33 | CPU 37-33 |
| 3.5 | CPU 57-55 | CPU 53-40 | P1 41-37 |
| 5.0 | P1 66-59 | CPU 53-47 | P1 48-37 |
| 8.0 | P1 82-60 | CPU 59-57 | P1 58-37 |

The winner matches the 30fps game at 2, 5 and 8 rotations a second; 3.5 is a coin
flip in the 30fps game itself and lands on the other side.

## Still wrong in this build

The struggle still runs in 1.63s rather than 2.95s, so the counts read low. It does
not change who wins. v22 found where that clock almost certainly lives: the rush
struggle is dispatched by `FUN_001D9330`, a sibling of the beam clash's manager.

## Get this version

    git show v21-rush-struggle:releases/v21-rush-struggle/428113C2.pnach > 428113C2.pnach

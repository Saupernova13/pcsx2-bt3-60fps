# v26 - transformations and Drain Life

| | |
|---|---|
| Tag | `v26-cinematic-camera` |
| Date | 2026-10-05 |
| Built on | [v25](v25-state-phase-timers.md) |
| Groups | 38 (550 patch lines) |
| Confidence | **CONFIRMED IN PLAY** - the user confirmed Vegeta (Scouter)'s and Cell's transformations and Drain Life on 2026-10-05, in the test build that also carries every other open fix |

## What it changed over v25

Five groups, 29 patch lines. Four fix transformation cinematics, one fixes Drain
Life.

**Transformations.** At 60fps a transformation's camera ran ahead of the
action. Vegeta (Scouter)'s camera cut away before his energy ball went up (#10),
and Cell's transformations showed the wrong shots (#7).

| Group | What ran at double speed | Now |
|---|---|---|
| `cinematic camera` | the camera clip a cinematic plays, stepped 2.0 a tick (`0023D6A4`) | 1.0 a tick |
| `transformation load` | the poll that loads the new form, one stage a tick, so the new form appeared early | polled on even ticks only |
| `effect track clock` | the scripted effects behind Vegeta's energy ball: its clock and four countdowns | runs on even ticks, countdowns step 0.5 |
| `transformation flash` | the white flash that hides the model swap, 11 ticks | held 22 vsyncs, as at 30fps |

| Vegeta (Scouter)'s Great Ape | 30fps | v25 | v26 |
|---|---|---|---|
| energy ball, big flash | v89 | v77 | v88 |
| cut to the Great Ape | v427 | v414 | v425 |
| frames v70-v130, drift from the best-matching 30fps frame | 0 | 8.4-61.2 | 1.0-2.3, one vsync later |

Goten's Super Saiyan reveal starts at v148 at 30fps, v135 on v25 and v145 on v26.

**Drain Life.** `rushing Blast 2 time limit`: a Blast 2 that dashes at the
opponent gives up after a limit in seconds, which the game turned into ticks
with `* 30`. At 60fps it gave up after half its time, so Cell 2nd Form's Drain
Life missed a far opponent and drained nothing (#115, #41). One word makes it
`* 60`.

| Drain Life from | 30fps | v25 | v26 |
|---|---|---|---|
| 510 units | grabs at v130 | grabs at v130 | grabs at v130 |
| 609 units | grabs at v142 | gives up 72 units short | grabs at v141 |
| 780 units | grabs at v160 | gives up 243 units short | grabs at v159 |

## What was discovered

- **The poses were never wrong, the camera was.** The model's animation timer
  reads the same in both arms at every vsync. A transformation looked broken
  because the camera clip ran on its own clock.
- **Loading is faster at 60fps only because it is polled twice as often.** The
  disc time is fixed; the number of polls is not. Polling at 30Hz puts the
  reveal back within 3 vsyncs.
- **On the SuperCombo wiki a "Rush Blast" is a tapped ki blast.** Drain Life is
  a Target Rush Blast 2. The group was renamed before it shipped, so no release
  carries the wrong name.
- v25's fix for the mid-combo freeze is now confirmed in play: no fighter has
  got stuck since.

## Known not fixed

Unchanged from v25, plus what these fixes leave behind:

- A transformation's first camera cut lands 2-3 vsyncs early, and its reveal
  about 3 vsyncs early.
- States 275-277 hold the same `* 30` time limit as Drain Life's. No move
  measured so far enters them, so it is not changed.
- The first step of states 90-93 still runs at double speed (133ms instead of
  267ms).
- An ultimate's beam still lands its first hit about half a second early.
- Frieza's rocks and Buu's charged blast still have a ~5-frame pre-launch
  overshoot.
- Some pre-fight intro animations are paced wrong against the camera.
- In a beam clash the CPU ends a little weaker than at 30fps at a middling
  rotation speed.
- Death by a body-erasing attack: the camera has never been re-checked.

## Get this version

Download `428113C2.pnach` from the
[v26 release](https://github.com/Saupernova13/pcsx2-bt3-60fps/releases/tag/v26-cinematic-camera),
or:

    git show v26-cinematic-camera:patch/428113C2.pnach > 428113C2.pnach

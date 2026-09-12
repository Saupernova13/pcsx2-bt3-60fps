# Releases

**The latest stable patch is [`patch/428113C2.pnach`](../patch/428113C2.pnach).**

That is the file to install, and the file to hand to anyone else. Everything else
in this repository is working material.

    patch/428113C2.pnach                        always the newest stable patch
    releases/v02-airborne-and-hover/...         the same file, kept under its version
    dev/pnach/working.pnach                     the working pnach - NOT for sharing

The filename has to stay `428113C2.pnach`. PCSX2 finds a pnach by the game's CRC
and ignores any other name, so rename the directory, never the file.

## Why not just share `dev/pnach/working.pnach`

The working pnach carries two groups that must never be enabled:

- `60FPS - animation rate` - superseded by `60FPS - animation clock`. Enabling
  both applies two different compensations to the same channel.
- `60FPS - EXPERIMENT halve root motion` - deliberately breaks ground movement.
  It exists to prove which channel carries movement, and nothing else.

They are switched off, but a pnach is presented to the user as a list of
checkboxes, and handing someone a file that punishes ticking every box is a trap.
`tools/export.py` strips both and writes the list of what to enable into the
header of the released file.

## Installing

    python tools/deploy.py patch/428113C2.pnach   # writes the cheat file and
                                                    # the enabled list, then say
                                                    # which groups with --only

Or by hand: drop the file in PCSX2's `cheats/`, set `EnableCheats = true` in
`gamesettings/SLUS-21678_428113C2.ini`, and add one `Enable = <group name>` line
per group listed in the released file's header. PCSX2 reads all of this at boot -
a reset or a save-state load is not enough, quit and relaunch.

## Cutting a new one

    python tools/export.py --release v3-something
    git tag v3-something

`--release` writes the versioned directory and refreshes `patch/`, so they cannot
drift apart. Tag the same commit, so a release directory and a tag always agree.

## History

| version | tag | what it added |
|---|---|---|
| v3 | `v3-blast-hit-cadence` | multi-hit attacks paced by real time: ki blasts land their hits at the right rate and last as long as they should. 14 groups. |
| v2 | `v2-airborne-and-hover` | airborne motion, vertical, residual and gravity; the tween system; aura and trail particles; the hovering idle bob. 13 groups. |
| v1 | `v1-60fps-input-fixed` | the battle loop at 60fps with animation, input timing and the ki aura correct. |

Earlier milestones are tagged `milestone-anim-rate` and `milestone-input-timing`.
The full derivation of every group is in [`docs/findings.md`](../docs/findings.md).

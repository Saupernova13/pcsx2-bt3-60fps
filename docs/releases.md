# Releases

**The latest stable patch is [`patch/428113C2.pnach`](patch/428113C2.pnach).**

That is the file to install, and the file to hand to anyone else. Everything else
in this repository is working material.

    patch/428113C2.pnach                        always the newest stable patch
    git tags v02-... through v22-...            every version, kept under its tag
    wip/working.pnach                           the working pnach - NOT for sharing

The filename has to stay `428113C2.pnach`. PCSX2 finds a pnach by the game's CRC
and ignores any other name, so rename the directory, never the file.

## Why not just share `wip/working.pnach`

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

    python tools/export.py --release v23-something
    git tag v23-something

`--release` refreshes `patch/`; the git tag is the versioned record, so a tag
always agrees with what `patch/` held at that commit.

## History

| version | tag | what it added |
|---|---|---|
| v3 | `v03-blast-hit-cadence` | multi-hit attacks paced by real time: ki blasts land their hits at the right rate and last as long as they should. 14 groups. |
| v2 | `v02-airborne-and-hover` | airborne motion, vertical, residual and gravity; the tween system; aura and trail particles; the hovering idle bob. 13 groups. |
| v1 | `v1-60fps-input-fixed` | the battle loop at 60fps with animation, input timing and the ki aura correct. |

v1 exists only as the `v1-60fps-input-fixed` tag - there is no v1 build to
point at; every version from v2 onward is a tag (`v02-...` through `v22-...`).

Earlier milestones are tagged `milestone-anim-rate` and `milestone-input-timing`.
Every build from v4 onward is catalogued with its confidence in
[`status.md`](status.md) - the per-build detail lives there. The full derivation
of every group is in [`findings.md`](findings.md).

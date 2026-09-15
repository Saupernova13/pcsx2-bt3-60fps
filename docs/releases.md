# Releases

**The latest stable patch is `428113C2.pnach` on the
[latest release](https://github.com/Saupernova13/pcsx2-bt3-60fps/releases/latest)**,
and the same file is [`patch/428113C2.pnach`](../patch/428113C2.pnach) here.

That is the file to install, and the file to hand to anyone else. Everything else
in this repository is working material.

    GitHub Releases                             the newest version, with the patch attached
    patch/428113C2.pnach                        always the newest stable patch
    git tags v01-... through v23-...            every version, kept under its tag
    docs/versions/                              what every version changed and discovered
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

1. Write `docs/versions/v23-something.md`: what this version changes over the last
   one, and what was discovered on the way. Add its row to
   [`versions/README.md`](versions/README.md).
2. Export, commit, and tag:

       python tools/export.py --release v24-something
       git tag -a v24-something -m "v24-something: <one line from the note>"

3. Once that commit is on `main`, push the tag:

       git push origin v24-something

`--release` refuses to run without the note, and refreshes `patch/`. The tag is the
versioned record, so a tag always agrees with what `patch/` held at that commit.

Pushing the tag runs `.github/workflows/release.yml`, which publishes a GitHub
Release named for the tag: `428113C2.pnach` attached as the download, install steps
and the version note as its text. It marks the new release Latest; older versions
stay tags, never downloads, so no one picks up a build the notes say not to use. A
tag without `patch/428113C2.pnach` or its note fails the run instead of publishing.
If a run fails, fix the cause and run the workflow by hand from the Actions tab,
giving it the tag name.

## History

Every version, what it changed and what it discovered, is in
**[`versions/`](versions/README.md)** - one note per version, v01 through v23.

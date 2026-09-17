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

The version is chosen by the merge, not by hand: a PR that changes what ships
becomes one. See [Cutting a new one](#cutting-a-new-one).

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

**A merge that changes the shipped patch is a version, and
`.github/workflows/version.yml` cuts it.** That is the whole rule. It compares
the `patch=` lines export would write against `patch/428113C2.pnach`, so only a
change PCSX2 would execute counts: docs, tooling and comment prose can edit
`wip/working.pnach` as much as they like.

The flow, after any merge to `main`:

1. **A fix PR merges.** The workflow sees the shipped patch no longer matches
   `patch/`, scaffolds `docs/versions/vNN-*.md` from the PR, exports the patch,
   and opens a **release PR** titled with the tag. It does not publish anything.
2. **Edit the note, then merge the release PR.** The scaffold is a DRAFT listing
   which groups changed; rewriting it is the deliberate step. Its merge is what
   records the release.
3. **The merge publishes.** The workflow verifies the note is no longer a DRAFT,
   tags the merged branch's name, and dispatches `release.yml`, which publishes
   the GitHub Release with `428113C2.pnach` attached.

Two things fall out of doing it this way:

- **A version is a snapshot.** The patch is exported when the release PR opens,
  so the note and the file describe the same build. A second fix merging while
  that PR waits is not folded into it; once the release publishes, the workflow
  stages the next version to carry it.
- **Nothing without a version gets in.** If a merge changes what ships while a
  release PR is already open, no second version is staged - one release at a
  time.

Doing it by hand is the same steps, and is how to recover if a run fails:

    python tools/version.py status                    what state the repo is in
    python tools/version.py changed                   which groups differ from patch/
    python tools/version.py prepare --pr "#26"        scaffold the note (edit it)
    python tools/export.py --release v24-something    write patch/; refuses without the note
    git add patch/ docs/versions/ && git commit
    git tag -a v24-something -m "v24-something: <one line from the note>"
    git push origin main v24-something

`--release` refuses to run without the note, and `version.py verify` refuses to
publish one that still says DRAFT, so a version cannot quietly lapse or ship a
scaffold. Push the tag and `.github/workflows/release.yml` publishes the GitHub
Release; if a run fails, fix the cause and run the workflow by hand from the
Actions tab, giving it the tag name.

`version.py` needs `keystone-engine`, `capstone`, `numpy` and `zstandard`
(PCSXROO installs them for its library); the workflow installs them before it
runs.

## History

Every version, what it changed and what it discovered, is in
**[`versions/`](versions/README.md)** - one note per version, v01 through v23.

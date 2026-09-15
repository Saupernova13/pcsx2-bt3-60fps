# v23 - the shipped header caught up with the beam clash

| | |
|---|---|
| Tag | `v23-known-issues-refresh` |
| Date | 2026-09-15 |
| Built on | [v22](v22-beam-clash.md) |
| Groups | 27 (313 patch lines) - identical to v22 |
| Confidence | **DURATION CONFIRMED IN PLAY** 2026-09-12, outcome not yet\* (the patch is v22's); inherits v12's flag |

## What it changed over v22

**No patch change.** Same 27 groups and 313 patch lines as v22; every line of the
file that is not a comment is identical.

What changed is the `KNOWN NOT FIXED` block at the top of the file. It now names
v22's own known gap: in a beam clash with every group enabled the CPU ends a
little weaker than it is at 30fps, so a near-tie the 30fps game gives the CPU can
fall the player's way. The v22 note recorded that; the file people install did
not.

It is also the first version published as a GitHub Release, with the patch
attached as the download.

Cut as its own version rather than retagging v22: a release is a record.

## What was discovered

- **A tag cut before the header is final ships the old header.** The caveat went
  into `tools/export.py` on 2026-09-12, the day v22 was tagged but after the tag,
  so v22's file went out without it and `patch/` has held an untagged file since.
  Write the known gaps into the header, export, then tag.

## Get this version

Download `428113C2.pnach` from the
[v23 release](https://github.com/Saupernova13/pcsx2-bt3-60fps/releases/tag/v23-known-issues-refresh),
or:

    git show v23-known-issues-refresh:patch/428113C2.pnach > 428113C2.pnach

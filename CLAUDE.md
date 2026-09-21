# Working in this repo

## Before you touch the emulator

Read [`docs/rig.md`](docs/rig.md). It is the runbook: how to start the rig, the
exact order an A/B has to run in, how to reach any character and stage by
driving the game's menus, and the traps that silently give a wrong answer
instead of an error. Several of them have each cost an hour or more. Do not
rediscover them.

Then [`docs/status.md`](docs/status.md) for what every group is and whether it is
trusted, and [`docs/findings/`](docs/findings/README.md), split by topic, for the derivation of any of
it.

## Pull requests

**The first line of the body is for a player, not a developer.** Someone who
plays Budokai Tenkaichi 3 and has never read this code should be able to read
that one line and know what changes for them. Write it in plain English, name
the thing they would actually see, and put it before anything else.

> This PR fixes background props like the blimp and the helicopter in the World
> Tournament stage animating at double speed.

Not "gates FUN_001C69C8's per-tick accumulator". That belongs further down, and
there should be plenty of it - the rest of the body stays as technical as the
change deserves.

**Run `/trim-pr-body` on the PR after opening it.**

Everything else follows the global conventions: conventional commit subjects,
one topic per branch, never commit to `main`, and merging is the repo owner's
call - open the PR and say it is ready.

## Shipping

A group is not shipped because it measures correct. It ships when it has been
**confirmed in play**, and `docs/status.md` records which is which - a starred
build is measured but unplayed. Do not cut a release for a group that has only
been measured; say it is ready for a play test and let the owner decide.

**A merge that changes the shipped patch becomes a version.** The owner's rule:
merges to `main` only happen once something has been played, so the merge is the
play-test gate. `.github/workflows/version.yml` enforces the rest - it compares
the exported `patch=` lines against `patch/428113C2.pnach` and, when they differ,
scaffolds a DRAFT `docs/versions/vNN-*.md` and opens a release PR. Edit the note
and merge that PR; its merge tags the version and publishes the Release. Docs,
tooling and comment-only edits to `wip/working.pnach` owe no version.

Do not tag a version by hand, and do not merge a release PR whose note is still
a DRAFT. `tools/version.py` is the reference for all of it;
[`docs/releases.md`](docs/releases.md) has the prose.

`patch/428113C2.pnach` is the released file and only `tools/export.py --release`
writes it (the release workflow calls it). Never deploy `wip/working.pnach` to a
real install: it carries groups that must never be enabled.

## Names

The owner often calls a mechanic by what it looks like ("Frieza's rock attack",
"the stomp", "buffs"). [`docs/names.md`](docs/names.md) maps those names to the
real ones and to the group that fixes each. When the owner uses a name that is
not in the table, work out what it is and add a row.

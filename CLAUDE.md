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

## Working an issue

The owner decides; you do everything else.

1. **Reproduce and measure it yourself, in the rig.** PCSXROO gives you both
   pads, breakpoints, pause, frame advance and screenshots, and
   `tools/transplant.py` loads the owner's own EmuDeck saves. Never ask the
   owner to try something, and never offer it as a next step.
2. **Comment on the issue as you go**: what you found, and how confident you
   are that it is the cause.
3. **Open a PR when you are confident the problem is fixed**, ending in
   `Closes #N`, with its confidence score (see Pull requests below).
4. **The owner play-tests the PR.** If it is solid they merge it; if not they
   hand it back, and you pick it up again from their comment.

**Never close an issue and never merge a PR - any PR, docs and tooling
included.** Both are the owner's. If an issue needs no change, say so on the
issue with the evidence and leave it open.

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

**Every PR carries a confidence score.** The second line of the body, right
after the player line, is `**Confidence: NN%**` - how sure you are that the PR
fixes the issue and breaks nothing else - followed by one short line on what
still keeps it from 100%. **The owner only play-tests a PR at 99% or more.**

| Score | Means |
|---|---|
| 99% | the mechanism is read in the BT3-Decompiled C, the issue's own case measures equal to 30fps in the rig, and the full test build shows no side effect; only a play test is left |
| 95-98% | measured equal to 30fps, but one of those three is missing or a small residual remains |
| below 95% | a known gap, a partial fix, or a mechanism not understood |

Below 99%, keep working the PR. Each time the score changes, post a comment on
the PR with the new score, what moved it and what still holds it below 99%,
and update the body's line to match. When it reaches 99%, the comment says it
is ready for a play test. `/trim-pr-body` keeps the confidence line.

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

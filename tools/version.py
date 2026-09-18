"""Version the patch: decide when a release is due, and scaffold its note.

A release is a version, and a version is owed whenever **what ships** changes.
The test is the state of `patch/428113C2.pnach` itself: it always holds the last
exported release, so if the shipped `patch=` lines in `wip/working.pnach` no
longer match it, a release is pending. Comment prose, docs and tooling do not
count - only the lines PCSX2 executes.

    python tools/version.py status                  what state the repo is in
    python tools/version.py pending                 exit 0 if a release is owed
    python tools/version.py changed                 which shipped groups differ
    python tools/version.py prepare --pr "#26"      scaffold the version note
    python tools/version.py verify                  refuse to publish a DRAFT
    python tools/version.py publish-tag             the note that is ready to tag
    python tools/version.py phase --head-ref REF    stage, publish, or nothing
                                                    (as phase= and tag= lines)

`prepare` writes docs/versions/<tag>.md and appends its row to the version
history; it does not export. Write the note, then run
`python tools/export.py --release <tag>`, which refuses to run without it.

`.github/workflows/version.yml` drives all of this on a merge to `main`; the
commands are here so the same steps can be run and checked by hand.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import re
import subprocess
from pathlib import Path

import _bootstrap  # noqa: F401
import export

from game import config

REPO = Path(__file__).resolve().parent.parent
VERSIONS = REPO / "docs" / "versions"
WORKING_PATH = "wip/working.pnach"        # as git spells it, on any platform
WORKING = REPO / WORKING_PATH
RELEASED = REPO / "patch" / f"{config.CRC}.pnach"
SLUG_RE = re.compile(r"[^a-z0-9]+")
NUMBER_RE = re.compile(r"^v(\d+)")


def git(*args: str) -> str:
    return subprocess.run(("git", *args), cwd=REPO, check=True,
                          capture_output=True, text=True).stdout


def shipped(text: str, development_only: list[str]) -> dict[str, list[str]]:
    """The groups a release would carry, each as its stripped ``patch=`` lines.

    Development-only groups are dropped, exactly as export drops them, so a
    group that must never ship can be edited without owing a version.
    """
    _, blocks = export.split_groups(text)
    return {
        name: [l.strip() for l in body if l.strip().startswith("patch=")]
        for name, body in blocks if name not in development_only
    }


def current() -> dict[str, list[str]]:
    return shipped(WORKING.read_text(encoding="utf-8"), export.DEVELOPMENT_ONLY)


def last_release() -> dict[str, list[str]]:
    if not RELEASED.is_file():
        return {}
    # The released file was filtered when it was written, so nothing is dropped here.
    return shipped(RELEASED.read_text(encoding="utf-8"), [])


def diff() -> tuple[list[str], list[str], list[str]]:
    """(added, removed, modified) shipped groups, last release against the tree."""
    before, after = last_release(), current()
    added = [n for n in after if n not in before]
    removed = [n for n in before if n not in after]
    modified = [n for n in after if n in before and after[n] != before[n]]
    return added, removed, modified


def pending() -> bool:
    return bool(any(diff()))


def note_number(path: Path) -> int | None:
    found = NUMBER_RE.match(path.name)
    return int(found.group(1)) if found else None


def notes() -> list[tuple[int, str, Path]]:
    """Every version note as (number, tag, path), tag being the file's stem."""
    out = []
    for path in VERSIONS.glob("v*.md"):
        number = note_number(path)
        if number is not None:
            out.append((number, path.stem, path))
    return sorted(out)


def tagged() -> set[str]:
    return set(git("tag", "-l", "v*").splitlines())


def next_tag() -> str:
    """The next number, from git tags alone.

    Tags are the published record. A draft note that is not tagged yet must not
    bump the number, or a re-run would quietly skip a version.
    """
    highest = 0
    for line in tagged():
        found = NUMBER_RE.match(line)
        if found:
            highest = max(highest, int(found.group(1)))
    return f"v{highest + 1:02d}"


def latest_tag() -> str | None:
    """The newest published tag, by number then name, so v06b beats v06."""
    best: tuple[int, str] | None = None
    for line in tagged():
        found = NUMBER_RE.match(line)
        if found:
            key = (int(found.group(1)), line)
            if best is None or key > best:
                best = key
    return best[1] if best else None


def shipping_commits() -> list[str]:
    """The commits that changed the working pnach since the last published tag.

    The scaffold used to be seeded from one PR - whichever merge tripped the
    check - and that PR is often not the one that owes the version: a run that
    failed, or a release PR waiting, leaves several patch merges to be carried
    by the next version. Listing them all is what stops the note describing the
    wrong change.
    """
    since = latest_tag()
    span = f"{since}..HEAD" if since else "HEAD"
    try:
        log = git("log", "--no-merges", "--format=%s (%h)", span, "--", WORKING_PATH)
    except subprocess.CalledProcessError:
        return []
    return [line for line in log.splitlines() if line.strip()]


def untagged() -> tuple[int, str, Path] | None:
    """The newest version note with no matching git tag, if there is one."""
    tags = tagged()
    for number, tag, path in reversed(notes()):
        if tag not in tags:
            return number, tag, path
    return None


def read_tag(path: Path) -> str:
    """The tag a note declares in its table, falling back to its filename."""
    found = re.search(r"\|\s*Tag\s*\|\s*`([^`]+)`", path.read_text(encoding="utf-8"))
    return found.group(1) if found else path.stem


def slug(name: str) -> str:
    trimmed = re.sub(r"^60FPS\s*-\s*", "", name, flags=re.IGNORECASE)
    return SLUG_RE.sub("-", trimmed.lower()).strip("-")


def previous_note(number: int) -> tuple[str, str] | None:
    """(tag, filename) of the newest note below ``number``."""
    for n, tag, path in reversed(notes()):
        if n < number:
            return read_tag(path), path.name
    return None


def summary_line(body: str) -> str:
    """One plain-English line for the version history table."""
    for line in body.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith(("#", "|", ">", "-", "*", "```")):
            return stripped
    return "see the version note"


def write_note(tag: str, changed: list[str], body: str, pr: str, url: str) -> Path:
    number = int(NUMBER_RE.match(tag).group(1))
    prev = previous_note(number)
    built_on = f"[{prev[0]}]({prev[1]})" if prev else "(first version)"
    listed = "\n".join(f"- `{g}`" for g in changed) or "- (no shipped group changed)"
    since = latest_tag()
    carried = "\n".join(f"- {line}" for line in shipping_commits())
    carried_from = f" since {since}" if since else ""
    text = f"""# {tag} - DRAFT

| | |
|---|---|
| Tag | `{tag}` |
| Date | {_dt.date.today().isoformat()} |
| Built on | {built_on} |
| Groups | {len(changed)} shipped group(s) changed |
| Confidence | **DRAFT - fill this in** |

> **DRAFT.** Every other note on this page is written for a player: what this
> version changes over the last one, and what was discovered on the way. Rewrite
> this before the release PR merges - its merge is what publishes the release.

## What it changed

Shipped groups this version carries that the last release did not:

{listed}

The commits to `wip/working.pnach` it carries{carried_from}:

{carried or '- (none found in the log)'}

## What was discovered

{body.strip() or '(fill this in)'}

> Seeded from one merge's body, which may describe only one of the changes
> listed above: {pr or 'the merge that owed this version'}.

## Get this version

Download `428113C2.pnach` from the
[{tag} release](https://github.com/Saupernova13/pcsx2-bt3-60fps/releases/tag/{tag}),
or:

    git show {tag}:patch/428113C2.pnach > 428113C2.pnach
"""
    path = VERSIONS / f"{tag}.md"
    path.write_text(text, encoding="utf-8", newline="\n")
    return path


def add_history_row(tag: str, path: Path, groups: int, what: str) -> None:
    readme = VERSIONS / "README.md"
    lines = readme.read_text(encoding="utf-8").splitlines()
    label = tag.split("-")[0]
    row = (f"| [`{label}`]({path.name}) | {_dt.date.today().isoformat()} | {groups} "
           f"| {what} | **DRAFT - not played** |")
    rows = [i for i, l in enumerate(lines) if l.startswith("| [`v")]
    if rows:
        at = max(rows) + 1
    else:
        # Before the first version there are no rows, so the new one goes
        # directly under the table's separator.
        rules = [i for i, l in enumerate(lines) if l.startswith("|---")]
        if not rules:
            raise SystemExit(f"{readme} has no version table to add a row to")
        at = rules[0] + 1
    lines.insert(at, row)
    readme.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def phase(head_ref: str, open_release: bool = False) -> tuple[str, str]:
    """What this merge should do, and the tag to publish: ``(phase, tag)``.

    Decided from the merged PR's head branch, which is unambiguous - the release
    PR this tool opens is always ``release/<tag>``.

    - a ``release/`` branch just merged means its note is final and needs
      publishing; the tag is the branch name, so it never has to be guessed
    - otherwise, a release already waiting (an open ``release/`` PR, or a note
      with no tag) means a human still has to edit it, so a second patch merge
      must not stage a competing version
    - otherwise, a change to what ships owes a new version

    An empty ``head_ref`` is a manual run, which is the recovery path for a run
    that failed halfway: publish the newest finished note, else stage. Nothing
    else can recover a version whose note reached ``main`` with no tag - the
    ``patch=`` test is satisfied by then, so no later merge will notice it.

    The tag is only returned for ``publish``; ``stage`` names its own.
    """
    if head_ref.startswith("release/"):
        tag = head_ref[len("release/"):]
        # A finished run that is re-run replays the same merge event. The tag it
        # pushed is the record that the version is already out, so the second
        # pass is a no-op rather than a failure on `git tag`.
        if tag in tagged():
            return "nothing", tag
        return ("publish", tag) if verify(tag) == 0 else ("nothing", tag)
    if not head_ref:
        found = untagged()
        if found and verify(found[1]) == 0:
            return "publish", found[1]
        return ("stage" if pending() else "nothing"), ""
    waiting = untagged()
    if waiting:
        # Said out loud because this is the one state nothing recovers on its
        # own: a note that reached main with no tag leaves patch/ matching the
        # tree, so no later merge sees a version owed, and every run after it is
        # a quiet "nothing". Finish the note and run this workflow by hand.
        print(f"{waiting[1]} is staged and not published; nothing else is staged "
              "while it waits")
        return "nothing", ""
    if open_release:
        return "nothing", ""
    return ("stage" if pending() else "nothing"), ""


def out(pairs: dict[str, str], github_output: str | None) -> None:
    for key, value in pairs.items():
        print(f"{key}={value}")
    if github_output:
        with open(github_output, "a", encoding="utf-8") as fh:
            for key, value in pairs.items():
                fh.write(f"{key}={value}\n")


def verify(tag: str) -> int:
    """Refuse to publish a note still carrying its scaffold.

    The scaffold is written before a human rewrites it, so this is what stops a
    DRAFT from becoming the release notes people read.
    """
    path = VERSIONS / f"{tag}.md"
    if not path.is_file():
        print(f"no note at {path.relative_to(REPO)}")
        return 1
    text = path.read_text(encoding="utf-8")
    problems = []
    if "DRAFT" in text:
        problems.append("it still says DRAFT - rewrite it for a player before merging")
    if "(fill this in)" in text:
        problems.append("the 'What was discovered' section is empty")
    if f"`{tag}`" not in text:
        problems.append(f"its table does not declare the tag `{tag}`")
    for problem in problems:
        print(f"{path.relative_to(REPO)}: {problem}")
    return 1 if problems else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("status", "pending", "changed", "prepare", "publish-tag",
                 "verify", "phase"):
        cmd = sub.add_parser(name)
        cmd.add_argument("--github-output", default=None)
        if name == "prepare":
            cmd.add_argument("--tag", default=None,
                             help="override the generated tag (also names the note)")
            cmd.add_argument("--pr", default="", help="e.g. #26, for the note")
            cmd.add_argument("--pr-url", default="")
            cmd.add_argument("--pr-title", default="")
            cmd.add_argument("--pr-body", default=None, help="file holding the PR body")
            cmd.add_argument("--skip-history", action="store_true")
        if name in ("verify", "publish-tag"):
            cmd.add_argument("--tag", default=None)
        if name == "phase":
            cmd.add_argument("--head-ref", default="",
                             help="merged PR's head branch; empty for a manual run")
            cmd.add_argument("--open-release", action="store_true",
                             help="a release/ PR is open, so one is already waiting")
    args = parser.parse_args()

    if args.command == "phase":
        name, tag = phase(args.head_ref, open_release=args.open_release)
        found = untagged()
        out({"phase": name, "tag": tag,
             "waiting": found[1] if found else ""}, args.github_output)
        return 0

    added, removed, modified = diff()
    changed = sorted(set(added + modified) | set(removed))

    if args.command == "pending":
        print("pending" if changed else "up-to-date")
        return 0

    if args.command == "changed":
        for label, names in (("added", added), ("removed", removed),
                             ("modified", modified)):
            for name in names:
                print(f"{label:9} {name}")
        return 0

    if args.command == "status":
        pending_note = untagged()
        out({
            "pending": "true" if changed else "false",
            "changed": ", ".join(changed),
            "next_tag": next_tag(),
            "untagged_note": pending_note[1] if pending_note else "",
            "released_groups": str(len(last_release())),
            "current_groups": str(len(current())),
        }, args.github_output)
        return 0

    if args.command == "publish-tag":
        found = untagged()
        if found is None:
            print("nothing to publish")
            out({"tag": ""}, args.github_output)
            return 0
        _, tag, _ = found
        if verify(tag):
            print("refusing to publish a scaffolded note")
            out({"tag": ""}, args.github_output)
            return 1
        print(f"publish {tag}")
        out({"tag": tag}, args.github_output)
        return 0

    if args.command == "verify":
        tag = args.tag
        if not tag:
            found = untagged()
            if not found:
                print("no untagged note to verify")
                return 0
            tag = found[1]
        return verify(tag)

    # prepare
    if not changed:
        print("nothing that ships has changed; no version owed")
        out({"changed": "false", "tag": "", "branch": ""}, args.github_output)
        return 0
    tag = args.tag or f"{next_tag()}-{slug(added[0] if added else changed[0])}"
    body = Path(args.pr_body).read_text(encoding="utf-8") if args.pr_body else ""
    if args.pr_title:
        body = f"{args.pr_title}\n\n{body}".strip()
    note = VERSIONS / f"{tag}.md"
    if note.exists():
        print(f"{note.relative_to(REPO)} already exists; leaving it alone")
        print(f"next:  python tools/export.py --release {tag}")
        out({"changed": "true", "tag": tag, "branch": f"release/{tag}"}, args.github_output)
        return 0
    note = write_note(tag, changed, body, args.pr, args.pr_url)
    if not args.skip_history:
        add_history_row(tag, note, len(current()), summary_line(body))
    print(f"wrote {note.relative_to(REPO)}")
    print(f"next:  python tools/export.py --release {tag}")
    out({"changed": "true", "tag": tag, "branch": f"release/{tag}"}, args.github_output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

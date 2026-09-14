"""Write a shareable copy of the patch, with the development-only groups removed.

The repo pnach is a working document: it carries an experiment that deliberately
breaks ground movement and a superseded alternative to the animation clock, both
switched off. Anyone handed that file sees a list of checkboxes with no way to
know which ones are the fix, and ticking them all breaks the game. This writes
out only the groups that are part of the fix, keeps each one's explanatory
comment with it, and puts the list of what to enable at the top.

The name matters: PCSX2 finds a pnach by the game's CRC, so the file has to be
called 428113C2.pnach wherever it ends up.

    python tools/export.py --release v23-something
    python tools/export.py --to build/

With --release it refreshes patch/ at the repo top level, which is always the
newest stable patch and the file to install. Named 428113C2.pnach, because
PCSX2 finds a pnach by CRC and will ignore any other name. The version history
is the git tags: tag the commit to match the release name, so a tag and what
patch/ held at that commit always agree.

Every release also carries a version note, docs/versions/NAME.md, saying what
the version changes over the one before it and what was discovered on the way.
--release refuses to run without it, so the history cannot quietly lapse.
"""

from __future__ import annotations

import argparse
import os
import re
from pathlib import Path

import _bootstrap  # noqa: F401
import patchctl

from game import config
from ps2ee.pnach import Pnach

# Present in the repo pnach, never in a shared copy. One list, in config, because
# deploy.py has to refuse the same names.
DEVELOPMENT_ONLY = config.NEVER_SHIP

# Stated plainly at the top of the shared file rather than left to be discovered.
KNOWN_BROKEN: list[str] = [
    "an ultimate's beam lands its first hit about half a second early. The "
    "cinematic up to the launch is now correct to within two vsyncs; what is "
    "left is the flight, and it is neither an integer tick counter nor a "
    "per-tick float step - every one of those in the game has been gated or "
    "halved and none of them moves it",
    "Frieza's summoned rocks now travel at the right speed, but the summon "
    "animation before the launch - which is most of that move - still runs "
    "about five frames fast. The same short pre-launch overshoot is on Buu's "
    "charged blast",
    "some pre-fight intro animations are paced wrong against the camera. The "
    "mouths in that scene are fixed; this is the other half of the same report",
    "in a beam clash the CPU ends a little weaker than it is at 30fps when both "
    "sides rotate at a middling speed. The clash's pacing and the player's own "
    "count are exact, but the beams now travelling at their correct speed change "
    "where the clash forms and the AI reacts to that, so a near-tie the 30fps "
    "game gives the CPU can fall the player's way",
    "death by a body-erasing attack: the camera around the victim was reported "
    "too fast and cutting oddly, and has never been re-checked since the camera "
    "work landed. It may have gone with the other camera fixes, or it may not",
]


def split_groups(text: str) -> tuple[list[str], list[tuple[str, list[str]]]]:
    """Slice into a file header and (name, lines) blocks.

    Everything since the previous group ends belongs to the group whose header
    comes next, so a group's explanatory comment travels with it.
    """
    header: list[str] = []
    blocks: list[tuple[str, list[str]]] = []
    buf: list[str] = []
    name: str | None = None
    for line in text.splitlines():
        found = re.match(r"^\[(.+)\]\s*$", line)
        if found:
            if name is None:
                cut = max((i for i, l in enumerate(buf) if not l.strip()),
                          default=len(buf))
                header, buf = buf[:cut], buf[cut:]
            else:
                blocks.append((name, buf))
                buf = []
            name = found.group(1)
        buf.append(line)
    if name is not None:
        blocks.append((name, buf))
    return header, blocks


def banner(names: list[str]) -> list[str]:
    rule = "// " + "-" * 69
    out = [rule,
           "// Every group in this file is part of the fix and all of them should be",
           "// enabled together. Groups are enabled per-cheat in PCSX2 2.x, under",
           "//   gamesettings/SLUS-21678_428113C2.ini   [Cheats]  Enable = <name>",
           "// or by ticking them in Settings -> Cheats. EnableCheats must be true.",
           "//"]
    out += [f"//   {n}" for n in names]
    if KNOWN_BROKEN:
        out += ["//", "// KNOWN NOT FIXED:"]
        out += [f"//   {n}" for n in KNOWN_BROKEN]
    out += ["//",
            "// Everything above is verified against the unpatched 30fps game as its",
            "// own oracle: same save state, same input, same number of vsyncs.",
            rule, ""]
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source", default="wip/working.pnach")
    parser.add_argument("--to", default=None,
                        help="directory to write into (default: the desktop)")
    parser.add_argument("--release", default=None, metavar="NAME",
                        help="refresh patch/; NAME is the git tag for the record")
    args = parser.parse_args()

    if args.release:
        note = Path(__file__).resolve().parent.parent / "docs" / "versions" / f"{args.release}.md"
        if not note.exists():
            raise SystemExit(
                f"no version note for {args.release}: write docs/versions/{args.release}.md "
                "first - what this version changes over the last one, and what was "
                "discovered. Every release carries one; see docs/releases.md.")

    source = Path(args.source)
    header, blocks = split_groups(source.read_text(encoding="utf-8"))
    kept = [(n, b) for n, b in blocks if n not in DEVELOPMENT_ONLY]
    dropped = [n for n, _ in blocks if n in DEVELOPMENT_ONLY]

    missing = [n for n in patchctl.PRESETS["full"] if n not in {k for k, _ in kept}]
    if missing:
        raise SystemExit("the shipping preset names groups this pnach lacks: "
                         + ", ".join(missing))

    lines = header + banner([n for n, _ in kept])
    for _, body in kept:
        lines += body
    text = "\n".join(lines).rstrip() + "\n"

    if args.release:
        repo = Path(__file__).resolve().parent.parent
        targets = [repo / "patch"]
    elif args.to:
        targets = [Path(args.to)]
    else:
        targets = [Path(os.path.expanduser("~")) / "Desktop"]

    for out_dir in targets:
        out_dir.mkdir(parents=True, exist_ok=True)
        dest = out_dir / f"{config.CRC}.pnach"
        dest.write_text(text, encoding="utf-8", newline="\r\n")
        problems = Pnach.load(dest).validate()
        if problems:
            raise SystemExit("the exported pnach did not validate:\n  "
                             + "\n  ".join(problems))
        written = Pnach.load(dest)
        print(f"{dest}")
        print(f"  {len(written.groups)} groups, "
              f"{sum(len(g.lines) for g in written.groups)} patch lines, validated")
    for name in dropped:
        print(f"  dropped (development only)  {name}")
    if args.release:
        print(f"tag this commit:  git tag -a {args.release} -m \"{args.release}: <one line from its note>\"")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Write a shareable copy of the patch, with the development-only groups removed.

The repo pnach is a working document: it carries an experiment that deliberately
breaks ground movement and a superseded alternative to the animation clock, both
switched off. Anyone handed that file sees a list of checkboxes with no way to
know which ones are the fix, and ticking them all breaks the game. This writes
out only the groups that are part of the fix, keeps each one's explanatory
comment with it, and puts the list of what to enable at the top.

The name matters: PCSX2 finds a pnach by the game's CRC, so the file has to be
called 428113C2.pnach wherever it ends up.

    python tools/export.py --release v2-airborne-and-hover
    python tools/export.py --to build/

With --release it writes two copies: releases/<name>/ for the record, and
releases/latest/ which is always the newest stable patch. Both are named
428113C2.pnach, because PCSX2 finds a pnach by CRC and will ignore any other
name. Tag the commit to match, so a release directory and a tag always agree.
"""

from __future__ import annotations

import argparse
import os
import re
from pathlib import Path

import _bootstrap  # noqa: F401
import patchctl

from ps2ee import config
from ps2ee.pnach import Pnach

# Present in the repo pnach, never in a shared copy.
DEVELOPMENT_ONLY = ["60FPS - animation rate", "60FPS - EXPERIMENT halve root motion"]

# Stated plainly at the top of the shared file rather than left to be discovered.
KNOWN_BROKEN: list[str] = []


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
    parser.add_argument("--source", default="patches/428113C2.pnach")
    parser.add_argument("--to", default=None,
                        help="directory to write into (default: the desktop)")
    parser.add_argument("--release", default=None, metavar="NAME",
                        help="write releases/NAME/ and refresh releases/latest/")
    args = parser.parse_args()

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
        root = Path(__file__).resolve().parent.parent / "releases"
        targets = [root / args.release, root / "latest"]
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

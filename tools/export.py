"""Write a shareable copy of the patch, with the development-only groups removed.

The repo pnach is a working document: it carries groups that break the game,
switched off. This writes out only the groups that are part of the fix, keeps
each one's description with it, and puts the list of what to enable at the top.
The file must be named 428113C2.pnach (PCSX2 finds a pnach by CRC).

Layout rule: a group's description is the comment block directly above its
header with no blank line between; a blank line separates groups. A description
not touching its header is carried with the wrong group.

    python tools/export.py --release v23-something
    python tools/export.py --to build/

--release refreshes patch/, the newest stable patch and the file to install; tag
the commit to match the release name. It refuses to run without a version note,
docs/versions/NAME.md.
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

# Stated plainly at the top of the shared file.
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

    A group's description is the comment run directly above its header and travels
    with it; everything before that run stays with the group above.
    """
    header: list[str] = []
    blocks: list[tuple[str, list[str]]] = []
    buf: list[str] = []
    name: str | None = None
    for line in text.splitlines():
        found = re.match(r"^\[(.+)\]\s*$", line)
        if found:
            cut = len(buf)
            while cut and buf[cut - 1].lstrip().startswith("//"):
                cut -= 1
            above, buf = buf[:cut], buf[cut:]
            if name is None:
                header = above
            else:
                blocks.append((name, above))
            name = found.group(1)
        buf.append(line)
    if name is not None:
        blocks.append((name, buf))
    return header, blocks


# Not ours: PCSX2's patch database ships the stock widescreen hack, which every
# aspect group says to turn off.
EXTERNAL_GROUPS = {"Widescreen 16:9"}


def stray_names(blocks: list[tuple[str, list[str]]]) -> list[str]:
    """Groups named in a kept group's description that the output does not have, usually
    a description that came loose from its group.
    """
    shipped = {name for name, _ in blocks} | EXTERNAL_GROUPS
    problems = []
    for name, body in blocks:
        for line in body:
            if not line.lstrip().startswith("//"):
                break
            for mentioned in re.findall(r"\[((?:60FPS - |Widescreen )[^\]]+)\]", line):
                if mentioned not in shipped:
                    problems.append(f"[{name}] is described as [{mentioned}], "
                                    "which is not in the file")
    return problems


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

    stray = stray_names(kept)
    if stray:
        raise SystemExit("a shipped group's description names a group the file does not "
                         "contain:\n  " + "\n  ".join(stray))

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
        # LF, as the attributes file stores every pnach (CRLF made patch/ look modified on Windows).
        dest.write_text(text, encoding="utf-8", newline="\n")
        problems = Pnach.load(dest).validate(exclusive=config.EXCLUSIVE)
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
        print(f"then, on main:    git push origin {args.release}   (publishes the GitHub Release)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Split docs/findings.md into topic files under docs/findings/, losing nothing.

Every `## ` section of the log is assigned to exactly one topic by its heading.
Sections keep their original order inside each topic, and the lines before the
first section become the index's introduction. A heading that matches no topic,
or more than one, stops the run, so a new section can never be dropped silently.

Fix PRs still append to docs/findings.md. After merging them, restore the file
from git, add a rule for any new heading below, and run this again:

    python tools/split_findings.py            # writes docs/findings/*.md
    python tools/split_findings.py --check    # verifies, writes nothing
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "docs" / "findings.md"
OUT = ROOT / "docs" / "findings"

# The log lives in docs/ and every file it is split into lives in docs/findings/,
# one level deeper, so a relative link written for the log points one directory
# short once it is moved. Rewrite those; leave absolute URLs, anchors, and links
# that already climb out alone, so a re-run cannot double-prefix them.
RELATIVE_LINK = re.compile(r"\]\((?!https?:|mailto:|#|\.\./)([^)\s]+?)\.md(#[^)]*)?\)")
RELATIVE_LINK_ANY = re.compile(r"\]\((?!https?:|mailto:|#)([^)\s]+?\.md)(#[^)]*)?\)")


def repath(line: str) -> str:
    return RELATIVE_LINK.sub(r"](../\1.md\2)", line)

# (file, title, scope, heading patterns). First match wins is NOT used: a
# heading must match exactly one topic.
TOPICS = [
    ("state-of-play.md", "State of play and the user's reports",
     "The running summary, the user's defect lists and every play-test.",
     [r"^STATE OF PLAY", r"user's full defect list", r"status from the user",
      r"the play-test: three milestones", r"play-test of v9"]),
    ("engine.md", "The engine, the frame routine and the first 60fps patch",
     "How BT3 runs a frame, where 60fps comes from, and the early probes.",
     [r"^Environment$", r"^Memory layout$", r"^The pre-existing 60fps code$",
      r"^The frame routine", r"^Open questions$", r"^Radar baseline$", r"^Test 1 - Probe 2",
      r"^Live PINE session", r"working 60fps battle patch", r"was never actually applied",
      r"has no timestep", r"animation system, fully mapped", r"^Bounding the motion search$"]),
    ("tooling-and-method.md", "Tooling, the rig and the measurement method",
     "Instruments, the 30fps oracle, and how a shipped group is A/B'd.",
     [r"^Instrument notes", r"A/B-ing a shipped", r"PCSXROO: the emulator became scriptable",
      r"the 30fps oracle, mechanised", r"EmuDeck install was running"]),
    ("input.md", "Input timing", "The input subsystem and the combat input counters.",
     [r"^Input subsystem map", r"combat input timing is 128 frame counters"]),
    ("airborne-and-hover.md", "Airborne motion, gravity and the hovering idle",
     "Flight, gravity, the airborne idle animation and the hover bob.",
     [r"remaining 2x is AIRBORNE", r"^Airborne motion - the full investigation", r"^Airborne 2x",
      r"airborne motion, solved", r"gravity, the fourth airborne channel", r"airborne idle",
      r"hovering idle"]),
    ("effects-aura-particles.md", "Effects, the ki aura and particles",
     "The effect-node system, the aura, effect rotation and the particle system.",
     [r"^Effects at 2x", r"^The effect system", r"ki aura", r"FUN_0012CB60 is gated",
      r"aura is advanced TWICE", r"effect rotation was not wrong", r"the particle system"]),
    ("tweens-fades-and-staging.md", "Tweens, fades and staged sequences",
     "The tween service, the scripted-sequence clocks and the screen fade service.",
     [r"the tween system", r"two clocks behind everything the game stages", r"Galick Cannon fade"]),
    ("blasts.md", "Blasts: hit cadence, effects, sequences and Flame Shower Breath",
     "Blast 2 and Ultimate Blast timing: hit cadence, effect duration, the sequence clock.",
     [r"ki blasts are cut short", r"ki blasts, reproduced", r"ki blasts solved", r"measured right and looked like nothing",
      r"the blast sequence, found by bisecting", r"gating an effect update deletes the beam",
      r"is a different code path, and SEQ kills it", r"what is left, and what has been ruled out on it",
      r"the blasts keep their real timing", r"WITHDRAWN: blast flash duration", r"Flame Shower Breath",
      r"issue #29, Demon Eye"]),
    ("state-machine.md", "The fighter state machine and the stuck loop",
     "Phase timers inside fighter states, and the state 157 trap.",
     [r"the stuck loop", r"ten user reports, and the state 157 trap"]),
    ("projectile-travel.md", "Projectile, rock and beam travel",
     "The three movers: effect-node projectiles, spawned objects and travelling beams.",
     [r"projectile travel: found", r"also exactly 2x, and a SECOND mover", r"Final Form Frieza: rocks",
      r"^The second mover", r"^The third mover", r"issue #5, Hercule's ki blast"]),
    ("smash-and-lightning-attack.md", "Full Power Smash and the Lightning Attack",
     "Hard Knockback and the Dragon Smash Circle hit, five frame counts in one chain.",
     [r"five frame counts in one chain", r"issue #6, the perfect smash"]),
    ("camera-and-mouth.md", "The camera and the cut-in mouth",
     "Camera pacing and the second clip player behind the mouths.",
     [r"Perfect Barrier: the camera", r"the camera, FIXED", r"the mouth, and the second clip player",
      r"confirmed in play: the camera and the mouth", r"issue #10, the Great Ape"]),
    ("struggles.md", "Rush Struggle and Beam Struggle",
     "Both stick-rotation contests, their tick clocks and the CPU's synthetic stick.",
     [r"rush struggle: confirmed doubled", r"Rush Struggle: confirmed doubled",
      r"beam clash: the whole contest", r"Beam Struggle: the whole contest"]),
    ("widescreen.md", "Widescreen", "The widescreen model and every aspect group.",
     [r"widescreen retargeted", r"issue #23, widescreen"]),
    ("meter-economy.md", "The ki economy, meters and Blast Stock",
     "Ki income and drain, Max Power Mode, and the game's per-second clock.",
     [r"issue #4, the ki economy"]),
    ("stage-and-scenery.md", "Stage scenery and ambient animation",
     "The stage scene graph, its keyframe tracks, and the ambient props on them.",
     [r"issue #9, the stage"]),
    ("buff-durations.md", "Blast 1 buffs and timed status effects",
     "The durations behind Blast 1 stat boosts and After Image Strike.",
     [r"issue #20, the Blast 1 buffs"]),
    ("status-timers.md", "Fighter status timers",
     "The per-tick status timer block: paralysis, Solar Flare's lock-off, the combat timers.",
     [r"issue #28, paralysis", r"issue #32, Solar Flare", r"issue #34, the combat timers"]),
]


def sections(text: str) -> tuple[list[str], list[tuple[str, list[str]]]]:
    lines = text.split("\n")
    first = next(i for i, ln in enumerate(lines) if ln.startswith("## "))
    out, cur = [], None
    for ln in lines[first:]:
        if ln.startswith("## "):
            cur = (ln[3:].strip(), [ln])
            out.append(cur)
        else:
            cur[1].append(ln)
    return lines[:first], out


def topic_of(heading: str) -> str:
    stripped = re.sub(r"^\d{4}-\d{2}-\d{2} - ", "", heading)
    hits = {t[0] for t in TOPICS for pat in t[3] if re.search(pat, stripped) or re.search(pat, heading)}
    if len(hits) != 1:
        raise SystemExit(f"heading matches {sorted(hits) or 'no topic'}: {heading!r}")
    return hits.pop()


def build(text: str) -> dict[str, str]:
    preamble, secs = sections(text)
    grouped = {t[0]: [] for t in TOPICS}
    for heading, body in secs:
        grouped[topic_of(heading)].append(body)
    files = {}
    index = ["# BT3 60fps - findings", "",
             "The findings log, split by topic. Every section of the original",
             "`docs/findings.md` is in exactly one file below, unedited and in its original",
             "order. `tools/split_findings.py` does the split and checks nothing was lost.", "",
             "| topic | covers | sections |", "|---|---|---|"]
    for name, title, scope, _ in TOPICS:
        bodies = grouped[name]
        if not bodies:
            continue
        index.append(f"| [{title}]({name}) | {scope} | {len(bodies)} |")
        chunk = [f"# {title}", "", scope, ""]
        for body in bodies:
            b = list(body)
            while b and b[-1] == "":
                b.pop()
            chunk += b + [""]
        files[name] = "\n".join(chunk)
    index += ["", "## The original introduction", ""] + preamble
    files["README.md"] = "\n".join(index).rstrip("\n") + "\n"
    return files


def verify_links(files: dict[str, str]) -> None:
    """A relative link in any written file must resolve from docs/findings/."""
    bad = []
    for name, content in files.items():
        for m in RELATIVE_LINK_ANY.finditer(content):
            target = m.group(1).split("#")[0]
            if target and not (OUT / target).resolve().exists():
                bad.append(f"{name} -> {m.group(0)}")
    if bad:
        raise SystemExit("link(s) do not resolve from docs/findings/: " + "; ".join(bad[:5]))


def verify(text: str, files: dict[str, str]) -> None:
    _, secs = sections(text)
    want = Counter(ln for _, body in secs for ln in body if ln.strip())
    got = Counter()
    for name, content in files.items():
        if name == "README.md":
            continue
        body = content.split("\n")[4:]            # the title, blank, scope, blank we add
        got.update(ln for ln in body if ln.strip())
    preamble = Counter(ln for ln in sections(text)[0] if ln.strip())
    readme = Counter(ln for ln in files["README.md"].split("\n") if ln.strip())
    missing = (want - got) + (preamble - readme)
    extra = got - want
    if missing or extra:
        raise SystemExit(f"split is not lossless: {sum(missing.values())} lines missing, "
                         f"{sum(extra.values())} extra; first missing: {list(missing)[:3]}")
    print(f"lossless: {sum(want.values())} non-blank lines in {len(secs)} sections, "
          f"{len(files) - 1} topic files")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    text = SOURCE.read_text(encoding="utf-8")
    # Every line ends up one directory deeper, so relative links are rewritten
    # before the split, and verify() then compares against what is written.
    text = "\n".join(repath(ln) for ln in text.split("\n"))
    files = build(text)
    verify(text, files)
    verify_links(files)
    if args.check:
        return 0
    OUT.mkdir(parents=True, exist_ok=True)
    for name, content in files.items():
        (OUT / name).write_text(content if content.endswith("\n") else content + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {len(files)} files to {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

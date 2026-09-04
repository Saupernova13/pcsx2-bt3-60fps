"""Record a fighter's trajectory frame by frame, and compare two of them.

This is the measurement the airborne question turned on. The game is correct at
30fps by definition, so the reference run is the same save state, the same
scripted input and the same number of vsyncs with every compensation patch
removed. A perfect 60fps patch makes the two trajectories identical; wherever
they separate, something is still running at the wrong rate.

Comparing per vsync rather than per logic tick is deliberate. At 30fps the game
ticks every second vsync, so equal vsync counts mean equal real time, which is
what "twice as fast" is a claim about. The ``ticks`` verb does the opposite and
folds each capture down to one row per tick, which answers the other question:
a channel whose per-tick step is the same at both rates is uncompensated, and
one whose step halves is already fixed.

A script is a list of segments, and a segment is either:

    ("hold", frames, buttons, stick)   advance in one call, no sampling
    ("record", frames, buttons, stick) advance a frame at a time, sample each

Recording with a button held needs a PCSXROO built after the frame-advance
input fix. Before it, the vsync handler paused the VM ahead of the input hook,
which then returned early - so an advance of a single frame applied no input at
all and a stepped capture recorded the game ignoring the pad.

    python tools/traj.py capture ref --script coast --config off  --slot 2
    python tools/traj.py capture new --script coast --config air  --slot 2
    python tools/traj.py compare ref new --who 1
    python tools/traj.py ticks ref new --who 1
"""

from __future__ import annotations

import argparse
import json
import struct

import _bootstrap  # noqa: F401
import patchctl

from ps2ee import config
from ps2ee.battle import (ANCHOR, FRAME_COUNTER, POS, ROOT_NOW, ROOT_PREV, VEL,
                          delta, norm, resolve)
from ps2ee.roo import Roo

OUT = config.WORK / "captures"

# Takeoff has a wind-up of roughly 35 vsyncs, so a hold shorter than that
# leaves the 30fps reference still standing on the floor while the 60fps run is
# already airborne - which reads as a far bigger difference than there is.
SCRIPTS: dict[str, list[tuple]] = {
    # Nothing but physics: start from an already-launched state and watch.
    # No input at all, so nothing here depends on the input path.
    "coast": [("record", 300, [], None)],
    # Climb, then let go.
    "fall": [("hold", 90, [], (0.0, 1.0)), ("record", 240, [], None)],
    # Stand still. Any divergence here is noise, not physics.
    "idle": [("record", 180, [], None)],
    # Held movement, recorded throughout. The hold before it exists so both
    # rates are already cruising when the recording starts - a 60fps run gets
    # further through a wind-up in the same real time, and that is not a rate
    # bug but it swamps one.
    "back": [("hold", 90, [], (0.0, 1.0)), ("record", 180, [], (0.0, 1.0))],
    "forward": [("hold", 90, [], (0.0, -1.0)), ("record", 180, [], (0.0, -1.0))],
    "strafe": [("hold", 90, [], (1.0, 0.0)), ("record", 180, [], (1.0, 0.0))],
    "dash": [("hold", 60, ["Cross"], (0.0, 1.0)),
             ("record", 180, ["Cross"], (0.0, 1.0))],
}


def capture(roo: Roo, tag: str, script: str, cfg: str, slot: int) -> None:
    # Flush the pad before the load, not after: the frame a stale button would
    # be read on is the first frame after the restore.
    roo.flush_input()
    roo.loadstate(slot)
    groups = patchctl.PRESETS.get(cfg) or cfg.split(",")
    patchctl.apply(roo, groups)
    roo.frame_advance(4)

    pairs = resolve(roo)
    rows, ticks = [], []
    for kind, frames, buttons, stick in SCRIPTS[script]:
        roo.input_set(*buttons, left=stick)
        if kind == "hold":
            roo.frame_advance(frames)
        else:
            for _ in range(frames):
                roo.frame_advance(1)
                rows.append([_row(roo, pair) for pair in pairs])
                ticks.append(roo.read(FRAME_COUNTER))
    roo.input_release()

    if [str(p) for p in resolve(roo)] != [str(p) for p in pairs]:
        raise RuntimeError("the fighters were reallocated mid-capture")

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{tag}.json").write_text(json.dumps({
        "tag": tag, "script": script, "config": cfg, "slot": slot,
        "fighters": [str(p) for p in pairs], "ticks": ticks, "rows": rows}))
    print(f"{OUT / f'{tag}.json'}  {len(rows)} vsyncs, "
          f"{ticks[-1] - ticks[0] if ticks else 0} game ticks")


def _row(roo: Roo, pair) -> dict:
    f = roo.read_bytes(pair.fighter + POS, 0x50)
    m = roo.read_bytes(pair.model + ROOT_PREV, 0x30)
    at = lambda b, o: list(struct.unpack_from("<4f", b, o))  # noqa: E731
    return {
        "pos": at(f, 0x00),
        "anchor": at(f, ANCHOR - POS),
        "vel": at(f, VEL - POS),
        "root_prev": at(m, 0x00),
        "root_now": at(m, ROOT_NOW - ROOT_PREV),
    }


def load(tag: str) -> dict:
    return json.loads((OUT / f"{tag}.json").read_text())


def compare(left: str, right: str, who: int) -> None:
    a, b = load(left), load(right)
    n = min(len(a["rows"]), len(b["rows"]))
    print(f"{left} ({a['config']}) vs {right} ({b['config']})   "
          f"script={a['script']}   {n} sampled vsyncs")
    print(f"{'vsync':>6} {'ref moved':>11} {'test moved':>11} {'ratio':>7} "
          f"{'ref y':>9} {'test y':>9}")

    a0, b0 = a["rows"][0][who]["pos"], b["rows"][0][who]["pos"]
    for i in list(range(0, n, max(1, n // 12))) + [n - 1]:
        ra, rb = a["rows"][i][who], b["rows"][i][who]
        da, db = norm(delta(ra["pos"], a0)), norm(delta(rb["pos"], b0))
        print(f"{i:6d} {da:11.4f} {db:11.4f} "
              f"{db / da if da > 1e-4 else float('nan'):7.3f} "
              f"{ra['pos'][1]:9.3f} {rb['pos'][1]:9.3f}")
    print(f"\n1.000 is correct; 2.000 is the bug.")


def ticks_only(cap: dict, who: int) -> list[tuple[int, dict]]:
    """One row per game tick - the vsyncs in between are duplicates."""
    out, last = [], None
    for tick, row in zip(cap["ticks"], cap["rows"]):
        if tick != last:
            out.append((tick, row[who]))
            last = tick
    return out


def show_ticks(tag: str, who: int, limit: int) -> None:
    cap = load(tag)
    rows = ticks_only(cap, who)
    print(f"\n=== {tag} ({cap['config']}) - {len(rows)} ticks over "
          f"{len(cap['rows'])} vsyncs ===")
    print(f"{'tick':>6} {'|dpos|':>10} {'|vel|':>10} {'|root delta|':>13} "
          f"{'|anchor|':>10} {'dpos off-root':>14}")
    for i in range(1, min(limit, len(rows))):
        tick, cur = rows[i]
        step = delta(cur["pos"], rows[i - 1][1]["pos"])
        root = delta(cur["root_now"], cur["root_prev"])
        print(f"{tick:6d} {norm(step):10.4f} {norm(cur['vel']):10.4f} "
              f"{norm(root):13.4f} {norm(cur['anchor']):10.4f} "
              f"{norm(delta(step, root)):14.4f}")


def speeds(tags: list[str], who: int, window: int) -> None:
    """Instantaneous speed in units per second, against real time.

    Everything else in this file compares distances, and a distance is the
    integral of the thing actually under test. Two runs whose speeds match
    perfectly still show different distances if one entered a ramp a fraction
    of a second earlier, and a run that is genuinely 20% slow looks fine over a
    window that happens to start later in the same ramp. So: sample the speed
    itself, at the same wall-clock offsets, in units both rates can be read in.

    A vsync is 1/60s whatever the game does with it, so the divisor is the same
    for both - which is the whole point of measuring per vsync.
    """
    caps = [(tag, load(tag)) for tag in tags]
    n = min(len(c["rows"]) for _, c in caps)
    print(f"speed in units/second, sampled over {window} vsyncs "
          f"({window / 60:.2f}s), {n} vsyncs recorded")
    print(f"{'at':>7} " + " ".join(f"{tag:>13}" for tag, _ in caps)
          + f" {'ratio':>7}")
    for i in range(window, n, max(window, (n - window) // 12)):
        values = []
        for _, cap in caps:
            here = cap["rows"][i][who]["pos"]
            back = cap["rows"][i - window][who]["pos"]
            values.append(norm(delta(here, back)) / (window / 60.0))
        ratio = values[-1] / values[0] if values[0] > 1e-6 else float("nan")
        print(f"{i / 60:6.2f}s " + " ".join(f"{v:13.3f}" for v in values)
              + f" {ratio:7.3f}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="verb", required=True)

    cap = sub.add_parser("capture")
    cap.add_argument("tag")
    cap.add_argument("--script", default="coast", choices=sorted(SCRIPTS))
    cap.add_argument("--config", default="air",
                     help="a preset (" + ", ".join(patchctl.PRESETS)
                          + ") or a comma-separated group list")
    cap.add_argument("--slot", type=int, default=2)

    cmp_ = sub.add_parser("compare")
    cmp_.add_argument("left")
    cmp_.add_argument("right")
    cmp_.add_argument("--who", type=int, default=0)

    tick = sub.add_parser("ticks")
    tick.add_argument("tags", nargs="+")
    tick.add_argument("--who", type=int, default=0)
    tick.add_argument("--limit", type=int, default=14)

    spd = sub.add_parser("speed")
    spd.add_argument("tags", nargs="+")
    spd.add_argument("--who", type=int, default=0)
    spd.add_argument("--window", type=int, default=12)

    args = parser.parse_args()
    if args.verb == "capture":
        capture(Roo().connect(), args.tag, args.script, args.config, args.slot)
    elif args.verb == "compare":
        compare(args.left, args.right, args.who)
    elif args.verb == "speed":
        speeds(args.tags, args.who, args.window)
    else:
        for tag in args.tags:
            show_ticks(tag, args.who, args.limit)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

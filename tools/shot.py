"""Drive an input for N frames from a save state, then photograph the result.

A screenshot is the only check that the numbers describe the situation you
think they do - a position vector far from the arena reads the same whether the
fighter flew there or the camera cut to a cutscene.

    python tools/shot.py idle
    python tools/shot.py fly --hold Cross --stick 0,1 --frames 90

Screenshots need a RUNNING VM, so this resumes, waits for the GS to present,
and only then captures.
"""

from __future__ import annotations

import argparse
import time

import _bootstrap  # noqa: F401

from ps2ee import config
from ps2ee.battle import POS, resolve, vec
from ps2ee.roo import Roo


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tag")
    parser.add_argument("--slot", type=int, default=1)
    parser.add_argument("--hold", nargs="*", default=[])
    parser.add_argument("--stick", default=None, help="X,Y each -1..1")
    parser.add_argument("--frames", type=int, default=60)
    parser.add_argument("--no-load", action="store_true")
    args = parser.parse_args()

    roo = Roo().connect()
    if not args.no_load:
        roo.flush_input()
        roo.loadstate(args.slot)
    pairs = resolve(roo)
    stick = tuple(float(v) for v in args.stick.split(",")) if args.stick else None
    if args.hold or stick:
        roo.input_set(*args.hold, left=stick)
    if args.frames:
        roo.frame_advance(args.frames)
    for pair in pairs:
        p = vec(roo, pair.fighter + POS)
        print(f"{pair}  pos ({p[0]:9.3f} {p[1]:9.3f} {p[2]:9.3f})")

    roo.resume()
    time.sleep(1.0)
    snaps = config.roo_snaps_dir()
    snaps.mkdir(parents=True, exist_ok=True)
    path = snaps / f"{args.tag}.png"
    roo.screenshot(path)
    for _ in range(20):
        time.sleep(0.25)
        if path.exists():
            break
    roo.input_release()
    print(f"{path}  {'written' if path.exists() else 'NEVER LANDED'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Watch a window of a fighter's struct tick by tick, as floats.

Once a watchpoint has named the fields a routine reads, the question becomes
which of them actually carries the motion this frame. Printing the window as
floats next to the position delta answers that by inspection: the one whose
magnitude matches the step is the channel in use.

    python tools/fields.py --who 1 --slot 2 --from 0x70 --to 0xC0 --ticks 8
"""

from __future__ import annotations

import argparse
import struct

import _bootstrap  # noqa: F401
import patchctl

from game.battle import POS, norm, resolve
from ps2ee.roo import Roo


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--who", type=int, default=1)
    parser.add_argument("--slot", type=int, default=2)
    parser.add_argument("--config", default="shipped")
    parser.add_argument("--from", dest="start", type=lambda s: int(s, 0), default=0x70)
    parser.add_argument("--to", dest="end", type=lambda s: int(s, 0), default=0xC0)
    parser.add_argument("--ticks", type=int, default=8)
    args = parser.parse_args()

    roo = Roo().connect()
    roo.flush_input()
    roo.loadstate(args.slot)
    patchctl.apply(roo, patchctl.SHIPPED if args.config == "shipped" else [])
    roo.frame_advance(2)

    pair = resolve(roo)[args.who]
    print(f"{pair}   offsets {args.start:#x}..{args.end:#x}")
    size = args.end - args.start
    previous = None
    for tick in range(args.ticks):
        roo.frame_advance(1)
        pos = struct.unpack("<4f", roo.read_bytes(pair.fighter + POS, 16))
        raw = roo.read_bytes(pair.fighter + args.start, size)
        step = norm([a - b for a, b in zip(pos, previous)]) if previous else 0.0
        previous = pos
        print(f"\n-- tick {tick}   |dpos| {step:.4f} --")
        for off in range(0, size, 16):
            vals = struct.unpack_from("<4f", raw, off)
            marker = "  <== |v| matches" if abs(norm(vals) - step) < 1e-3 and step else ""
            print(f"   +{args.start + off:04X}  "
                  + " ".join(f"{v:12.5f}" for v in vals)
                  + f"   |v| {norm(vals):9.4f}{marker}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

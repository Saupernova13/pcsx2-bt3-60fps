"""Static scan for frame-pacing constants - a fast standalone pass.

This is the core heuristic of the guide's PS2_Scoring_Radar Ghidra script,
reimplemented so candidates exist before Ghidra finishes auto-analysis. The
Ghidra script remains the authority: it has function names and call graphs,
which this does not. Use this to get moving, then confirm in Ghidra.

    python tools/radar.py                        # whole .text
    python tools/radar.py --near 102034 --span 2000
    python tools/radar.py --floats-only
"""

import argparse
from collections import Counter

import _bootstrap  # noqa: F401

from ps2ee import config
from ps2ee.disasm import function_start, scan_immediates
from ps2ee.eemem import EEMemory

# Integer strides the guide calls out, plus the float constants that show up as
# per-frame step multipliers. lui loads the upper half, so a float appears here
# as its top 16 bits.
INT_VALUES = {
    1: "stride 1 (already 60fps)",
    2: "stride 2 (30fps - halve for 60fps)",
    30: "30 (frames per second)",
    60: "60 (frames per second)",
}

FLOAT_VALUES = {
    0x3F00: "float 0.5 (already halved)",
    0x3F80: "float 1.0 (per-frame step)",
    0x4000: "float 2.0 (30fps step - halve for 60fps)",
    0x4170: "float 15.0",
    0x41F0: "float 30.0",
    0x4270: "float 60.0",
    0x3D23: "float ~0.0399 (1/25)",
    0x3C88: "float ~0.0166 (1/60)",
    0x3D08: "float ~0.0333 (1/30)",
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--state", help="explicit .p2s path")
    parser.add_argument("--near", help="hex address to centre the scan on")
    parser.add_argument("--span", default="4000", help="hex bytes either side of --near")
    parser.add_argument("--floats-only", action="store_true")
    parser.add_argument("--ints-only", action="store_true")
    parser.add_argument("--group", action="store_true",
                        help="group hits by enclosing function")
    parser.add_argument("--limit", type=int, default=120)
    args = parser.parse_args()

    values = {}
    if not args.floats_only:
        values.update(INT_VALUES)
    if not args.ints_only:
        values.update(FLOAT_VALUES)

    mem = EEMemory.from_state(args.state or config.latest_state())
    start, end = config.TEXT_BASE, config.TEXT_END
    if args.near:
        centre = int(args.near, 16)
        span = int(args.span, 16)
        start = max(start, centre - span)
        end = min(end, centre + span)

    hits = scan_immediates(mem, values, start, end)
    print(f"# source: {mem.source}")
    print(f"# scanned {start:08X}-{end:08X}, {len(hits)} hits\n")

    if args.group:
        buckets: dict[int, list] = {}
        for hit in hits[: args.limit]:
            buckets.setdefault(function_start(mem, hit[0]), []).append(hit)
        for func in sorted(buckets):
            print(f"  function {func:08X}  ({len(buckets[func])} hits)")
            for addr, _value, label, text in buckets[func]:
                print(f"    {addr:08X}  {text:<28} | {label}")
        return 0

    for addr, _value, label, text in hits[: args.limit]:
        print(f"  {addr:08X}  {text:<28} | {label}")
    if len(hits) > args.limit:
        print(f"  ... {len(hits) - args.limit} more")

    tally = Counter(label for _a, _v, label, _t in hits)
    print("\n# totals")
    for label, count in tally.most_common():
        print(f"  {count:>6}  {label}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

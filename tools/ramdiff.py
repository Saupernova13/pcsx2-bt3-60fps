"""Differential memory search across save states.

Replaces the PCSX2 GUI memory searcher. Capture a save state per condition,
then filter the whole 32 MB image at once.

    # something that is 2 in state A and 1 in state B (framerate stride)
    python tools/ramdiff.py a.p2s b.p2s --value 0:2 --value 1:1

    # a per-frame counter: went up by exactly 1 between two consecutive states
    python tools/ramdiff.py a.p2s b.p2s --delta 1

    # anything that changed at all, as floats
    python tools/ramdiff.py a.p2s b.p2s --changed --type f32
"""

import argparse

import _bootstrap  # noqa: F401

from ps2ee.diff import GAME_REGIONS, Region, Scan


def parse_value(spec: str) -> tuple[int, float]:
    """'0:2' -> (snapshot 0, value 2). Accepts 0x hex and floats."""
    index, _, raw = spec.partition(":")
    if not _:
        raise argparse.ArgumentTypeError("use SNAPSHOT:VALUE, e.g. 0:2")
    value = float(raw) if "." in raw else int(raw, 0)
    return int(index), value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("states", nargs="+", help="two or more .p2s files, in order")
    parser.add_argument("--type", default="u32", help="u8 u16 u32 i8 i16 i32 f32")
    parser.add_argument("--value", action="append", type=parse_value, default=[],
                        metavar="N:V", help="value V in snapshot N (repeatable)")
    parser.add_argument("--changed", action="store_true")
    parser.add_argument("--unchanged", action="store_true")
    parser.add_argument("--increased", action="store_true")
    parser.add_argument("--decreased", action="store_true")
    parser.add_argument("--delta", type=int, help="changed by exactly this amount")
    parser.add_argument("--range", metavar="LO:HI",
                        help="restrict to a hex address range, e.g. 2C3400:334BF8")
    parser.add_argument("--all-ram", action="store_true",
                        help="scan all 32 MB instead of just data+bss+heap")
    parser.add_argument("--limit", type=int, default=40)
    args = parser.parse_args()

    regions = [Region(0, 0x02000000, "all")] if args.all_ram else GAME_REGIONS
    scan = Scan.from_states(*args.states, dtype=args.type, regions=regions)
    print(f"# {len(args.states)} snapshots, {args.type}, "
          f"{scan.count():,} slots in scope")

    for index, value in args.value:
        scan.value(index, value)
    if args.changed:
        scan.changed()
    if args.unchanged:
        scan.unchanged()
    if args.increased:
        scan.increased()
    if args.decreased:
        scan.decreased()
    if args.delta is not None:
        scan.delta(args.delta)
    if args.range:
        lo, _, hi = args.range.partition(":")
        scan.in_range(int(lo, 16), int(hi, 16))

    print(scan.report(args.limit))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

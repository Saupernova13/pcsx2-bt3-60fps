"""Unpack a PCSX2 save state into work/ for offline analysis.

    python tools/dump-state.py                 # newest BT3 state
    python tools/dump-state.py --slot 1 --tag battle-goku-frieza
    python tools/dump-state.py --list
"""

import argparse

import _bootstrap  # noqa: F401

from game import config
from ps2ee.savestate import EE_MEMORY, IOP_MEMORY, SCREENSHOT, SaveState

WANTED = [EE_MEMORY, IOP_MEMORY, SCREENSHOT]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", help="explicit .p2s path")
    parser.add_argument("--slot", type=int, help="PCSX2 save slot number")
    parser.add_argument("--tag", help="name for the output folder under work/states")
    parser.add_argument("--all", action="store_true", help="dump every member")
    parser.add_argument("--list", action="store_true", help="list available states")
    args = parser.parse_args()

    if args.list:
        for path in sorted(config.sstates_dir().glob(f"{config.SERIAL} ({config.CRC}).*.p2s")):
            size_mb = path.stat().st_size / 1e6
            print(f"  {path.name:<40} {size_mb:6.1f} MB")
        return 0

    path = args.state or config.latest_state(args.slot)
    if args.tag:
        tag = args.tag
    elif args.slot is not None:
        tag = f"slot{args.slot:02d}"
    else:
        tag = "latest"
    dest = config.WORK / "states" / tag

    with SaveState(path) as state:
        print(f"{path}\n  written by PCSX2 {state.version()}")
        names = state.names() if args.all else WANTED
        for name in names:
            if name not in state.names():
                continue
            out = state.dump(name, dest / name)
            print(f"  {name:<32} -> {out}  ({out.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

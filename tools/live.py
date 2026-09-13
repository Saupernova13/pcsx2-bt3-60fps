"""Talk to a running PCSX2 over PINE - read, write, watch, apply patches live.

Needs EnablePINE = true in PCSX2.ini and a booted game.

    python tools/live.py status
    python tools/live.py read 264DBC 1DCB40
    python tools/live.py watch 00331D64 --seconds 5
    python tools/live.py apply wip/experiments/003-halve-anim.pnach
    python tools/live.py fps
"""

import argparse
import time

import _bootstrap  # noqa: F401

from game import config
from ps2ee.disasm import decode
from ps2ee.pine import Pine, PineNotRunning
from ps2ee.pnach import Pnach


def cmd_status(pine: Pine, args) -> int:
    print(f"emulator  {pine.emulator_version()}")
    print(f"status    {pine.status()}")
    print(f"title     {pine.title()}")
    print(f"game id   {pine.game_id()}  (expecting {config.SERIAL})")
    print(f"version   {pine.game_version()}")
    return 0


def cmd_read(pine: Pine, args) -> int:
    addrs = [int(a, 16) for a in args.addrs]
    values = pine.read_many(addrs, args.width)
    for addr, value in zip(addrs, values):
        line = f"{addr:08X}  {value:0{args.width * 2}X}"
        if args.width == 4:
            line += f"  {decode(value, addr)}"
        print(line)
    return 0


def cmd_write(pine: Pine, args) -> int:
    addr = int(args.addr, 16)
    value = int(args.value, 16)
    before = pine.read(addr, args.width)
    pine.write(addr, value, args.width)
    after = pine.read(addr, args.width)
    print(f"{addr:08X}  {before:0{args.width * 2}X} -> {after:0{args.width * 2}X}")
    if after != value:
        print("  WARNING: the game overwrote it immediately - it is written every frame")
    return 0


def cmd_watch(pine: Pine, args) -> int:
    """Sample addresses over time - how you measure a per-frame counter's rate."""
    addrs = [int(a, 16) for a in args.addrs]
    start = time.time()
    first = pine.read_many(addrs, args.width)
    print("  t(s)   " + "  ".join(f"{a:>10X}" for a in addrs))
    last = first
    while True:
        elapsed = time.time() - start
        if elapsed >= args.seconds:
            break
        time.sleep(args.interval)
        now = pine.read_many(addrs, args.width)
        deltas = "  ".join(f"{n - p:>10}" for n, p in zip(now, last))
        print(f"  {elapsed:5.2f}  {deltas}")
        last = now
    total = time.time() - start
    print("\n  rate per second over the whole window:")
    for addr, a, b in zip(addrs, first, last):
        print(f"    {addr:08X}  {(b - a) / total:10.2f}/s   (net {b - a})")
    return 0


def cmd_fps(pine: Pine, args) -> int:
    """Measure the game's own frame counter rate.

    BT3 increments a counter at 0x00331D64 once per main-loop iteration. If it
    climbs at ~30/s the game logic is running at 30fps; ~60/s means the limiter
    is off and every system is stepping twice as often as it was authored for.
    """
    addr = int(args.addr, 16)
    first = pine.read(addr)
    start = time.time()
    time.sleep(args.seconds)
    last = pine.read(addr)
    elapsed = time.time() - start
    rate = (last - first) / elapsed
    print(f"  counter {addr:08X}: {first} -> {last} over {elapsed:.2f}s")
    print(f"  {rate:.2f} increments/second")
    print(f"  -> game logic is stepping at approximately {round(rate)} Hz")
    return 0


def cmd_apply(pine: Pine, args) -> int:
    """Write a pnach's word patches straight into RAM - no restart needed.

    Only unconditional EE word writes are applied. E-code conditionals are
    evaluated by PCSX2 every frame and cannot be replayed this way, so they are
    reported and skipped.
    """
    pnach = Pnach.load(args.pnach)
    problems = pnach.validate()
    if problems:
        print("VALIDATION FAILED")
        for problem in problems:
            print(f"  {problem}")
        return 1

    applied = skipped = 0
    for group in pnach.groups:
        if args.only and group.name not in args.only:
            continue
        print(f"[{group.name}]")
        skip_next = False
        for line in group.lines:
            if line.is_condition:
                print(f"  skip E-code {line.render()} (evaluated per frame by PCSX2)")
                skip_next = True
                skipped += 1
                continue
            if skip_next:
                print(f"  skip conditional {line.addr:08X}")
                skip_next = False
                skipped += 1
                continue
            if line.cpu != "EE":
                skipped += 1
                continue
            width = {"byte": 1, "short": 2, "word": 4, "extended": 4}.get(line.type, 4)
            before = pine.read(line.addr, width)
            pine.write(line.addr, line.value, width)
            print(f"  {line.addr:08X}  {before:08X} -> {line.value:08X}"
                  f"   {line.comment}")
            applied += 1

    print(f"\n{applied} words written live, {skipped} skipped.")
    print("These writes are not sticky - the game may rewrite them, and they are")
    print("lost on reset. Use tools/deploy.py for a persistent patch.")
    return 0


def cmd_savestate(pine: Pine, args) -> int:
    pine.save_state(args.slot)
    print(f"Asked PCSX2 to save state slot {args.slot}.")
    time.sleep(1.0)
    try:
        path = config.latest_state(args.slot)
        print(f"  {path}  ({path.stat().st_size:,} bytes)")
    except FileNotFoundError:
        print("  (state file not visible yet - check the slot)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--port", type=int, default=28011)
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("status").set_defaults(func=cmd_status)

    p = sub.add_parser("read")
    p.add_argument("addrs", nargs="+")
    p.add_argument("--width", type=int, default=4, choices=[1, 2, 4, 8])
    p.set_defaults(func=cmd_read)

    p = sub.add_parser("write")
    p.add_argument("addr")
    p.add_argument("value")
    p.add_argument("--width", type=int, default=4, choices=[1, 2, 4, 8])
    p.set_defaults(func=cmd_write)

    p = sub.add_parser("watch")
    p.add_argument("addrs", nargs="+")
    p.add_argument("--width", type=int, default=4, choices=[1, 2, 4, 8])
    p.add_argument("--seconds", type=float, default=5.0)
    p.add_argument("--interval", type=float, default=0.5)
    p.set_defaults(func=cmd_watch)

    p = sub.add_parser("fps")
    p.add_argument("--addr", default="00331D64", help="the game's frame counter")
    p.add_argument("--seconds", type=float, default=5.0)
    p.set_defaults(func=cmd_fps)

    p = sub.add_parser("apply")
    p.add_argument("pnach")
    p.add_argument("--only", action="append", default=None)
    p.set_defaults(func=cmd_apply)

    p = sub.add_parser("savestate")
    p.add_argument("slot", type=int)
    p.set_defaults(func=cmd_savestate)

    args = parser.parse_args()
    try:
        with Pine(port=args.port) as pine:
            return args.func(pine, args)
    except PineNotRunning as exc:
        print(f"{exc}")
        print("\n  python tools/setup-pcsx2.py --enable-pine")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

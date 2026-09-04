"""Enumerate every instruction that writes to an address range.

The single most reliable technique this project has: a write watchpoint answers
"who changes this?" with an address, where reading disassembly answers it with a
guess. Every link in the position chain that was confirmed this way held up
under test; the one link inferred by reading code is the one that broke a fix.

Distinct PCs matter more than hit counts, so this keeps collecting until it has
seen ``--hits`` stops and reports the set. ``ra`` comes with each one - these
are leaf calls into a vector library, so the caller is the interesting half.

    python tools/writers.py 0x01871CD0 --size 16 --slot 2 --hits 40

PCSX2's memchecks do not observe every write path, so silence is not proof.
A range that stays quiet while the value provably changes means the write is
going through a path memchecks miss, not that the address is wrong.
"""

from __future__ import annotations

import argparse
from collections import Counter

import _bootstrap  # noqa: F401
import patchctl

from ps2ee.roo import Roo


def watch(roo: Roo, start: int, size: int, hits: int, kinds) -> Counter:
    note = roo.mc_add(start, start + size, on=kinds).get("note")
    if note:
        print(f"note: {note}")
    seen: Counter = Counter()
    context: dict[tuple[int, int], dict] = {}

    for _ in range(hits):
        seq = roo.seq()
        roo.resume()
        stop = roo.wait(seq, timeout_ms=8000)
        if stop is None:
            print("no further writes within the timeout")
            break
        ra = roo.reg("ra") if roo.paused() else 0
        key = (stop.pc, ra)
        seen[key] += 1
        if key not in context:
            context[key] = {"addr": stop.mem_addr, "size": stop.mem_size}
    roo.mc_clear()

    print(f"\n{sum(seen.values())} writes to {start:08X}..{start + size:08X}"
          f" from {len(seen)} distinct sites\n")
    print(f"{'pc':>10} {'ra':>10} {'hits':>6}  {'target':>10}  instruction")
    for (pc, ra), count in seen.most_common():
        text = roo.dis(pc, 1)[0][1].replace("\t", " ")
        info = context[(pc, ra)]
        print(f"  {pc:08X}   {ra:08X} {count:6d}  {info['addr']:08X}  {text}")
    return seen


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("addr", help="start of the watched range")
    parser.add_argument("--size", type=lambda s: int(s, 0), default=16)
    parser.add_argument("--hits", type=int, default=30)
    parser.add_argument("--slot", type=int, default=None,
                        help="load this state first, so the range is live")
    parser.add_argument("--config", default=None,
                        help='"shipped" or "off", applied after the load')
    parser.add_argument("--on", default="write", help="write, change, read")
    args = parser.parse_args()

    roo = Roo().connect()
    if args.slot is not None:
        roo.flush_input()
        roo.loadstate(args.slot)
        if args.config:
            patchctl.apply(roo, patchctl.PRESETS[args.config])
        roo.frame_advance(2)

    try:
        watch(roo, int(args.addr, 0), args.size, args.hits, args.on.split(","))
    finally:
        roo.mc_clear()
        roo.resume()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

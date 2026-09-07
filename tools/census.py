"""Which of a list of addresses actually execute during a window of the game.

A static scan finds hundreds of candidates and most of them have nothing to do
with the situation being measured. This puts a breakpoint on every one, removes
each the moment it fires, and runs the window - so the run converges instead of
stopping on the same hot site forever, and what comes out is the short list
worth sweeping.

Breakpoints are added in batches, because a few hundred at once is slow and the
run restarts from the save state for each batch anyway.

    python tools/census.py 8 full 130 work/tickcount.txt work/executed.txt
    python tools/census.py 8 full 30 work/tickcount.txt work/flight.txt --lead 134
"""

from __future__ import annotations

import argparse
import time

import _bootstrap  # noqa: F401
import patchctl

from ps2ee.roo import Roo

FRAME = 0x00331D64


def groups_for(spec: str) -> list[str]:
    preset, _, extra = spec.partition("+")
    return list(patchctl.PRESETS[preset]) + [g for g in extra.split(",") if g]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("slot", type=int)
    ap.add_argument("preset", help="PRESET[+group,...]")
    ap.add_argument("ticks", type=int, help="how many game ticks the window lasts")
    ap.add_argument("sites", help="file whose first column is a hex address")
    ap.add_argument("out")
    ap.add_argument("--lead", type=int, default=0, help="vsyncs to skip before the window")
    ap.add_argument("--batch", type=int, default=120)
    args = ap.parse_args()

    addrs = [int(line.split()[0], 16) for line in open(args.sites) if line[:1] == "0"]
    groups = groups_for(args.preset)
    roo = Roo().connect()
    seen: list[tuple[int, int]] = []

    for start in range(0, len(addrs), args.batch):
        chunk = addrs[start:start + args.batch]
        roo.flush_input()
        roo.loadstate(args.slot)
        time.sleep(0.9)
        patchctl.apply(roo, groups, quiet=True)
        roo.frame_advance(2 + args.lead)
        t0 = roo.read(FRAME)
        roo.bp_clear()
        for addr in chunk:
            roo.bp_add(addr)
        live = set(chunk)
        while live:
            seq = roo.seq()
            roo.resume()
            stop = roo.wait(seq, timeout_ms=2500)
            if stop is None:
                break
            if stop.pc in live:
                live.discard(stop.pc)
                roo.bp_remove(stop.pc)
                seen.append((stop.pc, roo.read(FRAME) - t0))
            if roo.read(FRAME) - t0 > args.ticks:
                break
        roo.bp_clear()
        print(f"  batch {start // args.batch}: {len(chunk) - len(live)}/{len(chunk)} fired")

    roo.flush_input()
    roo.resume()
    with open(args.out, "w") as fh:
        for pc, tick in sorted(seen):
            fh.write(f"{pc:08X}  first at tick {tick}\n")
    print(f"{len(seen)} of {len(addrs)} executed -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

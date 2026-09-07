"""Stop both arms at the same EVENT instead of the same time, and diff there.

Whatever a scripted sequence keeps time by has to read the same at a given
point of the script in both arms, because it is the same point. Everything
else - real time, tick count, every correctly compensated quantity - differs.
So: snapshot at the start and at the event in each arm, and keep the words that
started equal, moved, and arrived at the event equal again.

The event is a watched address changing by more than a threshold. The
opponent's HP dropping is the usual one; pick a threshold above whatever the
mode's health regeneration writes, or it will trigger on that instead.

This rarely names the answer on its own. It is worth running because it says
what the answer is *not*, which is how the search that found this game's two
scripted clocks narrowed from floats to integers.

    python tools/eventdiff.py 8 work/ev.npz
    python tools/eventdiff.py 1 work/ev.npz --hold L2,Triangle --leads 137,134
    python tools/eventdiff.py --report work/ev.npz --max-step 400
"""

from __future__ import annotations

import argparse
import collections
import time

import numpy as np

import _bootstrap  # noqa: F401
import patchctl

from ps2ee.roo import Roo

LO, HI = 0x00300000, 0x02000000
CHUNK = 8 << 20
FRAME = 0x00331D64
OPPONENT_HP = 0x018726A4


def snapshot(roo: Roo) -> np.ndarray:
    parts = [np.frombuffer(roo.read_bytes(off, min(CHUNK, HI - off)), dtype="<f4")
             for off in range(LO, HI, CHUNK)]
    return np.concatenate(parts)


def groups_for(spec: str) -> list[str]:
    preset, _, extra = spec.partition("+")
    return list(patchctl.PRESETS[preset]) + [g for g in extra.split(",") if g]


def capture(roo: Roo, slot: int, specs: list[str], leads: list[int], hold: list[str],
            watch: int, drop: int, limit: int) -> dict:
    out: dict[str, np.ndarray] = {"lo": np.array([LO])}
    for n, (spec, lead) in enumerate(zip(specs, leads)):
        key = "off" if n == 0 else "full"
        roo.flush_input()
        roo.loadstate(slot)
        time.sleep(1.0)
        patchctl.apply(roo, groups_for(spec), quiet=True)
        roo.frame_advance(2)
        if hold:
            roo.input_set(*hold)
        if lead:
            roo.frame_advance(lead)
        base = roo.read(watch)
        start = roo.read(FRAME)
        out[key + "_a"] = snapshot(roo)
        vsyncs = None
        for i in range(limit):
            roo.frame_advance(1)
            if abs(roo.read(watch) - base) > drop:
                vsyncs = i + 1
                break
        if vsyncs is None:
            raise SystemExit(f"{spec}: the event never happened inside {limit} vsyncs")
        out[key + "_b"] = snapshot(roo)
        ticks = roo.read(FRAME) - start
        out[key + "_ticks"] = np.array([ticks, vsyncs])
        roo.flush_input()
        print(f"  {spec}: event after {vsyncs} vsyncs ({vsyncs / 60:.2f}s), {ticks} ticks")
    return out


def report(path: str, max_step: int, top: int) -> None:
    np.seterr(all="ignore")
    z = np.load(path)
    lo = int(z["lo"][0])
    ints = lambda k: z[k].view(np.int32).astype(np.int64)
    oa, ob, fa, fb = ints("off_a"), ints("off_b"), ints("full_a"), ints("full_b")
    ot, ov = (int(v) for v in z["off_ticks"])
    ft, fv = (int(v) for v in z["full_ticks"])
    print(f"off  {ov} vsyncs / {ot} ticks     full  {fv} vsyncs / {ft} ticks")

    step = ob - oa
    cand = (oa == fa) & (step != 0) & (ob == fb)
    print(f"started equal, moved, and equal again at the event: {int(cand.sum())}")
    cand &= np.abs(step) <= max_step
    idx = np.flatnonzero(cand)
    print(f"  of those, a step of at most {max_step}: {idx.size}")
    totals = collections.Counter(int(step[i]) for i in idx)
    print("  most common totals:", totals.most_common(10))
    near = [i for i in idx if abs(abs(int(step[i])) - ot) <= max(2, ot // 20)]
    print(f"\n{len(near)} of them moved by about the 30fps arm's {ot} ticks:")
    for i in near[:top]:
        print(f"  {lo + i * 4:08X}  {int(oa[i]):>10d} -> {int(ob[i]):<10d}"
              f"  d={int(step[i]):+d}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("slot", nargs="?", type=int)
    ap.add_argument("out", nargs="?")
    ap.add_argument("--report", metavar="NPZ")
    ap.add_argument("--presets", default="off,full")
    ap.add_argument("--leads", default=None)
    ap.add_argument("--hold", default="")
    ap.add_argument("--watch", default=f"{OPPONENT_HP:x}", help="address to watch, hex")
    ap.add_argument("--drop", type=int, default=500, help="change that counts as the event")
    ap.add_argument("--limit", type=int, default=600, help="vsyncs to wait")
    ap.add_argument("--max-step", type=int, default=400)
    ap.add_argument("--top", type=int, default=40)
    args = ap.parse_args()

    if args.report:
        report(args.report, args.max_step, args.top)
        return 0
    if args.slot is None or not args.out:
        ap.error("give a save state slot and an output path, or --report")

    specs = args.presets.split(",", 1) if "," in args.presets else [args.presets] * 2
    leads = [int(x) for x in args.leads.split(",")] if args.leads else [0, 0]
    hold = [b for b in args.hold.split(",") if b]
    data = capture(Roo().connect(), args.slot, specs, leads, hold,
                   int(args.watch, 16), args.drop, args.limit)
    np.savez_compressed(args.out, **data)
    print("saved", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Ask every word in RAM whether it still moves at double speed.

Same save state, same scripted input, the same number of **vsyncs** - the same
real time - once unpatched and once patched. A quantity the patch compensates
covers the same distance in both arms; one it misses covers twice as much.

Three snapshots per arm, not two. A word that only moves because its pool was
freed and refilled jumps once, while a clock advances the same amount in each
half of the window, and requiring the halves to agree is what separates them:
on the run that mattered it cut 805 false candidates to 28 real ones.

Read as int32 as well as float32. An integer counter is a denormal when read as
a float and disappears from a float scan, and the two clocks behind every
staged beat in this game are integers.

    python tools/ratediff.py 8 120 work/rd.npz
    python tools/ratediff.py 8 120 work/rd.npz --hold L2,Triangle --lead 71
    python tools/ratediff.py --report work/rd.npz
    python tools/ratediff.py --report work/rd.npz --ints
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


def snapshot(roo: Roo) -> np.ndarray:
    parts = [np.frombuffer(roo.read_bytes(off, min(CHUNK, HI - off)), dtype="<f4")
             for off in range(LO, HI, CHUNK)]
    return np.concatenate(parts)


def groups_for(spec: str) -> list[str]:
    preset, _, extra = spec.partition("+")
    return list(patchctl.PRESETS[preset]) + [g for g in extra.split(",") if g]


def capture(roo: Roo, slot: int, vsyncs: int, specs: list[str], leads: list[int],
            hold: list[str]) -> dict:
    out: dict[str, np.ndarray] = {"lo": np.array([LO])}
    for n, (spec, lead) in enumerate(zip(specs, leads)):
        key = "off" if n == 0 else "full"
        roo.flush_input()
        roo.loadstate(slot)
        time.sleep(1.0)
        patchctl.apply(roo, groups_for(spec), quiet=True)
        # Never load the state again here. These states were captured while
        # patched, so a second load puts the patched words back and the
        # unpatched arm stops being unpatched.
        roo.frame_advance(2)
        if hold:
            roo.input_set(*hold)
        if lead:
            roo.frame_advance(lead)
        start = roo.read(FRAME)
        out[key + "_a"] = snapshot(roo)
        roo.frame_advance(vsyncs // 2)
        out[key + "_m"] = snapshot(roo)
        roo.frame_advance(vsyncs - vsyncs // 2)
        out[key + "_b"] = snapshot(roo)
        ticks = roo.read(FRAME) - start
        out[key + "_ticks"] = np.array([ticks, vsyncs])
        roo.flush_input()
        print(f"  {spec}: {vsyncs} vsyncs = {ticks} ticks")
        if n == 0 and ticks * 2 > vsyncs + 2:
            print("  WARNING: the unpatched arm ticked once per vsync. It is still "
                  "patched - see the note in the docstring.")
    return out


def report(path: str, ints: bool, top: int, any_start: bool) -> None:
    np.seterr(all="ignore")
    z = np.load(path)
    lo = int(z["lo"][0])
    if ints:
        get = lambda k: z[k].view(np.int32).astype(np.int64)
    else:
        get = lambda k: z[k]
    oa, om, ob = get("off_a"), get("off_m"), get("off_b")
    fa, fm, fb = get("full_a"), get("full_m"), get("full_b")

    if ints:
        good = np.ones(oa.shape, dtype=bool)
        steady = ((om - oa) == (ob - om)) & ((fm - fa) == (fb - fm))
        moved = (ob - oa) != 0
        good &= np.abs(ob - oa) < (1 << 24)
    else:
        plausible = lambda x: np.isfinite(x) & (np.abs(x) < 1e6)
        good = plausible(oa) & plausible(om) & plausible(ob)
        good &= plausible(fa) & plausible(fm) & plausible(fb)
        o1, o2, f1, f2 = om - oa, ob - om, fm - fa, fb - fm
        steady = (np.abs(o1 - o2) < 0.15 * np.maximum(np.abs(o1), 1e-9)) & \
                 (np.abs(f1 - f2) < 0.15 * np.maximum(np.abs(f1), 1e-9))
        moved = np.abs(ob - oa) > 1e-3
    if not any_start:
        same = (fa == oa) if ints else \
            (np.abs(fa - oa) <= 1e-4 * np.maximum(np.abs(oa), 1.0))
        good &= same

    do, df = ob - oa, fb - fa
    base = good & moved & steady
    ratio = df / np.where(do == 0, np.nan, do)
    two_x = base & (df == 2 * do) if ints else base & (ratio > 1.75) & (ratio < 2.30)
    one_x = base & (df == do) if ints else base & (ratio > 0.87) & (ratio < 1.15)
    print(f"steady movers in the 30fps arm : {int(base.sum())}")
    print(f"  still 2x with the patch on   : {int(two_x.sum())}")
    print(f"  compensated (1x)             : {int(one_x.sum())}")

    idx = np.flatnonzero(two_x)
    runs = np.split(idx, np.flatnonzero(np.diff(idx) != 1) + 1)
    runs.sort(key=lambda r: -r.size)
    print(f"\n{len(runs)} contiguous runs, largest first:")
    for run in runs[:top]:
        i = run[0]
        fmt = "{:>12d}" if ints else "{:>12.4f}"
        print(f"  {lo + i * 4:08X} x{run.size:<3d} start=" + fmt.format(oa[i])
              + "  d30=" + fmt.format(do[i]) + "  d60=" + fmt.format(df[i]))
    pages = collections.Counter((lo + i * 4) >> 16 for i in idx)
    print("\nby 64K page: "
          + "  ".join(f"{page << 16:08X}:{n}" for page, n in pages.most_common(12)))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("slot", nargs="?", type=int)
    ap.add_argument("vsyncs", nargs="?", type=int)
    ap.add_argument("out", nargs="?")
    ap.add_argument("--report", metavar="NPZ", help="analyse a capture instead")
    ap.add_argument("--ints", action="store_true", help="read as int32, where clocks live")
    ap.add_argument("--any-start", action="store_true",
                    help="do not require the two arms to start equal")
    ap.add_argument("--top", type=int, default=30)
    ap.add_argument("--presets", default="off,full",
                    help="two specs, each PRESET[+group,...]")
    ap.add_argument("--leads", default=None, help="vsyncs to skip first, per arm")
    ap.add_argument("--hold", default="", help="buttons held throughout")
    args = ap.parse_args()

    if args.report:
        report(args.report, args.ints, args.top, args.any_start)
        return 0
    if args.slot is None or args.vsyncs is None or not args.out:
        ap.error("give slot, vsyncs and an output path, or --report")

    specs = args.presets.split(",", 1) if "," in args.presets else [args.presets] * 2
    leads = [int(x) for x in args.leads.split(",")] if args.leads else [0, 0]
    hold = [b for b in args.hold.split(",") if b]
    data = capture(Roo().connect(), args.slot, args.vsyncs, specs, leads, hold)
    np.savez_compressed(args.out, **data)
    print("saved", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

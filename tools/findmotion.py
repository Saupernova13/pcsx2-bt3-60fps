"""Locate a moving object anywhere in EE RAM, in two stages.

Effects and projectiles are not in the model table and not inside the fighter
struct, so they have to be found by the memory they move. Scanning all of RAM
at frame precision is far too slow, so this does it in two passes:

  1. sweep RAM reading each chunk twice back to back, a few milliseconds apart,
     and keep only the words that changed - that is per-frame state, not drift
  2. re-sample just those words at frame precision and report which ones ramp,
     oscillate or count

Run it while the thing you care about is happening and does not stop: a held
ki charge, a sustained beam, repeated blasts.

    python tools/findmotion.py
    python tools/findmotion.py --seconds 6 --lo 340000 --hi 2000000
"""

import argparse
import time

import numpy as np

import _bootstrap  # noqa: F401

from ps2ee import fighter as fx
from ps2ee.pine import Pine, PineNotRunning


def sweep(pine: Pine, lo: int, hi: int, chunk: int) -> list[int]:
    hits = []
    for base in range(lo, hi, chunk * 4):
        n = min(chunk, (hi - base) // 4)
        a = pine.read_block(base, n)
        b = pine.read_block(base, n)
        hits += [base + i * 4 for i in range(n) if a[i] != b[i]]
    return hits


def watch(pine: Pine, addrs: list[int], seconds: float):
    frames, rows = [], []
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        values = pine.read_many([fx.FRAME_COUNTER] + addrs)
        frames.append(values[0])
        rows.append(values[1:])
    seen = {}
    for f, r in zip(frames, rows):
        seen[f] = r
    order = sorted(seen)
    return np.array(order, np.int64), np.array([seen[f] for f in order], np.uint32)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--lo", type=lambda s: int(s, 16), default=0x00340000)
    ap.add_argument("--hi", type=lambda s: int(s, 16), default=0x02000000)
    ap.add_argument("--chunk", type=int, default=4096)
    ap.add_argument("--seconds", type=float, default=5.0)
    ap.add_argument("--max-watch", type=int, default=900)
    ap.add_argument("--limit", type=int, default=30)
    args = ap.parse_args()

    try:
        pine = Pine().connect()
    except PineNotRunning as exc:
        print(exc)
        return 2

    with pine:
        t0 = time.monotonic()
        addrs = sweep(pine, args.lo, args.hi, args.chunk)
        print(f"stage 1: {(args.hi - args.lo) >> 20} MB in "
              f"{time.monotonic() - t0:.1f}s, {len(addrs)} live words")
        if not addrs:
            print("nothing is changing - is the effect actually running?")
            return 1
        if len(addrs) > args.max_watch:
            print(f"  narrowing to the first {args.max_watch}")
            addrs = addrs[:args.max_watch]
        frames, words = watch(pine, addrs, args.seconds)

    adjacent = np.diff(frames) == 1
    print(f"stage 2: {len(frames)} frames, {adjacent.sum()} adjacent pairs")
    if adjacent.sum() < 10:
        print("too few adjacent pairs - lower --max-watch")
        return 1

    vals = words.view(np.float32)
    finite = np.isfinite(vals).all(axis=0) & (np.abs(vals) < 1e9).all(axis=0)
    step = np.diff(vals, axis=0)[adjacent]

    print("\n## steady ramps - a velocity, a phase, or a float timer")
    ramps = []
    for i in np.nonzero(finite)[0]:
        col = step[:, i]
        nz = col[np.abs(col) > 1e-7]
        if len(nz) < len(col) * 0.8 or nz.min() * nz.max() <= 0:
            continue
        if np.abs(nz).std() > np.abs(nz).mean() * 0.2:
            continue
        ramps.append((addrs[i], float(np.abs(nz).mean()),
                      float(vals[0, i]), float(vals[-1, i])))
    for a, d, x, y in sorted(ramps, key=lambda r: -r[1])[:args.limit]:
        print(f"  {a:08X}  {d:+.6f}/frame   {x:.4f} -> {y:.4f}")
    print(f"  ({len(ramps)} total)")

    print("\n## integer counters")
    ints = words.astype(np.int64)
    di = np.diff(ints, axis=0)[adjacent]
    for want, name in ((1, "up"), (-1, "down")):
        score = (di == want).mean(axis=0)
        for i in np.nonzero(score > 0.7)[0][:args.limit]:
            col = ints[:, i]
            if col.max() - col.min() > 0x20000:
                continue
            print(f"  {addrs[i]:08X}  {name} {score[i]*100:.0f}%  "
                  f"range {col.min()}..{col.max()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

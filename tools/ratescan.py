"""Find every field still moving at double speed, by comparing per-tick motion.

The game has no timestep, so a quantity is correct at 60fps only if it moves
*half as far per tick* as it does at 30fps - twice as many ticks then cover the
same ground per second. That makes the audit mechanical: record the same memory
tick by tick under both configurations and take the ratio of per-tick motion.

    ratio ~0.50   compensated, correct at 60fps
    ratio ~1.00   NOT compensated, running at double real speed

Per tick, not per vsync: at 30fps the game ticks every second vsync, so the
frame counter is what says when a tick happened. The metric is total absolute
variation, which behaves the same for a ramp and for an oscillator, and it is
taken per word so a struct offset comes out named.

Both runs have to be in the same *situation*, not the same state - they will
have diverged by then. A hover with the pad released is ideal: nothing depends
on how far through an animation either run happens to be.

    python tools/ratescan.py --setup air --region model
    python tools/ratescan.py --setup ground --region fighter --limit 40
"""

from __future__ import annotations

import argparse
import struct

import _bootstrap  # noqa: F401
import patchctl

from bt3.battle import FRAME_COUNTER, POS, resolve, vec
from ps2ee.roo import Roo

SETUPS = {
    # Fly up, release, and hover. Needs no input while recording.
    "air": [("Cross", (0.0, 1.0), 120), (None, None, 60)],
    "ground": [(None, None, 60)],
}


def record(roo: Roo, cfg: str, setup: str, region: str, ticks: int, who: int):
    roo.flush_input()
    roo.loadstate(1)
    patchctl.apply(roo, patchctl.PRESETS.get(cfg) or cfg.split(","), quiet=True)
    roo.frame_advance(4)
    pair = resolve(roo)[who]

    for button, stick, frames in SETUPS[setup]:
        if button or stick:
            roo.input_set(*( [button] if button else [] ), left=stick)
            roo.frame_advance(frames)
            roo.flush_input()
        else:
            roo.frame_advance(frames)

    if region == "fighter":
        base, size = pair.fighter, 0x1600
    elif region == "model":
        base, size = pair.model, 0x1000
    else:
        start, _, end = region.partition(":")
        base, size = int(start, 0), int(end, 0) - int(start, 0)
    rows, last = [], None
    while len(rows) < ticks:
        roo.frame_advance(1)
        tick = roo.read(FRAME_COUNTER)
        if tick == last:
            continue
        last = tick
        rows.append(struct.unpack(f"<{size // 4}f", roo.read_bytes(base, size)))
    height = vec(roo, pair.fighter + POS)[1]
    roo.flush_input()
    return base, rows, height


def plausible(value: float) -> bool:
    """Could this word be a float the game animates, rather than an integer?

    Most of a fighter struct is counters, bitmasks and pointers, and reading
    those as floats produces changes of 1e20 that swamp everything real. A
    world-space quantity in this game lives well inside a million, and exact
    zero is always fine.
    """
    if value != value:                      # NaN
        return False
    magnitude = abs(value)
    return magnitude == 0.0 or 1e-20 < magnitude < 1e6


def variation(rows) -> list[float]:
    """Total absolute change per word across the recording, in float terms."""
    width = len(rows[0])
    out = [0.0] * width
    real = [True] * width
    for row in rows:
        for i in range(width):
            if not plausible(row[i]):
                real[i] = False
    for a, b in zip(rows, rows[1:]):
        for i in range(width):
            if real[i]:
                out[i] += abs(b[i] - a[i])
    return [v if real[i] else -1.0 for i, v in enumerate(out)]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--setup", default="air", choices=sorted(SETUPS))
    parser.add_argument("--region", default="model",
                        help='"model", "fighter", or an explicit START:END range')
    parser.add_argument("--ticks", type=int, default=24)
    parser.add_argument("--who", type=int, default=0)
    parser.add_argument("--limit", type=int, default=30)
    parser.add_argument("--min-motion", type=float, default=1e-4)
    parser.add_argument("--reference", default="off", help="the 30fps baseline config")
    parser.add_argument("--test", default="air", help="the 60fps config under test")
    args = parser.parse_args()

    roo = Roo().connect()
    base_a, rows_a, y_a = record(roo, args.reference, args.setup, args.region,
                                 args.ticks, args.who)
    base_b, rows_b, y_b = record(roo, args.test, args.setup, args.region,
                                 args.ticks, args.who)
    var_a, var_b = variation(rows_a), variation(rows_b)

    print(f"{args.region} at {base_a:08X} / {base_b:08X}   setup={args.setup}   "
          f"{args.ticks} ticks   height {y_a:.1f} vs {y_b:.1f}")
    print("ratio 0.50 = compensated, 1.00 = still running at double speed\n")
    print(f"{'offset':>8} {'30fps/tick':>12} {'60fps/tick':>12} {'ratio':>7}")

    rows = []
    for i, (a, b) in enumerate(zip(var_a, var_b)):
        if a < 0 or b < 0:               # not a float in one of the runs
            continue
        per_a, per_b = a / (args.ticks - 1), b / (args.ticks - 1)
        if per_a < args.min_motion and per_b < args.min_motion:
            continue
        rows.append((i * 4, per_a, per_b, per_b / per_a if per_a > 1e-9 else float("inf")))

    rows.sort(key=lambda r: -abs(r[3] - 0.5))
    for offset, per_a, per_b, ratio in rows[:args.limit]:
        flag = "  <== uncompensated" if ratio > 0.8 else ""
        print(f"  +{offset:04X} {per_a:12.5f} {per_b:12.5f} {ratio:7.3f}{flag}")
    print(f"\n{len(rows)} moving words, "
          f"{sum(1 for r in rows if r[3] > 0.8)} of them uncompensated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

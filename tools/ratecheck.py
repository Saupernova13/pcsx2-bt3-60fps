"""Audit which fields are still running at double speed, by A/B-ing the frame rate.

BT3 has no timestep: it is a fixed 30Hz tick loop, and the 60fps patch simply
ticks it twice as often. So every quantity in the game is 2x until something
halves it, and the only honest test of a fix is whether the quantity moves half
as far per frame at 60fps as it does at 30.

This forces the vblank wait to 2 (30fps) and then back to 1 (60fps) from the
outside, records the same memory in both, and reports the ratio:

    ratio ~0.50   compensated - correct at 60fps
    ratio ~1.00   NOT compensated - runs at double real speed

The metric is total absolute variation per game frame, which behaves the same
way for a ramp and for an oscillator and survives dropped samples.

Hold the game in a repeatable state for the whole run - hovering with the pad
untouched is ideal, since it needs no input and never stops.

    python tools/ratecheck.py --seconds 8
    python tools/ratecheck.py --seconds 8 --region model --limit 40
"""

import argparse
import time

import numpy as np

import _bootstrap  # noqa: F401

from game import fighter as fx
from ps2ee.pine import Pine, PineNotRunning

# FUN_00264D98 copies its vblank-count argument into $s1 here. Overwriting the
# copy with a constant pins the frame rate no matter what the caller asked for.
# Deliberately not a pnach address, so a live write is not undone every frame.
RATE_SITE = 0x00264DA4
RATE_STOCK = 0x0080882D           # daddu $s1, $a0, $zero
RATE_FORCE = {30: 0x24110002,     # addiu $s1, $zero, 2
              60: 0x24110001}     # addiu $s1, $zero, 1
MODEL_TABLE = 0x0031C640


def sample(pine: Pine, base: int, words: int, seconds: float):
    frames, rows = [], []
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        frames.append(pine.read(fx.FRAME_COUNTER))
        rows.append(pine.read_block(base, words))
    return np.array(frames, np.int64), np.array(rows, np.uint32)


def per_frame_variation(frames: np.ndarray, words: np.ndarray) -> tuple[np.ndarray, int]:
    """Total absolute change per game frame, for every lane, as float32."""
    keep = {}
    for i, f in enumerate(frames):
        keep[int(f)] = i
    order = [keep[f] for f in sorted(keep)]
    frames, words = frames[order], words[order]
    span = int(frames[-1] - frames[0]) or 1
    vals = words.view(np.float32)
    vals = np.where(np.isfinite(vals) & (np.abs(vals) < 1e9), vals, 0.0)
    return np.abs(np.diff(vals, axis=0)).sum(axis=0) / span, span


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fighter", type=int, default=0)
    ap.add_argument("--region", choices=("fighter", "model"), default="fighter")
    ap.add_argument("--words", type=lambda s: int(s, 0), default=None)
    ap.add_argument("--seconds", type=float, default=8.0)
    ap.add_argument("--limit", type=int, default=30)
    ap.add_argument("--floor", type=float, default=1e-4,
                    help="ignore lanes quieter than this per frame at 30fps")
    args = ap.parse_args()

    try:
        pine = Pine().connect()
    except PineNotRunning as exc:
        print(exc)
        return 2

    with pine:
        entity = fx.bases(pine)[args.fighter]
        if args.region == "fighter":
            base, words = entity, args.words or 0x1600 // 4
        else:
            base = pine.read(MODEL_TABLE + pine.read(entity + fx.MODEL_ID) * 4)
            words = args.words or 0x1000 // 4
        print(f"{args.region} @ {base:08X}, {words} words, {args.seconds:.0f}s each way")

        try:
            pine.write(RATE_SITE, RATE_FORCE[30])
            time.sleep(0.4)
            f30, w30 = sample(pine, base, words, args.seconds)
            pine.write(RATE_SITE, RATE_FORCE[60])
            time.sleep(0.4)
            f60, w60 = sample(pine, base, words, args.seconds)
        finally:
            pine.write(RATE_SITE, RATE_STOCK)
            back = pine.read(RATE_SITE)
            print("frame rate restored" if back == RATE_STOCK
                  else f"FRAME RATE NOT RESTORED - {RATE_SITE:08X} is {back:08X}")

    v30, s30 = per_frame_variation(f30, w30)
    v60, s60 = per_frame_variation(f60, w60)
    print(f"30fps: {s30} frames    60fps: {s60} frames\n")

    live = v30 > args.floor
    ratio = np.where(live, v60 / np.maximum(v30, 1e-12), np.nan)
    rows = [(i, float(ratio[i]), float(v30[i]), float(v60[i]))
            for i in np.nonzero(live)[0]]
    if not rows:
        print("nothing moved at 30fps - put the game in a state where the "
              "symptom is happening, and keep it there for the whole run")
        return 1

    bad = sorted((r for r in rows if r[1] > 0.75), key=lambda r: -r[2])
    good = sorted((r for r in rows if r[1] <= 0.75), key=lambda r: -r[2])
    for title, group in (("NOT COMPENSATED - same movement per frame at 60fps", bad),
                         ("compensated - roughly half per frame at 60fps", good)):
        print(f"## {title}  ({len(group)})")
        for i, r, a, b in group[:args.limit]:
            print(f"  +{i*4:04X}  {base + i*4:08X}  ratio {r:4.2f}   "
                  f"30fps {a:.5f}/frame   60fps {b:.5f}/frame")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

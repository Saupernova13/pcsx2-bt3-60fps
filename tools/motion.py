"""Record a fighter and its model while it moves, then find what integrates.

Everything in this game is 2x unless it has been halved by hand, so the way to
fix a motion symptom is to find the field that carries it and the constant that
drives it. Guessing from static analysis has a poor record here; this measures
instead.

Capture arms on real movement so the window belongs to the player rather than
to a timer, and the raw samples are saved so a new hypothesis does not cost
another play session.

    python tools/motion.py --capture work/captures/airborne.npz --seconds 25
    python tools/motion.py --analyse work/captures/airborne.npz
"""

import argparse
import pathlib
import struct
import time

import numpy as np

import _bootstrap  # noqa: F401

from game import fighter as fx
from ps2ee.pine import Pine, PineNotRunning

MODEL_TABLE = 0x0031C640
MODEL_WORDS = 0x1000 // 4
POS = 0x15A0            # fighter position, from the write breakpoint in docs/findings/


def as_f32(words: np.ndarray) -> np.ndarray:
    return words.view(np.float32)


def resolve(pine: Pine, index: int):
    base = fx.bases(pine)[index]
    model = pine.read(MODEL_TABLE + pine.read(base + fx.MODEL_ID) * 4)
    return base, model


def capture(pine: Pine, index: int, seconds: float, arm_timeout: float):
    base, model = resolve(pine, index)
    print(f"fighter {index} @ {base:08X}   model @ {model:08X}")

    def position():
        return tuple(pine.read_block(base + POS, 3))

    print(f"  armed - waiting up to {arm_timeout:.0f}s for the fighter to move ...",
          flush=True)
    start, give_up = position(), time.monotonic() + arm_timeout
    while time.monotonic() < give_up:
        if position() != start:
            break
    else:
        raise RuntimeError("nothing moved - wrong fighter index?")
    print(f"  moving, recording for {seconds:.0f}s", flush=True)

    frames, rows = [], []
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        frames.append(pine.read(fx.FRAME_COUNTER))
        rows.append(pine.read_block(base, 0x1600 // 4)
                    + pine.read_block(model, MODEL_WORDS))
    return base, model, np.array(frames, np.int64), np.array(rows, np.uint32)


def consecutive(frames: np.ndarray, words: np.ndarray):
    """One row per game frame, plus a mask of which rows are one frame apart."""
    keep = {}
    for i, f in enumerate(frames):
        keep[int(f)] = i
    order = [keep[f] for f in sorted(keep)]
    frames, words = frames[order], words[order]
    return frames, words, (frames[1:] - frames[:-1]) == 1


def report(path: pathlib.Path, limit: int):
    data = np.load(path)
    base, model = int(data["base"][0]), int(data["model"][0])
    frames, words, adjacent = consecutive(data["frames"], data["words"])
    n_fighter = 0x1600 // 4
    print(f"# {len(frames)} frames, {adjacent.sum()} consecutive pairs")
    print(f"# fighter {base:08X} words 0..{n_fighter}, model {model:08X} after that\n")
    if adjacent.sum() < 16:
        print("too few consecutive pairs to analyse"); return

    vals = as_f32(words)
    step = vals[1:] - vals[:-1]
    finite = np.isfinite(vals).all(axis=0) & (np.abs(vals) < 1e9).all(axis=0)
    step = step[adjacent]
    moved = np.abs(step) > 1e-6

    def label(i):
        if i < n_fighter:
            return f"fighter+{i*4:04X}  {base + i*4:08X}"
        j = i - n_fighter
        return f"model+{j*4:04X}    {model + j*4:08X}"

    # A ramp: same sign every frame and a near-constant size. Velocity, a phase
    # angle, or a timer counting in floats.
    print("## steady ramps (constant delta, one sign)")
    hits = []
    for i in np.nonzero(finite & (moved.mean(axis=0) > 0.8))[0]:
        d = step[moved[:, i], i]
        if d.min() * d.max() <= 0:
            continue
        if np.abs(d).std() > np.abs(d).mean() * 0.2:
            continue
        hits.append((i, float(np.abs(d).mean()), float(vals[0, i]), float(vals[-1, i])))
    for i, d, a, b in sorted(hits, key=lambda h: -h[1])[:limit]:
        print(f"  {label(i)}  delta {d:+.6f}/frame   {a:.4f} -> {b:.4f}")
    print(f"  ({len(hits)} total)\n")

    # An oscillator: crosses its own mean repeatedly. A hover bob or a spin.
    print("## oscillators (repeated mean crossings)")
    hits = []
    for i in np.nonzero(finite & (moved.mean(axis=0) > 0.5))[0]:
        col = vals[:, i]
        centred = col - col.mean()
        crossings = int((np.diff(np.sign(centred)) != 0).sum())
        if crossings >= 4 and col.std() > 1e-4:
            hits.append((i, crossings, float(col.min()), float(col.max())))
    for i, c, lo, hi in sorted(hits, key=lambda h: -h[1])[:limit]:
        period = 2.0 * len(vals) / c
        print(f"  {label(i)}  {c} crossings, period ~{period:.1f} frames, "
              f"{lo:.4f} .. {hi:.4f}")
    print(f"  ({len(hits)} total)\n")

    # Integer counters, up or down, one per frame.
    print("## integer counters (+/-1 per frame)")
    ints = words.astype(np.int64)
    d = ints[1:][adjacent] - ints[:-1][adjacent]
    for direction, want in (("up", 1), ("down", -1)):
        score = (d == want).mean(axis=0)
        for i in np.nonzero(score > 0.6)[0][:limit]:
            col = ints[:, i]
            if col.max() - col.min() > 0x10000:
                continue
            print(f"  {label(i)}  {direction} {score[i]*100:.0f}% of frames, "
                  f"range {col.min()} .. {col.max()}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--capture", metavar="FILE")
    ap.add_argument("--analyse", metavar="FILE")
    ap.add_argument("--fighter", type=int, default=0)
    ap.add_argument("--seconds", type=float, default=25.0)
    ap.add_argument("--arm-timeout", type=float, default=300.0)
    ap.add_argument("--limit", type=int, default=25)
    args = ap.parse_args()

    if args.analyse:
        report(pathlib.Path(args.analyse), args.limit)
        return 0
    if not args.capture:
        ap.error("give --capture FILE or --analyse FILE")

    try:
        pine = Pine().connect()
    except PineNotRunning as exc:
        print(exc)
        return 2
    with pine:
        base, model, frames, rows = capture(pine, args.fighter, args.seconds,
                                            args.arm_timeout)
    out = pathlib.Path(args.capture)
    out.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(out, frames=frames, words=rows,
                        base=np.array([base], np.uint32),
                        model=np.array([model], np.uint32))
    print(f"  saved {len(frames)} samples to {out}")
    report(out, args.limit)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Find countdown timers in a saved fighter trace, at byte granularity.

Scanning 32-bit words only is how a tap window gets missed: a one-byte counter
sitting in any lane but the lowest makes its containing word drop by 256 or
65536 per frame, so a "minus one per frame" test never fires. This re-reads a
capture as u8, u16 and u32 and reports every lane that ticks down.

    python tools/countdown.py work/captures/grabs.npz
    python tools/countdown.py work/captures/grabs.npz --width 8 --min-run 4
"""

import argparse

import numpy as np

import _bootstrap  # noqa: F401

WIDTHS = {8: np.uint8, 16: np.uint16, 32: np.uint32}


def per_frame(frames: np.ndarray, words: np.ndarray):
    """One row per distinct game frame, in frame order."""
    order = np.argsort(frames, kind="stable")
    frames, words = frames[order], words[order]
    keep = np.concatenate([frames[1:] != frames[:-1], [True]])   # last of each frame
    return frames[keep], words[keep]


def countdowns(frames: np.ndarray, values: np.ndarray, min_run: int, max_peak: int):
    """Lanes that decrease by exactly one across consecutive frames.

    Returns (lane, number of runs, longest run, peak value at a run start).
    """
    consecutive = (frames[1:] - frames[:-1]) == 1
    steps = values[1:].astype(np.int64) - values[:-1].astype(np.int64)
    ticking = consecutive[:, None] & (steps == -1)

    hits = []
    for lane in np.nonzero(ticking.any(axis=0))[0]:
        column = ticking[:, lane]
        runs, longest, peaks, run = 0, 0, [], 0
        for i, on in enumerate(column):
            if on:
                if run == 0:
                    peaks.append(int(values[i, lane]))
                run += 1
            else:
                if run >= min_run:
                    runs, longest = runs + 1, max(longest, run)
                else:
                    if peaks:
                        peaks.pop()
                run = 0
        if run >= min_run:
            runs, longest = runs + 1, max(longest, run)
        elif peaks:
            peaks.pop()
        if runs and peaks and max(peaks) <= max_peak:
            hits.append((int(lane), runs, longest, max(peaks)))
    return hits


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("capture")
    ap.add_argument("--width", type=int, choices=sorted(WIDTHS), action="append",
                    help="repeatable; default is all three")
    ap.add_argument("--min-run", type=int, default=3)
    ap.add_argument("--max-peak", type=int, default=240,
                    help="ignore lanes whose runs start above this - a frame clock "
                         "ticks down forever and is not a window")
    ap.add_argument("--limit", type=int, default=40)
    args = ap.parse_args()

    data = np.load(args.capture)
    frames, words = per_frame(data["frames"], data["words"])
    base, lo = int(data["base"][0]), int(data["lo"][0])
    raw = words.view(np.uint8) if words.dtype != np.uint8 else words
    print(f"# {len(frames)} distinct frames, fighter+{lo:03X} at {base + lo:08X}")

    for width in args.width or sorted(WIDTHS):
        view = raw.view(WIDTHS[width])
        hits = countdowns(frames, view, args.min_run, args.max_peak)
        print(f"\n## u{width}: {len(hits)} lanes tick down "
              f"at least {args.min_run} frames in a row")
        for lane, runs, longest, peak in sorted(hits, key=lambda h: (-h[1], -h[3]))[:args.limit]:
            off = lo + lane * (width // 8)
            print(f"  {base + off:08X}  fighter+{off:04X}  {runs:>4} runs  "
                  f"longest {longest:>3}  peak {peak}")
        if len(hits) > args.limit:
            print(f"  ... {len(hits) - args.limit} more")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

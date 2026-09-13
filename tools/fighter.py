"""Read live fighters, and find the frame counters inside them.

At 60fps every timer that counts loop iterations expires in half the real time
it used to, which is what breaks combo windows and double-taps. ``--timers``
finds those directly: sample a fighter repeatedly, and report every field that
moves by exactly one per game frame. That is the definition of a frame counter,
so the list it prints is the list of things the patch has to compensate for.

    python tools/fighter.py --info
    python tools/fighter.py --timers --seconds 4
    python tools/fighter.py --snap idle
    python tools/fighter.py --snap holding-x --against idle
"""

import argparse
import json
import pathlib
import time

import _bootstrap  # noqa: F401

from game import config, fighter as fx
from ps2ee.pine import Pine, PineNotRunning

SNAPS = config.WORK / "fighter-snaps"


def plausible_counter(values: list[int]) -> bool:
    """Rule out floats and pointers, which dominate the struct."""
    return all(-0x100000 < v < 0x100000 for v in values)


def find_timers(pine: Pine, index: int, seconds: float, threshold: float):
    """Fields that move one per frame, and how reliably.

    Scored over consecutive sample pairs rather than by fitting the whole run,
    because a timer that resets mid-capture is still a timer - it just breaks
    a global fit.
    """
    base = fx.bases(pine)[index]
    samples: list[tuple[int, list[int]]] = []
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        frame = pine.read(fx.FRAME_COUNTER)
        words = fx.read(pine, base, index).words
        samples.append((frame, words))
    if len(samples) < 3:
        raise RuntimeError(f"only {len(samples)} samples - raise --seconds")

    n_words = len(samples[0][1])
    down = [0] * n_words
    up = [0] * n_words
    pairs = 0
    for (fa, wa), (fb, wb) in zip(samples, samples[1:]):
        delta = fb - fa
        if delta <= 0:
            continue                    # game paused between samples
        pairs += 1
        for i in range(n_words):
            change = wb[i] - wa[i]
            if change == -delta:
                down[i] += 1
            elif change == delta:
                up[i] += 1

    hits = []
    for i in range(n_words):
        best, direction = max((down[i], "down"), (up[i], "up"))
        if pairs and best / pairs >= threshold:
            series = [w[i] for _, w in samples]
            if plausible_counter(series):
                hits.append((i * 4, direction, best / pairs, min(series), max(series)))
    return base, pairs, len(samples), hits


def by_frame(samples):
    """Collapse over-sampling into one value per game frame."""
    out = {}
    for frame, words in samples:
        out[frame] = words
    return [out[f] for f in sorted(out)], sorted(out)


def find_countdowns(samples, min_run: int):
    """Fields that step down one per frame and then reset.

    That is the shape of a timing window: something sets it to N on an event
    and it ticks to zero. The peak value is the window length in frames, which
    at 60fps is half the real time it was authored for - so the peaks this
    prints are the numbers a fix has to double.
    """
    frames, order = by_frame(samples)
    if len(frames) < min_run + 1:
        return []
    n_words = min(len(w) for w in frames)
    hits = []
    for i in range(n_words):
        series = [w[i] for w in frames]
        if not all(-0x10000 < v < 0x10000 for v in series):
            continue
        runs, peaks, run, peak = 0, [], 0, series[0]
        for a, b, fa, fb in zip(series, series[1:], order, order[1:]):
            if fb - fa == 1 and b == a - 1:
                if run == 0:
                    peak = a
                run += 1
            else:
                if run >= min_run:
                    runs += 1
                    peaks.append(peak)
                run = 0
        if run >= min_run:
            runs, peaks = runs + 1, peaks + [peak]
        if runs:
            hits.append((i * 4, runs, max(peaks), min(series), max(series)))
    return hits


def snap_path(tag: str):
    return SNAPS / f"{tag}.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--port", type=int, default=28011)
    parser.add_argument("--fighter", type=int, default=0, help="index into the list")
    parser.add_argument("--info", action="store_true")
    parser.add_argument("--timers", action="store_true",
                        help="find fields that move one per frame")
    parser.add_argument("--seconds", type=float, default=4.0)
    parser.add_argument("--threshold", type=float, default=0.7,
                        help="fraction of samples that must agree")
    parser.add_argument("--trace", action="store_true",
                        help="find countdown timers in a byte range of the fighter")
    parser.add_argument("--range", default="0-1600", metavar="LO-HI",
                        help="hex byte range within the fighter (default the whole struct)")
    parser.add_argument("--armed", action="store_true",
                        help="wait for the first button press before recording")
    parser.add_argument("--arm-timeout", type=float, default=300.0)
    parser.add_argument("--min-run", type=int, default=3,
                        help="frames a field must tick down to count as a timer")
    parser.add_argument("--save", metavar="FILE",
                        help="write the raw trace samples so they can be re-analysed "
                             "offline instead of asking the player for another run")
    parser.add_argument("--watch", metavar="OFFSETS",
                        help="comma-separated hex fighter offsets to sample at full "
                             "rate; prefix one with @ for an absolute EE address")
    parser.add_argument("--snap", metavar="TAG", help="save every fighter's struct")
    parser.add_argument("--against", metavar="TAG", help="diff --snap against this one")
    parser.add_argument("--limit", type=int, default=60)
    args = parser.parse_args()

    try:
        pine = Pine(port=args.port).connect()
    except PineNotRunning as exc:
        print(exc)
        return 2

    with pine:
        if args.info or not (args.timers or args.snap):
            root = fx.manager(pine)
            all_bases = fx.bases(pine)
            print(f"manager {root:08X}   {len(all_bases)} fighters   "
                  f"stride {fx.STRIDE:#x}")
            for i, base in enumerate(all_bases):
                f = fx.read(pine, base, i, size=0x0100)
                print(f"  [{i}] {base:08X}  pad={f.i32(fx.PAD_INDEX)}  "
                      f"slot={f.i32(fx.SLOT_ID)}  model_id={f.i32(fx.MODEL_ID)}")

        if args.timers:
            base, pairs, n, hits = find_timers(
                pine, args.fighter, args.seconds, args.threshold)
            print(f"\n# fighter {args.fighter} @ {base:08X}: {n} samples, "
                  f"{pairs} usable pairs")
            print(f"# {len(hits)} fields moving one per frame\n")
            for off, direction, score, lo, hi in sorted(hits,
                                                        key=lambda h: -h[2])[:args.limit]:
                print(f"  +{off:04X}  {direction:<4} {score*100:5.1f}%  "
                      f"range {lo} .. {hi}")
            if len(hits) > args.limit:
                print(f"  ... {len(hits) - args.limit} more")

        if args.trace:
            lo, hi = (int(x, 16) for x in args.range.split("-"))
            base = fx.bases(pine)[args.fighter]
            print(f"tracing {base + lo:08X}-{base + hi:08X} "
                  f"(fighter +{lo:03X}..+{hi:03X}) for {args.seconds}s")

            if args.armed:
                # Recording on a fixed timer means the capture is already half
                # over by the time anyone has read the instructions. Wait for a
                # real press instead, so the window belongs to the player.
                print(f"  armed - waiting up to {args.arm_timeout:.0f}s for a "
                      f"button press ...", flush=True)
                give_up = time.monotonic() + args.arm_timeout
                while time.monotonic() < give_up:
                    if (pine.read(base + fx.NEWPRESS_A)
                            or pine.read(base + fx.NEWPRESS_B)):
                        break
                else:
                    print("  no press seen - is this the right fighter index?")
                    return 1
                print("  press seen, recording", flush=True)

            samples = []
            presses = 0
            deadline = time.monotonic() + args.seconds
            while time.monotonic() < deadline:
                frame = pine.read(fx.FRAME_COUNTER)
                words = pine.read_block(base + lo, (hi - lo) // 4)
                samples.append((frame, words))
                if lo <= fx.NEWPRESS_A < hi and words[(fx.NEWPRESS_A - lo) // 4]:
                    presses += 1
            if args.save:
                import numpy as np
                out = pathlib.Path(args.save)
                out.parent.mkdir(parents=True, exist_ok=True)
                np.savez_compressed(
                    out,
                    frames=np.array([f for f, _ in samples], dtype=np.int64),
                    words=np.array([w for _, w in samples], dtype=np.uint32),
                    base=np.array([base], dtype=np.uint32),
                    lo=np.array([lo], dtype=np.uint32),
                )
                print(f"  saved {len(samples)} samples to {out}")

            frames, _ = by_frame(samples)
            hits = find_countdowns(samples, args.min_run)
            print(f"\n# {len(samples)} samples over {len(frames)} distinct frames")
            print(f"# {len(hits)} fields tick down at least {args.min_run} frames "
                  f"in a row\n")
            for off, runs, peak, mn, mx in sorted(hits, key=lambda h: -h[1])[:args.limit]:
                print(f"  {base + lo + off:08X}  fighter+{lo + off:03X}  "
                      f"{runs:>3} countdowns  peak {peak:>5}  range {mn} .. {mx}")

        if args.watch:
            base = fx.bases(pine)[args.fighter]
            spec = [x.strip() for x in args.watch.split(",")]
            # An absolute address lets the physical pad be watched next to the
            # fighter's copy of it, which separates "the press never arrived"
            # from "it arrived and nothing opened".
            addrs = [int(x[1:], 16) if x.startswith("@") else base + int(x, 16)
                     for x in spec]
            labels = [x if x.startswith("@") else f"+{int(x, 16):04X}" for x in spec]
            print("watching " + "  ".join(labels))
            if args.armed:
                print(f"  armed - waiting up to {args.arm_timeout:.0f}s for a press ...",
                      flush=True)
                give_up = time.monotonic() + args.arm_timeout
                while time.monotonic() < give_up:
                    if (pine.read(base + fx.NEWPRESS_A)
                            or pine.read(base + fx.NEWPRESS_B)):
                        break
                else:
                    print("  no press seen")
                    return 1
                print("  press seen, recording", flush=True)

            seen, last, first = [], None, None
            deadline = time.monotonic() + args.seconds
            while time.monotonic() < deadline:
                values = pine.read_many([fx.FRAME_COUNTER] + addrs)
                frame, values = values[0], values[1:]
                if first is None:
                    first = frame
                # Only changes matter; a full log at this rate is unreadable.
                if values != last:
                    seen.append((frame - first, values))
                    last = values

            print(f"\n# {len(seen)} changes over {frame - first} frames\n")
            header = "  frame  " + "  ".join(f"{l:<9}" for l in labels)
            print(header)
            for rel, values in seen[:args.limit * 4]:
                print(f"  {rel:>5}  " + "  ".join(f"{v:08X}" for v in values))
            if len(seen) > args.limit * 4:
                print(f"  ... {len(seen) - args.limit * 4} more changes")

        if args.snap:
            SNAPS.mkdir(parents=True, exist_ok=True)
            data = {
                "frame": pine.read(fx.FRAME_COUNTER),
                "fighters": [f.words for f in fx.read_all(pine)],
            }
            snap_path(args.snap).write_text(json.dumps(data), newline="\n")
            print(f"saved {args.snap} ({len(data['fighters'])} fighters, "
                  f"frame {data['frame']})")

            if args.against:
                other = json.loads(snap_path(args.against).read_text())
                print(f"\n# {args.against} -> {args.snap}  "
                      f"({data['frame'] - other['frame']} frames apart)")
                for i, (now, was) in enumerate(zip(data["fighters"], other["fighters"])):
                    diffs = [(j * 4, was[j], now[j])
                             for j in range(min(len(now), len(was))) if now[j] != was[j]]
                    print(f"\n  fighter {i}: {len(diffs)} fields differ")
                    for off, a, b in diffs[:args.limit]:
                        print(f"    +{off:04X}  {a:>11} -> {b:<11}  "
                              f"({a:08X} -> {b:08X})")
                    if len(diffs) > args.limit:
                        print(f"    ... {len(diffs) - args.limit} more")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

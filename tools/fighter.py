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
import time

import _bootstrap  # noqa: F401

from ps2ee import config, fighter as fx
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
                      f"slot={f.i32(fx.SLOT_ID)}  model={f.u32(fx.MODEL_PTR):08X}")

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

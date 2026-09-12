"""Time a multi-hit attack by its damage schedule, and optionally by the screen.

The damage readout at 0033371C moves in exact integers, so reading it once per
vsync says precisely when each hit lands - no screenshots, no threshold, no
sampling-grid artefacts. That is what this measures by default, and it is the
oracle that found the ki-blast bug:

    off  (30fps)   2840 4260 5680 7100 8520   every 8 vsyncs, span 32
    full (60fps)   the same five values       every 4 vsyncs, span 16

Same damage, same hit count, half the real time. A correct patch brings the
60fps span back to the 30fps span.

``--curve`` measures the other channel instead: mean screen luma every few
vsyncs, printed as a curve rather than thresholded. Use it for the launch flash
and other purely visual effects, which the damage counter cannot see. Read the
curve, do not threshold it - a fixed cutoff catches the flash and misses the
beam.

The move is Goku's Super Kamehameha, L2 + Triangle. Script input in TICKS, not
vsyncs: at 30fps the same vsync count is half as many ticks, and a press that
registers at 60fps can be too short at 30, so the move silently never fires.
The defaults here are long enough for both.

    python tools/hitclock.py --baselines
    python tools/hitclock.py --pokes "cand=0x00186358:0x3C014270"
    python tools/hitclock.py --baselines --curve
"""

from __future__ import annotations

import argparse
import pathlib
import time

import _bootstrap  # noqa: F401
import patchctl

from bt3 import config
from ps2ee.roo import Roo

DAMAGE = 0x0033371C          # the combo readout, exact integers
HITS = 0x00333724


def parse_pokes(text: str) -> list[tuple[str, list[tuple[int, int]]]]:
    """'label=ADDR:WORD;ADDR:WORD, label2=ADDR' -> runs of word writes."""
    runs = []
    for entry in (x for x in text.split(",") if x.strip()):
        label, _, rest = entry.partition("=")
        writes = []
        for token in rest.split(";"):
            addr, _, word = token.partition(":")
            writes.append((int(addr, 16), int(word, 16) if word else 0x3C014270))
        runs.append((label.strip(), writes))
    return runs


def fire(roo: Roo, groups: list[str], writes, hold: int, press: int) -> None:
    roo.flush_input()
    roo.loadstate(1)
    patchctl.apply(roo, groups, quiet=True)
    for addr, word in writes:
        if not roo.write(addr, word):
            raise SystemExit(f"poke {addr:08X} did not take")
    roo.frame_advance(4)
    roo.input_set("L2")
    roo.frame_advance(hold)
    roo.input_set("L2", "Triangle")
    roo.frame_advance(press)
    roo.input_set("L2")
    roo.flush_input()


def luma(roo: Roo, path: pathlib.Path) -> float:
    """Mean brightness of the current frame.

    The screenshot file appears before the writer has finished with it, so an
    exists() check races the capture and opening it then fails.
    """
    import numpy as np
    from PIL import Image

    if path.exists():
        path.unlink()
    roo.resume()
    roo.screenshot(path)
    for _ in range(40):
        time.sleep(0.06)
        if path.exists() and path.stat().st_size > 0:
            try:
                with Image.open(path) as image:
                    return float(np.asarray(image.convert("L").resize((96, 72)),
                                            dtype="float32").mean())
            except (OSError, PermissionError):
                pass
    return float("nan")


def schedule(roo: Roo, label: str, vsyncs: int) -> None:
    marks: list[tuple[int, int, int]] = []
    last = (roo.read(DAMAGE), roo.read(HITS))
    for v in range(1, vsyncs + 1):
        roo.frame_advance(1)
        now = (roo.read(DAMAGE), roo.read(HITS))
        if now != last:
            marks.append((v, now[1], now[0]))
            last = now
    if not marks:
        print(f"{label:<30} the move never landed")
        return
    steps = " ".join(f"{v}:h{h}:d{d}" for v, h, d in marks)
    print(f"{label:<30} hits={marks[-1][1]:2d} dmg={marks[-1][2]:5d} "
          f"first={marks[0][0]:3d} last={marks[-1][0]:3d} "
          f"span={marks[-1][0] - marks[0][0]:3d}  {steps}", flush=True)


def curve(roo: Roo, label: str, vsyncs: int, step: int) -> None:
    snaps = config.roo_snaps_dir()
    snaps.mkdir(parents=True, exist_ok=True)
    seen, done = [], 0
    for mark in range(0, vsyncs + 1, step):
        roo.frame_advance(mark - done)
        done = mark
        seen.append((mark, luma(roo, snaps / f"hc-{label.strip()}-{mark:03d}.png")))
    print(f"{label}:")
    print("  " + " ".join(f"{v:3d}" for v, _ in seen))
    print("  " + " ".join(f"{x:3.0f}" for _, x in seen), flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--pokes", default="",
                        help="label=ADDR[:WORD][;ADDR[:WORD]...] runs, each on "
                             "top of the full preset; WORD defaults to 60.0f")
    parser.add_argument("--baselines", action="store_true",
                        help="measure unpatched 30fps and patched 60fps first")
    parser.add_argument("--curve", action="store_true",
                        help="screen brightness instead of the damage schedule")
    parser.add_argument("--hold", type=int, default=48)
    parser.add_argument("--press", type=int, default=16)
    parser.add_argument("--step", type=int, default=3, help="--curve sampling")
    parser.add_argument("--vsyncs", type=int, default=110)
    args = parser.parse_args()

    runs: list[tuple[str, list[str], list]] = []
    if args.baselines:
        runs.append(("off (30fps oracle)", patchctl.PRESETS["off"], []))
        runs.append(("full (60fps)", patchctl.PRESETS["full"], []))
    runs += [(label, patchctl.PRESETS["full"], writes)
             for label, writes in parse_pokes(args.pokes)]
    if not runs:
        raise SystemExit("nothing to measure: pass --baselines or --pokes")

    roo = Roo().connect()
    for label, groups, writes in runs:
        fire(roo, groups, writes, args.hold, args.press)
        if args.curve:
            curve(roo, label, args.vsyncs, args.step)
        else:
            schedule(roo, label, args.vsyncs)
    roo.resume()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

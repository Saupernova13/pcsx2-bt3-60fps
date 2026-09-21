"""Score a group set by how far its picture drifts from the 30fps arm.

A desynchronised cinematic cannot be scored by duration - both arms can enter
and leave the same state on the same vsync and still show different frames in
between. What differs is WHAT IS ON SCREEN at a given real time, so this turns
that into one number: the mean absolute pixel difference against the first
preset, at a few fixed vsyncs, with each arm frame-stepped from the same state.

It is exactly reproducible. Pass the reference preset twice and the second copy
must score 0.00; if it does not, something in the setup is not deterministic
and no other number in the run means anything.

`--band` crops to a horizontal slice before scoring, which matters more than it
sounds: a whole frame is dominated by two fighters and a stadium crowd, so a
blimp moving at the wrong speed moves the score by almost nothing until the
fighters are cropped out of it.

    python tools/drift.py --slot 3 --press R3 --marks 39,65,91,130 \
        --presets off off "60FPS - battle" shipped full
    python tools/drift.py --slot 4 --marks 90,180,270 --band 0.07,0.42 \
        --presets off full "full+60FPS - stage animation"
"""

from __future__ import annotations

import argparse
import time

# Before numpy and PIL: until this has run, tools/ is at the front of
# sys.path and shadows the stdlib. See tools/_bootstrap.py.
import _bootstrap  # noqa: F401

import numpy as np
from PIL import Image

import patchctl
from game import config
from ps2ee.roo import Roo

SCORE_SIZE = (240, 168)


def groups(spec: str) -> list[str]:
    preset, _, extra = spec.partition("+")
    base = patchctl.PRESETS.get(preset, [] if preset == "off" else [preset])
    return list(base) + [g for g in extra.split(",") if g]


def grab(roo: Roo, path, band) -> np.ndarray:
    """A paused VM queues screenshots; frame_advance(1) is what flushes them."""
    if path.exists():
        path.unlink()
    roo.screenshot(str(path))
    roo.frame_advance(1)
    for _ in range(80):
        if path.exists():
            size = path.stat().st_size
            time.sleep(0.05)
            if path.exists() and path.stat().st_size == size and size:
                image = Image.open(path).convert("RGB")
                if band:
                    width, height = image.size
                    image = image.crop((0, int(height * band[0]),
                                        width, int(height * band[1])))
                return np.asarray(image.resize(SCORE_SIZE, Image.LANCZOS),
                                  dtype=np.float32)
        time.sleep(0.05)
    raise SystemExit("the screenshot never landed - is the VM running?")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--slot", type=int, required=True)
    parser.add_argument("--press", default=None)
    parser.add_argument("--frames", type=int, default=8)
    parser.add_argument("--lead", type=int, default=8)
    parser.add_argument("--marks", required=True, help="vsyncs, comma separated")
    parser.add_argument("--band", default=None,
                        help="crop to TOP,BOTTOM as fractions of the frame")
    parser.add_argument("--presets", nargs="+", required=True)
    args = parser.parse_args()

    marks = [int(m) for m in args.marks.split(",")]
    band = tuple(float(v) for v in args.band.split(",")) if args.band else None
    snaps = config.roo_snaps_dir()
    snaps.mkdir(parents=True, exist_ok=True)
    raw = snaps / "_drift.png"

    roo = Roo().connect()
    reference = None
    for spec in args.presets:
        roo.flush_input()
        roo.loadstate(args.slot)
        patchctl.apply(roo, groups(spec), quiet=True)
        roo.frame_advance(args.lead)
        if args.press:
            roo.input_press(args.press, frames=args.frames)
        shots, at = [], 0
        for mark in marks:
            roo.frame_advance(max(0, mark - at - 1))
            shots.append(grab(roo, raw, band))
            at = mark
        roo.flush_input()
        if reference is None:
            reference = shots
            print(f"{spec:36s} (reference)")
            continue
        per = [float(np.abs(a - b).mean()) for a, b in zip(shots, reference)]
        print(f"{spec:36s} drift {np.mean(per):6.2f}   " +
              " ".join(f"{m}v:{d:5.1f}" for m, d in zip(marks, per)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

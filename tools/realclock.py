"""Time and photograph a move in REAL time, with the game running free.

This exists because the obvious instrument does not work. A screenshot needs a
RUNNING VM, so any loop of "frame-advance N, screenshot" lets the game run a few
uncontrolled ticks at every sample - about five here, and 181 on the first one
after a state load. Every duration measured that way is fiction, and worse, the
error is invisible: the runs are reproducible, they are just reproducibly wrong.

Running free and sampling on the wall clock has no such problem. Each sample is
a real instant, so a 30fps run and a 60fps run line up on real time and can be
compared directly - which is the comparison a player is making when they say
something is too fast.

    python tools/realclock.py --slot 8 --presets off full
    python tools/realclock.py --slot 8 --presets full --sheet work/ult.png

--sheet tiles the frames into one image, labelled in seconds. Read the picture:
a numeric trace tells you when something changed, the tiles tell you what.
"""

from __future__ import annotations

import argparse
import time

import numpy as np
from PIL import Image, ImageDraw

import _bootstrap  # noqa: F401
import patchctl

from ps2ee import config
from ps2ee.roo import Roo


def parse_pokes(text: str) -> list[tuple[int, int]]:
    out = []
    for token in text.replace(",", " ").split():
        addr, _, word = token.partition(":")
        out.append((int(addr, 16), int(word, 16)))
    return out


def capture(roo: Roo, preset: str, slot: int, pokes, shots: int, cadence: float):
    """Run the state free and fire off one screenshot every `cadence` seconds."""
    roo.flush_input()
    roo.loadstate(slot)
    time.sleep(1.0)
    patchctl.apply(roo, patchctl.PRESETS[preset], quiet=True)
    roo.flush_input()
    roo.loadstate(slot)          # reload, so the patch is live from the first frame
    time.sleep(1.0)
    for addr, word in pokes:
        if not roo.write(addr, word):
            raise SystemExit(f"poke {addr:08X} did not take")

    snaps = config.roo_snaps_dir()
    snaps.mkdir(parents=True, exist_ok=True)
    paths = [snaps / f"realclock-{i:03d}.png" for i in range(shots)]
    for path in paths:
        if path.exists():
            try:
                path.unlink()
            except OSError:
                pass

    roo.resume()
    start = time.monotonic()
    for i, path in enumerate(paths):
        while time.monotonic() < start + i * cadence:
            time.sleep(0.003)
        roo.screenshot(path)
    time.sleep(1.5)
    roo.pause()

    frames = []
    for path in paths:
        image = None
        for _ in range(20):
            if path.exists() and path.stat().st_size > 0:
                try:
                    opened = Image.open(path)
                    opened.load()
                    image = opened.convert("RGB")
                    break
                except (OSError, PermissionError):
                    time.sleep(0.05)
            else:
                time.sleep(0.05)
        frames.append(image)
    return frames


def luma(image) -> float:
    if image is None:
        return float("nan")
    return float(np.asarray(image.convert("L").resize((80, 60)),
                            dtype="float32").mean())


def sheet(frames, cadence: float, path: str) -> None:
    tiles = [f for f in frames if f is not None]
    if not tiles:
        raise SystemExit("nothing captured")
    cols, width = 6, 300
    height = int(width * tiles[0].height / tiles[0].width)
    rows = (len(frames) + cols - 1) // cols
    out = Image.new("RGB", (cols * width, rows * height), "black")
    draw = ImageDraw.Draw(out)
    for i, frame in enumerate(frames):
        x, y = (i % cols) * width, (i // cols) * height
        if frame is not None:
            out.paste(frame.resize((width, height)), (x, y))
        draw.text((x + 6, y + 6), f"{i * cadence:.2f}s", fill="yellow")
    out.save(path)
    print(f"  wrote {path}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--slot", type=int, default=8)
    parser.add_argument("--presets", nargs="+", default=["off", "full"])
    parser.add_argument("--pokes", default="")
    parser.add_argument("--shots", type=int, default=30)
    parser.add_argument("--cadence", type=float, default=0.10)
    parser.add_argument("--sheet", default=None,
                        help="tile the LAST preset's frames into this file")
    args = parser.parse_args()

    roo = Roo().connect()
    pokes = parse_pokes(args.pokes)
    header = " ".join(f"{i * args.cadence:4.1f}" for i in range(args.shots))
    print(f"  {'preset':<10} {header}")
    frames = []
    for preset in args.presets:
        frames = capture(roo, preset, args.slot, pokes, args.shots, args.cadence)
        row = " ".join("   ?" if np.isnan(v) else f"{v:4.0f}"
                       for v in (luma(f) for f in frames))
        print(f"  {preset:<10} {row}", flush=True)
    if args.sheet:
        sheet(frames, args.cadence, args.sheet)
    roo.resume()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

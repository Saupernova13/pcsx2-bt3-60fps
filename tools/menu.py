"""Drive the game's menus, so any scene can be built rather than only reloaded.

Until this existed, an A/B could only use a character, stage and loadout that
somebody had already saved. The menus answer to pad injection like anything
else, so the roster, Custom Select and Map Select are all reachable from a
script - which is how the Vegeta (Scouter) and World Tournament states were
made.

Two traps are baked in. A menu press must be HELD about eight frames or the
menu simply does not see it, and the pad needs roughly three quarters of a
second between presses. And browsing a long list one screenshot at a time is
the expensive way, so `strip` presses a button N times and returns only the
label band from each, as one tall image.

    python tools/menu.py press Start Down Down Cross --shot pause
    python tools/menu.py strip Down 10 --band 0.62,0.80 --shot rows
    python tools/menu.py --shot now shot

The roster is a grid of 15 rows: Down moves a whole row, Right moves one
character within it, and both wrap. Map Select is the same shape. Confirming a
character opens its form list, then Custom Select, then Select Color - three
Crosses takes the defaults, and Custom Select is the only way to reach a move
that is not equipped by default.
"""

from __future__ import annotations

import argparse
import time

# Before PIL: until this has run, tools/ is at the front of sys.path and
# shadows the stdlib. See tools/_bootstrap.py.
import _bootstrap  # noqa: F401

from PIL import Image

from game import config
from ps2ee.roo import Roo

HOLD_FRAMES = 8
SETTLE = 0.75


def capture(roo: Roo, path) -> Image.Image:
    """Screenshots need a RUNNING VM, and land asynchronously."""
    if path.exists():
        path.unlink()
    roo.screenshot(str(path))
    for _ in range(80):
        if path.exists():
            size = path.stat().st_size
            time.sleep(0.12)
            if path.exists() and path.stat().st_size == size and size:
                return Image.open(path).convert("RGB")
        else:
            time.sleep(0.12)
    raise SystemExit("the screenshot never landed - is the VM running?")


def press(roo: Roo, button: str, frames: int) -> None:
    roo.input_press(button, frames=frames)
    time.sleep(SETTLE)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--frames", type=int, default=HOLD_FRAMES)
    parser.add_argument("--shot", default=None, help="save a screenshot under this name")
    parser.add_argument("--wait", type=float, default=1.0, help="settle before shooting")
    parser.add_argument("--width", type=int, default=560)
    sub = parser.add_subparsers(dest="what", required=True)

    p = sub.add_parser("press", help="press buttons in order, then shoot")
    p.add_argument("buttons", nargs="+")

    p = sub.add_parser("strip", help="press one button N times, keep only the label band")
    p.add_argument("button")
    p.add_argument("count", type=int)
    p.add_argument("--band", default="0.62,0.80",
                   help="TOP,BOTTOM of the label, as fractions of the frame")

    sub.add_parser("shot", help="photograph what is on screen now")

    args = parser.parse_args()
    snaps = config.roo_snaps_dir()
    snaps.mkdir(parents=True, exist_ok=True)
    raw = snaps / "_menu.png"

    roo = Roo().connect()
    roo.resume()

    if args.what == "strip":
        top, bottom = (float(v) for v in args.band.split(","))
        bands = []
        for _ in range(args.count):
            press(roo, args.button, args.frames)
            image = capture(roo, raw)
            width, height = image.size
            band = image.crop((0, int(height * top), width, int(height * bottom)))
            band.thumbnail((520, 520), Image.LANCZOS)
            bands.append(band)
        sheet = Image.new("RGB", (max(b.width for b in bands),
                                  sum(b.height for b in bands)), (0, 0, 0))
        y = 0
        for band in bands:
            sheet.paste(band, (0, y))
            y += band.height
        out = snaps / f"{args.shot or 'strip'}.png"
        sheet.save(out, optimize=True)
        print(f"{out}  {len(bands)} bands")
        return 0

    if args.what == "press":
        for button in args.buttons:
            press(roo, button, args.frames)

    time.sleep(args.wait)
    image = capture(roo, raw)
    image.thumbnail((args.width, args.width), Image.LANCZOS)
    out = snaps / f"{args.shot or 'menu'}.png"
    image.save(out, optimize=True)
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

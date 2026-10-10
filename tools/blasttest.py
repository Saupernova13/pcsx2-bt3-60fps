"""Fire a scripted blast at both rates and time how long the beam is on screen.

A Kamehameha whites out the screen, so mean brightness says when the beam starts
and stops. Same save state, scripted input and vsync count; a vsync is real time
at either rate.

* **Script the input in ticks, not vsyncs.** A press long enough at 60fps can be
  too short at 30 and the move never comes out. The defaults suit both.
* **Check the move actually fired**, by watching damage; a blast that never
  happened looks like a very short beam.

The move is Goku's Super Kamehameha, L2 + Triangle (3 blast stock). Pause, View
Skill List shows any character's inputs.

    python tools/blasttest.py
    python tools/blasttest.py --pokes "cand=0x00186810:0x3C013F00"
"""

from __future__ import annotations

import argparse
import pathlib
import time

# Before numpy and PIL; see tools/_bootstrap.py.
import _bootstrap  # noqa: F401

import numpy as np
from PIL import Image

import patchctl

from game import config
from ps2ee.roo import Roo

DAMAGE = 0x0033371C          # the combo readout, rises as the blast connects
HITS = 0x00333724
BRIGHT = 80.0                # mean luma that means "a beam is on screen"


def brightness(roo: Roo, path: pathlib.Path) -> float:
    """Photograph the current frame and reduce it to mean luma.

    The file appears before the writer has finished, so a bare exists() check races it.
    """
    if path.exists():
        path.unlink()
    roo.resume()
    roo.screenshot(path)
    value = float("nan")
    for _ in range(40):
        time.sleep(0.10)
        if path.exists() and path.stat().st_size > 0:
            try:
                with Image.open(path) as image:
                    value = float(np.asarray(image.convert("L").resize((96, 72)),
                                             dtype=np.float32).mean())
                break
            except (OSError, PermissionError):
                pass
    roo.frame_advance(1)
    return value


def fire(roo: Roo, groups, poke, hold: int, press: int) -> None:
    roo.flush_input()
    roo.loadstate(1)
    patchctl.apply(roo, groups, quiet=True)
    if poke and not roo.write(poke[0], poke[1]):
        raise SystemExit(f"poke {poke[0]:08X} did not take")
    roo.frame_advance(4)
    roo.input_set("L2")
    roo.frame_advance(hold)
    roo.input_set("L2", "Triangle")
    roo.frame_advance(press)
    roo.input_set("L2")
    roo.frame_advance(8)
    roo.flush_input()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--pokes", default="",
                        help="label=ADDR:WORD entries, each run on top of the "
                             "shipping preset")
    parser.add_argument("--hold", type=int, default=48)
    parser.add_argument("--press", type=int, default=16)
    parser.add_argument("--step", type=int, default=4)
    parser.add_argument("--vsyncs", type=int, default=60)
    args = parser.parse_args()

    runs = [("off", patchctl.PRESETS["off"], None),
            ("full", patchctl.PRESETS["full"], None)]
    for entry in (x for x in args.pokes.split(",") if x):
        label, rest = entry.split("=")
        addr, word = rest.split(":")
        runs.append((label, patchctl.PRESETS["full"],
                     (int(addr, 0), int(word, 0))))

    snaps = config.roo_snaps_dir()
    snaps.mkdir(parents=True, exist_ok=True)
    roo = Roo().connect()
    print(f"{'configuration':<22} {'damage':>8} {'hits':>5} {'beam':>6}  window")
    for label, groups, poke in runs:
        fire(roo, groups, poke, args.hold, args.press)
        lit, done = [], 0
        for mark in range(args.step, args.vsyncs + 1, args.step):
            roo.frame_advance(mark - done)
            done = mark
            if brightness(roo, snaps / f"blast-{label}-{mark:03d}.png") > BRIGHT:
                lit.append(mark)
        window = f"{min(lit)}..{max(lit)}" if lit else "the move never fired"
        print(f"{label:<22} {roo.read(DAMAGE):8d} {roo.read(HITS):5d} "
              f"{len(lit) * args.step:6d}  {window}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

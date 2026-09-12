"""Does injected pad input actually reach the game?

Position is a bad detector for this: a fighter that does not move might have
ignored the button, or might have been in an animation that cannot be
interrupted. The game's own libpad word cannot be ambiguous - it is active low,
so a held button is a zero bit.

    python tools/padcheck.py
    python tools/padcheck.py --buttons R1 R2 --frames 30
"""

from __future__ import annotations

import argparse

import _bootstrap  # noqa: F401

from bt3.battle import PAD_INDEX, resolve
from ps2ee.roo import Roo

RAW_PAD = 0x0033381C        # libpad's own word for pad 0, active low
FIGHTER_INPUT = 0x0570      # the fighter's private copy, +0x1CC is "currently held"

BUTTONS = ["Select", "L3", "R3", "Start", "Up", "Right", "Down", "Left",
           "L2", "R2", "L1", "R1", "Triangle", "Circle", "Cross", "Square"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--slot", type=int, default=1)
    parser.add_argument("--buttons", nargs="*", default=BUTTONS)
    parser.add_argument("--frames", type=int, default=8)
    args = parser.parse_args()

    roo = Roo().connect()
    roo.flush_input()
    roo.loadstate(args.slot)
    pair = resolve(roo)[0]
    print(f"{pair}  pad={roo.read(pair.fighter + PAD_INDEX)}")

    roo.input_release()
    roo.frame_advance(4)
    idle_raw = roo.read(RAW_PAD)
    idle_cur = roo.read(pair.fighter + FIGHTER_INPUT + 0x1CC)
    print(f"idle       raw {idle_raw:08X}  fighter_cur {idle_cur:08X}")

    for button in args.buttons:
        roo.input_set(button)
        roo.frame_advance(args.frames)
        raw = roo.read(RAW_PAD)
        cur = roo.read(pair.fighter + FIGHTER_INPUT + 0x1CC)
        held = idle_raw & ~raw          # active low: a held button clears a bit
        print(f"{button:9s} raw {raw:08X}  changed {held:08X}"
              f"  fighter_cur {cur:08X}"
              f"  {'REACHED' if held or cur != idle_cur else 'no effect'}")
        roo.input_release()
        roo.frame_advance(4)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

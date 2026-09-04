"""Build the save states the A/B runs start from.

An A/B is only meaningful if both runs begin from the identical situation, and
"identical" has to include the fighter's momentum, not just its position. The
launch itself runs at whatever rate is under test, so it cannot be part of the
measured window: the state has to be cut afterwards, once the victim is already
in the air with a velocity baked in.

    python tools/mkstate.py air --slot 2      opponent launched and flying
    python work/mkstate.py --list

Slot 1 is the hand-made ground state and is never overwritten here.
"""

from __future__ import annotations

import argparse
import time

import _bootstrap  # noqa: F401
import patchctl

from ps2ee import config
from ps2ee.battle import POS, resolve, vec
from ps2ee.roo import Roo

GROUND_SLOT = 1

# A rush combo. Four hits is enough to launch; ten sends the victim into orbit,
# which leaves no room to watch the fall.
RECIPES = {
    "air": [(["Square"], 4, 12)] * 4 + [([], 0, 20)],
    "highair": [(["Square"], 4, 12)] * 7 + [([], 0, 20)],
}


def build(roo: Roo, recipe: str, slot: int) -> None:
    roo.flush_input()
    roo.loadstate(GROUND_SLOT)
    patchctl.apply(roo, patchctl.SHIPPED)
    roo.frame_advance(4)

    victim = resolve(roo)[1]
    for buttons, press, gap in RECIPES[recipe]:
        if press:
            roo.input_set(*buttons)
            roo.frame_advance(press)
        roo.input_release()
        roo.frame_advance(gap)

    before = vec(roo, victim.fighter + POS)
    roo.frame_advance(1)
    after = vec(roo, victim.fighter + POS)
    speed = sum((a - b) ** 2 for a, b in zip(after[:3], before[:3])) ** 0.5
    print(f"victim at ({after[0]:8.2f} {after[1]:8.2f} {after[2]:8.2f})"
          f"   height {-after[1]:.2f}   speed {speed:.3f}/vsync")
    if after[1] > -5.0:
        raise RuntimeError("the victim never left the ground - recipe did not connect")

    roo.savestate(slot)
    print(f"saved slot {slot}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("recipe", nargs="?", choices=sorted(RECIPES))
    parser.add_argument("--slot", type=int, default=2)
    parser.add_argument("--list", action="store_true")
    args = parser.parse_args()

    if args.list or not args.recipe:
        for path in sorted((config.pcsxroo_dir() / "sstates").glob("*.p2s")):
            print(f"{path.name}   {time.ctime(path.stat().st_mtime)}")
        return 0
    if args.slot == GROUND_SLOT:
        raise SystemExit("slot 1 is the hand-made ground state; pick another")
    build(Roo().connect(), args.recipe, args.slot)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

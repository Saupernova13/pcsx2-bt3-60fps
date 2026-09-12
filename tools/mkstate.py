"""Build the save states the A/B runs start from.

An A/B is only meaningful if both runs begin from the identical situation, and
"identical" has to include the fighter's momentum, not just its position. The
launch itself runs at whatever rate is under test, so it cannot be part of the
measured window: the state has to be cut afterwards, once the victim is already
in the air with a velocity baked in.

    python tools/mkstate.py air --slot 2       opponent launched and flying
    python tools/mkstate.py airidle --slot 3   player hovering, fully settled
    python tools/mkstate.py --list

Slot 1 is the hand-made ground state and is never overwritten here.
"""

from __future__ import annotations

import argparse
import time

import _bootstrap  # noqa: F401
import patchctl

from bt3 import config
from bt3.battle import POS, resolve, vec
from ps2ee.roo import Roo

GROUND_SLOT = 1

# Each recipe names the fighter it is about and a list of
# (buttons, press vsyncs, release vsyncs, left stick) steps.
#
# A rush combo. Four hits is enough to launch; ten sends the victim into orbit,
# which leaves no room to watch the fall.
_RUSH = (["Square"], 4, 12, None)
RECIPES = {
    "air": (1, [_RUSH] * 4 + [([], 0, 20, None)]),
    "highair": (1, [_RUSH] * 7 + [([], 0, 20, None)]),
    # The player flying up under its own power and settling into the airborne
    # idle. Cross with the stick forward is the only input that gets off the
    # ground - R1 alone does nothing - and the long release is what makes this
    # worth cutting a state for: the ascent must finish before any measurement
    # starts. The same number of vsyncs is half as many ticks at 30fps, so a run
    # that flies inside its own measurement window arrives somewhere different,
    # carrying different momentum, and every positional word then differs for
    # reasons that have nothing to do with the patch.
    "airidle": (0, [(["Cross"], 180, 300, (0.0, 1.0))]),
}


def build(roo: Roo, recipe: str, slot: int, config: str = "shipped") -> None:
    roo.flush_input()
    roo.loadstate(GROUND_SLOT)
    patchctl.apply(roo, patchctl.PRESETS.get(config) or config.split(","))
    roo.frame_advance(4)

    who, steps = RECIPES[recipe]
    victim = resolve(roo)[who]
    for buttons, press, gap, stick in steps:
        if press:
            roo.input_set(*buttons, left=stick)
            roo.frame_advance(press)
        roo.input_release()
        roo.frame_advance(gap)

    before = vec(roo, victim.fighter + POS)
    roo.frame_advance(1)
    after = vec(roo, victim.fighter + POS)
    speed = sum((a - b) ** 2 for a, b in zip(after[:3], before[:3])) ** 0.5
    # World Y is inverted: altitude is negative, the ground about -0.05.
    print(f"fighter {who} at ({after[0]:8.2f} {after[1]:8.2f} {after[2]:8.2f})"
          f"   height {-after[1]:.2f}   speed {speed:.3f}/vsync")
    if after[1] > -5.0:
        raise RuntimeError("the fighter never left the ground - recipe did not connect")

    roo.savestate(slot)
    print(f"saved slot {slot}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("recipe", nargs="?", choices=sorted(RECIPES))
    parser.add_argument("--slot", type=int, default=2)
    parser.add_argument("--list", action="store_true")
    # Which patches are live while the state is cut. It matters more than it
    # looks: a tween object carries the step it was built with, so a state cut
    # under the wrong configuration hands both arms of a later A/B a set of
    # objects that were already wrong when they were frozen.
    parser.add_argument("--config", default="shipped")
    args = parser.parse_args()

    if args.list or not args.recipe:
        for path in sorted((config.pcsxroo_dir() / "sstates").glob("*.p2s")):
            print(f"{path.name}   {time.ctime(path.stat().st_mtime)}")
        return 0
    if args.slot == GROUND_SLOT:
        raise SystemExit("slot 1 is the hand-made ground state; pick another")
    build(Roo().connect(), args.recipe, args.slot, args.config)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

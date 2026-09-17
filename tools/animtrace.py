"""Trace a move by its BEATS rather than by its pictures or its clock.

FUN_001C4638 is a leaf that returns fighter+0x974, the current animation id,
and the cinematic handlers advance by asking whether that animation has
FINISHED - `FUN_001C47A8` - not by counting ticks. So for anything scripted,
the animation ids ARE the beats, and reading one word per vsync says exactly
where two arms part company.

This is what settled issue #10. A pixel score said the Great Ape transformation
was still 34 points wrong after every group in the patch; the beat trace said
the animation ids switch on the same vsync in both arms, which moved the hunt
off "the animation is cut short" and onto the camera inside it.

    python tools/animtrace.py --slot 3 --press R3 --presets off full
    python tools/animtrace.py --slot 3 --press R3 --vsyncs 700 \
        --presets off "60FPS - battle" "60FPS - battle+60FPS - animation clock"
"""

from __future__ import annotations

import argparse

import _bootstrap  # noqa: F401

import patchctl
from game.battle import FRAME_COUNTER, resolve
from ps2ee.roo import Roo

ANIM = 0x0974
STATE = 0x0948


def groups(spec: str) -> list[str]:
    """A preset name, a bare group name, or `preset+group,group`."""
    preset, _, extra = spec.partition("+")
    base = patchctl.PRESETS.get(preset, [] if preset == "off" else [preset])
    return list(base) + [g for g in extra.split(",") if g]


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--slot", type=int, required=True)
    parser.add_argument("--press", default=None, help="button that starts the move")
    parser.add_argument("--frames", type=int, default=8, help="how long to hold it")
    parser.add_argument("--vsyncs", type=int, default=520)
    parser.add_argument("--lead", type=int, default=8, help="settle after the load")
    parser.add_argument("--fighter", type=int, default=0)
    parser.add_argument("--presets", nargs="+", required=True)
    args = parser.parse_args()

    roo = Roo().connect()
    for spec in args.presets:
        roo.flush_input()
        roo.loadstate(args.slot)
        patchctl.apply(roo, groups(spec), quiet=True)
        roo.frame_advance(args.lead)
        me = resolve(roo)[args.fighter].fighter
        if args.press:
            roo.input_press(args.press, frames=args.frames)
        started = roo.read(FRAME_COUNTER)
        beats, last = [], None
        for vsync in range(1, args.vsyncs + 1):
            roo.frame_advance(1)
            now = (roo.read(me + ANIM), roo.read(me + STATE))
            if now != last:
                beats.append((vsync, *now))
                last = now
        ticks = roo.read(FRAME_COUNTER) - started
        print(f"{spec:40s} {args.vsyncs} vsyncs = {ticks} ticks")
        print("    " + "  ".join(f"v{v}:a{a:X}/s{s}" for v, a, s in beats))
    roo.flush_input()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

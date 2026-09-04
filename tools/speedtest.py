"""The acceptance test: how far does a fighter travel in a fixed real time?

One number per situation, measured the only way that means anything - against
the same situation on the unpatched 30fps game. 1.00 is correct. 2.00 is the
bug this project exists to remove.

Everything is measured over bulk frame-advances rather than single steps,
because PCSXROO does not apply injected input on the final frame of an advance:
holding a button through 120 single steps holds it for zero frames. In one bulk
call of 120 it holds for 119, which is close enough to a held button that the
comparison is fair - both sides lose the same frame.

    python tools/speedtest.py
    python tools/speedtest.py --configs off air --cases fly dash
"""

from __future__ import annotations

import argparse
import _bootstrap  # noqa: F401
import patchctl

from ps2ee.battle import POS, norm, delta, resolve, vec
from ps2ee.roo import Roo

# (slot, who, buttons, stick, vsyncs). "who" is which fighter to measure.
CASES: dict[str, tuple] = {
    "forward":  (1, 0, [], (0.0, -1.0), 120),
    "back":     (1, 0, [], (0.0, 1.0), 120),
    "strafe":   (1, 0, [], (1.0, 0.0), 120),
    "fly":      (1, 0, [], (0.0, 1.0), 240),
    "dash":     (1, 0, ["Cross"], (0.0, 1.0), 150),
    "rush":     (1, 0, ["Square"], None, 120),
    "knockback": (2, 1, [], None, 60),
    "idle":     (1, 0, [], None, 120),
}


def run(roo: Roo, case: str, config: str) -> float:
    slot, who, buttons, stick, frames = CASES[case]
    # Before the load, not after: a button still held from the previous case
    # is read by the game on the first frame after a restore, and one stray
    # punch there changes everything that follows.
    roo.flush_input()
    roo.loadstate(slot)
    patchctl.apply(roo, patchctl.PRESETS[config], quiet=True)
    roo.frame_advance(4)

    pair = resolve(roo)[who]
    start = vec(roo, pair.fighter + POS)
    if buttons or stick:
        roo.input_set(*buttons, left=stick)
    roo.frame_advance(frames)
    roo.input_release()
    return norm(delta(vec(roo, pair.fighter + POS), start))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--cases", nargs="*", default=list(CASES))
    parser.add_argument("--configs", nargs="*", default=["shipped", "air"])
    args = parser.parse_args()

    roo = Roo().connect()
    width = max(len(c) for c in args.cases)
    header = f"{'case':<{width}} {'30fps ref':>10}"
    for config in args.configs:
        header += f" {config:>12} {'ratio':>7}"
    print(header)
    print("-" * len(header))

    for case in args.cases:
        reference = run(roo, case, "off")
        row = f"{case:<{width}} {reference:10.3f}"
        for config in args.configs:
            travelled = run(roo, case, config)
            ratio = travelled / reference if reference > 1e-3 else float("nan")
            row += f" {travelled:12.3f} {ratio:7.3f}"
        print(row)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

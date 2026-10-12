"""The acceptance test: how far does a fighter travel in a fixed real time?

One number per situation, against the same situation on the unpatched 30fps game.
1.00 is correct; 2.00 is the bug this project exists to remove.

Measured over bulk frame-advances: PCSXROO does not apply injected input on the
final frame of an advance, so single steps would hold a button for zero frames.

    python tools/speedtest.py
    python tools/speedtest.py --configs off air --cases fly dash
"""

from __future__ import annotations

import argparse
import _bootstrap  # noqa: F401
import patchctl

from game.battle import POS, norm, delta, resolve, vec
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


def run(roo: Roo, case: str, config: str) -> tuple[float, float]:
    """Return (total travelled, travelled during the second half).

    The second half is the "speed"; total distance also carries how far the fighter
    got through a wind-up, which swamps the comparison.
    """
    slot, who, buttons, stick, frames = CASES[case]
    # Before the load: a button still held from the previous case is read on the first
    # frame after a restore.
    roo.flush_input()
    roo.loadstate(slot)
    patchctl.apply(roo, patchctl.PRESETS[config], quiet=True)
    roo.frame_advance(4)

    pair = resolve(roo)[who]
    start = vec(roo, pair.fighter + POS)
    if buttons or stick:
        roo.input_set(*buttons, left=stick)
    roo.frame_advance(frames // 2)
    middle = vec(roo, pair.fighter + POS)
    if buttons or stick:
        roo.input_set(*buttons, left=stick)
    roo.frame_advance(frames - frames // 2)
    end = vec(roo, pair.fighter + POS)
    roo.input_release()
    return norm(delta(end, start)), norm(delta(end, middle))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--cases", nargs="*", default=list(CASES))
    parser.add_argument("--configs", nargs="*", default=["shipped", "air"])
    args = parser.parse_args()

    roo = Roo().connect()
    width = max(len(c) for c in args.cases)
    header = f"{'case':<{width}} {'ref total':>10} {'ref cruise':>11}"
    for config in args.configs:
        header += f" {config[:6] + ' total':>13} {config[:6] + ' cruise':>14}"
    print(header)
    print("-" * len(header))
    print("(ratios against the unpatched 30fps game; 1.000 is correct)")

    for case in args.cases:
        total, cruise = run(roo, case, "off")
        row = f"{case:<{width}} {total:10.3f} {cruise:11.3f}"
        for config in args.configs:
            t, c = run(roo, case, config)
            row += (f" {t / total if total > 1e-3 else float('nan'):13.3f}"
                    f" {c / cruise if cruise > 1e-3 else float('nan'):14.3f}")
        print(row)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

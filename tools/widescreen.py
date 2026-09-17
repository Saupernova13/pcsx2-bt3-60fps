"""Generate a widescreen group for any display aspect.

BT3's field of view lives in three words, and the third gives the rule away:

    002FE4CC   1.166667   projection scale, 7/6 at 4:3
    002FE594   298.6667   the same constant x256
    00130BF0   lui $at, 0x3F40   an INSTRUCTION - the immediate is 0.75

0.75 is 3/4, which is 1/aspect at 4:3, and PCSX2's own [Widescreen 16:9] sets
that immediate to 0x3F10 - 0.5625, which is 9/16. So the instruction carries
1/aspect and the two floats scale by aspect / (4/3), the factor by which the
horizontal field of view widens.

    python tools/widescreen.py 21:9
    python tools/widescreen.py 3440x1440 --name "Widescreen 43:18 - 3440x1440"
    python tools/widescreen.py --selftest

`lui` writes only the top 16 bits of the register, so 1/aspect is rounded to a
half-precision-sized mantissa. The tool prints that error; below about 0.2% it
is a fraction of a pixel across the screen and a trampoline to fix it would buy
nothing visible.

This does not talk to the emulator - it is arithmetic, and it runs anywhere.
"""

from __future__ import annotations

import argparse
import struct

SCALE_ADDR = 0x002FE4CC   # projection scale, 7/6 at 4:3
SCALE256_ADDR = 0x002FE594  # the same constant x256
LUI_ADDR = 0x00130BF0     # lui $at, imm -- the immediate is 1/aspect
LUI_OPCODE = 0x3C010000   # lui $at, 0x0000

STOCK_SCALE = 7.0 / 6.0   # what 002FE4CC holds at 4:3
STOCK_ASPECT = 4.0 / 3.0


def f32(x: float) -> int:
    """The IEEE-754 single-precision bits of x, as the pnach would carry them."""
    return struct.unpack(">I", struct.pack(">f", x))[0]


def from_bits(bits: int) -> float:
    return struct.unpack(">f", struct.pack(">I", bits))[0]


def parse_aspect(text: str) -> float:
    """Accept 21:9, 3440x1440 or a bare ratio like 2.370370."""
    for separator in (":", "x", "X"):
        if separator in text:
            width, _, height = text.partition(separator)
            try:
                w, h = float(width), float(height)
            except ValueError:
                raise SystemExit(f"{text!r} is not a W{separator}H pair of numbers.") from None
            if h <= 0 or w <= 0:
                raise SystemExit(f"{text!r} has a zero or negative side.")
            return w / h
    try:
        aspect = float(text)
    except ValueError:
        raise SystemExit(f"{text!r} is not an aspect: give 21:9, 3440x1440 or 2.37037.") from None
    if aspect <= 0:
        raise SystemExit(f"{text!r} is not a positive aspect.")
    return aspect


class Widescreen:
    """The three words, for one display aspect."""

    def __init__(self, aspect: float) -> None:
        self.aspect = aspect
        self.widen = aspect / STOCK_ASPECT
        self.scale = STOCK_SCALE * self.widen
        self.inverse = 1.0 / aspect
        self.lui_imm = f32(self.inverse) >> 16
        self.lui_value = from_bits(self.lui_imm << 16)

    @property
    def lui_error(self) -> float:
        """How far the truncated immediate is from 1/aspect, as a fraction."""
        return abs(self.lui_value - self.inverse) / self.inverse

    def lines(self) -> list[str]:
        return [
            f"patch=1,EE,{SCALE_ADDR:08X},word,{f32(self.scale):08X} "
            f"// projection scale  7/6 * {self.widen:.6f} = {self.scale:.6f}",
            f"patch=1,EE,{SCALE256_ADDR:08X},word,{f32(self.scale * 256):08X} "
            f"// the same, x256    = {self.scale * 256:.6f}",
            f"patch=1,EE,{LUI_ADDR:08X},word,{LUI_OPCODE | self.lui_imm:08X} "
            f"// lui $at, 0x{self.lui_imm:04X}   = {self.lui_value:.7f}, for 1/{self.aspect:.6f}",
        ]


def group(ws: Widescreen, name: str) -> str:
    """The pasteable group, comment header and all."""
    return "\n".join([
        "// PCSX2 has no display aspect for this shape, so set Aspect Ratio to Stretch",
        "// and give it a matching window or fullscreen target. At any other display",
        "// aspect this patch renders a correctly-wide FOV into the wrong box.",
        f"[{name}]",
        f"description=Widescreen hack retargeted from 16:9 to {name}. "
        "Turn the stock Widescreen 16:9 patch OFF.",
        *ws.lines(),
    ])


# The two aspects whose words are already known: BT3's stock 4:3, and PCSX2's
# own shipped [Widescreen 16:9] from resources/patches.zip.
#
# The 16:9 scale is 1.5551670 where the model says 1.5555556, and the reason is
# visible in the arithmetic: 7/6 * 1.333 is 1.5551667. The official patch typed
# the widen factor as 1.333 rather than 4/3. That is a 0.025% narrower field of
# view, about half a pixel across 1920, so the tolerance here is relative and
# loose enough to accept it while still catching a real mistake.
#
# The lui immediate is the part that actually carries the aspect, and it must
# match bit for bit.
SCALE_TOLERANCE = 0.0005  # 0.05%, twice the official patch's own rounding

REFERENCES = [
    (4 / 3, 0x3F955555, 0x3F40, "stock 4:3"),
    (16 / 9, 0x3FC70FB6, 0x3F10, "PCSX2's shipped [Widescreen 16:9]"),
]


def selftest() -> int:
    """Check the model against the two aspects whose words are already known."""
    failures = 0
    for aspect, scale_bits, lui_imm, label in REFERENCES:
        ws = Widescreen(aspect)
        theirs = from_bits(scale_bits)
        error = abs(ws.scale - theirs) / theirs
        close = error <= SCALE_TOLERANCE
        exact = ws.lui_imm == lui_imm
        if not (close and exact):
            failures += 1
        print(f"{'ok' if close and exact else 'FAIL':4s} {label}")
        print(f"       scale  ours {f32(ws.scale):08X} {ws.scale:.7f}   "
              f"theirs {scale_bits:08X} {theirs:.7f}   "
              f"{error * 100:.4f}% {'within tolerance' if close else 'TOO FAR'}")
        print(f"       lui    ours 0x{ws.lui_imm:04X}    theirs 0x{lui_imm:04X}    "
              f"{'exact' if exact else 'DIFFERS'}")
    return 1 if failures else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("aspect", nargs="?", help="21:9, 3440x1440 or 2.37037")
    ap.add_argument("--name", help="the group name (default: Widescreen <aspect>)")
    ap.add_argument("--selftest", action="store_true",
                    help="check the model against 4:3 and the shipped 16:9 patch")
    args = ap.parse_args()

    if args.selftest:
        return selftest()
    if not args.aspect:
        ap.error("give an aspect, or --selftest")

    ws = Widescreen(parse_aspect(args.aspect))
    print(group(ws, args.name or f"Widescreen {args.aspect}"))
    print()
    print(f"// aspect {ws.aspect:.6f}, FOV widens x{ws.widen:.6f}; "
          f"lui immediate is {ws.lui_error * 100:.4f}% from 1/aspect")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

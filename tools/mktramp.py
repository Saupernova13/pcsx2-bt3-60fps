"""Assemble a trampoline with PCSXROO and emit it as pnach lines.

Hand-encoding MIPS by hand is how this project has produced its worst bugs, and
re-assembling an instruction the game already contains is nearly as bad: a
displaced instruction has to be replayed *exactly*, and an assembler that turns
``dmove a0, sp`` back into ``addu`` has quietly changed a 64-bit move into a
32-bit one. So a trampoline is built from two kinds of item:

    ("asm", "mul.s $f14, $f14, $f2")   new code, assembled
    ("copy", 0x001DE034)               a word lifted verbatim from the game

The assembling is done into the live game's own scratch zone, then read back,
so what lands in the pnach is exactly what the emulator's assembler produced.

    python tools/mktramp.py air
"""

from __future__ import annotations

import argparse

import _bootstrap  # noqa: F401

from ps2ee import config
from ps2ee.roo import Roo

SCRATCH = 0x000F7000        # far end of the safe zone, nothing else uses it


def build(roo: Roo, base: int, items: list[tuple[str, object]]) -> list[int]:
    """Assemble at ``base`` and return the finished words."""
    text = [i[1] if i[0] == "asm" else "nop" for i in items]
    roo.cmd("asm", addr=SCRATCH, instructions=text)
    words = roo.read_block(SCRATCH, len(items))
    for index, (kind, value) in enumerate(items):
        if kind == "copy":
            words[index] = roo.read(int(value))
    return words


def emit(name: str, base: int, words: list[int], items, hooks) -> str:
    lines = [f"[{name}]"]
    for index, word in enumerate(words):
        kind, value = items[index]
        note = value if kind == "asm" else f"replay {int(value):08X}"
        lines.append(f"patch=1,EE,{base + index * 4:08X},word,{word:08X} // {note}")
    for addr, word, note in hooks:
        lines.append(f"patch=1,EE,{addr:08X},word,{word:08X} // {note}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# The airborne channels. Both have the same shape: a per-tick "approach" step
# updates a stored speed, and the speed is then applied to the position. At
# 60fps both halves have to be halved - the applied step so the fighter covers
# the same ground per second, and the approach step so the ramp and the decay
# still take the same real time.

HALF = ["lui $at, 0x3F00", "mtc1 $at, $f2"]     # $f2 = 0.5f


def air_speed(roo: Roo) -> tuple[str, int, list, list]:
    """FUN_001DE000: pos += dir(+0x90) * speed(+0xA8)."""
    base = 0x000F0900
    items = [
        *[("asm", t) for t in HALF],
        ("asm", "mul.s $f14, $f14, $f2"),       # approach step, halved
        ("asm", "jal 0x001DBFF8"),
        ("asm", "nop"),
        ("copy", 0x001DE034),                   # addiu a1, s0, 0x80
        ("copy", 0x001DE038),                   # swc1 f00, 0x98(s0)  unhalved
        *[("asm", t) for t in HALF],
        ("asm", "mul.s $f12, $f00, $f2"),       # displacement, halved
        ("asm", "jal 0x00121F38"),              # Vec4Scale
        ("copy", 0x001DE044),                   # dmove a0, sp
        ("asm", "j 0x001DE048"),
        ("asm", "nop"),
    ]
    words = build(roo, base, items)
    hook = [(0x001DE02C, jump(base), "jal 001DBFF8 -> j trampoline")]
    return "60FPS - airborne motion", base, items, (words, hook)


def air_vertical(roo: Roo) -> tuple[str, int, list, list]:
    """FUN_001DED78: pos.y += vy(+0xAC)."""
    base = 0x000F0940
    items = [
        *[("asm", t) for t in HALF],
        ("asm", "mul.s $f14, $f14, $f2"),
        ("asm", "jal 0x001DBFF8"),
        ("asm", "nop"),
        ("copy", 0x001DEDAC),                   # lwc1 f01, 0x4(s0)
        ("copy", 0x001DEDB0),                   # swc1 f00, 0x9C(s0)  unhalved
        *[("asm", t) for t in HALF],
        ("asm", "mul.s $f00, $f00, $f2"),
        ("asm", "add.s $f1, $f1, $f0"),
        ("asm", "j 0x001DEDB8"),
        ("asm", "nop"),
    ]
    words = build(roo, base, items)
    hook = [(0x001DEDA4, jump(base), "jal 001DBFF8 -> j trampoline")]
    return "60FPS - airborne vertical", base, items, (words, hook)


def air_residual(roo: Roo) -> tuple[str, int, list, tuple]:
    """FUN_001DFD88: pos += residual(+0x80), then shrink it by a fixed eps.

    A hit leaves a decaying slide behind. The whole vector is added every tick
    and then shortened by an absolute epsilon, so at 60fps it is delivered in
    half the real time and decays in half the real time - same total distance,
    twice the speed. Halving both the application and the epsilon puts it back.

    The scaled copy goes to a fixed scratch vector rather than the stack:
    nothing runs between the scale and the add, so there is nothing to be
    re-entrant against, and leaving sp alone keeps the trampoline harmless.
    """
    base, temp = 0x000F0980, 0x000F09E0
    items = [
        *[("asm", t) for t in ["lui $at, 0x3F00", "mtc1 $at, $f12"]],
        ("asm", f"lui $a0, 0x{temp >> 16:04X}"),
        ("asm", f"ori $a0, $a0, 0x{temp & 0xFFFF:04X}"),
        ("asm", "jal 0x00121F38"),               # Vec4Scale(temp, residual, 0.5)
        # The word at 001DFDB8 is "dmove a2, s1", not a1 - it is the delay slot
        # of the guard branch, feeding the add that this replaces. The scale
        # wants the residual as its source, so this one is assembled.
        ("asm", "daddu $a1, $s1, $zero"),        # src = residual
        ("copy", 0x001DFDB0),                    # dmove a0, s0   pos
        ("copy", 0x001DFDAC),                    # dmove a1, s0   pos
        ("asm", f"lui $a2, 0x{temp >> 16:04X}"),
        ("asm", "jal 0x00121EA8"),               # Vec4Add(pos, pos, temp)
        ("asm", f"ori $a2, $a2, 0x{temp & 0xFFFF:04X}"),
        ("asm", "j 0x001DFDC4"),
        ("asm", "nop"),
        # The decay epsilon, halved. Hooked one instruction early so the load
        # of the epsilon rides in the delay slot and is already done here.
        *[("asm", t) for t in HALF],
        ("asm", "mul.s $f1, $f1, $f2"),
        ("copy", 0x001DFDD8),                    # dmove a0, s1
        ("asm", "j 0x001DFDE0"),
        ("asm", "nop"),
    ]
    words = build(roo, base, items)
    hooks = [
        (0x001DFDBC, jump(base), "jal Vec4Add -> j trampoline"),
        (0x001DFDD8, jump(base + 13 * 4), "dmove -> j epsilon trampoline"),
    ]
    return "60FPS - airborne residual", base, items, (words, hooks)


def gravity(roo: Roo) -> tuple[str, int, list, tuple]:
    """FUN_001DED28: vy(+0xAC) += g, clamped, then pos.y += vy.

    The real gravity, and a separate routine from the vertical channel in
    FUN_001DED78 - which is why a breakpoint there never fires during a free
    fall. Both constants are plain gp-relative data words with exactly one
    reader each, so the acceleration is halved in data; only the application
    needs code.

    The terminal-velocity clamp is deliberately left alone: vy stays in its
    authored 30Hz units, so the value it is clamped to is still correct.
    """
    base = 0x000F0A00
    items = [
        ("copy", 0x001DED58),                    # lwc1 f00, 0x4(v0)   pos.y
        *[("asm", t) for t in HALF],
        ("asm", "mul.s $f1, $f1, $f2"),          # vy, halved at the point of use
        ("copy", 0x001DED60),                    # ld ra, (sp)
        ("copy", 0x001DED64),                    # add.s f00, f00, f01
        ("copy", 0x001DED68),                    # swc1 f00, 0x4(v0)
        ("asm", "j 0x001DED6C"),
        ("asm", "nop"),
    ]
    words = build(roo, base, items)
    gp = config.GP_BASE
    hooks = [
        (0x001DED58, jump(base), "lwc1 -> j trampoline"),
        (gp - 0x6E4C, roo.read(gp - 0x6E4C) - 0x00800000,
         "gravity 0.462963 -> 0.231481 per tick"),
    ]
    return "60FPS - gravity", base, items, (words, hooks)


def jump(target: int) -> int:
    return 0x08000000 | (target >> 2)


PARTS = {"air": air_speed, "vert": air_vertical, "residual": air_residual,
         "gravity": gravity}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("parts", nargs="*", default=sorted(PARTS))
    args = parser.parse_args()

    roo = Roo().connect()
    for part in args.parts:
        name, base, items, (words, hook) = PARTS[part](roo)
        print(emit(name, base, words, items, hook))
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

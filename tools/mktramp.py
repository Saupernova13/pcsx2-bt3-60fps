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


def jump(target: int) -> int:
    return 0x08000000 | (target >> 2)


PARTS = {"air": air_speed, "vert": air_vertical}


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

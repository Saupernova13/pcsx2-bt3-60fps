"""Find every 'field += 1.0' in the binary, including the hoisted ones.

A game with no timestep counts time by adding one to a float every tick, and
the idiom is always load the field, add one, store it back to the same place.
The one is not always loaded next to the add: a function that steps several
fields hoists `lui $at, 0x3f80; mtc1 $at, $f20` to its prologue and reuses the
register throughout, which a fixed-size peephole window cannot see. So this
tracks which FP registers hold 1.0 across the whole function instead.

Scope is approximated by `jr $ra`: everything between two returns is treated as
one function, which is what the compiler's layout gives here. Calls clobber the
caller-saved half of the FP file, so those registers are dropped at every jal.

    python tools/tickstep.py                     # every site
    python tools/tickstep.py --lo 184000 --hi 187000
    python tools/tickstep.py --addrs-only
"""

from __future__ import annotations

import argparse

import _bootstrap  # noqa: F401

from ps2ee import config
from ps2ee.eemem import ElfImage

LUI_AT_ONE = 0x3C013F80          # lui $at, 0x3f80   -> 1.0f
CALLEE_SAVED = set(range(20, 32))


def decode(word: int):
    """(kind, dest_fpr, extra) for the instructions this pass cares about."""
    op = word >> 26
    if op == 0x31:                                    # lwc1 ft, imm(base)
        imm = word & 0xFFFF
        return "lwc1", (word >> 16) & 0x1F, ((word >> 21) & 0x1F,
                                             imm - 0x10000 if imm >= 0x8000 else imm)
    if op == 0x39:                                    # swc1 ft, imm(base)
        imm = word & 0xFFFF
        return "swc1", (word >> 16) & 0x1F, ((word >> 21) & 0x1F,
                                             imm - 0x10000 if imm >= 0x8000 else imm)
    if op == 0x11:
        rs = (word >> 21) & 0x1F
        if rs == 4:                                   # mtc1 rt, fs
            return "mtc1", (word >> 11) & 0x1F, (word >> 16) & 0x1F
        if rs == 0x10:                                # single-precision ALU
            func = word & 0x3F
            fd, fs, ft = (word >> 6) & 0x1F, (word >> 11) & 0x1F, (word >> 16) & 0x1F
            if func in (0, 1):
                return ("add" if func == 0 else "sub"), fd, (fs, ft)
            if func >= 0x30:                          # compares write no register
                return None
            return "fpu", fd, None
        return None
    if op == 0x03 or (op == 0 and (word & 0x3F) == 9):    # jal / jalr
        return "call", None, None
    if op == 0 and (word & 0x3F) == 8 and ((word >> 21) & 0x1F) == 31:
        return "return", None, None
    return None


def scan(elf: ElfImage, lo: int, hi: int):
    ones: set[int] = set()
    held: dict[int, tuple[int, int]] = {}     # fpr -> (base, offset) it was loaded from
    prev_lui = False
    for addr in range(lo, hi, 4):
        word = elf.u32(addr)
        info = decode(word)
        if info is None:
            prev_lui = word == LUI_AT_ONE
            continue
        kind, dest, extra = info
        if kind == "return":
            ones.clear(); held.clear()
        elif kind == "call":
            ones -= set(range(0, 20))
            held.clear()
        elif kind == "mtc1":
            (ones.add if prev_lui and extra == 1 else ones.discard)(dest)
            held.pop(dest, None)
        elif kind == "lwc1":
            held[dest] = extra
            ones.discard(dest)
        elif kind in ("add", "sub"):
            fs, ft = extra
            if ft in ones and fs in held:
                yield addr, kind, held[fs], dest, fs
            held.pop(dest, None)
            ones.discard(dest)
        elif kind == "fpu":
            held.pop(dest, None)
            ones.discard(dest)
        prev_lui = False


def confirm(elf: ElfImage, addr: int, dest: int, place: tuple[int, int], span: int = 12):
    """True if the sum really is stored back where the operand came from."""
    for a in range(addr + 4, addr + 4 * span, 4):
        info = decode(elf.u32(a))
        if info is None:
            continue
        kind, d, extra = info
        if kind == "swc1" and d == dest:
            return extra == place
        if kind in ("add", "sub", "fpu", "lwc1", "mtc1") and d == dest:
            return False
        if kind in ("call", "return"):
            return False
    return False


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--lo", default=f"{config.TEXT_BASE:x}")
    ap.add_argument("--hi", default=f"{config.TEXT_END:x}")
    ap.add_argument("--addrs-only", action="store_true")
    args = ap.parse_args()
    elf = ElfImage.load(config.elf_path())
    lo, hi = int(args.lo, 16) & ~3, int(args.hi, 16) & ~3
    rows = [(addr, kind, place)
            for addr, kind, place, dest, _fs in scan(elf, lo, hi)
            if confirm(elf, addr, dest, place)]
    for addr, kind, (base, off) in rows:
        print(f"{addr:08X}" if args.addrs_only
              else f"{addr:08X}  [r{base}+0x{off:X}] {'+=' if kind == 'add' else '-='} 1.0")
    if not args.addrs_only:
        print(f"\n{len(rows)} per-tick 1.0 steps")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

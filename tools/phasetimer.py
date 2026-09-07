"""Find the fighter state machine's phase timers.

Every attack, block, charge and stagger is a state, and every state handler
keeps its own timer in the scratch block the dispatcher zeroes on entry -
`addiu $sN, $fighter, 0x3d8` in the prologue, then `[$sN] += 1` once a tick.
Those counts are authored in 30Hz frames: how long a charge takes, how long a
recovery lasts, when a beam is let go. At 60fps every one of them expires in
half its real time.

    python tools/phasetimer.py
    python tools/phasetimer.py --sites-only
"""

from __future__ import annotations

import argparse

import _bootstrap  # noqa: F401

from ps2ee import config
from ps2ee.eemem import ElfImage

SCRATCH_OFFSET = 0x3D8
BACK = 400        # instructions to look back for the prologue that names the pointer


def addiu(word: int):
    """`addiu rt, rs, imm` -> (rt, rs, imm)."""
    if (word >> 26) != 0x09:
        return None
    imm = word & 0xFFFF
    return (word >> 16) & 0x1F, (word >> 21) & 0x1F, imm - 0x10000 if imm >= 0x8000 else imm


def lw_sw(word: int):
    op = word >> 26
    if op not in (0x23, 0x2B):
        return None
    imm = word & 0xFFFF
    return ("lw" if op == 0x23 else "sw", (word >> 16) & 0x1F,
            (word >> 21) & 0x1F, imm - 0x10000 if imm >= 0x8000 else imm)


def is_return(word: int) -> bool:
    return (word >> 26) == 0 and (word & 0x3F) == 8 and ((word >> 21) & 0x1F) == 31


def scan(elf: ElfImage, lo: int, hi: int):
    for addr in range(lo, hi, 4):
        step = addiu(elf.u32(addr))
        if not step or step[2] != 1 or step[0] != step[1]:
            continue
        rd = step[0]
        load = lw_sw(elf.u32(addr - 4))
        if not load or load[0] != "lw" or load[1] != rd or load[3] != 0:
            continue
        base = load[2]
        store = None
        for a in range(addr + 4, addr + 4 * 8, 4):
            m = lw_sw(elf.u32(a))
            if m and m[0] == "sw" and m[1] == rd and m[2] == base and m[3] == 0:
                store = a
                break
        if store is None:
            continue
        # the pointer has to be the state scratch block, named in the prologue
        named = None
        for a in range(addr - 4, max(lo, addr - BACK * 4), -4):
            if is_return(elf.u32(a)):
                break
            m = addiu(elf.u32(a))
            if m and m[0] == base and m[2] == SCRATCH_OFFSET:
                named = a
                break
        if named:
            yield addr - 4, addr, store, base, named


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sites-only", action="store_true",
                    help="print just the load address, for tools/mkgate.py")
    args = ap.parse_args()
    elf = ElfImage.load(config.elf_path())
    rows = list(scan(elf, config.TEXT_BASE, config.TEXT_END))
    for load, step, store, base, named in rows:
        print(f"{load:08X}" if args.sites_only
              else f"{load:08X}  lw/addiu/sw on r{base} (+0x3d8 taken at {named:08X})")
    if not args.sites_only:
        print(f"\n{len(rows)} state phase timers")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

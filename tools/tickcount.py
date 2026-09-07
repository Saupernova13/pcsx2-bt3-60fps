"""Find every integer 'field = field + 1' in the binary - the frame counters.

The float twin of this lives in tools/tickstep.py. Integer counters are the
ones a scripted sequence actually keeps time by: load a field, add one, store
it back. Every one of them counts ticks, so every one of them runs at double
speed once the battle loop runs at 60Hz.

    python tools/tickcount.py                    # every site
    python tools/tickcount.py --addrs-only
"""

from __future__ import annotations

import argparse

import _bootstrap  # noqa: F401

from ps2ee import config
from ps2ee.eemem import ElfImage

WINDOW = 6


def lw_sw(word: int):
    """`lw`/`sw rt, imm(base)` -> (kind, rt, base, imm)."""
    op = word >> 26
    if op not in (0x23, 0x2B):
        return None
    imm = word & 0xFFFF
    if imm >= 0x8000:
        imm -= 0x10000
    return ("lw" if op == 0x23 else "sw",
            (word >> 16) & 0x1F, (word >> 21) & 0x1F, imm)


def addiu_one(word: int):
    """`addiu rt, rs, +/-1` -> (rt, rs, step)."""
    if (word >> 26) != 0x09:
        return None
    imm = word & 0xFFFF
    if imm not in (1, 0xFFFF):
        return None
    return (word >> 16) & 0x1F, (word >> 21) & 0x1F, 1 if imm == 1 else -1


def scan(elf: ElfImage, lo: int, hi: int):
    for addr in range(lo, hi, 4):
        pair = addiu_one(elf.u32(addr))
        if not pair:
            continue
        rt, rs, step = pair
        start, stop = max(lo, addr - WINDOW * 4), min(hi, addr + WINDOW * 4 + 4)
        window = [(a, elf.u32(a)) for a in range(start, stop, 4)]
        src = dst = None
        for a, w in window:
            m = lw_sw(w)
            if not m:
                continue
            if a < addr and m[0] == "lw" and m[1] == rs:
                src = m
            elif a > addr and m[0] == "sw" and m[1] == rt and dst is None:
                dst = m
        if src and dst and src[2] == dst[2] and src[3] == dst[3]:
            yield addr, dst[2], dst[3], step


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--lo", default=f"{config.TEXT_BASE:x}")
    ap.add_argument("--hi", default=f"{config.TEXT_END:x}")
    ap.add_argument("--addrs-only", action="store_true")
    args = ap.parse_args()
    elf = ElfImage.load(config.elf_path())
    rows = list(scan(elf, int(args.lo, 16) & ~3, int(args.hi, 16) & ~3))
    for addr, base, off, step in rows:
        print(f"{addr:08X}" if args.addrs_only
              else f"{addr:08X}  [r{base}+0x{off:X}] {'+=' if step > 0 else '-='} 1")
    if not args.addrs_only:
        print(f"\n{len(rows)} per-tick integer counters (up and down)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

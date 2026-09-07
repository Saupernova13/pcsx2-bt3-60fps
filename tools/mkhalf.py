"""Turn 'field += 1.0' sites into 'field += 0.5', one trampoline each.

The one is usually not an immediate at the site: it lives in a register the
function hoisted to its prologue and shares with comparisons, so the constant
cannot simply be halved in place. Each site instead jumps to six words that
build 0.5 in the destination register - safe, because the destination is about
to be overwritten anyway - and add that instead.

    python tools/mkhalf.py 00184E3C,00184ECC --base F0C00
    python tools/mkhalf.py --file work/sites.txt --base F0C00
"""

from __future__ import annotations

import argparse

import _bootstrap  # noqa: F401

from ps2ee import config
from ps2ee.eemem import ElfImage


def parts(word: int):
    """(func, fd, fs, ft) of a single-precision add.s/sub.s."""
    if (word >> 26) != 0x11 or ((word >> 21) & 0x1F) != 0x10 or (word & 0x3F) not in (0, 1):
        return None
    return word & 0x3F, (word >> 6) & 0x1F, (word >> 11) & 0x1F, (word >> 16) & 0x1F


def is_branch(word: int) -> bool:
    """True for anything that has a delay slot - jumps, branches, calls."""
    op = word >> 26
    if op in (0x02, 0x03) or 0x04 <= op <= 0x07 or 0x14 <= op <= 0x17:
        return True
    if op == 0x01:                              # regimm: bltz/bgez and their links
        return True
    if op == 0x11 and ((word >> 21) & 0x1F) == 8:   # bc1t/bc1f
        return True
    if op == 0 and (word & 0x3F) in (8, 9):     # jr / jalr
        return True
    return False


def trampoline(site: int, at: int, word: int) -> list[tuple[int, int, str]]:
    func, fd, fs, ft = parts(word)
    if fd == fs:
        raise ValueError(f"{site:08X}: destination is also the source, no free scratch")
    op = "add" if func == 0 else "sub"
    half = 0x46000000 | (fd << 16) | (fs << 11) | (fd << 6) | func
    back = 0x08000000 | ((site + 4) >> 2)
    return [
        (at + 0x00, 0x3C013F00, "lui $at, 0x3f00           0.5"),
        (at + 0x04, 0x44810000 | (fd << 11), f"mtc1 $at, $f{fd}"),
        (at + 0x08, 0x00000000, "nop                       mtc1 use delay"),
        (at + 0x0C, half, f"{op}.s $f{fd}, $f{fs}, $f{fd}   half step"),
        (at + 0x10, back, f"j 0x{site + 4:X}"),
        (at + 0x14, 0x00000000, "nop"),
        (site, 0x08000000 | (at >> 2), f"{op}.s -> j {at:08X}"),
    ]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("sites", nargs="?", default="")
    ap.add_argument("--file")
    ap.add_argument("--base", default="F0C00", help="first free scratch address, hex")
    args = ap.parse_args()

    text = args.sites
    if args.file:
        text = ",".join(line.split()[0] for line in open(args.file) if line[:1] == "0")
    sites = [int(s, 16) for s in text.replace(",", " ").split()]
    elf = ElfImage.load(config.elf_path())
    at = int(args.base, 16)
    for site in sites:
        if is_branch(elf.u32(site - 4)):
            raise SystemExit(f"{site:08X} sits in a delay slot - hook it another way")
        for addr, word, note in trampoline(site, at, elf.u32(site)):
            print(f"patch=1,EE,{addr:08X},word,{word:08X} // {note}")
        at += 0x18
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

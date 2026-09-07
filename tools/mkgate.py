"""Turn an integer 'field += 1' into one that counts on even ticks only.

The counter is authored in 30Hz frames, so at 60fps it has to advance half as
often. Halving is not an option for an integer, and freezing it is not either,
so each site jumps to a small trampoline that reloads the field, adds one only
when the global frame counter is even, replays whatever sat between the add and
the next branch, and returns to that branch. Nothing else about the site
changes: the store in the branch's delay slot still runs every tick.

    python tools/mkgate.py 001F7A00,001F6778 --base F1000
    python tools/phasetimer.py --sites-only | python tools/mkgate.py --stdin --base F1000
"""

from __future__ import annotations

import argparse
import sys

import _bootstrap  # noqa: F401

from ps2ee import config
from ps2ee.eemem import ElfImage

FRAME_COUNTER = 0x00331D64
AT_LOOKAHEAD = 3


def is_branch(word: int) -> bool:
    """True for anything with a delay slot."""
    op = word >> 26
    if op in (0x02, 0x03) or 0x01 <= op <= 0x07 or 0x14 <= op <= 0x17:
        return True
    if op == 0x11 and ((word >> 21) & 0x1F) == 8:      # bc1t / bc1f
        return True
    return op == 0 and (word & 0x3F) in (8, 9)         # jr / jalr


def touches_at(word: int) -> bool:
    """True if the instruction reads or writes $at, which the gate clobbers."""
    op = word >> 26
    fields = [(word >> 21) & 0x1F, (word >> 16) & 0x1F]
    if op == 0:
        fields.append((word >> 11) & 0x1F)
    return 1 in fields


def gate(elf: ElfImage, site: int, at: int):
    load, step = elf.u32(site), elf.u32(site + 4)
    if is_branch(elf.u32(site - 4)):
        raise ValueError(f"{site:08X} sits in a delay slot")
    # Return to the instruction after the add. It can never be a delay slot -
    # the instruction before it is the add - so no replay is needed at all.
    ret = site + 8
    for a in range(ret, ret + 4 * AT_LOOKAHEAD, 4):
        word = elf.u32(a)
        if touches_at(word):
            raise ValueError(f"{site:08X}: {a:08X} reads $at, which the gate clobbers")
        if is_branch(word):
            break

    words = [
        (load, "reload the counter"),
        (0x3C010000 | (FRAME_COUNTER >> 16), "lui $at, frame counter"),
        (0x8C210000 | (FRAME_COUNTER & 0xFFFF) | (1 << 21), "lw $at, ($at)"),
        (0x30210001, "andi $at, $at, 1"),
        (0x14200002, "bnez $at, odd tick: hold"),
        (0x00000000, "nop"),
        (step, "even tick: count"),
    ]
    words += [(0x08000000 | (ret >> 2), f"j 0x{ret:X}"), (0x00000000, "nop")]
    lines = [(at + 4 * i, w, note) for i, (w, note) in enumerate(words)]
    lines.append((site, 0x08000000 | (at >> 2), f"gate -> {at:08X}"))
    return lines, len(words)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("sites", nargs="?", default="")
    ap.add_argument("--stdin", action="store_true")
    ap.add_argument("--base", default="F1000")
    args = ap.parse_args()
    text = sys.stdin.read() if args.stdin else args.sites
    sites = [int(s, 16) for s in text.replace(",", " ").split()]
    elf = ElfImage.load(config.elf_path())
    at = int(args.base, 16)
    for site in sites:
        lines, n = gate(elf, site, at)
        for addr, word, note in lines:
            print(f"patch=1,EE,{addr:08X},word,{word:08X} // {note}")
        at += 4 * n
    if at > config.SAFE_ZONE + config.SAFE_ZONE_SIZE:
        raise SystemExit("ran past the end of the scratch zone")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

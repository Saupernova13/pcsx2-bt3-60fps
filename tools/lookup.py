"""Three questions about the boot ELF that this project keeps asking by hand.

None of them needs the emulator running, so none of them should cost a boot.

    python tools/lookup.py state 238 239      # which routine handles a state
    python tools/lookup.py callers 001E16C0   # every jal to an address
    python tools/lookup.py gp 6D80            # who reads a gp-relative word
"""

from __future__ import annotations

import argparse
import struct

import _bootstrap  # noqa: F401

from game import config
from ps2ee.eemem import ElfImage

STATE_TABLE = 0x002C4980
LOADS_AND_STORES = {0x20: "lb", 0x21: "lh", 0x23: "lw", 0x24: "lbu",
                    0x25: "lhu", 0x28: "sb", 0x29: "sh", 0x2B: "sw",
                    0x31: "lwc1", 0x39: "swc1"}


def text_segments(elf: ElfImage):
    for seg in elf.segments:
        if config.TEXT_BASE <= seg.vaddr < config.TEXT_END:
            yield seg


def show_state(elf: ElfImage, args) -> None:
    for value in args.values:
        state = int(value, 0)
        handler = elf.u32(STATE_TABLE + state * 4)
        print(f"state {state:3d} (0x{state:02X})  ->  {handler:08X}")


def show_callers(elf: ElfImage, args) -> None:
    """A jal is the only call form this game uses for a fixed target."""
    for value in args.values:
        target = int(value, 16)
        word = (3 << 26) | ((target >> 2) & 0x03FFFFFF)
        sites = [seg.vaddr + off
                 for seg in text_segments(elf)
                 for off in range(0, len(seg.data) - 3, 4)
                 if struct.unpack_from("<I", seg.data, off)[0] == word]
        print(f"jal {target:08X} == {word:08X}: {len(sites)} site(s)")
        for site in sites:
            print(f"  {site:08X}")


def show_gp(elf: ElfImage, args) -> None:
    """A gp word with exactly one reader can be halved in data.

    That is how the gravity constant, the smash charge step and the stage
    animation step were all fixed. More than one reader and the value is
    shared, so halving it changes something else too.
    """
    for value in args.values:
        offset = int(value, 16)
        addr = config.GP_BASE - offset
        raw = elf.u32(addr)
        as_float = struct.unpack("<f", struct.pack("<I", raw))[0]
        print(f"\ngp-0x{offset:X} = {addr:08X}  raw {raw:08X}  float {as_float!r}")
        immediate = (-offset) & 0xFFFF
        found = 0
        for seg in text_segments(elf):
            for off in range(0, len(seg.data) - 3, 4):
                w = struct.unpack_from("<I", seg.data, off)[0]
                if (w & 0xFFFF) != immediate or ((w >> 21) & 0x1F) != 28:
                    continue
                name = LOADS_AND_STORES.get(w >> 26)
                if name is None:
                    continue
                print(f"  {seg.vaddr + off:08X}  {w:08X}  {name}")
                found += 1
        print(f"  {found} reader(s)")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="what", required=True)
    for name, help_text in (("state", "state number -> handler address"),
                            ("callers", "address -> every jal to it"),
                            ("gp", "gp offset -> its value and its readers")):
        p = sub.add_parser(name, help=help_text)
        p.add_argument("values", nargs="+")

    args = parser.parse_args()
    elf = ElfImage.load(config.elf_path())
    {"state": show_state, "callers": show_callers, "gp": show_gp}[args.what](elf, args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

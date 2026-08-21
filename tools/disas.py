"""Disassemble EE code around one or more addresses.

    python tools/disas.py 264DBC 1DCB40
    python tools/disas.py --func 264DBC          # whole containing function
    python tools/disas.py --source elf 1DCB40    # from the ELF, not a state
"""

import argparse

import _bootstrap  # noqa: F401

from ps2ee import config
from ps2ee.disasm import (
    branch_target,
    function_body,
    function_start,
    jump_target,
    window,
)
from ps2ee.eemem import EEMemory, ElfImage


def load_memory(source: str, state: str | None):
    if source == "elf":
        elf = ElfImage.load(config.elf_path())
        # Splice loaded segments into a full RAM image so one code path serves both.
        buffer = bytearray(config.EE_RAM_SIZE)
        for seg in elf.segments:
            buffer[seg.vaddr : seg.end] = seg.data
        return EEMemory(bytes(buffer), source=str(config.elf_path()))
    return EEMemory.from_state(state or config.latest_state())


def render_annotated(insns, mark: int) -> str:
    """Like render(), but resolves j/jal/branch targets on the right."""
    lines = []
    for ins in insns:
        target = jump_target(ins.word, ins.addr) or branch_target(ins.word, ins.addr)
        note = f"   -> {target:08X}" if target else ""
        prefix = ">>" if ins.addr == mark else "  "
        lines.append(f"{prefix} {ins}{note}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("addrs", nargs="+", help="hex EE addresses")
    parser.add_argument("--source", choices=["state", "elf"], default="state")
    parser.add_argument("--state", help="explicit .p2s path")
    parser.add_argument("--func", action="store_true", help="whole containing function")
    parser.add_argument("--before", type=int, default=8)
    parser.add_argument("--after", type=int, default=16)
    args = parser.parse_args()

    mem = load_memory(args.source, args.state)
    print(f"# source: {mem.source}\n")

    for text in args.addrs:
        addr = int(text, 16)
        if args.func:
            start = function_start(mem, addr)
            insns = function_body(mem, addr)
            print(f"===== function {start:08X} "
                  f"({len(insns)} instructions), marked {addr:08X} =====")
        else:
            insns = window(mem, addr, args.before, args.after)
            print(f"===== {addr:08X} =====")
        print(render_annotated(insns, mark=addr))
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

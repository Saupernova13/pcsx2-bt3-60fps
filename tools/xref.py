"""Find who calls a function, and where its address is stored.

Zero direct callers means the function is reached indirectly - a vtable, jump
table or callback. That is the guide's '0 callers group', where the main-loop
code usually lives.

    python tools/xref.py 264D98
    python tools/xref.py --resolve 264DBC     # find the enclosing function first
"""

import argparse

import _bootstrap  # noqa: F401

from ps2ee import config
from ps2ee.disasm import callers, function_start, render
from ps2ee.eemem import EEMemory


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("addrs", nargs="+", help="hex EE addresses")
    parser.add_argument("--state", help="explicit .p2s path")
    parser.add_argument(
        "--resolve",
        action="store_true",
        help="treat each address as an instruction and xref its function instead",
    )
    args = parser.parse_args()

    mem = EEMemory.from_state(args.state or config.latest_state())
    print(f"# source: {mem.source}\n")

    for text in args.addrs:
        addr = int(text, 16)
        if args.resolve:
            resolved = function_start(mem, addr)
            print(f"===== {addr:08X} is inside function {resolved:08X} =====")
            addr = resolved
        else:
            print(f"===== callers of {addr:08X} =====")

        refs = callers(mem, addr)
        direct = [r for r in refs if r.kind in ("jal", "j")]
        pointers = [r for r in refs if r.kind == "pointer"]

        for ref in direct:
            print(f"  [{ref.kind:>3}] {ref.site:08X}")
            print(render(ref.context))
        for ref in pointers:
            print(f"  [ptr] {ref.site:08X}  (function pointer / table entry)")

        if not direct:
            print("  no direct j/jal callers - reached indirectly (0 callers group)")
        print(f"  total: {len(direct)} direct, {len(pointers)} pointers\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

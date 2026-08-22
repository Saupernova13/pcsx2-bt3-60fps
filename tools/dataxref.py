"""Find the code that touches a global, by address rather than by call graph.

``xref.py`` answers "who calls this function". This answers "who reads or
writes this variable", which is the only way in when the consumers are reached
through function pointers - as BT3's input readers are.

    python tools/dataxref.py 33398C
    python tools/dataxref.py 333988-333994 --group
    python tools/dataxref.py 33398C --in 200000-2C0000 --context 6
"""

import argparse

import _bootstrap  # noqa: F401

from ps2ee import config
from ps2ee.disasm import data_refs, function_start, render, window
from ps2ee.eemem import EEMemory


def parse_range(text: str) -> tuple[int, int]:
    if "-" in text:
        lo, hi = text.split("-", 1)
        return int(lo, 16), int(hi, 16)
    base = int(text, 16)
    return base, base + 4


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("target", help="hex address or LO-HI range")
    parser.add_argument("--state", help="explicit .p2s path")
    parser.add_argument("--in", dest="scope", metavar="LO-HI",
                        help="only report sites inside this code range")
    parser.add_argument("--group", action="store_true",
                        help="group by enclosing function instead of listing sites")
    parser.add_argument("--stores", action="store_true", help="writers only")
    parser.add_argument("--context", type=int, default=0,
                        help="disassemble N instructions either side of each site")
    args = parser.parse_args()

    mem = EEMemory.from_state(args.state or config.latest_state())
    lo, hi = parse_range(args.target)
    scope = parse_range(args.scope) if args.scope else (config.TEXT_BASE, config.TEXT_END)

    refs = data_refs(mem, lo, hi, *scope)
    if args.stores:
        refs = [r for r in refs if r.kind.startswith("s")]

    print(f"# {len(refs)} references to {lo:08X}-{hi:08X} from {scope[0]:08X}-{scope[1]:08X}")

    if args.group:
        by_func: dict[int, list] = {}
        for ref in refs:
            by_func.setdefault(function_start(mem, ref.site), []).append(ref)
        print(f"# in {len(by_func)} functions\n")
        for func in sorted(by_func):
            hits = by_func[func]
            kinds = ", ".join(sorted({r.kind for r in hits}))
            print(f"  {func:08X}  {len(hits):>3} refs  ({kinds})")
            for ref in hits:
                print(f"      {ref.site:08X}  {ref.kind:<5} {ref.target:08X}  {ref.text}")
        return 0

    for ref in refs:
        print(f"  {ref.site:08X}  {ref.kind:<5} -> {ref.target:08X}   {ref.text}")
        if args.context:
            print(render(window(mem, ref.site, args.context, args.context), mark=ref.site))
            print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

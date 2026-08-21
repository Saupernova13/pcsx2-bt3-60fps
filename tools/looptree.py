"""Walk the call tree under a loop, then scan only that code for step constants.

The unscoped radar returns thousands of hits. Scoping it to the functions a
specific loop actually reaches is what makes the heuristic usable - the same
idea as the Ghidra script's main-loop tree, done locally and fast.

    python tools/looptree.py 12BBD0 --depth 4
    python tools/looptree.py 12BBD0 --depth 4 --scan
    python tools/looptree.py 12BBD0 --scan --only-floats --exclude 2BF588
"""

import argparse
from collections import deque

import _bootstrap  # noqa: F401

from ps2ee import config
from ps2ee.disasm import decode, jump_target
from ps2ee.eemem import EEMemory

JR_RA = 0x03E00008


def function_span(mem: EEMemory, entry: int, limit: int = 0x8000) -> tuple[int, int]:
    """Entry to just past the end, ending at 'jr ra' or an outbound tail jump."""
    at = entry
    ceiling = min(config.TEXT_END, entry + limit)
    while at < ceiling:
        word = mem.u32(at)
        if word == JR_RA:
            return entry, at + 8
        if (word >> 26) == 0x02:  # plain j
            target = jump_target(word, at)
            if target is not None and not (entry <= target < at + 8):
                return entry, at + 8   # tail call out of the function
        at += 4
    return entry, ceiling


def calls_from(mem: EEMemory, entry: int) -> tuple[set[int], int]:
    """Direct j/jal targets inside one function, and the function's size."""
    start, end = function_span(mem, entry)
    targets = set()
    for at in range(start, end, 4):
        word = mem.u32(at)
        op = word >> 26
        if op in (0x02, 0x03):
            target = jump_target(word, at)
            if target is not None and config.TEXT_BASE <= target < config.TEXT_END:
                targets.add(target)
    return targets, end - start


def build_tree(mem: EEMemory, root: int, depth: int,
               exclude: set[int]) -> dict[int, int]:
    """Breadth-first callee closure. Returns {function entry: depth reached at}."""
    seen = {root: 0}
    queue = deque([(root, 0)])
    while queue:
        entry, level = queue.popleft()
        if level >= depth:
            continue
        for target in calls_from(mem, entry)[0]:
            if target in seen or target in exclude:
                continue
            seen[target] = level + 1
            queue.append((target, level + 1))
    return seen


# Constants worth flagging, as the upper half a lui would load.
FLOAT_HITS = {
    0x4000: "float 2.0  <- 30fps step, halve to 0x3F00",
    0x3F80: "float 1.0  <- per-frame step, halve to 0x3F00",
    0x3F00: "float 0.5  (already halved)",
}
INT_HITS = {2: "int 2", 1: "int 1", 30: "int 30", 60: "int 60"}


def scan(mem: EEMemory, tree: dict[int, int], floats_only: bool, ints_only: bool):
    """Immediate loads of suspect constants, grouped by function."""
    results = []
    for entry in sorted(tree):
        start, end = function_span(mem, entry)
        found = []
        for at in range(start, end, 4):
            word = mem.u32(at)
            op, rs, imm = word >> 26, (word >> 21) & 0x1F, word & 0xFFFF
            if op == 0x0F and not ints_only:                 # lui rt, imm
                if imm in FLOAT_HITS:
                    found.append((at, FLOAT_HITS[imm], decode(word, at)))
            elif op in (0x09, 0x0D) and rs == 0 and not floats_only:  # li
                if imm in INT_HITS:
                    found.append((at, INT_HITS[imm], decode(word, at)))
        if found:
            results.append((entry, tree[entry], end - start, found))
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("root", help="hex address of the loop function")
    parser.add_argument("--state", help="explicit .p2s path")
    parser.add_argument("--depth", type=int, default=4)
    parser.add_argument("--scan", action="store_true", help="scan for step constants")
    parser.add_argument("--only-floats", action="store_true")
    parser.add_argument("--only-ints", action="store_true")
    parser.add_argument("--exclude", action="append", default=[],
                        metavar="ADDR", help="prune a subtree (repeatable)")
    parser.add_argument("--limit", type=int, default=60)
    args = parser.parse_args()

    mem = EEMemory.from_state(args.state or config.latest_state())
    root = int(args.root, 16)
    exclude = {int(a, 16) for a in args.exclude}

    tree = build_tree(mem, root, args.depth, exclude)
    total_bytes = sum(function_span(mem, f)[1] - f for f in tree)
    print(f"# root {root:08X}, depth {args.depth}")
    print(f"# {len(tree)} functions, {total_bytes:,} bytes of code in the tree")

    if not args.scan:
        by_level: dict[int, list[int]] = {}
        for func, level in tree.items():
            by_level.setdefault(level, []).append(func)
        for level in sorted(by_level):
            funcs = sorted(by_level[level])
            print(f"\n  depth {level}: {len(funcs)} functions")
            for i in range(0, min(len(funcs), args.limit), 8):
                print("    " + "  ".join(f"{f:08X}" for f in funcs[i : i + 8]))
        return 0

    results = scan(mem, tree, args.only_floats, args.only_ints)
    hits = sum(len(r[3]) for r in results)
    print(f"# {hits} constant loads across {len(results)} functions\n")
    for entry, level, size, found in results:
        print(f"  {entry:08X}  depth {level}  {size:>6} bytes  ({len(found)} hits)")
        for at, label, text in found:
            print(f"      {at:08X}  {text:<26} | {label}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

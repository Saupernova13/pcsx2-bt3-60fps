"""Disable one call in a loop at a time, live, to see what it drives.

This is the guide's Step 3 isolation testing, done over PINE so the emulator
never has to restart. Each experiment is: neutralise one call, you look at the
game, tell me what changed, we restore and move on.

    python tools/probe-loop.py 12BBD0 --list
    python tools/probe-loop.py 12BBD0 --nop 6
    python tools/probe-loop.py 12BBD0 --restore

Calls whose return value the loop actually uses are marked RISKY and refused
unless --force is given: blanking those leaves a garbage result in $v0 and can
hang or crash the loop rather than telling you anything.
"""

import argparse
import json

import _bootstrap  # noqa: F401

from ps2ee import config
from ps2ee.disasm import jump_target
from ps2ee.eemem import EEMemory
from ps2ee.pine import Pine, PineNotRunning

STATE = config.WORK / "probe-state.json"
NOP = 0x00000000


def loop_calls(mem: EEMemory, root: int, limit: int = 0x400):
    """Every j/jal inside the loop body, in order."""
    calls = []
    at = root
    while at < root + limit:
        word = mem.u32(at)
        if (word >> 26) in (0x02, 0x03):
            target = jump_target(word, at)
            if target and config.TEXT_BASE <= target < config.TEXT_END:
                calls.append((at, target, "jal" if (word >> 26) == 0x03 else "j"))
            if (word >> 26) == 0x02 and target and not (root <= target < at):
                break     # tail jump out of the function
        if word == 0x03E00008:
            break
        at += 4
    return calls


def uses_result(mem: EEMemory, site: int) -> bool:
    """Does the loop read $v0 soon after this call returns?

    Crude but effective: look for any instruction in the next few slots that
    reads register 2 as rs or rt.
    """
    for offset in (8, 12, 16):
        word = mem.u32(site + offset)
        rs, rt = (word >> 21) & 0x1F, (word >> 16) & 0x1F
        op = word >> 26
        if rs == 2 or (op not in (0x0F,) and rt == 2 and op != 0x00):
            return True
        if op == 0x00 and (rs == 2 or rt == 2):
            return True
    return False


def load_state() -> dict:
    return json.loads(STATE.read_text()) if STATE.exists() else {}


def save_state(data: dict) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(data, indent=2), newline="\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("root", help="hex address of the loop function")
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--nop", type=int, metavar="N", help="disable call number N")
    parser.add_argument("--restore", action="store_true", help="undo every change")
    parser.add_argument("--force", action="store_true", help="allow RISKY calls")
    parser.add_argument("--port", type=int, default=28011)
    args = parser.parse_args()

    mem = EEMemory.from_state(config.latest_state())
    root = int(args.root, 16)
    calls = loop_calls(mem, root)

    if args.list:
        print(f"# calls inside {root:08X}\n")
        for i, (site, target, kind) in enumerate(calls):
            risky = "RISKY " if uses_result(mem, site) else "      "
            print(f"  [{i:>2}] {site:08X}  {kind:<3} {target:08X}  {risky}")
        print(f"\n  {len(calls)} calls. --nop N to disable one live.")
        return 0

    try:
        pine = Pine(port=args.port).connect()
    except PineNotRunning as exc:
        print(exc)
        return 2

    with pine:
        saved = load_state()

        if args.restore:
            if not saved:
                print("Nothing to restore.")
                return 0
            for addr_text, word in saved.items():
                addr = int(addr_text, 16)
                pine.write(addr, word)
                print(f"  restored {addr:08X} = {word:08X}")
            save_state({})
            print("\nAll probe changes undone.")
            return 0

        if args.nop is None:
            parser.error("give --list, --nop N, or --restore")

        if not 0 <= args.nop < len(calls):
            parser.error(f"call index must be 0..{len(calls) - 1}")

        site, target, kind = calls[args.nop]
        if uses_result(mem, site) and not args.force:
            print(f"[{args.nop}] {site:08X} -> {target:08X} is RISKY: the loop reads its")
            print("result. Blanking it leaves garbage in $v0 and may hang the loop.")
            print("Pass --force if you accept that.")
            return 1

        before = pine.read(site)
        saved[f"{site:08X}"] = before
        save_state(saved)
        pine.write(site, NOP)
        after = pine.read(site)

        print(f"Disabled call [{args.nop}]  {site:08X}  {kind} {target:08X}")
        print(f"  {before:08X} -> {after:08X}")
        if after != NOP:
            print("  WARNING: the write did not stick.")
        print("\nLook at the game and tell me what changed. Then:")
        print("  python tools/probe-loop.py "
              f"{args.root} --restore")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

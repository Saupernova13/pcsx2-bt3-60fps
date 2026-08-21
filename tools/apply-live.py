"""Re-apply the current patch into a running PCSX2 over PINE.

Loading a save state restores EE RAM wholesale and wipes any live writes, and
a freshly deployed cheat file is only read at boot. This puts the patch back
without restarting.

    python tools/apply-live.py                    # apply patches/428113C2.pnach
    python tools/apply-live.py --check            # report only
"""
import argparse
import _bootstrap  # noqa: F401
from ps2ee import config, Pine, PineNotRunning
from ps2ee.pnach import Pnach

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pnach", nargs="?", default=str(config.PATCHES / "428113C2.pnach"))
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    pnach = Pnach.load(args.pnach)
    problems = pnach.validate()
    if problems:
        print("VALIDATION FAILED")
        for p in problems:
            print(f"  {p}")
        return 1

    try:
        pine = Pine(timeout=20.0).connect()
    except PineNotRunning as exc:
        print(exc)
        return 2

    applied = wrong = 0
    with pine:
        for g in pnach.groups:
            print(f"[{g.name}]")
            for line in g.lines:
                if line.is_condition or line.cpu != "EE":
                    continue
                cur = pine.read(line.addr)
                ok = cur == line.value
                if args.check:
                    print(f"  {line.addr:08X}  {cur:08X}  {'ok' if ok else 'MISSING'}")
                    wrong += 0 if ok else 1
                    continue
                if not ok:
                    pine.write(line.addr, line.value)
                    now = pine.read(line.addr)
                    print(f"  {line.addr:08X}  {cur:08X} -> {now:08X}"
                          f"{'' if now == line.value else '   WRITE FAILED'}")
                    applied += 1
                else:
                    print(f"  {line.addr:08X}  already correct")
    print(f"\n{'missing: '+str(wrong) if args.check else 'wrote '+str(applied)+' words'}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

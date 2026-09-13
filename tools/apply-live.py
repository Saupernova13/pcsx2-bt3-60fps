"""Re-apply the current patch into a running PCSX2 over PINE.

Loading a save state restores EE RAM wholesale and wipes any live writes, and
a freshly deployed cheat file is only read at boot. This puts the patch back
without restarting.

    python tools/apply-live.py                    # apply wip/working.pnach
    python tools/apply-live.py --check            # report only
"""
import argparse
import _bootstrap  # noqa: F401
from game import config
from ps2ee import Pine, PineNotRunning
from ps2ee.pnach import Pnach


def in_safe_zone(addr: int) -> bool:
    return config.SAFE_ZONE <= addr < config.SAFE_ZONE + config.SAFE_ZONE_SIZE


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pnach", nargs="?", default=str(config.WIP / "working.pnach"))
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

    # Trampoline bodies before the hooks that jump to them. Applying in file
    # order arms a jump into whatever the safe zone happened to contain, which
    # is a crash rather than a failed experiment.
    todo = [(g.name, line) for g in pnach.groups for line in g.lines
            if not line.is_condition and line.cpu == "EE"]
    todo.sort(key=lambda item: not in_safe_zone(item[1].target))

    applied = wrong = 0
    with pine:
        section = None
        for name, line in todo:
            zone = "safe zone" if in_safe_zone(line.target) else "hooks"
            if zone != section:
                section = zone
                print(f"\n# {zone}")
            cur = pine.read(line.target)
            ok = cur == line.value
            if args.check:
                print(f"  {line.target:08X}  {cur:08X}  {'ok' if ok else 'MISSING'}"
                      f"   [{name}]")
                wrong += 0 if ok else 1
                continue
            if not ok:
                pine.write(line.target, line.value)
                now = pine.read(line.target)
                print(f"  {line.target:08X}  {cur:08X} -> {now:08X}"
                      f"{'' if now == line.value else '   WRITE FAILED'}   [{name}]")
                applied += 1
            else:
                print(f"  {line.target:08X}  already correct   [{name}]")
    print(f"\n{'missing: '+str(wrong) if args.check else 'wrote '+str(applied)+' words'}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

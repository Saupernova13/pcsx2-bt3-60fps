"""Install a pnach into PCSX2 and enable it, so the user only has to launch.

    python tools/deploy.py patches/428113C2.pnach
    python tools/deploy.py patches/exp/003-halve-anim.pnach --only 60FPS
    python tools/deploy.py --off                 # disable every cheat
    python tools/deploy.py --status
"""

import argparse
import shutil
from datetime import datetime

import _bootstrap  # noqa: F401

from ps2ee import config
from ps2ee.pine import Pine, PineNotRunning
from ps2ee.pnach import Pnach, _set_enabled_cheats, deploy


def emulator_running() -> bool:
    """True if a PCSX2 with PINE enabled is answering right now."""
    try:
        with Pine().connect():
            return True
    except (PineNotRunning, OSError):
        return False


def show_status() -> int:
    cheats = config.cheats_dir() / f"{config.CRC}.pnach"
    print(f"PCSX2      {config.pcsx2_dir()}")
    print(f"cheat file {cheats}  {'(present)' if cheats.exists() else '(absent)'}")
    if cheats.exists():
        for group in Pnach.load(cheats).groups:
            print(f"  [{group.name}]  {len(group.lines)} lines  {group.description}")
    ini = config.game_ini()
    print(f"game ini   {ini}")
    if ini.exists():
        for line in ini.read_text(errors="replace").splitlines():
            if line.strip().lower().startswith("enable"):
                print(f"  {line.strip()}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("pnach", nargs="?", help="pnach file to install")
    parser.add_argument("--only", action="append", default=None,
                        metavar="GROUP", help="enable just these groups (repeatable)")
    parser.add_argument("--off", action="store_true", help="disable all cheats")
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force-development", action="store_true",
                        help="enable groups that must never ship (experiments only)")
    args = parser.parse_args()

    if args.status:
        return show_status()

    if args.off:
        _set_enabled_cheats(config.game_ini(), [])
        print(f"All cheats disabled in {config.game_ini()}")
        return 0

    if not args.pnach:
        parser.error("give a pnach path, or use --off / --status")

    source = Pnach.load(args.pnach)
    problems = source.validate()
    if problems:
        print("VALIDATION FAILED")
        for problem in problems:
            print(f"  {problem}")
        return 1

    groups = args.only if args.only else [g.name for g in source.groups
                                          if g.name not in config.OPTIONAL]

    # Handing this the WORKING pnach enables every group in it, five of which
    # must never be on in a real install: two withdrawn blast groups, the state
    # 157 trap, an experiment that breaks ground movement, and `animation rate`,
    # which together with `animation clock` gives quarter-speed animation. That
    # is how an install ends up "broken beyond belief", and it is silent -
    # everything looks deployed. Deploy releases/latest/ instead.
    poison = [n for n in groups if n in config.NEVER_SHIP]
    if poison and not args.force_development:
        print(f"{args.pnach}")
        print("")
        print("  REFUSING to enable groups that must never ship:")
        for name in poison:
            print(f"     {name}")
        print("")
        print("  This looks like the working pnach. Deploy the export instead:")
        print("     python tools/export.py --release <name>")
        print("     python tools/deploy.py releases/latest/428113C2.pnach")
        print("")
        print("  --only NAME deploys a chosen subset; --force-development")
        print("  overrides this, and is only right for a deliberate experiment.")
        return 1

    print(f"{args.pnach}")
    for group in source.groups:
        state = "ON " if group.name in groups else "off"
        print(f"  [{state}] [{group.name}]  {len(group.lines)} lines")

    if args.dry_run:
        print("\n(dry run - nothing written)")
        return 0

    # Keep whatever was previously installed; these are cheap and easy to lose.
    dest = config.cheats_dir() / f"{config.CRC}.pnach"
    if dest.exists():
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup = config.WORK / "cheat-backups" / f"{config.CRC}.{stamp}.pnach"
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(dest, backup)
        print(f"\n  previous cheat file backed up to {backup}")

    written, enabled = deploy(source, enable=groups)
    print(f"  installed  {written}")
    print(f"  enabled    {', '.join(enabled) if enabled else '(none)'}")
    print(f"  ini        {config.game_ini()}")

    # PCSX2 reads the cheat file and the per-game ini once, at boot. Deploying
    # under a running emulator therefore changes nothing the player can see,
    # and the next test reports "no difference" for a patch that was never
    # loaded. Say so loudly rather than let that be found by playing.
    if emulator_running():
        print("")
        print("  !! PCSX2 IS RUNNING - it will not see any of this.")
        print("     Quit PCSX2 completely and relaunch. A reset or a")
        print("     save-state load is NOT enough: the cheat file is read")
        print("     at boot. Then check with tools/apply-live.py --check")
        return 0
    print("\nReady - launch PCSX2, boot BT3, load your save state.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

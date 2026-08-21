"""Inspect and adjust the PCSX2 settings this workflow depends on.

    python tools/setup-pcsx2.py                  # report only
    python tools/setup-pcsx2.py --enable-pine
    python tools/setup-pcsx2.py --disable-pine
"""

import argparse
import shutil
from datetime import datetime
from pathlib import Path

import _bootstrap  # noqa: F401

from ps2ee import config
from ps2ee.pine import Pine


def read_setting(path: Path, section: str, key: str) -> str | None:
    if not path.exists():
        return None
    in_section = False
    for line in path.read_text(errors="replace").splitlines():
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            in_section = stripped.lower() == section.lower()
            continue
        if in_section and "=" in stripped:
            name, _, value = stripped.partition("=")
            if name.strip().lower() == key.lower():
                return value.strip()
    return None


def write_setting(path: Path, section: str, key: str, value: str) -> None:
    """Set one key in one section, preserving everything else byte for byte."""
    text = path.read_text(errors="replace")
    lines = text.splitlines()
    out, in_section, done = [], False, False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            if in_section and not done:
                out.append(f"{key} = {value}")
                done = True
            in_section = stripped.lower() == section.lower()
            out.append(line)
            continue
        if in_section and "=" in stripped:
            name = stripped.split("=", 1)[0].strip()
            if name.lower() == key.lower():
                out.append(f"{key} = {value}")
                done = True
                continue
        out.append(line)
    if not done:
        if in_section:
            out.append(f"{key} = {value}")
        else:
            out += ["", section, f"{key} = {value}"]
    path.write_text("\n".join(out).rstrip() + "\n", newline="\n")


def backup(path: Path) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    dest = config.WORK / "ini-backups" / f"{path.name}.{stamp}"
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, dest)
    return dest


def report() -> None:
    ini = config.global_ini()
    game = config.game_ini()
    print(f"PCSX2 dir     {config.pcsx2_dir()}")
    print(f"global ini    {ini}")
    print(f"  EnablePINE               {read_setting(ini, '[EmuCore]', 'EnablePINE')}")
    print(f"  PINESlot                 {read_setting(ini, '[EmuCore]', 'PINESlot')}")
    print(f"  EnableCheats             {read_setting(ini, '[EmuCore]', 'EnableCheats')}")
    print(f"  EnablePatches            {read_setting(ini, '[EmuCore]', 'EnablePatches')}")
    print(f"  EnableWideScreenPatches  {read_setting(ini, '[EmuCore]', 'EnableWideScreenPatches')}")
    print(f"\ngame ini      {game}")
    if game.exists():
        for line in game.read_text(errors="replace").splitlines():
            if line.strip():
                print(f"  {line.rstrip()}")

    port_setting = read_setting(ini, "[EmuCore]", "PINESlot") or "28011"
    live = Pine.available(int(port_setting))
    print(f"\nPINE socket   {'reachable' if live else 'not reachable'} on 127.0.0.1:{port_setting}")
    if not live:
        print("  (expected unless PCSX2 is running right now with a game booted)")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--enable-pine", action="store_true")
    parser.add_argument("--disable-pine", action="store_true")
    args = parser.parse_args()

    ini = config.global_ini()
    if args.enable_pine or args.disable_pine:
        value = "true" if args.enable_pine else "false"
        saved = backup(ini)
        write_setting(ini, "[EmuCore]", "EnablePINE", value)
        print(f"EnablePINE = {value}")
        print(f"  backup of the previous ini: {saved}")
        print("  PCSX2 reads this at startup - restart it if it is running.\n")

    report()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

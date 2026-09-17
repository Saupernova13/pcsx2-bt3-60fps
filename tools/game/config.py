"""This game's config: repo paths, patch policy, and the bound identity.

Imports the generic discovery config from the sibling pcsxroo checkout's
ps2ee, binds this game's identity, then re-exports the generic functions so
tools keep reading ``from game import config`` the way they read the old
``from ps2ee import config``.
"""

from __future__ import annotations

import os
from pathlib import Path

from ps2ee import config as _generic

from game import identity

REPO = Path(__file__).resolve().parent.parent.parent
WORK = REPO / "work"
PATCHES = REPO / "patch"
WIP = REPO / "wip"

# This repo's overrides come from ITS local.json, not pcsxroo's.
_generic.LOCAL_JSON = REPO / "local.json"

_generic.bind(identity.IDENTITY)

# Game constants as module-level names, so the tools stay unchanged.
SERIAL = identity.SERIAL
CRC = identity.CRC
ELF_NAME = identity.ELF_NAME
GAME = identity.GAME
TEXT_BASE = identity.TEXT_BASE
TEXT_END = identity.TEXT_END
DATA_BASE = identity.DATA_BASE
BSS_END = identity.BSS_END
GP_BASE = identity.GP_BASE
SAFE_ZONE = identity.SAFE_ZONE
SAFE_ZONE_SIZE = identity.SAFE_ZONE_SIZE
EE_RAM_SIZE = _generic.EE_RAM_SIZE
NEVER_SHIP = identity.NEVER_SHIP
OPTIONAL = identity.OPTIONAL
EXCLUSIVE = identity.EXCLUSIVE

# Re-export the generic discovery, identity-driven helpers.
from ps2ee.config import (  # noqa: E402, F401
    _setting,
    cheats_dir,
    game_ini,
    global_ini,
    latest_state,
    pcsx2_dir,
    pcsxroo_dir,
    roo_cheat_file,
    roo_enabled_cheats,
    roo_game_ini,
    roo_snaps_dir,
    sstates_dir,
)


def elf_path() -> Path:
    """Where tools/extract-elf.py drops the extracted boot ELF."""
    return WORK / ELF_NAME


def game_image() -> Path:
    """The BT3 disc image (.cso, .iso or .chd)."""
    explicit = _setting("GAME_IMAGE")
    if explicit:
        return Path(explicit)
    roots = [Path(p) for p in _setting("ROM_DIRS", "").split(os.pathsep) if p]
    if not roots:
        # Fall back to whatever PCSX2 itself has been told about.
        roots = _rom_dirs_from_ini()
    for root in roots:
        for pattern in ("*Tenkaichi 3*.cso", "*Tenkaichi 3*.iso", "*Tenkaichi 3*.chd"):
            for hit in sorted(root.rglob(pattern)):
                return hit
    raise FileNotFoundError(
        "Could not locate the BT3 disc image. Set GAME_IMAGE in the "
        "environment or in local.json."
    )


def _rom_dirs_from_ini() -> list[Path]:
    ini = global_ini()
    if not ini.exists():
        return []
    dirs, in_section = [], False
    for line in ini.read_text(errors="replace").splitlines():
        stripped = line.strip()
        if stripped.startswith("["):
            in_section = stripped.lower() == "[gamelist]"
            continue
        if in_section and "=" in stripped:
            value = stripped.split("=", 1)[1].strip()
            if value and Path(value).is_dir():
                dirs.append(Path(value))
    return dirs

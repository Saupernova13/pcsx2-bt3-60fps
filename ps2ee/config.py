"""Project paths and target-game constants.

Every path is discovered from the environment or a local override file so the
repo stays portable. Nothing machine-specific is hardcoded as a default that
would break on another install.

Override any value with an environment variable of the same name, or by
creating a ``local.json`` next to this package's parent directory:

    {"PCSX2_DIR": "D:/emu/PCSX2", "GAME_IMAGE": "D:/roms/bt3.iso"}
"""

from __future__ import annotations

import json
import os
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
WORK = REPO / "work"
PATCHES = REPO / "patch"
DEV_PNACH = REPO / "dev" / "pnach"

# --- target game -----------------------------------------------------------

SERIAL = "SLUS-21678"

# Groups that exist in the working pnach and must NEVER be enabled in a real
# install. Two of them are withdrawn because gating deleted the beam, one is the
# state 157 trap, one deliberately breaks ground movement, and `animation rate`
# is a superseded alternative to `animation clock` - both on together give
# QUARTER speed animation. Handing the working pnach to deploy.py enables every
# group in it, which is exactly how an install ends up broken beyond belief.
# Groups that belong in a shared copy but must NOT be switched on for you.
# A display-aspect hack is a preference, not a fix, and this one additionally
# conflicts with PCSX2's own [Widescreen 16:9] - both write the same three
# addresses every frame. Installed, listed, off until the user says otherwise.
OPTIONAL = [
    "Widescreen 19.5:9 - S24 Ultra",
]

NEVER_SHIP = [
    "60FPS - animation rate",
    "60FPS - EXPERIMENT halve root motion",
    "60FPS - blast effect rate",
    "60FPS - blast sequence rate",
    "60FPS - state phase timers",
]

CRC = "428113C2"
ELF_NAME = "SLUS_216.78"
GAME = "Dragon Ball Z: Budokai Tenkaichi 3 (USA)"

# ELF load layout, confirmed against a live save state (see docs/findings.md).
TEXT_BASE = 0x00100000
TEXT_END = 0x002C33C0
DATA_BASE = 0x002C3400
BSS_END = 0x00334BF8

# $gp is set once at boot and never changes, so gp-relative loads resolve to
# fixed addresses. Read out of a live save state.
GP_BASE = 0x00304270

# Guide Section 7 safe zone. Verified zero-filled in a mid-battle save state.
SAFE_ZONE = 0x000F0000
SAFE_ZONE_SIZE = 0x8000

EE_RAM_SIZE = 32 * 1024 * 1024

# --- discovery -------------------------------------------------------------

_CANDIDATE_PCSX2_DIRS = [
    Path(os.environ.get("APPDATA", "")) / "EmuDeck" / "Emulators" / "PCSX2-Qt",
    Path(os.environ.get("APPDATA", "")) / "PCSX2",
    Path(os.environ.get("USERPROFILE", "")) / "Documents" / "PCSX2",
]

_local_cache: dict | None = None


def _local() -> dict:
    global _local_cache
    if _local_cache is None:
        path = REPO / "local.json"
        _local_cache = json.loads(path.read_text()) if path.exists() else {}
    return _local_cache


def _setting(name: str, default=None):
    if name in os.environ:
        return os.environ[name]
    if name in _local():
        return _local()[name]
    return default


def pcsx2_dir() -> Path:
    """Root of the PCSX2 install (the one holding inis/, cheats/, sstates/)."""
    explicit = _setting("PCSX2_DIR")
    if explicit:
        return Path(explicit)
    for candidate in _CANDIDATE_PCSX2_DIRS:
        if (candidate / "inis" / "PCSX2.ini").exists():
            return candidate
    raise FileNotFoundError(
        "Could not locate a PCSX2 install. Set PCSX2_DIR in the environment "
        "or in local.json."
    )


def cheats_dir() -> Path:
    return pcsx2_dir() / "cheats"


def sstates_dir() -> Path:
    return pcsx2_dir() / "sstates"


def game_ini() -> Path:
    return pcsx2_dir() / "gamesettings" / f"{SERIAL}_{CRC}.ini"


def global_ini() -> Path:
    return pcsx2_dir() / "inis" / "PCSX2.ini"


def game_image() -> Path:
    """The BT3 disc image (.cso or .iso)."""
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


def elf_path() -> Path:
    """Where tools/extract-elf.py drops the extracted boot ELF."""
    return WORK / ELF_NAME


def latest_state(slot: int | None = None) -> Path:
    """Most recent BT3 save state, optionally pinned to one slot."""
    pattern = (
        f"{SERIAL} ({CRC}).{slot:02d}.p2s" if slot is not None
        else f"{SERIAL} ({CRC}).*.p2s"
    )
    hits = [p for p in sstates_dir().glob(pattern) if p.suffix == ".p2s"]
    if not hits:
        raise FileNotFoundError(f"No save state matching {pattern}")
    return max(hits, key=lambda p: p.stat().st_mtime)


# --- PCSXROO ---------------------------------------------------------------
# The fork that exposes the debugger over a socket. It runs in portable mode,
# so its cheats/, sstates/ and snaps/ live next to the executable and are
# entirely separate from the PCSX2 install above.

_CANDIDATE_PCSXROO_DIRS = [
    REPO.parent / "pcsxroo" / "bin",
    REPO.parent / "PCSXROO" / "bin",
]


def pcsxroo_dir() -> Path:
    explicit = _setting("PCSXROO_DIR")
    if explicit:
        return Path(explicit)
    for candidate in _CANDIDATE_PCSXROO_DIRS:
        if (candidate / "pcsxroo.exe").exists():
            return candidate
    raise FileNotFoundError(
        "Could not locate PCSXROO. Set PCSXROO_DIR in the environment or in "
        "local.json."
    )


def roo_cheat_file() -> Path:
    return pcsxroo_dir() / "cheats" / f"{CRC}.pnach"


def roo_snaps_dir() -> Path:
    return pcsxroo_dir() / "snaps"


def roo_game_ini() -> Path:
    """PCSXROO's own per-game settings, which is NOT game_ini().

    game_ini() points at the user's installed PCSX2 (EmuDeck). PCSXROO is a
    separate, portable build and keeps its per-game settings under its data
    root, not under inis/. The [Cheats] Enable list there is read at boot and is
    what decides whether a pnach group applies at all - a group missing from it
    is silently ignored, however correct the pnach is.
    """
    return pcsxroo_dir() / "gamesettings" / f"{SERIAL}_{CRC}.ini"


def roo_enabled_cheats() -> list[str]:
    """The group names PCSXROO will honour, as of its last boot."""
    path = roo_game_ini()
    if not path.exists():
        return []
    names, in_cheats = [], False
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            in_cheats = stripped.lower() == "[cheats]"
            continue
        if in_cheats and stripped.lower().startswith("enable"):
            names.append(stripped.split("=", 1)[1].strip())
    return names


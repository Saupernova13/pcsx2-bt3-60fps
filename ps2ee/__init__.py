"""Tooling for PS2 60fps patch development against Budokai Tenkaichi 3.

    from ps2ee import config, EEMemory, Scan, Pnach, Pine

    mem = EEMemory.from_state(config.latest_state())
    print(render(window(mem, 0x00264DBC), mark=0x00264DBC))
"""

from . import config  # noqa: F401
from .asm import PatchBuilder, SafeZone, Trampoline, assemble  # noqa: F401
from .diff import Region, Scan  # noqa: F401
from .disasm import (  # noqa: F401
    callers,
    disasm,
    function_body,
    function_end,
    function_start,
    render,
    scan_immediates,
    window,
)
from .eemem import EEMemory, ElfImage  # noqa: F401
from .pine import Pine, PineNotRunning  # noqa: F401
from .pnach import Group, Line, Pnach, deploy  # noqa: F401
from .savestate import SaveState  # noqa: F401

__all__ = [
    "config",
    "EEMemory",
    "ElfImage",
    "SaveState",
    "Scan",
    "Region",
    "Pnach",
    "Group",
    "Line",
    "deploy",
    "Pine",
    "PineNotRunning",
    "PatchBuilder",
    "SafeZone",
    "Trampoline",
    "assemble",
    "disasm",
    "window",
    "render",
    "callers",
    "function_start",
    "function_end",
    "function_body",
    "scan_immediates",
]

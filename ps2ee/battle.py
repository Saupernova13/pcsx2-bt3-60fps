"""The live battle, resolved over PCSXROO: fighters, models, and their fields.

``ps2ee.fighter`` does the same job over PINE and is kept for the scripts that
already use it. This one exists because the debugger client can also stop the
CPU, so everything built on top of it - watchpoints, frame-precise capture -
needs the same resolution without a second dependency.

Offsets recovered by write watchpoint rather than by reading disassembly; see
docs/findings.md for which routine writes which field.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass

from .roo import Roo

MANAGER = 0x002FEB14        # $gp-0x575c, null outside a fight
MODEL_TABLE = 0x0031C640
STRIDE = 0x1600             # 11 << 9, from the index maths in FUN_001DC178
FRAME_COUNTER = 0x00331D64  # one per game tick, so 30Hz stock and 60Hz patched

# --- fighter fields, four floats each unless noted ------------------------

PAD_INDEX = 0x0004          # u32: which controller drives this fighter
MODEL_ID = 0x000C           # u32: index into MODEL_TABLE, not a pointer
POS = 0x0010                # world position, w = 1
ANCHOR = 0x0030             # model+0x950 = POS + this
VEL = 0x0050                # last frame's displacement, a follower not a cause
RESIDUAL = 0x0080           # decaying slide, added whole then shrunk by an eps
AIR_DIR = 0x0090            # unit direction of airborne travel
AIR_SPEED = 0x00A8          # f32: airborne units per tick, along AIR_DIR
AIR_VSPEED = 0x00AC         # f32: vertical units per tick, added to POS.y

# --- model fields ---------------------------------------------------------

ROOT_PREV = 0x0950          # skeleton input:  where the root bone was
ROOT_NOW = 0x0970           # skeleton output: where the root bone is now
MATRIX_T = 0x09D0           # translation row of the world matrix


class NoBattle(RuntimeError):
    """The fighter manager is null - no fight is running."""


@dataclass(frozen=True)
class Pair:
    index: int
    fighter: int
    model: int

    def __str__(self) -> str:
        return f"F{self.index} {self.fighter:08X} M{self.index} {self.model:08X}"


def resolve(roo: Roo) -> list[Pair]:
    manager = roo.read(MANAGER)
    if not manager:
        raise NoBattle(f"{MANAGER:08X} is null - start a fight first")
    count, base = roo.read(manager), roo.read(manager + 4)
    return [
        Pair(i, base + i * STRIDE,
             roo.read(MODEL_TABLE + roo.read(base + i * STRIDE + MODEL_ID) * 4))
        for i in range(count)
    ]


def vec(roo: Roo, addr: int) -> tuple[float, float, float, float]:
    return struct.unpack("<4f", roo.read_bytes(addr, 16))


def norm(v) -> float:
    """Length of the first three components; the fourth is homogeneous."""
    return sum(x * x for x in v[:3]) ** 0.5


def delta(a, b) -> list[float]:
    return [x - y for x, y in zip(a[:3], b[:3])]


def fmt(v) -> str:
    return "(" + " ".join(f"{x:9.4f}" for x in v[:3]) + ")"

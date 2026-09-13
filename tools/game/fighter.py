"""The battle's fighter objects, resolved live.

Everything the combat code does is a method on one of these. The animation
rate this project already patches is a field inside one (``+0xC80``), and the
move-timing windows are frame counters inside one too, so being able to read a
whole fighter out of a running game is what makes those findable.

Layout recovered from ``FUN_001DC168`` / ``FUN_001DC178``:

    manager    = *(u32*)MANAGER_PTR
    count      = *(u32*)(manager + 0x00)
    fighter[i] = *(u32*)(manager + 0x04) + i * STRIDE
"""

from __future__ import annotations

from dataclasses import dataclass

from ps2ee.pine import Pine

# $gp - 0x575c. Set once at boot; holds the battle manager, or 0 outside a fight.
MANAGER_PTR = 0x002FEB14

STRIDE = 0x1600          # 11 << 9, from the index maths in FUN_001DC178
SIZE = STRIDE            # the readable extent of one fighter

PAD_INDEX = 0x0004       # which controller slot drives this fighter
SLOT_ID = 0x0008         # the id FUN_001DC210 searches on
MODEL_ID = 0x000C        # an index, not a pointer: FUN_002499B0 maps it to the model

# The fighter's own input block, maintained by FUN_001D4A70/FUN_001D4A00.
# Combat keeps edge state here rather than reading the shared globals at
# 0x00333988, which is why the shared ones have no gameplay readers.
INPUT = 0x0570
RAW_BUTTONS = INPUT + 0x000
CUR_A = INPUT + 0x1CC
PREV_A = INPUT + 0x1D0
NEWPRESS_A = INPUT + 0x1D4
RELEASED_A = INPUT + 0x1D8
CUR_B = INPUT + 0x1DC
PREV_B = INPUT + 0x1E0
NEWPRESS_B = INPUT + 0x1E4
RELEASED_B = INPUT + 0x1E8

# The animation rate the 60fps patch halves is +0xC80 on the object
# FUN_001DC280 returns, NOT on the fighter - resolving it needs FUN_002499B0,
# so it cannot be read by offsetting the fighter base.
ANIM_RATE_ON_MODEL = 0x0C80

FRAME_COUNTER = 0x00331D64   # advances once per FrameStep


class NoBattle(RuntimeError):
    """The fighter manager is null - not in a fight."""


@dataclass
class Fighter:
    index: int
    base: int
    words: list[int]

    def u32(self, offset: int) -> int:
        return self.words[offset // 4]

    def i32(self, offset: int) -> int:
        value = self.u32(offset)
        return value - 0x100000000 if value & 0x80000000 else value


def manager(pine: Pine) -> int:
    base = pine.read(MANAGER_PTR)
    if not base:
        raise NoBattle(
            f"{MANAGER_PTR:08X} is null - no battle is running. Start a fight first."
        )
    return base


def bases(pine: Pine) -> list[int]:
    """Address of each live fighter."""
    root = manager(pine)
    count = pine.read(root)
    array = pine.read(root + 4)
    if not 0 < count <= 8 or not array:
        raise NoBattle(f"implausible fighter list: count={count} array={array:08X}")
    return [array + i * STRIDE for i in range(count)]


def read(pine: Pine, base: int, index: int = 0, size: int = SIZE,
         chunk: int = 512) -> Fighter:
    """One fighter's whole struct.

    Chunked because a single PINE packet carrying 1400 read commands is large
    enough to be worth not finding out about the hard way.
    """
    words: list[int] = []
    for start in range(0, size // 4, chunk):
        n = min(chunk, size // 4 - start)
        words += pine.read_block(base + start * 4, n)
    return Fighter(index, base, words)


def read_all(pine: Pine, **kwargs) -> list[Fighter]:
    return [read(pine, base, i, **kwargs) for i, base in enumerate(bases(pine))]

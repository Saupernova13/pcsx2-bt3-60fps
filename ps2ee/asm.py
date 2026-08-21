"""MIPS assembler for safe-zone hook code.

Writing trampolines as raw pnach hex words is where these patches go wrong.
This module lets a fix be written as assembly, assembled with keystone, and
emitted as pnach lines with the hook jumps computed for us.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field

from keystone import KS_ARCH_MIPS, KS_MODE_LITTLE_ENDIAN, KS_MODE_MIPS64, Ks, KsError

from . import config
from .disasm import j_word, jal_word

_ks = Ks(KS_ARCH_MIPS, KS_MODE_MIPS64 | KS_MODE_LITTLE_ENDIAN)

# Without these the LLVM assembler behind keystone silently rewrites our code:
# 'reorder' invents a nop after every branch (so a hand-written delay slot
# becomes a second instruction and the layout shifts), 'macro' expands pseudo
# instructions into multi-instruction sequences, and 'at' lets it clobber $at -
# the register these float-constant patches deliberately use.
_PRELUDE = ".set noreorder\n.set nomacro\n.set noat\n"


class AsmError(RuntimeError):
    pass


def assemble(source: str, addr: int = 0) -> list[int]:
    """Assemble MIPS source into a list of 32-bit words.

    Delay slots are yours to fill: nothing is reordered and no nop is inserted.
    """
    try:
        encoding, _count = _ks.asm(_PRELUDE + source, addr)
    except KsError as exc:
        raise AsmError(f"{exc} while assembling at {addr:08X}:\n{source}") from exc
    if encoding is None:
        raise AsmError(f"keystone produced nothing for:\n{source}")
    raw = bytes(encoding)
    if len(raw) % 4:
        raise AsmError(f"assembled {len(raw)} bytes, not a whole number of words")
    return list(struct.unpack(f"<{len(raw) // 4}I", raw))


def float_bits(value: float) -> int:
    return struct.unpack("<I", struct.pack("<f", value))[0]


def lui_for(value: float) -> int:
    """Word for 'lui $at, <upper half of this float>'.

    Only valid for floats whose low 16 bits are zero, which covers the
    constants this work uses: 0.5, 1.0, 2.0.
    """
    bits = float_bits(value)
    if bits & 0xFFFF:
        raise ValueError(f"{value} needs both halves; lui alone cannot load it")
    return 0x3C010000 | (bits >> 16)


@dataclass
class Block:
    """A run of words destined for one address."""

    addr: int
    words: list[int]
    comment: str = ""


@dataclass
class Trampoline:
    """A hook that redirects one instruction into safe-zone code.

    ``hook_at``   instruction we overwrite in the game's own code
    ``body``      assembly placed in the safe zone
    ``kind``      "j" for a tail jump, "jal" to keep $ra for a return
    ``delay``     assembly for the hook's delay slot; defaults to nop
    """

    hook_at: int
    body: str
    kind: str = "j"
    delay: str = "nop"
    comment: str = ""
    at: int | None = None      # explicit safe-zone address, else allocated


class SafeZone:
    """Bump allocator over the guide's 0x000F0000 scratch region."""

    def __init__(self, base: int = config.SAFE_ZONE, size: int = config.SAFE_ZONE_SIZE):
        self.base = base
        self.size = size
        self.cursor = base

    def alloc(self, n_words: int, align: int = 0x10) -> int:
        addr = (self.cursor + align - 1) & ~(align - 1)
        end = addr + n_words * 4
        if end > self.base + self.size:
            raise AsmError(
                f"safe zone exhausted: need {end - self.base} bytes, have {self.size}"
            )
        self.cursor = end
        return addr

    def reserve(self, addr: int, n_bytes: int) -> int:
        """Claim a fixed address (for toggle flags and counters)."""
        self.cursor = max(self.cursor, addr + n_bytes)
        return addr


class PatchBuilder:
    """Collects raw word writes and trampolines, resolves them to blocks."""

    def __init__(self, zone: SafeZone | None = None):
        self.zone = zone or SafeZone()
        self.blocks: list[Block] = []

    def word(self, addr: int, value: int, comment: str = "") -> "PatchBuilder":
        self.blocks.append(Block(addr, [value], comment))
        return self

    def asm_at(self, addr: int, source: str, comment: str = "") -> "PatchBuilder":
        self.blocks.append(Block(addr, assemble(source, addr), comment))
        return self

    def data(self, addr: int, words: list[int], comment: str = "") -> "PatchBuilder":
        self.blocks.append(Block(addr, words, comment))
        return self

    def trampoline(self, tramp: Trampoline) -> int:
        """Install a hook. Returns the safe-zone address the body landed at."""
        # Assemble once at a provisional address to learn the size, then place
        # it and assemble again so PC-relative operands resolve correctly.
        provisional = assemble(tramp.body, self.zone.cursor)
        target = tramp.at if tramp.at is not None else self.zone.alloc(len(provisional))
        words = assemble(tramp.body, target)

        hook = j_word(target) if tramp.kind == "j" else jal_word(target)
        delay_words = assemble(tramp.delay, tramp.hook_at + 4)
        if len(delay_words) != 1:
            raise AsmError("a delay slot holds exactly one instruction")

        label = tramp.comment or f"hook {tramp.hook_at:08X} -> {target:08X}"
        self.blocks.append(Block(tramp.hook_at, [hook], label))
        self.blocks.append(Block(tramp.hook_at + 4, delay_words, "delay slot"))
        self.blocks.append(Block(target, words, f"body of {label}"))
        return target

    def to_pnach(self) -> list[str]:
        """Flatten to pnach 'patch=' lines, one per 32-bit word."""
        lines: list[str] = []
        for block in self.blocks:
            if block.comment:
                lines.append(f"// {block.comment}")
            for i, word in enumerate(block.words):
                addr = block.addr + i * 4
                lines.append(f"patch=1,EE,{addr:08X},extended,{word:08X}")
        return lines

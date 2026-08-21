"""A view over EE main memory, from a save state, a raw dump, or the ELF.

Addresses are always given the way pnach gives them: a physical EE address
such as 0x00264DBC. Segment bits (0x2000_0000 / 0x8000_0000) are masked off,
so 0x20264DBC and 0x00264DBC address the same word.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from pathlib import Path

from . import config

EE_MASK = 0x01FFFFFF


def normalise(addr: int) -> int:
    """Strip segment bits to get an offset into the 32 MB RAM image."""
    return addr & EE_MASK


@dataclass
class Segment:
    vaddr: int
    data: bytes

    @property
    def end(self) -> int:
        return self.vaddr + len(self.data)


class EEMemory:
    """32 MB of EE RAM with word/half/byte accessors."""

    def __init__(self, data: bytes, source: str = "?"):
        if len(data) != config.EE_RAM_SIZE:
            raise ValueError(
                f"expected {config.EE_RAM_SIZE} bytes of EE RAM, got {len(data)}"
            )
        self.data = data
        self.source = source

    # --- constructors ------------------------------------------------------

    @classmethod
    def from_state(cls, path: str | Path) -> "EEMemory":
        from .savestate import SaveState

        with SaveState(path) as state:
            return cls(state.ee, source=str(path))

    @classmethod
    def from_dump(cls, path: str | Path) -> "EEMemory":
        return cls(Path(path).read_bytes(), source=str(path))

    # --- reads -------------------------------------------------------------

    def bytes(self, addr: int, length: int) -> bytes:
        off = normalise(addr)
        return self.data[off : off + length]

    def u8(self, addr: int) -> int:
        return self.data[normalise(addr)]

    def u16(self, addr: int) -> int:
        return struct.unpack_from("<H", self.data, normalise(addr))[0]

    def u32(self, addr: int) -> int:
        return struct.unpack_from("<I", self.data, normalise(addr))[0]

    def i32(self, addr: int) -> int:
        return struct.unpack_from("<i", self.data, normalise(addr))[0]

    def u64(self, addr: int) -> int:
        return struct.unpack_from("<Q", self.data, normalise(addr))[0]

    def f32(self, addr: int) -> float:
        return struct.unpack_from("<f", self.data, normalise(addr))[0]

    def words(self, start: int, end: int):
        """Yield (address, word) across a half-open address range."""
        for addr in range(start, end, 4):
            yield addr, self.u32(addr)

    # --- searching ---------------------------------------------------------

    def find(self, needle: bytes, start: int = 0, end: int | None = None) -> list[int]:
        """Every offset of a byte pattern, as EE addresses."""
        end = config.EE_RAM_SIZE if end is None else normalise(end)
        hits, at = [], normalise(start)
        while True:
            at = self.data.find(needle, at, end)
            if at < 0:
                return hits
            hits.append(at)
            at += 1

    def find_u32(self, value: int, start: int = 0, end: int | None = None) -> list[int]:
        return self.find(struct.pack("<I", value), start, end)

    def pointers_to(self, target: int, start: int = 0, end: int | None = None) -> list[int]:
        """Addresses holding a 32-bit pointer to ``target`` (any segment)."""
        found = []
        for seg in (0x00000000, 0x20000000, 0x80000000):
            found += self.find_u32((target & EE_MASK) | seg, start, end)
        return sorted(set(found))


class ElfImage:
    """The boot ELF, as loaded segments, for comparing against live RAM."""

    def __init__(self, raw: bytes, source: str = "?"):
        if raw[:4] != b"\x7fELF":
            raise ValueError("not an ELF")
        self.raw = raw
        self.source = source
        self.entry, phoff, _shoff = struct.unpack_from("<III", raw, 24)
        phentsize, phnum = struct.unpack_from("<HH", raw, 42)
        self.segments: list[Segment] = []
        for i in range(phnum):
            off = phoff + i * phentsize
            p_type, p_off, p_vaddr, _p_paddr, p_filesz, _p_memsz, _fl, _al = (
                struct.unpack_from("<8I", raw, off)
            )
            if p_type == 1 and p_filesz:  # PT_LOAD with file backing
                self.segments.append(
                    Segment(p_vaddr, raw[p_off : p_off + p_filesz])
                )

    @classmethod
    def load(cls, path: str | Path) -> "ElfImage":
        path = Path(path)
        return cls(path.read_bytes(), source=str(path))

    def segment_for(self, addr: int) -> Segment | None:
        addr = normalise(addr)
        for seg in self.segments:
            if seg.vaddr <= addr < seg.end:
                return seg
        return None

    def bytes(self, addr: int, length: int) -> bytes:
        seg = self.segment_for(addr)
        if seg is None:
            raise KeyError(f"{addr:08X} not in any loaded segment")
        off = normalise(addr) - seg.vaddr
        return seg.data[off : off + length]

    def u32(self, addr: int) -> int:
        return struct.unpack("<I", self.bytes(addr, 4))[0]

    def diff_against(self, mem: EEMemory) -> list[tuple[int, int, int]]:
        """Every byte where the loaded ELF disagrees with live RAM.

        A near-empty result means no overlays and no self-modifying code, so
        static analysis addresses map one-to-one onto pnach addresses.
        """
        out = []
        for seg in self.segments:
            live = mem.bytes(seg.vaddr, len(seg.data))
            for i, (a, b) in enumerate(zip(seg.data, live)):
                if a != b:
                    out.append((seg.vaddr + i, a, b))
        return out

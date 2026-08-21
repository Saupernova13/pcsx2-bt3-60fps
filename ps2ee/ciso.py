"""Random-access reader for CISO/ZISO disc images plus a minimal ISO9660 walker.

Lets us pull the ~2 MB boot ELF straight out of a 2 GB .cso without
decompressing the 3 GB ISO it expands to.
"""

from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass
from pathlib import Path

SECTOR = 2048


class DiscImage:
    """A .cso/.zso or plain .iso, addressed by 2048-byte LBA."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._f = open(self.path, "rb")
        magic = self._f.read(4)
        self._f.seek(0)
        if magic in (b"CISO", b"ZISO"):
            self._init_ciso(magic)
        else:
            self.compressed = False
            self.block_size = SECTOR
            self.total_bytes = self.path.stat().st_size
            self.n_blocks = self.total_bytes // SECTOR

    def _init_ciso(self, magic: bytes) -> None:
        header = self._f.read(24)
        _, _hdr_size, total, block_size, version, align = struct.unpack(
            "<4sIQIBB", header[:22]
        )
        self.compressed = True
        self.magic = magic
        self.version = version
        self.align = align
        self.block_size = block_size
        self.total_bytes = total
        self.n_blocks = total // block_size
        raw = self._f.read(4 * (self.n_blocks + 1))
        self.index = struct.unpack(f"<{self.n_blocks + 1}I", raw)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def close(self) -> None:
        self._f.close()

    def read_block(self, n: int) -> bytes:
        if n >= self.n_blocks:
            raise IndexError(f"block {n} beyond end of image ({self.n_blocks})")
        if not self.compressed:
            self._f.seek(n * self.block_size)
            return self._f.read(self.block_size)
        entry, nxt = self.index[n], self.index[n + 1]
        stored_plain = bool(entry & 0x80000000)
        start = (entry & 0x7FFFFFFF) << self.align
        end = (nxt & 0x7FFFFFFF) << self.align
        self._f.seek(start)
        # An aligned image can under-report the span; never read less than a block.
        data = self._f.read(max(end - start, self.block_size))
        if stored_plain:
            return data[: self.block_size]
        return zlib.decompressobj(-15).decompress(data, self.block_size)

    def read(self, lba: int, count: int = 1) -> bytes:
        return b"".join(self.read_block(lba + i) for i in range(count))

    def read_range(self, lba: int, length: int) -> bytes:
        blocks = (length + self.block_size - 1) // self.block_size
        return self.read(lba, blocks)[:length]


@dataclass
class DirEntry:
    name: str
    lba: int
    size: int
    is_dir: bool


def _parse_dir(data: bytes, length: int) -> list[DirEntry]:
    entries: list[DirEntry] = []
    i = 0
    while i < length:
        rec_len = data[i]
        if rec_len == 0:
            # Records never straddle a sector; skip to the next one.
            i = (i // SECTOR + 1) * SECTOR
            continue
        rec = data[i : i + rec_len]
        lba = struct.unpack("<I", rec[2:6])[0]
        size = struct.unpack("<I", rec[10:14])[0]
        flags = rec[25]
        name_len = rec[32]
        name = rec[33 : 33 + name_len].decode("ascii", "replace")
        if name not in ("\x00", "\x01"):
            entries.append(DirEntry(name, lba, size, bool(flags & 0x02)))
        i += rec_len
    return entries


def read_root(img: DiscImage) -> list[DirEntry]:
    """Directory listing for the image root, via the Primary Volume Descriptor."""
    pvd = img.read(16)
    if pvd[1:6] != b"CD001":
        raise ValueError("No ISO9660 Primary Volume Descriptor at LBA 16")
    root_rec = pvd[156:190]
    lba = struct.unpack("<I", root_rec[2:6])[0]
    size = struct.unpack("<I", root_rec[10:14])[0]
    return _parse_dir(img.read_range(lba, size), size)


def find(img: DiscImage, name: str) -> DirEntry:
    """Locate a root-level file, ignoring case and the ';1' version suffix."""
    wanted = name.upper().split(";")[0]
    for entry in read_root(img):
        if entry.name.upper().split(";")[0] == wanted:
            return entry
    raise FileNotFoundError(f"{name} not in image root")


def extract(img: DiscImage, name: str) -> bytes:
    entry = find(img, name)
    return img.read_range(entry.lba, entry.size)

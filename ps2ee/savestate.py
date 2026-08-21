"""Reader for PCSX2 .p2s save states.

A .p2s is a ZIP whose members use compression method 93 (Zstandard), which
Python's zipfile cannot decode before 3.14. We locate each member's raw bytes
from its local header and hand them to the zstandard module directly.
"""

from __future__ import annotations

import struct
import zipfile
from pathlib import Path

import zstandard

ZIP_ZSTD = 93

EE_MEMORY = "eeMemory.bin"
IOP_MEMORY = "iopMemory.bin"
SCRATCHPAD = "Scratchpad.bin"
SCREENSHOT = "Screenshot.png"


class SaveState:
    """Random access to the members of one PCSX2 save state."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._zip = zipfile.ZipFile(self.path)
        self._f = open(self.path, "rb")
        self._cache: dict[str, bytes] = {}

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def close(self) -> None:
        self._f.close()
        self._zip.close()

    def names(self) -> list[str]:
        return self._zip.namelist()

    def _raw(self, info: zipfile.ZipInfo) -> bytes:
        self._f.seek(info.header_offset)
        header = struct.unpack("<IHHHHHIIIHH", self._f.read(30))
        name_len, extra_len = header[9], header[10]
        self._f.seek(info.header_offset + 30 + name_len + extra_len)
        return self._f.read(info.compress_size)

    def read(self, name: str) -> bytes:
        if name in self._cache:
            return self._cache[name]
        info = self._zip.getinfo(name)
        if info.compress_type == ZIP_ZSTD:
            data = zstandard.ZstdDecompressor().decompress(
                self._raw(info), max_output_size=info.file_size
            )
        elif info.compress_type == zipfile.ZIP_STORED:
            data = self._raw(info)
        else:
            data = self._zip.read(name)
        if len(data) != info.file_size:
            raise ValueError(
                f"{name}: decompressed {len(data)} bytes, expected {info.file_size}"
            )
        self._cache[name] = data
        return data

    @property
    def ee(self) -> bytes:
        """The full 32 MB EE main memory image."""
        return self.read(EE_MEMORY)

    @property
    def iop(self) -> bytes:
        return self.read(IOP_MEMORY)

    @property
    def screenshot(self) -> bytes:
        return self.read(SCREENSHOT)

    def version(self) -> str:
        """Emulator version that wrote this state, e.g. 'v2.5.274'.

        Layout is a 4-byte savestate format magic followed by a null-padded
        ASCII version string and further binary fields.
        """
        raw = self.read("PCSX2 Savestate Version.id")
        return raw[4:].split(b"\x00", 1)[0].decode("ascii", "replace")

    def dump(self, name: str, dest: str | Path) -> Path:
        dest = Path(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(self.read(name))
        return dest


def load_ee(path: str | Path) -> bytes:
    """Convenience: just the EE RAM of one state."""
    with SaveState(path) as state:
        return state.ee

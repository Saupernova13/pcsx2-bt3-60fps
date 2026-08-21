"""Differential RAM scanning across save states.

This replaces PCSX2's GUI memory searcher for the guide's Section 1/3/4
techniques. Instead of clicking through scans, capture a save state per
condition and filter the whole 32 MB image at once.

    scan = Scan.from_states("a.p2s", "b.p2s")
    scan.eq(0, 0).then_eq(1, 1)      # was 0 in A, is 1 in B
    scan.increased()                 # counters that went up
    scan.addresses()
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from . import config
from .eemem import EEMemory, normalise

DTYPES = {
    "u8": np.uint8,
    "u16": np.uint16,
    "u32": np.uint32,
    "i8": np.int8,
    "i16": np.int16,
    "i32": np.int32,
    "f32": np.float32,
}


@dataclass
class Region:
    start: int
    end: int
    name: str = ""


# Scanning all 32 MB finds thousands of false positives in uninitialised and
# stack memory. These are the regions worth scanning by default.
GAME_REGIONS = [
    Region(config.DATA_BASE, config.BSS_END, "data+bss"),
    Region(config.BSS_END, 0x02000000, "heap"),
]


class Scan:
    """A candidate address set narrowed across two or more memory snapshots."""

    def __init__(self, snapshots: list[EEMemory], dtype: str = "u32",
                 regions: list[Region] | None = None):
        if len(snapshots) < 1:
            raise ValueError("need at least one snapshot")
        self.snapshots = snapshots
        self.dtype = dtype
        self.np_dtype = DTYPES[dtype]
        self.stride = np.dtype(self.np_dtype).itemsize
        self.regions = regions if regions is not None else list(GAME_REGIONS)

        self._views = [self._view(s) for s in snapshots]
        self._offsets = self._region_offsets()
        self.mask = np.ones(len(self._offsets), dtype=bool)

    @classmethod
    def from_states(cls, *paths: str | Path, dtype: str = "u32",
                    regions: list[Region] | None = None) -> "Scan":
        return cls([EEMemory.from_state(p) for p in paths], dtype, regions)

    def _view(self, mem: EEMemory) -> np.ndarray:
        return np.frombuffer(mem.data, dtype=self.np_dtype)

    def _region_offsets(self) -> np.ndarray:
        """Element indices (not byte addresses) covered by the scan regions."""
        chunks = []
        for region in self.regions:
            lo = normalise(region.start) // self.stride
            hi = normalise(region.end) // self.stride
            chunks.append(np.arange(lo, hi, dtype=np.int64))
        return np.concatenate(chunks) if chunks else np.empty(0, dtype=np.int64)

    # --- filters -----------------------------------------------------------

    def _snap(self, index: int) -> np.ndarray:
        return self._views[index][self._offsets]

    def _apply(self, predicate: np.ndarray) -> "Scan":
        self.mask &= predicate
        return self

    def value(self, snapshot: int, wanted) -> "Scan":
        """Value equals ``wanted`` in the given snapshot."""
        return self._apply(self._snap(snapshot) == wanted)

    def unchanged(self, a: int = 0, b: int = 1) -> "Scan":
        return self._apply(self._snap(a) == self._snap(b))

    def changed(self, a: int = 0, b: int = 1) -> "Scan":
        return self._apply(self._snap(a) != self._snap(b))

    def increased(self, a: int = 0, b: int = 1) -> "Scan":
        return self._apply(self._snap(b) > self._snap(a))

    def decreased(self, a: int = 0, b: int = 1) -> "Scan":
        return self._apply(self._snap(b) < self._snap(a))

    def delta(self, amount, a: int = 0, b: int = 1) -> "Scan":
        """Changed by exactly ``amount`` - the signature of a frame counter."""
        left = self._snap(b).astype(np.int64)
        right = self._snap(a).astype(np.int64)
        return self._apply((left - right) == amount)

    def between(self, low, high, snapshot: int = 0) -> "Scan":
        snap = self._snap(snapshot)
        return self._apply((snap >= low) & (snap <= high))

    def in_range(self, start: int, end: int) -> "Scan":
        """Keep only candidates whose address falls in a byte range."""
        addrs = self._offsets * self.stride
        return self._apply((addrs >= normalise(start)) & (addrs < normalise(end)))

    # --- results -----------------------------------------------------------

    def count(self) -> int:
        return int(self.mask.sum())

    def addresses(self, limit: int | None = None) -> list[int]:
        addrs = (self._offsets[self.mask] * self.stride).tolist()
        return addrs[:limit] if limit else addrs

    def rows(self, limit: int = 40) -> list[tuple[int, list]]:
        """(address, [value per snapshot]) for the surviving candidates."""
        out = []
        for addr in self.addresses(limit):
            index = normalise(addr) // self.stride
            out.append((addr, [view[index].item() for view in self._views]))
        return out

    def report(self, limit: int = 40) -> str:
        lines = [
            f"{self.count()} candidates ({self.dtype}) across "
            f"{len(self.snapshots)} snapshots"
        ]
        for addr, values in self.rows(limit):
            rendered = "  ".join(
                f"{v:>12}" if not isinstance(v, float) else f"{v:>12.4f}"
                for v in values
            )
            lines.append(f"  {addr:08X}  {rendered}")
        if self.count() > limit:
            lines.append(f"  ... {self.count() - limit} more")
        return "\n".join(lines)

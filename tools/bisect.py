"""Find the code that drives a live value, by disabling calls and watching it.

Write breakpoints do not always work here - the effect clocks are not written
by plain cached EE stores, so the PCSX2 memory breakpoint never trips on them.
But a value that ticks continuously is enough on its own: nop out one call at a
time, see whether it stops, and descend into whichever call owned it.

Every write is restored immediately and verified, and the frame counter is
checked after each test so a call that hangs the game is put back at once.

    python tools/bisect.py 01B1F038 --from 12B6E0
    python tools/bisect.py 01B1F038 --from 12B6E0 --depth 4
"""

import argparse
import struct
import time

import _bootstrap  # noqa: F401

from ps2ee import config
from ps2ee.disasm import decode, jump_target
from ps2ee.eemem import EEMemory, ElfImage
from ps2ee.pine import Pine, PineNotRunning

JR_RA = 0x03E00008
FRAME_COUNTER = 0x00331D64
f32 = lambda w: struct.unpack("<f", struct.pack("<I", w))[0]


def load_elf() -> EEMemory:
    elf = ElfImage.load(config.elf_path())
    buf = bytearray(config.EE_RAM_SIZE)
    for seg in elf.segments:
        buf[seg.vaddr:seg.end] = seg.data
    return EEMemory(bytes(buf), source="elf")


def call_sites(mem: EEMemory, entry: int, limit: int = 0x6000):
    """Every jal in a function, skipping ones whose result is consumed.

    Nopping a call whose return value the caller then uses does not test
    anything - it corrupts the caller. $v0/$v1 use within the next few
    instructions is the cheap signal for that.
    """
    out, at = [], entry
    ceiling = min(config.TEXT_END, entry + limit)
    while at < ceiling:
        word = mem.u32(at)
        if word == JR_RA:
            break
        if word >> 26 == 0x03:
            target = jump_target(word, at)
            if target and config.TEXT_BASE <= target < config.TEXT_END:
                if not _result_used(mem, at):
                    out.append((at, target))
        at += 4
    return out


def _result_used(mem: EEMemory, call: int, window: int = 4) -> bool:
    for a in range(call + 8, call + 8 + 4 * window, 4):
        word = mem.u32(a)
        for shift in (21, 16):
            if (word >> shift) & 31 in (2, 3):      # $v0, $v1
                return True
    return False


class Probe:
    def __init__(self, pine: Pine, addrs: list[int], seconds: float):
        self.pine, self.addrs, self.seconds = pine, addrs, seconds

    def moving(self):
        seen, start = {}, time.monotonic()
        while time.monotonic() - start < self.seconds:
            values = self.pine.read_many([FRAME_COUNTER] + self.addrs)
            seen[values[0]] = values[1:]
        frames = sorted(seen)
        if len(frames) < 4:
            return None, len(frames)                # game stalled
        return [len({round(f32(seen[f][i]), 4) for f in frames}) > 1
                for i in range(len(self.addrs))], len(frames)

    def without(self, site: int):
        """Result with `site` nopped, always restoring the original word."""
        original = self.pine.read(site)
        try:
            self.pine.write(site, 0x00000000)
            if self.pine.read(site) != 0:
                return None, 0
            return self.moving()
        finally:
            self.pine.write(site, original)
            if self.pine.read(site) != original:
                raise RuntimeError(f"could not restore {site:08X}")


def descend(mem, probe, entry, depth, indent=""):
    sites = call_sites(mem, entry)
    print(f"{indent}{entry:08X}: {len(sites)} testable calls")
    for site, target in sites:
        result, frames = probe.without(site)
        if result is None:
            print(f"{indent}  {site:08X} -> {target:08X}  (game stalled, skipped)")
            continue
        if not all(result):
            stopped = [f"{probe.addrs[i]:08X}"
                       for i, ok in enumerate(result) if not ok]
            print(f"{indent}  {site:08X} -> {target:08X}  STOPS {stopped}")
            if depth > 1:
                descend(mem, probe, target, depth - 1, indent + "    ")
            return True
    print(f"{indent}  no single call owns it - written here, or by several")
    return False


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("addrs", nargs="+", help="hex EE addresses to watch")
    ap.add_argument("--from", dest="entry", default="12B6E0")
    ap.add_argument("--depth", type=int, default=4)
    ap.add_argument("--seconds", type=float, default=0.7)
    args = ap.parse_args()

    mem = load_elf()
    try:
        pine = Pine().connect()
    except PineNotRunning as exc:
        print(exc)
        return 2
    with pine:
        probe = Probe(pine, [int(a, 16) for a in args.addrs], args.seconds)
        base, frames = probe.moving()
        print("baseline (%d frames): " % frames +
              "  ".join(f"{a:08X}={'move' if m else 'STOP'}"
                        for a, m in zip(probe.addrs, base or [])))
        if not base or not all(base):
            print("watch every address actually moving before bisecting")
            return 1
        descend(mem, probe, int(args.entry, 16), args.depth)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

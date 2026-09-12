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

from bt3 import config
from ps2ee.disasm import decode, jump_target
from ps2ee.eemem import EEMemory, ElfImage
from ps2ee.pine import Pine, PineNotRunning

JR_RA = 0x03E00008
FRAME_COUNTER = 0x00331D64

# Skipping a call that feeds the VIF/GIF DMA leaves the EE reading an empty
# FIFO, and PCSX2 aborts with "FQC = 0 on VIF FIFO READ". Restoring the
# instruction does not undo the desync - the emulator has to be restarted.
# These are the battle-loop subsystems that push display lists, so they are
# never nopped, and neither is anything reached only through them.
DMA_UNSAFE = {
    0x00102038,   # present / flush
    0x00102060,   # end of frame, vblank wait
    0x001BB620,   # draws, reaches the effect renderer
    0x00212990,   # draws
    0x002129B0,   # draws
    0x00126FB0,   # draws
    0x00263508,
}
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
                if target not in DMA_UNSAFE and not _result_used(mem, at):
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


def descend(mem, probe, entry, depth, indent="", base=None):
    """Find the call that owns the watched values.

    `base` is which addresses were moving before any nopping. Only those can
    testify: an address that was already still says nothing about the call
    under test, and counting it turns the first site tested into a false hit.
    """
    if base is None:
        base, _ = probe.moving()
    watched = [i for i, m in enumerate(base or []) if m]
    if not watched:
        print(f"{indent}nothing is moving - cannot bisect")
        return False
    sites = call_sites(mem, entry)
    print(f"{indent}{entry:08X}: {len(sites)} testable calls")
    for site, target in sites:
        result, frames = probe.without(site)
        if result is None:
            print(f"{indent}  {site:08X} -> {target:08X}  (game stalled, skipped)")
            continue
        if not all(result[i] for i in watched):
            # A value can stop for reasons that have nothing to do with this
            # call - the effect ended, the slot was recycled, the game died.
            # Without this check the first such stop is reported as a hit and
            # every later test inherits it, which reads as dozens of owners.
            again, _ = probe.moving()
            if again is None or not any(again[i] for i in watched):
                print(f"{indent}  {site:08X} -> {target:08X}  stopped, but it did "
                      f"NOT resume after restoring - not this call.")
                print(f"{indent}  the value died on its own; re-locate it and start over")
                return False
            stopped = [f"{probe.addrs[i]:08X}" for i in watched if not result[i]]
            print(f"{indent}  {site:08X} -> {target:08X}  STOPS {stopped}  (resumed after restore)")
            if depth > 1:
                descend(mem, probe, target, depth - 1, indent + "    ", base=again)
            return True
    print(f"{indent}  no single call owns it - written here, or by several")
    return False


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("addrs", nargs="+", help="hex EE addresses to watch")
    ap.add_argument("--from", dest="entry", default="12B6E0")
    ap.add_argument("--depth", type=int, default=4)
    ap.add_argument("--seconds", type=float, default=0.25,
                    help="how long each call stays nopped; keep it short, a "
                         "long gap in a subsystem desyncs more than the value "
                         "being watched")
    ap.add_argument("--allow-dma", action="store_true",
                    help="also test the display-list subsystems - this can "
                         "abort the emulator with a VIF FIFO assertion")
    args = ap.parse_args()

    if args.allow_dma:
        DMA_UNSAFE.clear()
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

"""Sweep all of RAM for what OSCILLATES twice as fast, not what steps twice as far.

An animation at double speed reverses direction twice as often in the same number
of vsyncs. Counting sign changes needs no magnitude and no alignment, and costs
one word of state per address, so it can sweep the whole 32 MB (unlike ratescan,
which needs both runs in the same situation).

Requirements:

* **Sample both rates on the same real-time grid, same number of samples.**
  Reading every vsync gives the 60fps run twice as many looks at a noisy word.
  ``--stride 2`` is one sample per tick at 30fps.
* **Check the words are floats.** Display packets (DMA/GIF data) read as
  denormals and spikes; their sign flips are meaningless.
* **Start from a state that needs no input.** Use ``tools/mkstate.py airidle``;
  the same vsync count is half the ticks at 30fps.

    python tools/oscscan.py --slot 3
    python tools/oscscan.py --slot 3 --base 0x01870000 --size 0x10000
"""

from __future__ import annotations

import argparse
import collections
import time

import numpy as np

import _bootstrap  # noqa: F401
import patchctl

from ps2ee.roo import Roo

CHUNK = 1 << 22


def as_float64(raw: np.ndarray) -> np.ndarray:
    """Widen the snapshot, with the non-finite bit patterns flattened to zero.

    Packet bytes that decode as NaN would trip numpy's invalid warning.
    """
    with np.errstate(invalid="ignore"):
        return np.nan_to_num(raw.astype(np.float64), posinf=0.0, neginf=0.0)


def snap(roo: Roo, base: int, size: int) -> np.ndarray:
    out = bytearray()
    for off in range(0, size, CHUNK):
        out += roo.read_bytes(base + off, min(CHUNK, size - off))
    return np.frombuffer(bytes(out), dtype="<f4")


def plausible(a: np.ndarray) -> np.ndarray:
    """A float the game could be using, as opposed to reinterpreted packet data."""
    m = np.abs(a)
    return np.isfinite(a) & ((m == 0.0) | ((m > 1e-20) & (m < 1e6)))


def measure(roo: Roo, cfg: str, base: int, size: int, samples: int,
            stride: int, slot: int, poke=(), settle: int = 0) -> dict:
    roo.flush_input()
    roo.loadstate(slot)
    patchctl.apply(roo, patchctl.PRESETS.get(cfg) or cfg.split(","), quiet=True)
    for addr, value in poke:
        if not roo.write(addr, value):
            raise SystemExit(f"poke {addr:08X}={value:08X} did not take")
    # Let the configuration take hold before the first sample: anything the state
    # froze mid-flight still runs on the old numbers until something rebuilds it.
    roo.frame_advance(2 + settle)

    raw = snap(roo, base, size)
    ok = plausible(raw)
    prev = as_float64(raw)
    n = prev.size
    sign = np.zeros(n, dtype=np.int8)
    flips = np.zeros(n, dtype=np.int32)
    total = np.zeros(n, dtype=np.float64)
    count = np.zeros(n, dtype=np.int32)
    start = time.time()
    for i in range(samples):
        roo.frame_advance(stride)
        raw = snap(roo, base, size)
        ok &= plausible(raw)
        cur = as_float64(raw)
        d = cur - prev
        s = np.sign(d).astype(np.int8)
        live = s != 0
        flips += (live & (sign != 0) & (s != sign)).astype(np.int32)
        total += np.abs(d)
        count += live
        sign = np.where(live, s, sign).astype(np.int8)
        prev = cur
        print(f"    {cfg} {i + 1}/{samples}  {time.time() - start:.0f}s",
              end="\r", flush=True)
    print()
    step = np.divide(total, np.maximum(count, 1)) * (count / samples)
    return {"flips": flips, "step": step, "ok": ok}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--base", type=lambda s: int(s, 0), default=0x00100000)
    parser.add_argument("--size", type=lambda s: int(s, 0), default=0x01F00000)
    parser.add_argument("--samples", type=int, default=60)
    parser.add_argument("--stride", type=int, default=2,
                        help="vsyncs between samples; 2 keeps both rates on one "
                             "real-time grid and reads each 30fps tick once")
    parser.add_argument("--slot", type=int, default=3)
    parser.add_argument("--ref", default="off", help="the 30fps oracle")
    parser.add_argument("--cfg", default="air", help="the configuration under test")
    parser.add_argument("--poke", default="",
                        help="ADDR=WORD[,...] written into the tested arm only")
    parser.add_argument("--min-flips", type=int, default=3,
                        help="ignore words too slow to judge")
    parser.add_argument("--max-flips", type=int, default=20,
                        help="ignore words that reverse on nearly every sample - "
                             "those are toggles, not animations")
    parser.add_argument("--settle", type=int, default=0,
                        help="vsyncs to run under the configuration before the "
                             "first sample, so state frozen mid-flight rebuilds")
    parser.add_argument("--limit", type=int, default=40)
    args = parser.parse_args()

    poke = [tuple(int(y, 0) for y in x.split("=")) for x in args.poke.split(",") if x]
    roo = Roo().connect()
    a = measure(roo, args.ref, args.base, args.size, args.samples,
                args.stride, args.slot, settle=args.settle)
    b = measure(roo, args.cfg, args.base, args.size, args.samples,
                args.stride, args.slot, poke, settle=args.settle)

    fa, fb = a["flips"], b["flips"]
    real = a["ok"] & b["ok"]
    band = ((fa >= args.min_flips) & (fa <= args.max_flips)
            & (fb >= 1.7 * fa) & (fb <= 2.4 * fa))
    hits = np.flatnonzero(band & real)

    print(f"\n{args.base:08X}+{args.size:#x}  {args.samples} samples every "
          f"{args.stride} vsyncs, slot {args.slot}, {args.ref} vs {args.cfg}")
    print(f"{int(band.sum())} words reverse about twice as often, "
          f"{hits.size} of them hold plausible floats\n")
    pages = collections.Counter((args.base + i * 4) & 0xFFFFF000 for i in hits)
    for page, n in sorted(pages.items(), key=lambda kv: -kv[1])[:8]:
        print(f"  page {page:08X}  {n}")
    print(f"\n{'addr':>10} {'rev ref':>8} {'rev cfg':>8} {'ratio':>6} "
          f"{'step ref':>10} {'step cfg':>10}")
    for i in hits[np.argsort(-fb[hits])][:args.limit]:
        print(f"  {args.base + i * 4:08X} {fa[i]:8d} {fb[i]:8d} "
              f"{fb[i] / fa[i]:6.2f} {a['step'][i]:10.5f} {b['step'][i]:10.5f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

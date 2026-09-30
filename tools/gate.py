"""Run chosen call sites on even frames only, to see what drives a symptom.

Gating beats nopping as a probe. Nopping asks "does this subsystem exist?" and
usually answers by breaking something; gating asks "does this subsystem drive
the SPEED of what I am looking at?", which is the actual question for a 60fps
patch. The failure modes are informative too: a subtree that *flickers* when
gated is render submission, one that *slows down* is simulation.

Each gate is a 9-word trampoline in the safe zone. The call sites must not have
their return value consumed - tools/bisect.call_sites already filters those.

    python tools/gate.py --list
    python tools/gate.py 0 1 3 4          # gate these, by index
    python tools/gate.py --off            # restore everything
"""
import argparse
import importlib.util
import json
from pathlib import Path

import _bootstrap  # noqa: F401

from game import config
from ps2ee.pine import Pine, PineNotRunning

# bisect.py is loaded by path, not imported, because its name is the stdlib's -
# see tools/_bootstrap.py. The path is taken from this file so it does not
# depend on which directory the tool is run from.
_BISECT = Path(__file__).resolve().parent / "bisect.py"
spec = importlib.util.spec_from_file_location("bm", _BISECT)
bm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bm)

ROOT = 0x0012B6E0
ZONE = 0x000F0400          # clear of everything the shipped patch uses
STRIDE = 0x28
STATE = config.WORK / "gate-state.json"
FRAME_COUNTER = 0x00331D64


def trampoline(slot: int, target: int, resume: int) -> dict[int, int]:
    """Even frames call `target`, odd frames skip it; both rejoin at `resume`."""
    a = ZONE + slot * STRIDE
    hi, lo = (FRAME_COUNTER >> 16) & 0xFFFF, FRAME_COUNTER & 0xFFFF
    return {
        a + 0x00: 0x3C080000 | hi,                    # lui  $8, hi(counter)
        a + 0x04: 0x8D080000 | lo,                    # lw   $8, lo($8)
        a + 0x08: 0x31080001,                         # andi $8, $8, 1
        a + 0x0C: 0x15000003,                         # bnez $8, +3   (odd: skip)
        a + 0x10: 0x00000000,
        a + 0x14: 0x0C000000 | ((target >> 2) & 0x03FFFFFF),   # jal target
        a + 0x18: 0x00000000,
        a + 0x1C: 0x08000000 | ((resume >> 2) & 0x03FFFFFF),   # j resume
        a + 0x20: 0x00000000,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("indices", nargs="*", type=int)
    ap.add_argument("--root", default=f"{ROOT:X}",
                    help="function whose call sites are gated (hex)")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--off", action="store_true")
    args = ap.parse_args()

    sites = bm.call_sites(bm.load_elf(), int(args.root, 16))
    if args.list:
        for i, (site, target) in enumerate(sites):
            print(f"  [{i:2}] {site:08X} -> {target:08X}")
        return 0

    try:
        pine = Pine(timeout=20.0).connect()
    except PineNotRunning as exc:
        print(exc)
        return 2

    with pine:
        # always restore whatever is currently gated first
        if STATE.exists():
            saved = json.loads(STATE.read_text())
            for a, w in saved.items():
                pine.write(int(a, 16), int(w, 16))
            bad = [a for a, w in saved.items() if pine.read(int(a, 16)) != int(w, 16)]
            print(f"restored {len(saved)} previously gated site(s)"
                  + (f"  FAILED {bad}" if bad else ""))
            STATE.unlink()
        if args.off:
            for a in range(ZONE, ZONE + STRIDE * 24, 4):
                pine.write(a, 0)
            print("all gates off, safe zone cleared")
            return 0

        saved = {}
        for slot, idx in enumerate(args.indices):
            site, target = sites[idx]
            orig = pine.read(site)
            if orig != (0x0C000000 | ((target >> 2) & 0x03FFFFFF)):
                print(f"  [{idx}] {site:08X} is not the expected jal - skipping")
                continue
            for a, w in trampoline(slot, target, site + 8).items():
                pine.write(a, w)
            pine.write(site, 0x08000000 | (((ZONE + slot * STRIDE) >> 2) & 0x03FFFFFF))
            saved[f"{site:08X}"] = f"{orig:08X}"
            print(f"  gated [{idx:2}] {site:08X} -> {target:08X}")
        STATE.write_text(json.dumps(saved, indent=1))
        print(f"\n{len(saved)} call site(s) now run on even frames only")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

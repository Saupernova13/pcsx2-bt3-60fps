"""Carry a save state into PCSXROO from a PCSX2 build whose format it refuses.

PCSXROO tracks a newer savestate format than the user's install (0x9A59 against
0x9A55 - SPU decode buffers, then the EE and VU cycle counters widening to 64
bit), so it rejects those files outright, and rewriting the version stamp only
gets as far as "corruption in internal structures". Converting the internal
structures properly would mean re-serialising sections across four format
bumps, and a subtly wrong VM is worse than no VM at all.

None of those bumps touch what matters for this project. The fight lives in EE
main memory, the ELF is byte-identical in both builds, and every pointer in it
is an absolute EE address - so the state can be carried across as raw memory
rather than as a file. Pause the target at a frame boundary, where the game's
main loop is where it was when the source state was written, write the source's
EE RAM and scratchpad over it, and resume.

The target must already be running the same game in a comparable scene: this
replaces memory, not CPU registers, so the EE resumes from wherever the target
was. A battle save state is the right thing to load first.

    python tools/transplant.py work/state-backups/some-fight.p2s
    python tools/transplant.py some-fight.p2s --save-slot 3

Verify before trusting it: the fighter states printed at the end should match
the source, and a screenshot should show the source's scene.
"""

import argparse
import time

import _bootstrap  # noqa: F401

from ps2ee.roo import Roo
from ps2ee.savestate import SaveState

CHUNK = 256 * 1024
SCRATCHPAD = 0x70000000

# The debug server guards EE addresses below this, and it is the same PS2 kernel
# in both builds anyway - the game's own memory starts well above it.
EE_START = 0x00080000

MANAGER_PTR = 0x002FEB14
STRIDE = 0x1600
STATE = 0x948


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("state", help="the .p2s to carry across")
    parser.add_argument("--port", type=int, default=28110)
    parser.add_argument("--save-slot", type=int, default=None,
                        help="write the result to this PCSXROO slot, in its own format")
    args = parser.parse_args()

    with SaveState(args.state) as state:
        print(f"source: PCSX2 {state.version()}")
        ee = state.ee
        scratch = state.read("Scratchpad.bin")
    print(f"  EE {len(ee)/1048576:.0f} MB, scratchpad {len(scratch)} bytes")

    with Roo(args.port).connect() as roo:
        roo.frame_advance(1)
        if not roo.paused():
            print("  WARNING: not paused at a frame boundary")
        start = time.time()
        for off in range(EE_START, len(ee), CHUNK):
            if not roo.write_bytes(off, ee[off:off + CHUNK]):
                print(f"  write failed at {off:08X}")
                return 1
        print(f"  EE written in {time.time()-start:.1f}s")
        roo.write_bytes(SCRATCHPAD, scratch)

        manager = roo.read(MANAGER_PTR)
        print(f"  fighter manager {manager:08X}")
        if manager:
            fighters = roo.read(manager + 4)
            for i in range(roo.read(manager)):
                base = fighters + i * STRIDE
                print(f"    f{i} {base:08X}  state {roo.read(base + STATE)}")
        if args.save_slot is not None:
            roo.savestate(args.save_slot)
            print(f"  saved to PCSXROO slot {args.save_slot} - no transplant needed again")
        roo.resume()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

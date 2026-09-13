"""The heavy smash and its Circle pursuit stomp, played in REAL time.

The stomp is the one bug in this project that cannot be judged from a numeric
trace alone: the question is whether Goku's dive lands on the victim or sails
past behind them, and the answer is a picture. So this drives the pad on the
wall clock with the VM running free - a hold on Square and Up until the charge
releases itself, then Circle a fixed real-time delay after the hit lands - and
photographs the result. Frame-advancing instead would be worse than useless
here, because a screenshot needs a running VM and every sample would leak ticks.

The hit is read from the victim's HP at fighter+0x9E4: one drop for the smash,
a second one if the stomp connects.

    python tools/stomptest.py --presets off nopursuit full
    python tools/stomptest.py --presets full --sheet work/stomp-full.png
"""

from __future__ import annotations

import argparse
import time

import _bootstrap  # noqa: F401
import patchctl
import realclock

from game import config
from ps2ee.roo import Roo
from game import battle as B

HP = 0x9E4


def play(roo: Roo, preset: str, slot: int, delay_s: float, tap_s: float,
         shots: int, cadence: float, settle_s: float = 1.5):
    roo.flush_input()
    roo.loadstate(slot)
    time.sleep(1.0)
    # Apply LAST and never load again. Some save states were captured while
    # patched, so a reload after apply writes the patched words straight back
    # and the "unpatched" arm silently runs at 60fps. Slot 4 does exactly that.
    patchctl.apply(roo, patchctl.PRESETS[preset], quiet=True)
    time.sleep(0.3)
    pair = B.resolve(roo)
    me, foe = pair[0].fighter, pair[1].fighter

    snaps = config.roo_snaps_dir()
    snaps.mkdir(parents=True, exist_ok=True)
    paths = [snaps / f"stomp-{i:03d}.png" for i in range(shots)]
    for path in paths:
        if path.exists():
            try:
                path.unlink()
            except OSError:
                pass

    # Settle first. The save state is mid-combo, and the mode regenerates the
    # victim to full within about a second of the load - so an HP baseline read
    # before that rises rather than falls, and the smash looks like it missed.
    roo.resume()
    time.sleep(settle_s)
    hp0 = roo.read(foe + HP)
    start = time.monotonic()
    roo.input_set("Square", "Up")

    impact_hp, impact_t, tapped, released = None, None, False, False
    stomp_t = None
    for i, path in enumerate(paths):
        now = start + i * cadence
        while time.monotonic() < now:
            time.sleep(0.002)
        roo.screenshot(path)
        hp = roo.read(foe + HP)
        # The stomp has to be caught while it happens. This mode regenerates the
        # victim to full within about a second, so a single read after the dive
        # reports 40000 whether the stomp connected or sailed past.
        if impact_hp is not None and stomp_t is None and hp < impact_hp:
            stomp_t = time.monotonic() - impact_t
        if impact_t is None and hp < hp0:
            impact_t, impact_hp = time.monotonic(), hp
            roo.input_release()
        elif impact_t is not None and not tapped and time.monotonic() >= impact_t + delay_s:
            roo.input_set("Circle")
            tapped = True
        elif tapped and not released and time.monotonic() >= impact_t + delay_s + tap_s:
            roo.input_release()
            released = True

    roo.pause()
    roo.flush_input()

    landed = stomp_t is not None
    when = f" {stomp_t:.2f}s after the smash" if landed else ""
    print(f"  {preset:10s} smash {'landed' if impact_t else 'NEVER LANDED'};"
          f" stomp {'CONNECTED' + when if landed else 'MISSED'}"
          f"  (hp {hp0} -> {impact_hp})")
    return realclock.load_frames(paths), landed


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--slot", type=int, default=9)
    ap.add_argument("--presets", nargs="+", default=["off", "full"])
    ap.add_argument("--delay", type=float, default=0.33, help="seconds after the hit")
    ap.add_argument("--tap", type=float, default=0.13, help="how long Circle is held")
    ap.add_argument("--shots", type=int, default=34)
    ap.add_argument("--cadence", type=float, default=0.10)
    ap.add_argument("--settle", type=float, default=1.5,
                    help="seconds of free running before the baseline HP read")
    ap.add_argument("--sheet", default=None, help="tile each preset's frames to PATH-<preset>.png")
    args = ap.parse_args()

    roo = Roo().connect()
    for preset in args.presets:
        frames, _ = play(roo, preset, args.slot, args.delay, args.tap,
                         args.shots, args.cadence, args.settle)
        if args.sheet:
            stem, _, ext = args.sheet.rpartition(".")
            realclock.sheet(frames, args.cadence, f"{stem}-{preset}.{ext or 'png'}")
    roo.resume()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

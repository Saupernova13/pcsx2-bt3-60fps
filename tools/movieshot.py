"""Charge, fire a scripted move, and photograph its cinematic in real time.

The ultimates and transformations are the part of this game a numeric trace is
worst at. Their defects are things like "the camera arrives too early and sits
there" or "the sky snaps instead of turning" - visible instantly, invisible in a
column of state indices. So this drives the pad on the wall clock with the VM
running free and takes one screenshot every `--cadence` seconds from the moment
the move actually starts, which makes a 30fps sheet and a 60fps sheet directly
comparable tile for tile: the same real instant is the same tile index.

The charge is held for a fixed number of real seconds and is deliberately
OUTSIDE the photographed window, along with the command press. Nothing is
pressed once the window opens, so the tick-versus-vsync asymmetry of a button
hold cannot bias the comparison.

    # Cell's Perfect Barrier, both arms
    python tools/movieshot.py --slot 4 --presets off full \
        --charge 6 --command L2,Down,Triangle --state 264 --sheet work/cell.png

    # whatever the fighter is already able to do, no charge
    python tools/movieshot.py --slot 8 --charge 0 --command L2,Triangle --state 264
"""

from __future__ import annotations

import argparse
import time

import _bootstrap  # noqa: F401
import patchctl
import realclock

from ps2ee import config
from ps2ee.roo import Roo
from ps2ee import battle as B

STATE = 0x948


def perform(roo: Roo, preset: str, slot: int, charge_s: float, command: list[str],
            want_state: int, shots: int, cadence: float, settle_s: float = 1.0):
    roo.flush_input()
    roo.loadstate(slot)
    time.sleep(1.0)
    patchctl.apply(roo, patchctl.PRESETS[preset], quiet=True)
    roo.flush_input()
    roo.loadstate(slot)            # reload, so the patch is live from frame one
    time.sleep(1.0)
    me = B.resolve(roo)[0].fighter

    snaps = config.roo_snaps_dir()
    snaps.mkdir(parents=True, exist_ok=True)
    paths = [snaps / f"movie-{i:03d}.png" for i in range(shots)]
    for path in paths:
        if path.exists():
            try:
                path.unlink()
            except OSError:
                pass

    roo.resume()
    time.sleep(settle_s)
    if charge_s > 0:
        roo.input_set("L2")
        time.sleep(charge_s)
    roo.input_set(*command)

    # Wait for the move to actually start. Timing the window from the press
    # instead would fold the command's own recognition delay into the comparison.
    deadline = time.monotonic() + 6.0
    started = False
    while time.monotonic() < deadline:
        if roo.read(me + STATE) == want_state:
            started = True
            break
        time.sleep(0.004)
    roo.input_release()
    if not started:
        roo.pause()
        print(f"  {preset:5s} the move never reached state {want_state}")
        return None

    start = time.monotonic()
    states = []
    for i, path in enumerate(paths):
        while time.monotonic() < start + i * cadence:
            time.sleep(0.002)
        roo.screenshot(path)
        states.append(roo.read(me + STATE))

    roo.pause()
    roo.flush_input()
    held = sum(1 for s in states if s == want_state)
    print(f"  {preset:5s} state {want_state} held for {held * cadence:.2f}s "
          f"({held}/{shots} frames); then " +
          " ".join(str(s) for s in sorted({s for s in states if s != want_state})))
    return realclock.load_frames(paths)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--slot", type=int, default=4)
    ap.add_argument("--presets", nargs="+", default=["off", "full"])
    ap.add_argument("--charge", type=float, default=6.0, help="seconds holding L2")
    ap.add_argument("--command", default="L2,Down,Triangle")
    ap.add_argument("--state", type=int, default=264, help="the state the move enters")
    ap.add_argument("--shots", type=int, default=44)
    ap.add_argument("--cadence", type=float, default=0.10)
    ap.add_argument("--sheet", default=None, help="tile each preset to PATH-<preset>.png")
    args = ap.parse_args()

    command = [b for b in args.command.split(",") if b]
    roo = Roo().connect()
    for preset in args.presets:
        frames = perform(roo, preset, args.slot, args.charge, command,
                         args.state, args.shots, args.cadence)
        if frames and args.sheet:
            stem, _, ext = args.sheet.rpartition(".")
            realclock.sheet(frames, args.cadence, f"{stem}-{preset}.{ext or 'png'}")
    roo.resume()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

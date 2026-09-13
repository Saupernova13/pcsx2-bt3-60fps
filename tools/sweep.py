"""Change one site at a time and score it against the oracles that matter.

A site is only worth keeping if it moves the thing being fixed *and* leaves
alone something that was already right. Half the counters this finds are levels
rather than clocks - a combo index, an input window - and slowing one of those
breaks an ordinary combo while the number you were watching does not move at
all. Two oracles catch that; one does not.

The probe goes into a spare group, so nothing has to be rebuilt or restarted
between sites. Gating is used rather than freezing on purpose: nopping an
increment hangs anything waiting on it, while a counter that is gated and turns
out not to be a clock simply leaves the measurement where it was.

    python tools/sweep.py work/phase-sites.txt work/out.txt --oracles charge,melee
    python tools/sweep.py work/flight.txt work/out.txt --oracles ultimate --how half

Oracles, all counted in vsyncs so they mean real time at either rate:

    charge    save state 1, L2 then L2+Triangle held, to the first hit
    melee     save state 1, rush mashed on a real-time cadence, to the 4th hit
    ultimate  save state 8, the Angry Kamehameha, to the first hit
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import time
from pathlib import Path

import _bootstrap  # noqa: F401
import patchctl

from game import config
from ps2ee.roo import Roo

OPPONENT_HP = 0x018726A4
PROBE_GROUP = "60FPS - spare 1"


def set_probe(body: str) -> None:
    """Put `body` in the probe group, replacing whatever was there."""
    path = config.roo_cheat_file()
    text = path.read_text(encoding="utf-8", errors="replace")
    text = re.sub(r"^\[" + re.escape(PROBE_GROUP) + r"(?: \[off\])?\]\n(?:(?!\[).*\n)*",
                  "", text, flags=re.M)
    path.write_text(text.rstrip("\n") + f"\n[{PROBE_GROUP}]\ndescription=sweep probe\n"
                    + body, encoding="utf-8")


def _run(roo: Roo, slot: int, groups: list[str]) -> None:
    roo.flush_input()
    roo.loadstate(slot)
    time.sleep(0.8)
    patchctl.apply(roo, groups, quiet=True)
    roo.frame_advance(2)


def oracle_charge(roo: Roo, groups: list[str]) -> int | None:
    _run(roo, 1, groups)
    roo.input_set("L2")
    roo.frame_advance(30)
    roo.input_set("L2", "Triangle")
    hp = roo.read(OPPONENT_HP)
    for i in range(300):
        roo.frame_advance(1)
        now = roo.read(OPPONENT_HP)
        if hp - now > 500:
            roo.flush_input()
            return i + 1
        hp = now
    roo.flush_input()
    return None


def oracle_melee(roo: Roo, groups: list[str]) -> int | None:
    _run(roo, 1, groups)
    hp = roo.read(OPPONENT_HP)
    hits = []
    for i in range(220):
        roo.input_set("Square") if (i // 6) % 2 == 0 else roo.input_release()
        roo.frame_advance(1)
        now = roo.read(OPPONENT_HP)
        if hp - now > 100:
            hits.append(i + 1)
        hp = now
    roo.flush_input()
    return hits[3] if len(hits) > 3 else None


def oracle_ultimate(roo: Roo, groups: list[str]) -> int | None:
    _run(roo, 8, groups)
    hp = roo.read(OPPONENT_HP)
    for i in range(320):
        roo.frame_advance(1)
        if roo.read(OPPONENT_HP) != hp:
            roo.flush_input()
            return i + 1
    roo.flush_input()
    return None


ORACLES = {"charge": oracle_charge, "melee": oracle_melee, "ultimate": oracle_ultimate}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("sites", help="file whose first column is a hex address")
    ap.add_argument("out")
    ap.add_argument("--oracles", default="charge,melee")
    ap.add_argument("--how", choices=("gate", "half"), default="gate",
                    help="gate an integer counter, or halve a float step")
    ap.add_argument("--base", default="F1800", help="scratch address for the probe")
    ap.add_argument("--preset", default="full")
    args = ap.parse_args()

    names = [n for n in args.oracles.split(",") if n]
    for name in names:
        if name not in ORACLES:
            ap.error(f"unknown oracle {name}; pick from {', '.join(ORACLES)}")
    sites = [line.split()[0] for line in open(args.sites) if line[:1] == "0"]
    maker = "tools/mkgate.py" if args.how == "gate" else "tools/mkhalf.py"
    groups = list(patchctl.PRESETS[args.preset])
    roo = Roo().connect()
    rows: list[tuple[str, list]] = []

    def score(extra: list[str]) -> list:
        return [ORACLES[n](roo, groups + extra) for n in names]

    set_probe("")
    rows.append(("baseline", score([])))
    print(f"  baseline  " + "  ".join(f"{n} {v}" for n, v in zip(names, rows[0][1])))

    for i, site in enumerate(sites):
        try:
            body = subprocess.run([sys.executable, maker, site, "--base", args.base],
                                  capture_output=True, text=True, check=True).stdout
        except subprocess.CalledProcessError as exc:
            note = exc.stderr.strip().splitlines()[-1][:70] if exc.stderr else "failed"
            rows.append((site, [f"skip: {note}"]))
            print(f"  {i + 1:3d}/{len(sites)}  {site}  {note}")
            Path(args.out).write_text("\n".join(f"{a}\t{b}" for a, b in rows))
            continue
        set_probe(body)
        values = score([PROBE_GROUP])
        rows.append((site, values))
        print(f"  {i + 1:3d}/{len(sites)}  {site}  "
              + "  ".join(f"{n} {v}" for n, v in zip(names, values)))
        Path(args.out).write_text("\n".join(f"{a}\t{b}" for a, b in rows))

    set_probe("")
    roo.flush_input()
    roo.resume()
    print(f"\n{args.out} written. Restart the emulator before measuring anything else: "
          "the probe group has shrunk and its last hooks are still in RAM.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

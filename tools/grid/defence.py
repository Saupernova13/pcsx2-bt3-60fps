"""Defence window sweep (PR #65 method). Slot 7: pad 2 holds Square 20 vsyncs (level-1 smash).
Find the hit vsync H with no defence, then press BUTTONS on pad 1 for 2 vsyncs at H-d for each d;
success = P1 enters any of OK states.   python defence.py BUTTONS OKSTATES DMAX ARM..."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hs  # noqa
import patchctl  # noqa
from game import battle
from ps2ee.roo import Roo
buttons, ok, dmax = sys.argv[1].split(','), [int(x) for x in sys.argv[2].split(',')], int(sys.argv[3])
roo = Roo().connect(); roo.bp_clear()
def run(arm, press_at):
    roo.flush_input(); roo.cmd('input.set', buttons=[], pad=1); roo.loadstate(7)
    patchctl.apply(roo, hs.arm_groups(arm), quiet=True); roo.frame_advance(4)
    f0 = battle.resolve(roo)[0].fighter
    states = []
    for v in range(80):
        if v == 0: roo.cmd('input.set', buttons=['Square'], pad=1)
        if v == 20: roo.cmd('input.set', buttons=[], pad=1)
        if press_at is not None and v == press_at: roo.input_set(*buttons)
        if press_at is not None and v == press_at + 2: roo.input_set()
        states.append(roo.read(f0 + 0x948)); roo.frame_advance(1)
    roo.flush_input(); roo.cmd('input.set', buttons=[], pad=1)
    return states
for arm in sys.argv[4:]:
    st = run(arm, None)
    hit = next((i for i, s in enumerate(st) if s == 196), None)
    good = []
    for d in range(1, dmax + 1):
        s = run(arm, hit - d)
        if any(x in ok for x in s):
            good.append(d)
    print(f'{arm:22s} hit at v{hit}; defended when pressed at hit-{good} -> {len(good)} vsyncs', flush=True)

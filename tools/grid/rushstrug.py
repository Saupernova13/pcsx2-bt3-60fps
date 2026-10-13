"""Rush Struggle: spin P1's left stick at RPS rotations per real second (angle from game time),
report the struggle's length (P1 in state 250) and both hit counts (+0xE50).
    python rushstrug.py SLOT VSYNCS RPS[,RPS...] ARM..."""
import math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hs  # noqa
import patchctl  # noqa
from game import battle
from ps2ee.roo import Roo
slot, n = int(sys.argv[1]), int(sys.argv[2])
speeds = [float(x) for x in sys.argv[3].split(',')]
roo = Roo().connect(); roo.bp_clear()
for rps in speeds:
    for arm in sys.argv[4:]:
        roo.flush_input(); roo.loadstate(slot)
        patchctl.apply(roo, hs.arm_groups(arm.replace('+aigate', '')), quiet=True)
        if arm.endswith('+aigate'):
            import aigate; aigate.apply(roo)
        roo.frame_advance(2 + int(os.environ.get('DELAY', '0')))
        f0, f1 = (p.fighter for p in battle.resolve(roo)[:2])
        st, h0, h1 = [], [], []
        for v in range(n):
            if rps > 0:
                a = 2 * math.pi * rps * v / 59.94
                roo.input_set(left=(math.cos(a), math.sin(a)))
            st.append(roo.read(f0 + 0x948)); h0.append(roo.read(f0 + 0xE50)); h1.append(roo.read(f1 + 0xE50))
            roo.frame_advance(1)
        roo.flush_input()
        idx = [i for i, s in enumerate(st) if s == 250]
        dur = (idx[-1] - idx[0] + 1) if idx else 0
        # counts at the last vsync of the struggle
        e = idx[-1] if idx else n - 1
        print(f'rps {rps:3.1f}  {arm:20s} struggle {dur} vsyncs  P1 {max(h0[:e + 1])}  CPU {max(h1[:e + 1])}  winner {"P1" if max(h0[:e+1]) > max(h1[:e+1]) else "CPU"}', flush=True)

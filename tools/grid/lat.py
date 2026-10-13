"""Input latency A/B: vsyncs from a press (or release) reaching the game to P1's first state change.
python lat.py ARM...   Every slot x input x tick phase; prints one line per case, then the cases where an arm
differs from the first arm."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hs  # noqa
import patchctl  # noqa
from game import battle
from ps2ee.roo import Roo
# (buttons, hold vsyncs): the change after the press, and for long holds also the change after the release
CASES = [('Square', 2), ('Triangle', 2), ('Cross', 2), ('Circle', 2), ('L2,Triangle', 2), ('Up,Square', 2),
         ('Square', 24), ('Triangle', 24), ('R1', 2), ('Up', 2), ('Left', 2), ('L1', 2), ('R2', 2)]
SLOTS = [int(s) for s in os.environ.get('SLOTS', '0,1,2,3,4,5,6').split(',')]
roo = Roo().connect(); roo.bp_clear()
def run(arm, slot, buttons, hold, phase):
    roo.flush_input(); roo.loadstate(slot)
    patchctl.apply(roo, hs.arm_groups(arm), quiet=True); roo.frame_advance(4 + phase)
    f0 = battle.resolve(roo)[0].fighter
    roo.write(f0 + 0x9F0, 100000); roo.frame_advance(1)
    par = roo.read(0x331D64) & 1
    held = []; st = []; s0 = (roo.read(f0 + 0x948), roo.read(f0 + 0x974))
    roo.input_set(*buttons)
    for v in range(hold + 40):
        if v == hold: roo.input_set()
        roo.frame_advance(1)
        held.append(roo.read(f0 + 0x73C)); st.append((roo.read(f0 + 0x948), roo.read(f0 + 0x974)))
    roo.flush_input()
    arrive = next((v for v, h in enumerate(held) if h), None)
    gone = next((v for v in range(hold, len(held)) if not held[v] and held[v - 1]), None) if arrive is not None else None
    def first(after):
        if after is None: return None
        prev = st[after - 1] if after else s0
        return next((v - after for v in range(after, len(st)) if st[v] != prev), None)
    return par, first(arrive), first(gone) if hold > 2 else None, st
res = {}
for slot in SLOTS:
    for b, hold in CASES:
        for phase in (0, 1):
            row = []
            for arm in sys.argv[1:]:
                par, a, r, st = run(arm, slot, b.split(','), hold, phase)
                row.append((a, r, st))
            res[(slot, b, hold, phase)] = row
            print('slot %d %-12s hold %2d par %d  ' % (slot, b, hold, par) +
                  '  '.join('%s/%s' % (a, r) for a, r, _ in row), flush=True)
print('--- differences from %s (press latency / release latency) ---' % sys.argv[1])
n = 0
for k, row in res.items():
    if any(x[:2] != row[0][:2] for x in row[1:]):
        n += 1; print(k, [x[:2] for x in row])
print('cases', len(res), 'differing', n)

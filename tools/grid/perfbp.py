"""First pass through the Perfect test (001E4804; a0 = d84, v0 = compare value) after a release at R.
python perfbp.py SLOT R0 R1 ARM..."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hs, patchctl  # noqa
from game import battle
from ps2ee.roo import Roo
slot, r0, r1 = (int(x) for x in sys.argv[1:4])
roo = Roo().connect(); roo.bp_clear()
for arm in sys.argv[4:]:
    res = []
    for r in range(r0, r1 + 1):
        roo.flush_input(); roo.loadstate(slot)
        patchctl.apply(roo, hs.arm_groups(arm), quiet=True); roo.frame_advance(4)
        SH = int(os.environ.get('SHIFT', '0')); roo.frame_advance(SH) if SH else None
        roo.input_set('Square'); hit = None
        for v in range(r + 10):
            if v == r: roo.input_set(); roo.bp_add(0x001E4804)
            before = roo.status().get('last_stop') or {}
            roo.frame_advance(1)
            st = roo.status().get('last_stop') or {}
            if st != before and st.get('reason') == 'breakpoint':
                hit = 'v%d d84=%d par=%d' % (v, roo.reg('a0'), roo.read(0x331D64) & 1); break
        roo.bp_clear(); roo.flush_input()
        res.append('R%d:%s' % (r, hit))
    print(arm, ' | '.join(res))

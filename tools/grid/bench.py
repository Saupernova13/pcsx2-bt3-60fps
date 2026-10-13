"""Hand-off benchmark: for each scene, every arm's first-hit and worst hit offset and its return-to-idle lead
against 30fps (off).   python bench.py ARM [ARM ...]    (+ = later than 30fps)"""
import json, os, shutil, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ab, hs
from ps2ee.roo import Roo
BK = os.path.join(hs.FK, '..', 'state-backups')
SLOT9 = r'C:\Users\RaaViVi\Documents\GitHub\pcsxroo\bin\sstates\SLUS-21678 (428113C2).09.p2s'
SCENES = [('ult4', None), ('ult5', None), ('ult6', None), ('fork', None), ('sbc', None), ('hellstorm', None),
          ('a18dd', 'rocky-android18-vs-com-gohan-v570'), ('pchz', 'rocky-piccolo-end-vs-com-gohan-v570'),
          ('hercb2', 'rocky-hercule-vs-standing-gohan'), ('ringb2u', None)]
only = os.environ.get('ONLY')
roo = Roo().connect(); roo.bp_clear()
arms = ['off'] + sys.argv[1:]
print('%-10s' % 'scene' + ''.join('%-34s' % a[-30:] for a in arms[1:]))
for name, state in SCENES:
    if only and name not in only.split(','): continue
    spec = json.load(open('specs/%s.json' % name))
    probes = [p[0] for p in spec.get('probes', [])]
    if 'hp' not in probes: spec.setdefault('probes', []).append(['hp', 'p2', 2532, 'u32'])
    if 'st' not in probes: spec['probes'].append(['st', 'p1', 2376, 'u32'])
    if state: shutil.copy(os.path.join(BK, state + '.p2s'), SLOT9); spec['slot'] = 9
    res = {}
    for arm in arms:
        s = ab.run_arm(roo, spec, arm); hp, st = s['hp'], s['st']
        hits = [v for v in range(1, len(hp)) if hp[v] < hp[v - 1]]
        ch = [(v, st[v]) for v in range(1, len(st)) if st[v] != st[v - 1]]
        res[arm] = (hits, ch)
    h0, c0 = res['off']; cells = []
    for arm in arms[1:]:
        h, c = res[arm]
        d = [b - a for a, b in zip(h0, h)]
        hs_ = 'hit %+d/%s' % (d[0], max(d, key=abs)) if d and len(h) == len(h0) else 'hits %d vs %d' % (len(h), len(h0))
        if [x for _, x in c] == [x for _, x in c0] and c:
            es = 'end %+d' % (c[-1][0] - c0[-1][0])
        else:
            es = 'seq differs'
        cells.append('%-34s' % (hs_ + ' ' + es))
    print('%-10s' % name + ''.join(cells), flush=True)
shutil.copy(os.path.join(BK, 'story-frieza-recoome-intro.p2s'), SLOT9)

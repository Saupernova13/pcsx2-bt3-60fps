"""Make the rig run the full test build.

Copies every group of a test-build pnach into the rig's cheat file under its real name (comments stripped), adds 12
empty spare groups, and enables every name in the rig's ini. The rig reads its ini at boot only: restart it after a
new group name appears (trap 14 in docs/rig.md).

    python tools/rigsync.py [--from PNACH] [--dry]

--from defaults to the owner's EmuDeck cheat file, %APPDATA%/EmuDeck/Emulators/PCSX2-Qt/cheats/428113C2.pnach.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _bootstrap  # noqa: F401,E402
from game import config  # noqa: E402

SPARES = 12


def main() -> int:
    if '--from' in sys.argv:
        src = sys.argv[sys.argv.index('--from') + 1]
    else:
        src = os.path.join(os.environ.get('APPDATA', ''), 'EmuDeck', 'Emulators', 'PCSX2-Qt', 'cheats',
                           '428113C2.pnach')
    rig_cheats, rig_ini = str(config.roo_cheat_file()), str(config.roo_game_ini())

    groups, cur = [], None
    for line in open(src, encoding='utf-8'):
        line = line.rstrip('\n')
        m = re.match(r'^\[(.+)\]$', line)
        if m:
            cur = [m.group(1), []]
            groups.append(cur)
            continue
        if cur and line.startswith(('patch=', 'description=')):
            cur[1].append(line.split(' //')[0].rstrip())
    names = [g[0] for g in groups]

    out = ['gametitle=DragonBall Z - Budokai Tenkaichi 3 (USA) SLUS-21678', '',
           '// Rig copy of the test build, written by tools/rigsync.py.', '']
    for name, body in groups:
        out += ['[%s]' % name] + body + ['']
    for i in range(1, SPARES + 1):
        out += ['[60FPS - spare %d [off]]' % i, 'description=free', '']

    ini = open(rig_ini, encoding='utf-8').read()
    head, _, rest = ini.partition('[Cheats]')
    tail = rest[rest.find('\n['):] if '\n[' in rest else '\n'
    enables = ['Enable = %s' % n for n in names] + ['Enable = 60FPS - spare %d' % i for i in range(1, SPARES + 1)]
    new_ini = head + '[Cheats]\n' + '\n'.join(enables) + '\n' + tail.lstrip('\n')

    lines = sum(1 for g in groups for x in g[1] if x.startswith('patch='))
    print('%d groups from %s; %d patch lines' % (len(names), src, lines))
    if '--dry' not in sys.argv:
        open(rig_cheats, 'w', encoding='utf-8', newline='\n').write('\n'.join(out))
        open(rig_ini, 'w', encoding='utf-8', newline='\n').write(new_ini)
        print('wrote', rig_cheats, 'and', rig_ini)
    return 0


if __name__ == '__main__':
    sys.exit(main())

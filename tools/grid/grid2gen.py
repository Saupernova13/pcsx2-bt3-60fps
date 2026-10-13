"""Grid v2: grid.lines (A state switch on even ticks, B animation end, S pad) plus effect-raised held flags
0xA7..0xAB deferred to the next even-tick fighter update.  python grid2gen.py > grid2.lines"""
import asm
SETHELD, TABLE = 0x001DA9D0, 0x000F2800
out = []
D = asm.A(0x000F2820)
D.lui('t0', 0xF); D.addiu('t0', 't0', TABLE & 0xFFFF, 'addiu t0,t0,0x2800      pending table: 4 x {chr, mask}')
D.addiu('t3', 't0', 0x20); D.addiu('t1', 'a1', -0xA7); D.addiu('t2', 'zero', 1); D.sllv('t2', 't2', 't1', 'sllv t2,t2,t1           bit of flag - 0xA7')
D.L('loop'); D.lw('t4', 0, 't0'); D.beq('t4', 'a0', 'hit'); D.nop(); D.beq('t4', 'zero', 'hit'); D.nop()
D.addiu('t0', 't0', 8); D.bne('t0', 't3', 'loop'); D.nop()
D.j(SETHELD, 'j BtlChar_SetHeldFlag    table full: raise it now'); D.nop()
D.L('hit'); D.sw('a0', 0, 't0'); D.lw('t4', 4, 't0'); D.or_('t4', 't4', 't2'); D.sw('t4', 4, 't0')
D.jr('ra', 'jr ra                    deferred'); D.nop()
F = asm.A(0x000F2880)
F.addiu('sp', 'sp', -0x30); F.sd('ra', 0, 'sp'); F.sd('s1', 8, 'sp'); F.sd('s2', 0x10, 'sp'); F.sd('s3', 0x18, 'sp'); F.sd('s4', 0x20, 'sp')
F.move('s3', 'a0', 'move s3,a0               the fighter'); F.lui('s1', 0xF); F.addiu('s1', 's1', TABLE & 0xFFFF); F.addiu('s2', 's1', 0x20)
F.L('loop'); F.lw('t0', 0, 's1'); F.bne('t0', 's3', 'next'); F.nop()
F.lw('s4', 4, 's1'); F.sw('zero', 0, 's1'); F.sw('zero', 4, 's1')
for k in range(5):
    F.andi('t0', 's4', 1 << k); F.beq('t0', 'zero', 'k%d' % k); F.nop()
    F.move('a0', 's3'); F.jal(SETHELD, 'jal BtlChar_SetHeldFlag'); F.addiu('a1', 'zero', 0xA7 + k, 'li a1,0x%X' % (0xA7 + k)); F.L('k%d' % k)
F.L('next'); F.addiu('s1', 's1', 8); F.bne('s1', 's2', 'loop'); F.nop()
F.ld('ra', 0, 'sp'); F.ld('s1', 8, 'sp'); F.ld('s2', 0x10, 'sp'); F.ld('s3', 0x18, 'sp'); F.ld('s4', 0x20, 'sp')
F.jr('ra'); F.addiu('sp', 'sp', 0x30)
G = asm.A(0x000F2A00)
G.lui('t0', 0x33); G.lw('t0', 0x1D64, 't0', 'lw t0,0x1D64(t0)        frame counter'); G.andi('t0', 't0', 1); G.bne('t0', 'zero', 'odd'); G.nop()
G.jal(0x000F2880, 'jal flush                even: effect flags raised since the last even tick become visible'); G.move('a0', 's0')
G.lw('v0', 4, 's1', 'lw v0,4(s1)              displaced: act.request'); G.beq('v0', 's2', 'noreq'); G.nop()
G.j(0x001E243C, 'j 001E243C               even + request: switch now'); G.nop()
G.L('noreq'); G.j(0x001E2530, 'j 001E2530               even, no request: apply animation requests'); G.nop()
G.L('odd'); G.jal(0x001D7320, 'jal 001D7320             odd: BtlChar_ApplyRootYaw only'); G.move('a0', 's0')
G.j(0x001E2550, 'j 001E2550               then the RUN phase'); G.nop()
base = [l.rstrip('\n') for l in open('grid.lines') if l.startswith('patch=') and ',001E2430,' not in l]
print('\n'.join(base))
print('patch=1,EE,001E2430,word,%08X // lw v0,4(s1) -> j 000F2A00' % (0x08000000 | (0x000F2A00 >> 2)))
print('\n'.join(D.lines() + F.lines() + G.lines()))
for a in (0x002072C8, 0x00207300, 0x00207338, 0x00207370, 0x002073A8):
    print('patch=1,EE,%08X,word,%08X // j BtlChar_SetHeldFlag -> j defer (flag 0xA7..0xAB raised by an effect)' % (a, 0x08000000 | (0x000F2820 >> 2)))

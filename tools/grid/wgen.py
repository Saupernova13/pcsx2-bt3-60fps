"""Fighter event wrapper for the grid: python wgen.py BASE.lines OUT.lines"""
import sys, asm
R = asm.R
def lwc1(ft, off, base): return 0xC4000000 | (R[base] << 21) | (ft << 16) | (off & 0xFFFF)
def swc1(ft, off, base): return 0xE4000000 | (R[base] << 21) | (ft << 16) | (off & 0xFFFF)
def adds(fd, fs, ft): return 0x46000000 | (ft << 16) | (fs << 11) | (fd << 6)
def muls(fd, fs, ft): return 0x46000002 | (ft << 16) | (fs << 11) | (fd << 6)
def lb(rt, off, base): return 0x80000000 | (R[base] << 21) | (R[rt] << 16) | (off & 0xFFFF)
def sb(rt, off, base): return 0xA0000000 | (R[base] << 21) | (R[rt] << 16) | (off & 0xFFFF)
UE, WB = 0x0024CC88, 0x000F3000
def build():
    W = asm.A(WB)
    W.addiu('sp', 'sp', -0xA0); W.sd('ra', 0, 'sp'); W.sw('a0', 8, 'sp')
    W.lui('t0', 0x33); W.lw('t0', 0x1D64, 't0', 'lw t0,0x1D64(t0)        frame counter'); W.andi('t0', 't0', 1)
    W.beq('t0', 'zero', 'even'); W.nop()
    W.jal(UE, 'jal BtlObjAnim_UpdateEvents  odd tick: hit windows only'); W.nop()
    W.lw('a0', 8, 'sp'); W.raw(sb('zero', 0xCAE, 'a0'), 'sb zero,0xCAE(a0)        no events on an odd tick')
    W.beq('zero', 'zero', 'done'); W.nop()
    W.L('even')
    W.raw(lwc1(0, 0xC78, 'a0'), 'lwc1 f0,0xC78(a0)        frame'); W.raw(lwc1(1, 0xC7C, 'a0'), 'lwc1 f1,0xC7C(a0)        prevFrame (frame of the last even tick)')
    W.raw(swc1(0, 0x10, 'sp'), 'swc1 f0,0x10(sp)'); W.raw(swc1(1, 0x14, 'sp'), 'swc1 f1,0x14(sp)')
    W.raw(lwc1(2, 0xC80, 'a0'), 'lwc1 f2,0xC80(a0)        step a 30fps tick'); W.lui('t0', 0x3F00); W.raw(0x44881800, 'mtc1 t0,f3')
    W.raw(muls(2, 2, 3), 'mul.s f2,f2,f3            half a tick: what the 30fps tick has already shown')
    W.raw(adds(0, 0, 2), 'add.s f0,f0,f2')
    W.raw(0x44802000, 'mtc1 zero,f4'); W.raw(0x46012034, 'c.olt.s f4,f1             prevFrame > 0?')
    W.bc1f('noprev', 'bc1f noprev              a new animation: its window starts at frame 0, as at 30fps'); W.nop()
    W.raw(adds(1, 1, 2), 'add.s f1,f1,f2')
    W.L('noprev')
    W.raw(swc1(0, 0xC78, 'a0'), 'swc1 f0,0xC78(a0)'); W.raw(swc1(1, 0xC7C, 'a0'), 'swc1 f1,0xC7C(a0)')
    W.jal(UE, 'jal BtlObjAnim_UpdateEvents  pass 1: events of the whole 30fps tick'); W.nop()
    W.lw('a0', 8, 'sp')
    W.raw(lb('t1', 0xCAE, 'a0'), 'lb t1,0xCAE(a0)          save: event count'); W.sw('t1', 0x18, 'sp')
    W.lw('t1', 0xCB4, 'a0', 'lw t1,0xCB4(a0)          save: event node'); W.sw('t1', 0x1C, 'sp')
    for i in range(24):
        W.lw('t1', 0xCC0 + 4 * i, 'a0', 'lw t1,0x%X(a0)          save: events and args' % (0xCC0 + 4 * i) if i == 0 else ''); W.sw('t1', 0x20 + 4 * i, 'sp')
    W.raw(lwc1(0, 0x10, 'sp'), 'lwc1 f0,0x10(sp)'); W.raw(lwc1(1, 0x14, 'sp'), 'lwc1 f1,0x14(sp)')
    W.raw(swc1(0, 0xC78, 'a0'), 'swc1 f0,0xC78(a0)        frame restored'); W.raw(swc1(1, 0xC7C, 'a0'), 'swc1 f1,0xC7C(a0)        prevFrame restored')
    W.jal(UE, 'jal BtlObjAnim_UpdateEvents  pass 2: hit windows at the real frame'); W.nop()
    W.lw('a0', 8, 'sp')
    W.lw('t1', 0x18, 'sp'); W.raw(sb('t1', 0xCAE, 'a0'), 'sb t1,0xCAE(a0)          events of pass 1')
    W.lw('t1', 0x1C, 'sp'); W.sw('t1', 0xCB4, 'a0')
    for i in range(24):
        W.lw('t1', 0x20 + 4 * i, 'sp'); W.sw('t1', 0xCC0 + 4 * i, 'a0')
    W.L('done'); W.ld('ra', 0, 'sp'); W.jr('ra'); W.addiu('sp', 'sp', 0xA0)
    assert W.pc() < 0x000F3400
    return W
if __name__ == '__main__':
    W = build()
    L = {l.split(',')[2]: l.rstrip('\n') for l in open(sys.argv[1]) if l.startswith('patch=') and not (0x000F3000 <= int(l.split(',')[2], 16) < 0x000F3400)}
    for l in W.lines(): L[l.split(',')[2]] = l
    L['001C1F54'] = 'patch=1,EE,001C1F54,word,%08X // jal BtlObjAnim_UpdateEvents -> jal %08X (fighter)' % (0x0C000000 | (WB >> 2), WB)
    open(sys.argv[2], 'w', newline='\n').write('\n'.join(L.values()) + '\n'); print(len(L))

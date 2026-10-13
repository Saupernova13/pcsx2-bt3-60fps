"""Grid with input at 60Hz: python gridIgen.py gridF.lines gridI.lines
Drops part S (pad read on even ticks). Part A (state switch on even ticks) lets a switch through on an odd
vsync when the fighter's input changed this vsync or the last one (pressed / released / command edges),
so a press acts on the vsync it arrives, as in the build without the grid."""
import os, sys, asm
PREV = os.environ.get('PREV', '1') == '1'   # an edge on the last vsync also counts
CPU = os.environ.get('CPU', '1') == '1'     # the CPU's injected input counts
R = asm.R
def subu(rd, rs, rt): return (R[rs] << 21) | (R[rt] << 16) | (R[rd] << 11) | 0x23
def sltiu(rt, rs, imm): return (0x0B << 26) | (R[rs] << 21) | (R[rt] << 16) | (imm & 0xFFFF)
GB, TB = 0x000F2A00, 0x000F2B80   # code, stamp table 4 x {chr, last vsync with an input edge}
def build():
    G = asm.A(GB)
    G.lui('t0', 0x33); G.lw('t0', 0x1D64, 't0', 'lw t0,0x1D64(t0)        frame counter')
    G.lw('t1', 0x744, 's0', 'lw t1,0x744(s0)          input.pressed'); G.lw('t2', 0x748, 's0', 'lw t2,0x748(s0)          input.released')
    G.or_('t1', 't1', 't2'); G.lw('t2', 0x754, 's0', 'lw t2,0x754(s0)          input.cmdPressed'); G.or_('t1', 't1', 't2')
    G.lw('t2', 0x758, 's0', 'lw t2,0x758(s0)          input.cmdReleased'); G.or_('t1', 't1', 't2')
    if not CPU:
        G.lw('t2', 0x1278, 's0', 'lw t2,0x1278(s0)         injectOn: a CPU fighter'); G.raw((0x0B << 26) | (R['t2'] << 21) | (R['t2'] << 16) | 1, 'sltiu t2,t2,1            human?')
        G.raw((R['zero'] << 21) | (R['t2'] << 16) | (R['t2'] << 11) | 0x23, 'negu t2,t2'); G.raw((R['t1'] << 21) | (R['t2'] << 16) | (R['t1'] << 11) | 0x24, 'and t1,t1,t2             CPU edges ignored')
    G.lui('t3', 0xF); G.addiu('t3', 't3', TB & 0xFFFF, 'addiu t3,t3,0x%X      stamp table' % (TB & 0xFFFF)); G.addiu('t4', 't3', 0x20)
    G.L('find'); G.lw('t5', 0, 't3'); G.beq('t5', 's0', 'hit'); G.nop(); G.beq('t5', 'zero', 'claim'); G.nop()
    G.addiu('t3', 't3', 8); G.bne('t3', 't4', 'find'); G.nop()
    G.beq('zero', 'zero', 'parity', 'b parity                 table full: treat as an input edge'); G.addiu('t6', 't0', 0)
    G.L('claim'); G.sw('s0', 0, 't3', 'sw s0,0(t3)              new fighter'); G.addiu('t5', 'zero', -16); G.sw('t5', 4, 't3')
    G.L('hit'); G.beq('t1', 'zero', 'stale'); G.nop(); G.sw('t0', 4, 't3', 'sw t0,4(t3)              input edge this vsync')
    G.L('stale'); G.lw('t6', 4, 't3', 'lw t6,4(t3)              last vsync with an input edge')
    G.L('parity'); G.andi('t7', 't0', 1); G.beq('t7', 'zero', 'even'); G.nop()
    G.raw(subu('t7', 't0', 't6'), 'subu t7,t0,t6'); G.raw(sltiu('t7', 't7', 2 if PREV else 1), 'sltiu t7,t7,%d            edge this vsync%s?' % (2 if PREV else 1, ' or the last' if PREV else ''))
    G.bne('t7', 'zero', 'req', 'bne t7,zero,req          odd + input: as the game'); G.nop()
    G.jal(0x001D7320, 'jal 001D7320             odd, no input: BtlChar_ApplyRootYaw only'); G.move('a0', 's0')
    G.j(0x001E2550, 'j 001E2550               then the RUN phase'); G.nop()
    G.L('even'); G.jal(0x000F2880, 'jal flush                even: effect flags raised since the last even tick become visible'); G.move('a0', 's0')
    G.L('req'); G.lw('v0', 4, 's1', 'lw v0,4(s1)              displaced: act.request'); G.beq('v0', 's2', 'noreq'); G.nop()
    G.j(0x001E243C, 'j 001E243C               request: switch now'); G.nop()
    G.L('noreq'); G.j(0x001E2530, 'j 001E2530               no request: apply animation requests'); G.nop()
    assert G.pc() <= TB, hex(G.pc())
    return G
if __name__ == '__main__':
    drop = lambda a: 0x000F21C0 <= a < 0x000F21E8 or a in (0x001D4A24, 0x001D4A28) or GB <= a < TB + 0x20
    L = [l.rstrip('\n') for l in open(sys.argv[1]) if l.startswith('patch=') and not drop(int(l.split(',')[2], 16))]
    L += asm.A.lines(build())
    assert sum(',001E2430,' in l for l in L) == 1
    open(sys.argv[2], 'w', newline='\n').write('\n'.join(L) + '\n'); print(len(L))

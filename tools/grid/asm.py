"""Tiny MIPS (EE) encoder for patch caves: asm.py emits patch lines.  Used by grid2gen.py."""
R = {n: i for i, n in enumerate('zero at v0 v1 a0 a1 a2 a3 t0 t1 t2 t3 t4 t5 t6 t7 s0 s1 s2 s3 s4 s5 s6 s7 t8 t9 k0 k1 gp sp fp ra'.split())}
def _i(op, rs, rt, imm): return (op << 26) | (R[rs] << 21) | (R[rt] << 16) | (imm & 0xFFFF)
def _r(rs, rt, rd, sh, fn): return (R[rs] << 21) | (R[rt] << 16) | (R[rd] << 11) | (sh << 6) | fn
class A:
    def __init__(s, base): s.base = base; s.ins = []; s.labels = {}; s.fix = []
    def pc(s): return s.base + 4 * len(s.ins)
    def L(s, name): s.labels[name] = s.pc()
    def emit(s, w, c=''): s.ins.append([w, c])
    def lui(s, rt, imm, c=''): s.emit(_i(0x0F, 'zero', rt, imm), c or 'lui %s,0x%X' % (rt, imm))
    def addiu(s, rt, rs, imm, c=''): s.emit(_i(0x09, rs, rt, imm), c or 'addiu %s,%s,%d' % (rt, rs, imm))
    def andi(s, rt, rs, imm, c=''): s.emit(_i(0x0C, rs, rt, imm), c or 'andi %s,%s,0x%X' % (rt, rs, imm))
    def lw(s, rt, off, base, c=''): s.emit(_i(0x23, base, rt, off), c or 'lw %s,0x%X(%s)' % (rt, off & 0xFFFF, base))
    def sw(s, rt, off, base, c=''): s.emit(_i(0x2B, base, rt, off), c or 'sw %s,0x%X(%s)' % (rt, off & 0xFFFF, base))
    def sd(s, rt, off, base, c=''): s.emit(_i(0x3F, base, rt, off), c or 'sd %s,0x%X(%s)' % (rt, off, base))
    def ld(s, rt, off, base, c=''): s.emit(_i(0x37, base, rt, off), c or 'ld %s,0x%X(%s)' % (rt, off, base))
    def move(s, rd, rs, c=''): s.emit(_r(rs, 'zero', rd, 0, 0x2D), c or 'move %s,%s' % (rd, rs))
    def or_(s, rd, rs, rt, c=''): s.emit(_r(rs, rt, rd, 0, 0x25), c or 'or %s,%s,%s' % (rd, rs, rt))
    def sllv(s, rd, rt, rs, c=''): s.emit(_r(rs, rt, rd, 0, 0x04), c or 'sllv %s,%s,%s' % (rd, rt, rs))
    def jr(s, rs, c=''): s.emit(_r(rs, 'zero', 'zero', 0, 0x08), c or 'jr %s' % rs)
    def nop(s, c=''): s.emit(0, c or 'nop')
    def j(s, tgt, c=''): s.emit(0x08000000 | ((tgt >> 2) & 0x3FFFFFF), c or 'j %08X' % tgt)
    def jal(s, tgt, c=''): s.emit(0x0C000000 | ((tgt >> 2) & 0x3FFFFFF), c or 'jal %08X' % tgt)
    def _b(s, op, rs, rt, lab, c):
        s.fix.append((len(s.ins), lab)); s.emit(_i(op, rs, rt, 0), c)
    def beq(s, rs, rt, lab, c=''): s._b(0x04, rs, rt, lab, c or 'beq %s,%s,%s' % (rs, rt, lab))
    def bne(s, rs, rt, lab, c=''): s._b(0x05, rs, rt, lab, c or 'bne %s,%s,%s' % (rs, rt, lab))
    def lines(s):
        for idx, lab in s.fix:
            off = (s.labels[lab] - (s.base + 4 * idx + 4)) >> 2
            s.ins[idx][0] = (s.ins[idx][0] & 0xFFFF0000) | (off & 0xFFFF)
        return ['patch=1,EE,%08X,word,%08X // %s' % (s.base + 4 * i, w, c) for i, (w, c) in enumerate(s.ins)]
def _bc1f(self, lab, c=''):
    self.fix.append((len(self.ins), lab)); self.emit(0x45000000, c or 'bc1f %s' % lab)
A.bc1f = _bc1f
def _raw(self, w, c): self.emit(w, c)
A.raw = _raw

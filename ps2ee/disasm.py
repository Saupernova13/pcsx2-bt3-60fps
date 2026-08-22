"""MIPS disassembly, function boundaries and cross-references for EE code.

Capstone has no R5900 mode, so COP2/VU macro-mode instructions come back as
undefined. That is fine for frame-pacing work, which lives in ordinary integer
and COP1 code, but do not trust this module inside a VU-heavy routine.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass

from capstone import CS_ARCH_MIPS, CS_MODE_LITTLE_ENDIAN, CS_MODE_MIPS64, Cs

from . import config
from .eemem import EEMemory, normalise

JR_RA = 0x03E00008
NOP = 0x00000000

_md = Cs(CS_ARCH_MIPS, CS_MODE_MIPS64 | CS_MODE_LITTLE_ENDIAN)
_md.detail = False


@dataclass
class Insn:
    addr: int
    word: int
    text: str

    def __str__(self) -> str:
        return f"{self.addr:08X}  {self.word:08X}  {self.text}"


def decode(word: int, addr: int = 0) -> str:
    ins = next(_md.disasm(struct.pack("<I", word), addr), None)
    return f"{ins.mnemonic} {ins.op_str}".strip() if ins else ".word"


def disasm(mem: EEMemory, start: int, count: int) -> list[Insn]:
    out = []
    for i in range(count):
        addr = start + i * 4
        word = mem.u32(addr)
        out.append(Insn(addr, word, decode(word, addr)))
    return out


def window(mem: EEMemory, addr: int, before: int = 8, after: int = 16) -> list[Insn]:
    return disasm(mem, addr - before * 4, before + after + 1)


def render(insns: list[Insn], mark: int | None = None) -> str:
    lines = []
    for ins in insns:
        prefix = ">>" if ins.addr == mark else "  "
        lines.append(f"{prefix} {ins}")
    return "\n".join(lines)


# --- jump/branch encoding --------------------------------------------------

def jal_word(target: int) -> int:
    return 0x0C000000 | ((normalise(target) >> 2) & 0x03FFFFFF)


def j_word(target: int) -> int:
    return 0x08000000 | ((normalise(target) >> 2) & 0x03FFFFFF)


def jump_target(word: int, addr: int) -> int | None:
    """Absolute target of a j/jal, resolved in the delay slot's 256 MB region."""
    if (word >> 26) not in (0x02, 0x03):
        return None
    return ((addr + 4) & 0xF0000000) | ((word & 0x03FFFFFF) << 2)


def branch_target(word: int, addr: int) -> int | None:
    """Target of a PC-relative branch, or None if this is not one."""
    op = word >> 26
    branch_ops = {0x01, 0x04, 0x05, 0x06, 0x07, 0x14, 0x15, 0x16, 0x17}
    cop_branch = op in (0x10, 0x11, 0x12) and ((word >> 21) & 0x1F) == 0x08
    if op not in branch_ops and not cop_branch:
        return None
    offset = struct.unpack("<h", struct.pack("<H", word & 0xFFFF))[0]
    return addr + 4 + offset * 4


# --- function boundaries ---------------------------------------------------

def function_start(mem: EEMemory, addr: int, limit: int = 0x4000) -> int:
    """Walk back to the instruction after the previous 'jr ra' delay slot.

    Heuristic, but reliable for compiler-emitted EE code where every function
    ends in 'jr ra' followed by its delay slot.
    """
    at = normalise(addr) & ~3
    floor = max(config.TEXT_BASE, at - limit)
    while at > floor:
        at -= 4
        if mem.u32(at) == JR_RA:
            return at + 8
    return floor


def function_end(mem: EEMemory, start: int, limit: int = 0x4000) -> int:
    """Address just past the delay slot of the function's first 'jr ra'."""
    at = normalise(start) & ~3
    ceiling = min(config.TEXT_END, at + limit)
    while at < ceiling:
        if mem.u32(at) == JR_RA:
            return at + 8
        at += 4
    return ceiling


def function_body(mem: EEMemory, addr: int) -> list[Insn]:
    start = function_start(mem, addr)
    end = function_end(mem, start)
    return disasm(mem, start, (end - start) // 4)


# --- cross references ------------------------------------------------------

@dataclass
class Xref:
    site: int
    kind: str          # "jal" | "j" | "pointer"
    context: list[Insn]


def callers(
    mem: EEMemory,
    target: int,
    start: int = config.TEXT_BASE,
    end: int = config.TEXT_END,
) -> list[Xref]:
    """Direct j/jal sites for a function, plus function-pointer references.

    A function with zero direct callers is reached indirectly (vtable, jump
    table, callback). The guide calls this the '0 callers group', and it is
    where the interesting main-loop code usually lives.
    """
    want_jal = jal_word(target)
    want_j = j_word(target)
    out: list[Xref] = []
    for addr in range(normalise(start), normalise(end), 4):
        word = mem.u32(addr)
        if word == want_jal or word == want_j:
            kind = "jal" if word == want_jal else "j"
            out.append(Xref(addr, kind, disasm(mem, addr - 8, 4)))
    for addr in mem.pointers_to(target):
        if not (normalise(start) <= addr < normalise(end)):
            out.append(Xref(addr, "pointer", []))
    return out


def scan_immediates(
    mem: EEMemory,
    values: dict[int, str],
    start: int = config.TEXT_BASE,
    end: int = config.TEXT_END,
) -> list[tuple[int, int, str, str]]:
    """Find li/lui/addiu/ori instructions loading suspect constants.

    This is the core heuristic of the guide's PS2_Scoring_Radar, reimplemented
    so candidates are available before Ghidra finishes auto-analysis. ``values``
    maps an immediate to a human label, e.g. {2: "30fps stride"}.
    """
    hits = []
    for addr in range(normalise(start), normalise(end), 4):
        word = mem.u32(addr)
        op = word >> 26
        imm = word & 0xFFFF
        rs = (word >> 21) & 0x1F
        if op == 0x0F:                      # lui rt, imm
            found = imm
        elif op == 0x09 and rs == 0:        # addiu rt, zero, imm  (li)
            found = imm
        elif op == 0x0D and rs == 0:        # ori rt, zero, imm    (li)
            found = imm
        else:
            continue
        if found in values:
            hits.append((addr, found, values[found], decode(word, addr)))
    return hits


# Memory-access opcodes: {opcode: (mnemonic, is_store)}.
_MEM_OPS = {
    0x20: ("lb", False), 0x21: ("lh", False), 0x22: ("lwl", False),
    0x23: ("lw", False), 0x24: ("lbu", False), 0x25: ("lhu", False),
    0x26: ("lwr", False), 0x27: ("lwu", False), 0x37: ("ld", False),
    0x31: ("lwc1", False), 0x35: ("ldc1", False), 0x1E: ("lq", False),
    0x28: ("sb", True), 0x29: ("sh", True), 0x2A: ("swl", True),
    0x2B: ("sw", True), 0x2C: ("sdl", True), 0x2D: ("sdr", True),
    0x2E: ("swr", True), 0x3F: ("sd", True), 0x39: ("swc1", True),
    0x3D: ("sdc1", True), 0x1F: ("sq", True),
}

# Registers a called function may not preserve, so an address held in one of
# them cannot be trusted across a jal.
_CALLER_SAVED = set(range(2, 16)) | {24, 25, 31}

_GP = 28


def _signed16(imm: int) -> int:
    return imm - 0x10000 if imm & 0x8000 else imm


def _dest_gpr(word: int) -> int | None:
    """The general register an instruction writes, if any.

    Deliberately pessimistic: anything unrecognised is treated as writing its
    rd field, because over-invalidating only costs a missed reference whereas
    under-invalidating invents one.
    """
    op, rs, rt, rd = word >> 26, (word >> 21) & 0x1F, (word >> 16) & 0x1F, (word >> 11) & 0x1F
    func = word & 0x3F
    if op == 0x00:
        if func in (0x08, 0x18, 0x19, 0x1A, 0x1B) or func in (0x0C, 0x0D, 0x0F):
            return None                     # jr, mult/div, syscall/break/sync
        return rd
    if op == 0x01:                          # REGIMM: only the ...al forms write
        return 31 if rt in (0x10, 0x11, 0x12, 0x13) else None
    if op in (0x02,):                       # j
        return None
    if op in (0x03,):                       # jal
        return 31
    if op in (0x04, 0x05, 0x06, 0x07, 0x14, 0x15, 0x16, 0x17):
        return None                         # branches
    if op == 0x11:                          # COP1: only mfc1/cfc1 write a GPR
        return rt if rs in (0x00, 0x02) else None
    if op in _MEM_OPS:
        mnemonic, is_store = _MEM_OPS[op]
        if is_store or mnemonic in ("lwc1", "ldc1"):
            return None
        return rt
    if op in (0x08, 0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x0E, 0x0F, 0x18, 0x19):
        return rt
    if op == 0x1C:                          # MMI
        return rd
    return rd


@dataclass
class DataRef:
    site: int
    kind: str          # load mnemonic, store mnemonic, or "&" for an address taken
    target: int
    text: str


def data_refs(
    mem: EEMemory,
    lo: int,
    hi: int,
    start: int = config.TEXT_BASE,
    end: int = config.TEXT_END,
) -> list[DataRef]:
    """Every instruction that reads, writes or takes the address of [lo, hi).

    MIPS has no absolute addressing, so a global is reached either through
    ``lui``/offset pairs or gp-relative. Both are reconstructed here by tracking
    what each register holds. This is the missing half of ``callers()``: for
    globals that are dispatched through function pointers, following the *data*
    is the only way to find the code that uses them.
    """
    lo, hi = normalise(lo), normalise(hi)
    tracked: dict[int, int] = {}
    out: list[DataRef] = []

    def record(site: int, kind: str, target: int, word: int) -> None:
        if lo <= normalise(target) < hi:
            out.append(DataRef(site, kind, target, decode(word, site)))

    for addr in range(normalise(start), normalise(end), 4):
        word = mem.u32(addr)
        op, rs, rt = word >> 26, (word >> 21) & 0x1F, (word >> 16) & 0x1F
        imm = word & 0xFFFF
        produced: int | None = None

        if op in _MEM_OPS:
            base = tracked.get(rs, config.GP_BASE if rs == _GP else None)
            if base is not None:
                record(addr, _MEM_OPS[op][0], base + _signed16(imm), word)
        elif op in (0x09, 0x19) and rs in tracked:          # addiu / daddiu
            produced = tracked[rs] + _signed16(imm)
            record(addr, "&", produced, word)
        elif op == 0x0D and rs in tracked:                  # ori
            produced = tracked[rs] | imm
            record(addr, "&", produced, word)

        if op == 0x0F:                                      # lui
            tracked[rt] = imm << 16
            continue
        dest = _dest_gpr(word)
        if dest is not None:
            # An addiu/ori off a tracked base carries the address forward, so
            # the load that follows still resolves.
            if produced is not None:
                tracked[dest] = produced
            else:
                tracked.pop(dest, None)
        if op == 0x03 or (op == 0x00 and (word & 0x3F) == 0x09):   # jal / jalr
            for reg in _CALLER_SAVED:
                tracked.pop(reg, None)
    return out

"""Safe installation of safe-zone trampolines into a running game.

Hand-rolling this is how you crash the emulator: assemble, write, arm the hook,
and if any step produced something unintended you find out by the game dying.
Every install here verifies the body read back byte-identical *before* the hook
is armed, and keeps the original word so it can be undone.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import config
from .asm import AsmError, assemble
from .disasm import decode, j_word, jump_target
from .pine import Pine


class InstallError(RuntimeError):
    pass


_REG_NAMES = [
    "zero", "at", "v0", "v1", "a0", "a1", "a2", "a3",
    "t0", "t1", "t2", "t3", "t4", "t5", "t6", "t7",
    "s0", "s1", "s2", "s3", "s4", "s5", "s6", "s7",
    "t8", "t9", "k0", "k1", "gp", "sp", "fp", "ra",
]

# Opcodes that write their rt field (loads and immediate arithmetic).
_WRITES_RT = {0x08, 0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x0E, 0x0F,
              0x18, 0x19, 0x20, 0x21, 0x22, 0x23, 0x24, 0x25,
              0x26, 0x27, 0x1A, 0x1B, 0x37}
# Opcodes that read both rs and rt without writing a GPR (stores, branches).
_READS_RS_RT = {0x04, 0x05, 0x14, 0x15, 0x28, 0x29, 0x2A, 0x2B,
                0x2C, 0x2D, 0x2E, 0x3F, 0x38, 0x39, 0x3D, 0x31, 0x35}


def _regs(word: int, addr: int) -> tuple[set[int], set[int]]:
    """(registers read, registers written) for one instruction.

    capstone does not implement regs_access() for MIPS, so the fields are
    decoded directly. Only GPRs matter here - the hazard we are guarding
    against is a displaced instruction that produces a value the delay slot
    consumes, and in practice that is always an integer register (usually $sp).
    """
    op = word >> 26
    rs, rt, rd = (word >> 21) & 0x1F, (word >> 16) & 0x1F, (word >> 11) & 0x1F
    reads: set[int] = set()
    writes: set[int] = set()
    if op == 0x00:                      # SPECIAL: reads rs+rt, writes rd
        reads |= {rs, rt}
        writes.add(rd)
    elif op == 0x1C:                    # MMI, treat conservatively
        reads |= {rs, rt}
        writes.add(rd)
    elif op in _WRITES_RT:
        if op != 0x0F:                  # lui has no rs operand
            reads.add(rs)
        writes.add(rt)
    elif op in _READS_RS_RT:
        reads |= {rs, rt}
    elif op in (0x02, 0x03):            # j / jal
        pass
    else:
        reads |= {rs, rt}
    reads.discard(0)
    writes.discard(0)
    return reads, writes


def _reg_name(n: int) -> str:
    return f"${_REG_NAMES[n]}" if 0 <= n < 32 else f"$r{n}"


def delay_slot_hazard(displaced: int, delay: int, addr: int) -> str | None:
    """Why a plain `j` hook at this site would corrupt state, or None if safe.

    Overwriting instruction H with a jump does NOT skip H+4: the delay slot
    still executes, *before* control reaches the trampoline. So the original
    order H then H+4 becomes H+4 then H. That reordering is only safe when the
    delay-slot instruction does not depend on the one being displaced.

    The classic trap is a function prologue: displacing `addiu $sp, $sp, -N`
    leaves `sd $ra, K($sp)` running against the old $sp, and if the trampoline
    then resumes at H+4 the store runs a second time as well.
    """
    _, writes = _regs(displaced, addr)
    reads, _ = _regs(delay, addr + 4)
    clash = writes & reads
    if clash:
        names = ", ".join(sorted(_reg_name(r) for r in clash))
        return (
            f"delay-slot hazard: the instruction at {addr+4:08X} reads {names}, "
            f"which {addr:08X} writes. Reordering them corrupts state - pick a "
            f"hook site whose next instruction is independent (a nop is ideal)."
        )
    return None


@dataclass
class Installed:
    hook: int
    original: int
    base: int
    words: list[int]


@dataclass
class LiveSession:
    """Tracks what has been written so it can all be rolled back."""

    pine: Pine
    installed: list[Installed] = field(default_factory=list)

    def check_alive(self) -> float:
        """Frames per second of the game's own counter - 0 means it is stuck."""
        import time

        a = self.pine.read(0x00331D64)
        time.sleep(0.7)
        b = self.pine.read(0x00331D64)
        return (b - a) / 0.7

    def install(self, hook: int, base: int, source: str, *,
                verify: bool = True, allow_hazard: bool = False) -> Installed:
        """Assemble source at base, verify it landed, then arm the hook.

        The hook word is a plain `j base`. The instruction in the hook's delay
        slot (hook+4) still runs before the jump, so the trampoline must replay
        only the displaced instruction at `hook` and resume at **hook+8**.
        Refuses sites where that reordering would corrupt state.
        """
        problem = delay_slot_hazard(self.pine.read(hook), self.pine.read(hook + 4), hook)
        if problem and not allow_hazard:
            raise InstallError(problem)
        if not (config.SAFE_ZONE <= base < config.SAFE_ZONE + config.SAFE_ZONE_SIZE):
            raise InstallError(f"{base:08X} is outside the safe zone")

        words = assemble(source, base)
        end = base + len(words) * 4
        if end > config.SAFE_ZONE + config.SAFE_ZONE_SIZE:
            raise InstallError("trampoline runs past the end of the safe zone")

        # Resuming at hook+4 runs the delay-slot instruction a second time,
        # because it already executed on the way into the trampoline. This is
        # the single easiest way to corrupt a stack frame, so refuse it.
        for i, w in enumerate(words):
            target = jump_target(w, base + i * 4)
            if target == hook + 4:
                raise InstallError(
                    f"trampoline jumps back to {hook+4:08X}, the hook's delay slot, "
                    f"which has already executed - resume at {hook+8:08X} instead"
                )
            if target == hook:
                raise InstallError(
                    f"trampoline jumps back to the hook itself ({hook:08X}) - infinite loop"
                )

        for other in self.installed:
            if base < other.base + len(other.words) * 4 and other.base < end:
                raise InstallError(
                    f"trampoline at {base:08X} overlaps the one at {other.base:08X}"
                )

        original = self.pine.read(hook)
        self.pine.write_words(base, words)

        if verify:
            back = self.pine.read_block(base, len(words))
            if back != words:
                for i, (w, b) in enumerate(zip(words, back)):
                    if w != b:
                        raise InstallError(
                            f"trampoline mismatch at {base + i*4:08X}: "
                            f"wrote {w:08X}, read {b:08X}"
                        )
                raise InstallError("trampoline length mismatch")

        self.pine.write(hook, j_word(base))
        armed = self.pine.read(hook)
        if armed != j_word(base):
            self.pine.write(hook, original)
            raise InstallError(f"hook at {hook:08X} did not take ({armed:08X})")

        record = Installed(hook, original, base, words)
        self.installed.append(record)
        return record

    def revert(self) -> None:
        """Restore every hooked instruction, newest first, and blank the bodies."""
        for rec in reversed(self.installed):
            self.pine.write(rec.hook, rec.original)
        for rec in reversed(self.installed):
            for i in range(len(rec.words)):
                self.pine.write(rec.base + i * 4, 0)
        self.installed.clear()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, *_):
        # A failed experiment must not leave the game in a broken state.
        if exc_type is not None:
            self.revert()


def replay_of(word: int, addr: int) -> str:
    """Assembly text that reproduces a displaced instruction.

    Round-trips through the assembler and refuses anything that does not
    re-encode to the identical word - capstone's text is not always something
    keystone reads back the same way, and a silently different instruction in a
    trampoline is very hard to debug.
    """
    text = decode(word, addr)
    try:
        back = assemble(text, addr)
    except AsmError as exc:
        raise InstallError(f"cannot re-assemble displaced insn {word:08X} ({text}): {exc}")
    if len(back) != 1 or back[0] != word:
        got = back[0] if len(back) == 1 else None
        raise InstallError(
            f"displaced insn {word:08X} ({text}) re-assembles to "
            f"{got:08X}" if got is not None else f"{len(back)} words"
        )
    return text

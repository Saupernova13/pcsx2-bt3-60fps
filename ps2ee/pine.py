"""PINE IPC client for a running PCSX2.

PINE is PCSX2's instrumentation socket. With it we can read and write EE memory,
save and load states and query emulator status while the game runs, so patch
experiments no longer need an emulator restart.

Enable it in PCSX2.ini under [EmuCore]:  EnablePINE = true  (PINESlot = 28011)

Wire format, all little-endian:
  request   u32 total_length | u8 opcode | payload
  reply     u32 total_length | u8 result (0 = ok) | payload

A single packet may carry several commands back to back; the replies come back
in the same order, which is what makes bulk reads usable.
"""

from __future__ import annotations

import socket
import struct
from dataclasses import dataclass

DEFAULT_PORT = 28011

MSG_READ8 = 0x00
MSG_READ16 = 0x01
MSG_READ32 = 0x02
MSG_READ64 = 0x03
MSG_WRITE8 = 0x04
MSG_WRITE16 = 0x05
MSG_WRITE32 = 0x06
MSG_WRITE64 = 0x07
MSG_VERSION = 0x08
MSG_SAVE_STATE = 0x09
MSG_LOAD_STATE = 0x0A
MSG_TITLE = 0x0B
MSG_ID = 0x0C
MSG_UUID = 0x0D
MSG_GAME_VERSION = 0x0E
MSG_STATUS = 0x0F

STATUS = {0: "running", 1: "paused", 2: "shutdown"}

_READ_SIZES = {MSG_READ8: 1, MSG_READ16: 2, MSG_READ32: 4, MSG_READ64: 8}
_WRITE_FMT = {MSG_WRITE8: "<B", MSG_WRITE16: "<H", MSG_WRITE32: "<I", MSG_WRITE64: "<Q"}


class PineError(RuntimeError):
    pass


class PineNotRunning(PineError):
    """PCSX2 is not listening - not enabled, not launched, or no game booted."""


@dataclass
class _Cmd:
    opcode: int
    payload: bytes
    reply_len: int   # bytes of reply payload, -1 for a length-prefixed string


class Pine:
    def __init__(self, port: int = DEFAULT_PORT, host: str = "127.0.0.1", timeout: float = 5.0):
        # 127.0.0.1 rather than localhost: localhost resolves ::1 first and
        # PCSX2 binds IPv4, costing a couple of seconds per connect.
        self.host = host
        self.port = port
        self.timeout = timeout
        self._sock: socket.socket | None = None

    # --- connection --------------------------------------------------------

    def connect(self) -> "Pine":
        try:
            self._sock = socket.create_connection((self.host, self.port), self.timeout)
            self._sock.settimeout(self.timeout)
        except OSError as exc:
            raise PineNotRunning(
                f"No PINE server on {self.host}:{self.port}. Check that PCSX2 is "
                f"running with EnablePINE = true and a game booted."
            ) from exc
        return self

    def close(self) -> None:
        if self._sock:
            self._sock.close()
            self._sock = None

    def __enter__(self):
        return self.connect()

    def __exit__(self, *exc):
        self.close()

    @classmethod
    def available(cls, port: int = DEFAULT_PORT) -> bool:
        try:
            with cls(port=port, timeout=1.0):
                return True
        except PineNotRunning:
            return False

    # --- transport ---------------------------------------------------------

    def _recv_exactly(self, n: int) -> bytes:
        chunks, got = [], 0
        while got < n:
            chunk = self._sock.recv(n - got)
            if not chunk:
                raise PineError("PINE connection closed mid-reply")
            chunks.append(chunk)
            got += len(chunk)
        return b"".join(chunks)

    def _send(self, commands: list[_Cmd]) -> list[bytes]:
        if self._sock is None:
            self.connect()
        body = b"".join(bytes([c.opcode]) + c.payload for c in commands)
        packet = struct.pack("<I", len(body) + 4) + body
        self._sock.sendall(packet)

        total = struct.unpack("<I", self._recv_exactly(4))[0]
        rest = self._recv_exactly(total - 4)
        if not rest:
            raise PineError("empty PINE reply")
        if rest[0] != 0:
            raise PineError(f"PINE returned error code {rest[0]}")

        replies, at = [], 1
        for cmd in commands:
            if cmd.reply_len < 0:
                size = struct.unpack_from("<I", rest, at)[0]
                at += 4
                replies.append(rest[at : at + size])
                at += size
            else:
                replies.append(rest[at : at + cmd.reply_len])
                at += cmd.reply_len
        return replies

    # --- memory ------------------------------------------------------------

    def read(self, addr: int, width: int = 4) -> int:
        opcode = {1: MSG_READ8, 2: MSG_READ16, 4: MSG_READ32, 8: MSG_READ64}[width]
        reply = self._send([_Cmd(opcode, struct.pack("<I", addr), width)])[0]
        return int.from_bytes(reply, "little")

    def read_many(self, addrs: list[int], width: int = 4) -> list[int]:
        """Batch several reads into one round trip."""
        opcode = {1: MSG_READ8, 2: MSG_READ16, 4: MSG_READ32, 8: MSG_READ64}[width]
        cmds = [_Cmd(opcode, struct.pack("<I", a), width) for a in addrs]
        return [int.from_bytes(r, "little") for r in self._send(cmds)]

    def read_block(self, addr: int, n_words: int) -> list[int]:
        return self.read_many([addr + i * 4 for i in range(n_words)], 4)

    def write(self, addr: int, value: int, width: int = 4) -> None:
        opcode = {1: MSG_WRITE8, 2: MSG_WRITE16, 4: MSG_WRITE32, 8: MSG_WRITE64}[width]
        payload = struct.pack("<I", addr) + struct.pack(_WRITE_FMT[opcode], value)
        self._send([_Cmd(opcode, payload, 0)])

    def write_words(self, addr: int, words: list[int]) -> None:
        """Apply a run of word writes in one round trip.

        This is how a patch gets tested without restarting: assemble it, write
        it live, and the next frame runs the new code.
        """
        cmds = [
            _Cmd(MSG_WRITE32, struct.pack("<II", addr + i * 4, w), 0)
            for i, w in enumerate(words)
        ]
        self._send(cmds)

    # --- emulator ----------------------------------------------------------

    def status(self) -> str:
        raw = self._send([_Cmd(MSG_STATUS, b"", 4)])[0]
        return STATUS.get(struct.unpack("<I", raw)[0], "unknown")

    def _string(self, opcode: int) -> str:
        raw = self._send([_Cmd(opcode, b"", -1)])[0]
        return raw.rstrip(b"\x00").decode("utf-8", "replace")

    def title(self) -> str:
        return self._string(MSG_TITLE)

    def game_id(self) -> str:
        return self._string(MSG_ID)

    def game_version(self) -> str:
        return self._string(MSG_GAME_VERSION)

    def emulator_version(self) -> str:
        return self._string(MSG_VERSION)

    def save_state(self, slot: int) -> None:
        self._send([_Cmd(MSG_SAVE_STATE, bytes([slot]), 0)])

    def load_state(self, slot: int) -> None:
        self._send([_Cmd(MSG_LOAD_STATE, bytes([slot]), 0)])

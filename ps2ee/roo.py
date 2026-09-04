"""PCSXROO debug-server client.

PCSXROO is a PCSX2 fork that exposes the whole debugger over a loopback JSON
socket, so breakpoints, registers, single stepping and screenshots are all
scriptable. PINE could only read and write memory; this can stop the CPU and
ask it where it came from, which is the tool this project actually needs.

Wire format: one UTF-8 JSON object per line, request and reply both.

    {"id": 7, "cmd": "mem.read", "args": {"addr": 1227728, "size": 4}}
    {"id": 7, "ok": true, "result": {...}}
    {"id": 7, "ok": false, "error": {"code": "not_paused", "message": "..."}}

The read/write surface deliberately matches ``ps2ee.pine.Pine`` so a script can
switch between the two by changing one constructor call.

Traps, all of them learned the hard way and all of them silent:

* ``wait`` without ``since`` blocks for the *next* stop, so a breakpoint that
  fired between ``resume()`` and ``wait()`` hangs the caller forever. Every
  helper here threads a sequence number through instead.
* Registers, ``stack`` and stepping need a paused VM; memory reads do not.
* Screenshots need a *running* VM and a **backslash Windows path**. A forward
  slash path is accepted, reports ``queued``, and never writes a file.
* An armed breakpoint in a hot loop re-pauses the VM before it can present a
  frame, so screenshots stop landing until it is cleared.
"""

from __future__ import annotations

import json
import socket
import struct
import time
from dataclasses import dataclass

DEFAULT_PORT = 28110


class RooError(RuntimeError):
    """The server answered, and said no."""

    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


class RooNotRunning(RooError):
    """Nothing is listening - PCSXROO is not up, or is on another port."""

    def __init__(self, port: int):
        RuntimeError.__init__(
            self, f"nothing listening on 127.0.0.1:{port} - launch PCSXROO first"
        )
        self.code = "no_server"
        self.message = "not running"


@dataclass
class Stop:
    """A stop event. The same shape comes back from wait, pause and step."""

    seq: int
    reason: str
    pc: int
    bp_addr: int
    mem_addr: int
    mem_size: int
    mem_write: bool

    @classmethod
    def from_json(cls, d: dict) -> "Stop":
        return cls(
            seq=d.get("seq", 0),
            reason=d.get("reason", "none"),
            pc=d.get("pc", 0),
            bp_addr=d.get("bp_addr", 0),
            mem_addr=d.get("mem_addr", 0),
            mem_size=d.get("mem_size", 0),
            mem_write=d.get("mem_write", False),
        )

    def __str__(self) -> str:
        where = f"pc={self.pc:08X}"
        if self.mem_addr:
            what = "write" if self.mem_write else "read"
            where += f" {what} {self.mem_addr:08X}+{self.mem_size}"
        return f"[{self.seq}] {self.reason} {where}"


class Roo:
    """A connection to one PCSXROO debug server."""

    def __init__(self, port: int = DEFAULT_PORT, host: str = "127.0.0.1",
                 timeout: float = 10.0):
        self.port = port
        self.host = host
        self.timeout = timeout
        self._sock: socket.socket | None = None
        self._buf = b""
        self._id = 0

    # --- connection --------------------------------------------------------

    def connect(self) -> "Roo":
        try:
            self._sock = socket.create_connection((self.host, self.port), self.timeout)
        except OSError as exc:
            raise RooNotRunning(self.port) from exc
        self._sock.settimeout(self.timeout)
        return self

    def close(self) -> None:
        if self._sock:
            self._sock.close()
            self._sock = None

    def __enter__(self):
        return self.connect() if self._sock is None else self

    def __exit__(self, *exc):
        self.close()

    @classmethod
    def available(cls, port: int = DEFAULT_PORT) -> bool:
        try:
            with cls(port=port, timeout=1.0):
                return True
        except RooNotRunning:
            return False

    # --- protocol ----------------------------------------------------------

    def cmd(self, command: str, /, timeout: float | None = None, **args):
        """Send one command and return its ``result``, or raise RooError.

        ``command`` is positional-only because several commands take an
        argument of their own called ``name``, which would collide with it.
        """
        if self._sock is None:
            self.connect()
        self._id += 1
        line = json.dumps({"id": self._id, "cmd": command, "args": args}) + "\n"
        if timeout is not None:
            self._sock.settimeout(timeout)
        try:
            self._sock.sendall(line.encode())
            reply = json.loads(self._readline())
        finally:
            if timeout is not None:
                self._sock.settimeout(self.timeout)
        if not reply.get("ok"):
            error = reply.get("error", {})
            raise RooError(error.get("code", "?"), error.get("message", ""))
        return reply.get("result", {})

    def _readline(self) -> bytes:
        while b"\n" not in self._buf:
            chunk = self._sock.recv(65536)
            if not chunk:
                raise RooError("io_error", "the server closed the connection")
            self._buf += chunk
        line, self._buf = self._buf.split(b"\n", 1)
        return line

    # --- memory, matching the Pine surface ---------------------------------

    def read_bytes(self, addr: int, size: int) -> bytes:
        return bytes.fromhex(self.cmd("mem.read", addr=addr, size=size)["data"])

    def read(self, addr: int, width: int = 4) -> int:
        raw = self.read_bytes(addr, width)
        return int.from_bytes(raw, "little")

    def read_many(self, addrs: list[int], width: int = 4) -> list[int]:
        return [self.read(a, width) for a in addrs]

    def read_block(self, addr: int, n_words: int) -> list[int]:
        raw = self.read_bytes(addr, n_words * 4)
        return list(struct.unpack(f"<{n_words}I", raw))

    def read_f32(self, addr: int) -> float:
        return struct.unpack("<f", self.read_bytes(addr, 4))[0]

    def read_vec(self, addr: int) -> tuple[float, ...]:
        """The engine's native quantity: four contiguous floats."""
        return struct.unpack("<4f", self.read_bytes(addr, 16))

    def write_bytes(self, addr: int, data: bytes) -> bool:
        """Write, and report whether the readback matched.

        Always check the return value. A word the game rewrites every frame -
        or one a ``patch=1`` cheat line owns - looks exactly like a successful
        write otherwise.
        """
        return self.cmd("mem.write", addr=addr, data=data.hex())["verified"]

    def write(self, addr: int, value: int, width: int = 4) -> bool:
        return self.write_bytes(addr, value.to_bytes(width, "little"))

    def write_words(self, addr: int, words: list[int]) -> bool:
        return self.write_bytes(addr, struct.pack(f"<{len(words)}I", *words))

    # --- execution ---------------------------------------------------------

    def status(self) -> dict:
        return self.cmd("status")

    def seq(self) -> int:
        """The sequence number of the newest stop, to pass to wait()."""
        return self.status()["last_stop"]["seq"]

    def paused(self) -> bool:
        return self.status()["paused"]

    def pause(self) -> Stop:
        return Stop.from_json(self.cmd("pause"))

    def resume(self) -> None:
        self.cmd("run")

    def wait(self, since: int, timeout_ms: int = 60000) -> Stop | None:
        """Block for the next stop after ``since``. None on timeout.

        ``since`` is not optional on purpose: a bare wait blocks for the stop
        *after* one that has already happened, which is the single most common
        way an unattended session hangs.
        """
        try:
            return Stop.from_json(self.cmd(
                "wait", since=since, timeout_ms=timeout_ms,
                timeout=timeout_ms / 1000 + 5))
        except RooError as exc:
            if exc.code == "timeout":
                return None
            raise

    def frame_advance(self, count: int = 1) -> Stop:
        return Stop.from_json(self.cmd(
            "frame-advance", count=count, timeout_ms=10000, timeout=20)["stop"])

    def step(self, mode: str = "into") -> Stop:
        return Stop.from_json(self.cmd("step", mode=mode))

    # --- breakpoints -------------------------------------------------------

    def bp_add(self, addr: int, condition: str | None = None,
               description: str = "", temporary: bool = False) -> None:
        args = {"addr": addr, "temporary": temporary, "description": description}
        if condition:
            args["condition"] = condition
        self.cmd("bp.add", **args)

    def bp_remove(self, addr: int) -> None:
        self.cmd("bp.remove", addr=addr)

    def bp_clear(self) -> None:
        self.cmd("bp.clear")

    def mc_add(self, start: int, end: int, on=("write",)) -> dict:
        return self.cmd("mc.add", start=start, end=end, on=list(on))

    def mc_clear(self) -> None:
        self.cmd("mc.clear")

    # --- registers (paused only) -------------------------------------------

    def reg(self, name: str) -> int:
        """One GPR as an unsigned 32-bit value, which is what addresses are."""
        return self.cmd("reg.get", name=name)["value_u64"] & 0xFFFFFFFF

    def regs(self, category: str = "GPR") -> dict[str, int]:
        dump = self.cmd("reg.dump", category=category)
        return {r["name"]: r["value_u64"] & 0xFFFFFFFF
                for r in dump.get("registers", [])}

    def dis(self, addr: int, count: int = 8) -> list[tuple[int, str]]:
        out = self.cmd("dis", addr=addr, count=count)["instructions"]
        return [(i["addr"], i["text"]) for i in out]

    # --- observation -------------------------------------------------------

    def screenshot(self, path) -> str:
        """Queue a screenshot. Needs a RUNNING VM and a backslash path.

        Returns the path; poll for the file, the capture is asynchronous.
        """
        native = str(path).replace("/", "\\")
        self.cmd("screenshot", path=native)
        return native

    def savestate(self, slot: int, wait_flush: bool = True) -> None:
        self.cmd("savestate", slot=slot, wait_flush=wait_flush, timeout=60)

    def loadstate(self, slot: int) -> None:
        """Restore a state, deterministically.

        Pausing first matters more than it looks. A load into a running VM
        leaves the game executing while the client gets its reply, so however
        many frames fit in that window are already gone - and the number varies
        per call. Two runs of the same experiment then start from different
        states. Loading into a paused VM restores bit-identically every time.
        """
        if not self.paused():
            self.pause()
        self.cmd("loadstate", slot=slot, timeout=60)

    def patch_reload(self) -> None:
        """Re-read the pnach files. Without this they are only read at boot."""
        self.cmd("patch.reload", timeout=20)

    def input_press(self, *buttons: str, frames: int = 2) -> None:
        self.cmd("input.press", buttons=list(buttons), duration_frames=frames)

    def input_set(self, *buttons: str, left=None, right=None) -> None:
        args: dict = {"buttons": list(buttons)}
        analog = {}
        if left:
            analog["left"] = {"x": left[0], "y": left[1]}
        if right:
            analog["right"] = {"x": right[0], "y": right[1]}
        if analog:
            args["analog"] = analog
        self.cmd("input.set", **args)

    def input_release(self) -> None:
        self.cmd("input.release")

    def flush_input(self) -> None:
        """Release the pad and make sure the release actually lands.

        ``input.release`` only queues: the hook that writes the pad runs on
        frames the VM executes, and is skipped on the last frame of any
        advance. A release issued while paused therefore does nothing at all,
        and the pad keeps the previous test's button held. The next state load
        then starts with that button still down for one frame - enough to
        throw a punch, which quietly invalidates the run that follows.

        Call this before loading a state, not after: the contaminated frame is
        the first frame after the load, so a flush that comes later is too
        late to prevent it.
        """
        self.input_release()
        self.frame_advance(3)
        self.input_release()

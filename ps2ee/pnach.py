"""Parse, emit, validate and deploy PCSX2 pnach files.

Only the subset PCSX2 2.x actually honours is modelled: 'patch=<place>,<cpu>,
<address>,<type>,<value>' plus the '[Group]' / 'description=' headers, and
E-code conditionals.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from . import config

WIDTHS = {
    "byte": 1,
    "short": 2,
    "word": 4,
    "double": 8,
    "extended": 4,   # 'extended' is a word write with raw-code semantics
    "leshort": 2,
    "leword": 4,
    "beshort": 2,
    "beword": 4,
}

PATCH_RE = re.compile(
    r"^patch\s*=\s*(?P<place>[01])\s*,\s*(?P<cpu>EE|IOP)\s*,\s*"
    r"(?P<addr>[0-9A-Fa-f]{1,8})\s*,\s*(?P<type>\w+)\s*,\s*"
    r"(?P<value>[0-9A-Fa-f]{1,16})\s*(?://(?P<comment>.*))?$",
    re.IGNORECASE,
)


@dataclass
class Line:
    place: int
    cpu: str
    addr: int
    type: str
    value: int
    comment: str = ""

    @property
    def is_condition(self) -> bool:
        """E-codes gate the line that follows them (guide Section 5)."""
        return (self.addr >> 28) == 0xE

    def render(self) -> str:
        width = WIDTHS.get(self.type.lower(), 4)
        text = f"patch={self.place},{self.cpu},{self.addr:08X},{self.type},{self.value:0{width * 2}X}"
        return f"{text} // {self.comment}" if self.comment else text


@dataclass
class Group:
    name: str
    description: str = ""
    lines: list[Line] = field(default_factory=list)
    raw: list[str] = field(default_factory=list)

    def render(self) -> str:
        out = [f"[{self.name}]"]
        if self.description:
            out.append(f"description={self.description}")
        out += [line.render() for line in self.lines]
        return "\n".join(out)


class Pnach:
    def __init__(self, groups: list[Group] | None = None, preamble: list[str] | None = None):
        self.groups = groups or []
        self.preamble = preamble or []

    @classmethod
    def parse(cls, text: str) -> "Pnach":
        pnach = cls()
        current: Group | None = None
        for raw in text.splitlines():
            stripped = raw.strip()
            if stripped.startswith("[") and stripped.endswith("]"):
                current = Group(stripped[1:-1])
                pnach.groups.append(current)
                continue
            if current is None:
                pnach.preamble.append(raw)
                continue
            if stripped.lower().startswith("description="):
                current.description = stripped.split("=", 1)[1].strip()
                continue
            match = PATCH_RE.match(stripped)
            if match:
                current.lines.append(
                    Line(
                        place=int(match["place"]),
                        cpu=match["cpu"].upper(),
                        addr=int(match["addr"], 16),
                        type=match["type"].lower(),
                        value=int(match["value"], 16),
                        comment=(match["comment"] or "").strip(),
                    )
                )
            else:
                current.raw.append(raw)
        return pnach

    @classmethod
    def load(cls, path: str | Path) -> "Pnach":
        return cls.parse(Path(path).read_text(errors="replace"))

    def render(self) -> str:
        parts = list(self.preamble)
        parts += [group.render() for group in self.groups]
        return "\n".join(parts).rstrip() + "\n"

    def save(self, path: str | Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        # LF endings; PCSX2 accepts either and LF keeps git diffs clean.
        path.write_text(self.render(), newline="\n")
        return path

    def group(self, name: str) -> Group:
        for group in self.groups:
            if group.name == name:
                return group
        group = Group(name)
        self.groups.append(group)
        return group

    def validate(self) -> list[str]:
        """Problems that would silently produce a no-op or a crash."""
        problems: list[str] = []
        seen: dict[tuple[str, int], str] = {}
        for group in self.groups:
            pending_condition = False
            for line in group.lines:
                where = f"[{group.name}] {line.render()}"
                if line.type.lower() not in WIDTHS:
                    problems.append(f"{where}: unknown patch type '{line.type}'")
                if line.is_condition:
                    pending_condition = True
                    continue
                if line.cpu == "EE":
                    addr = line.addr & 0x01FFFFFF
                    if addr >= config.EE_RAM_SIZE:
                        problems.append(f"{where}: address beyond 32 MB of EE RAM")
                    in_text = config.TEXT_BASE <= addr < config.TEXT_END
                    in_safe = (
                        config.SAFE_ZONE
                        <= addr
                        < config.SAFE_ZONE + config.SAFE_ZONE_SIZE
                    )
                    in_data = config.DATA_BASE <= addr < config.BSS_END
                    if not (in_text or in_safe or in_data):
                        problems.append(
                            f"{where}: {addr:08X} is outside .text, .data and the safe zone"
                        )
                    if addr % 4 and line.type.lower() in ("word", "extended"):
                        problems.append(f"{where}: unaligned word write")
                # A conditional line consumes the condition above it.
                key = (line.cpu, line.addr)
                if not pending_condition and key in seen:
                    problems.append(
                        f"{where}: overwrites an earlier write from {seen[key]}"
                    )
                seen[key] = group.name
                pending_condition = False
            if pending_condition:
                problems.append(f"[{group.name}]: E-code condition with no line after it")
        return problems


def deploy(
    pnach: Pnach | str | Path,
    enable: list[str] | None = None,
    dest: Path | None = None,
) -> tuple[Path, list[str]]:
    """Install a pnach into PCSX2's cheats dir and enable groups in the game ini.

    Returns the destination path and the list of enabled group names. PCSX2 2.x
    keeps per-cheat enablement in gamesettings/<SERIAL>_<CRC>.ini under
    [Cheats]; a cheat present in the pnach but absent there stays off.
    """
    if not isinstance(pnach, Pnach):
        pnach = Pnach.load(pnach)
    problems = pnach.validate()
    if problems:
        raise ValueError("refusing to deploy an invalid pnach:\n  " + "\n  ".join(problems))

    dest = dest or (config.cheats_dir() / f"{config.CRC}.pnach")
    pnach.save(dest)

    names = enable if enable is not None else [g.name for g in pnach.groups]
    _set_enabled_cheats(config.game_ini(), names)
    return dest, names


def _set_enabled_cheats(ini_path: Path, names: list[str]) -> None:
    """Rewrite the [Cheats] section, leaving every other section untouched."""
    ini_path.parent.mkdir(parents=True, exist_ok=True)
    text = ini_path.read_text(errors="replace") if ini_path.exists() else ""
    lines = text.splitlines()

    out: list[str] = []
    in_cheats = False
    replaced = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            if in_cheats:
                in_cheats = False
            if stripped.lower() == "[cheats]":
                in_cheats = True
                replaced = True
                out.append("[Cheats]")
                out += [f"Enable = {name}" for name in names]
                continue
        if in_cheats:
            continue  # drop the old Enable lines
        out.append(line)

    if not replaced:
        if out and out[-1].strip():
            out.append("")
        out.append("[Cheats]")
        out += [f"Enable = {name}" for name in names]

    ini_path.write_text("\n".join(out).rstrip() + "\n", newline="\n")

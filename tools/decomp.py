"""Decompile BT3 functions through Ghidra headless.

Runs DumpFunction.java against the analysed project and prints the C pseudocode
plus listing for each address. Results are cached under work/decomp/ because a
headless round trip costs about half a minute.

    python tools/decomp.py 264D98
    python tools/decomp.py 102034 --xrefs
    python tools/decomp.py 1DCB20 --refresh
"""

import argparse
import re
import subprocess
import sys

import _bootstrap  # noqa: F401

from bt3 import config



def ghidra_home():
    """Locate the Ghidra install."""
    import os
    from pathlib import Path

    explicit = os.environ.get("GHIDRA_HOME")
    if explicit:
        return Path(explicit)
    from bt3.config import _setting

    configured = _setting("GHIDRA_HOME")
    if configured:
        return Path(configured)
    for candidate in (Path("C:/Utils/ghidra"), Path("C:/ghidra"),
                      Path.home() / "ghidra"):
        if (candidate / "support" / "analyzeHeadless.bat").exists():
            return candidate
    raise FileNotFoundError(
        "Ghidra not found. Set GHIDRA_HOME in the environment or local.json."
    )


PROJECT_DIR = config.WORK / "ghidra"
PROJECT_NAME = "BT3"
CACHE = config.WORK / "decomp"


def run_headless(addrs: list[str], xrefs: bool) -> str:
    home = ghidra_home()
    script_args = (["-xrefs"] if xrefs else []) + addrs
    cmd = [
        str(home / "support" / "analyzeHeadless.bat"),
        str(PROJECT_DIR),
        PROJECT_NAME,
        "-process", config.ELF_NAME,
        "-noanalysis",
        "-scriptPath", str(config.REPO / "ghidra" / "scripts"),
        "-postScript", "DumpFunction.java", *script_args,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, errors="replace")
    if result.returncode != 0:
        sys.stderr.write(result.stdout[-4000:])
        sys.stderr.write(result.stderr[-4000:])
        raise RuntimeError(f"analyzeHeadless failed with {result.returncode}")
    return result.stdout


# Headless wraps each println as 'INFO  <script>.java> <text> (GhidraScript)'. A
# multi-line println only gets the prefix on its first line and the suffix on its
# last, so both have to be stripped independently, line by line.
_PREFIX = re.compile(r"^INFO\s+\S+\.java>\s?")
_SUFFIX = re.compile(r"\s*\(GhidraScript\)\s*$")


def split_sections(output: str) -> dict[str, str]:
    """Pull each ###BEGIN/###END block out of the headless log noise."""
    sections: dict[str, str] = {}
    current: str | None = None
    body: list[str] = []
    for raw in output.splitlines():
        line = _SUFFIX.sub("", _PREFIX.sub("", raw))
        stripped = line.strip()
        if stripped.startswith("###BEGIN "):
            current = stripped.split(None, 1)[1]
            body = []
            continue
        if stripped.startswith("###END ") and current is not None:
            sections[current] = "\n".join(body).strip("\n")
            current = None
            continue
        if current is not None:
            body.append(line)
    return sections


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("addrs", nargs="+", help="hex EE addresses")
    parser.add_argument("--xrefs", action="store_true", help="also list callers/callees")
    parser.add_argument("--refresh", action="store_true", help="ignore the cache")
    args = parser.parse_args()

    CACHE.mkdir(parents=True, exist_ok=True)
    suffix = "-xrefs" if args.xrefs else ""
    wanted, cached = [], {}
    for addr in args.addrs:
        key = addr.upper().removeprefix("0X")
        path = CACHE / f"{key}{suffix}.txt"
        if path.exists() and not args.refresh:
            cached[addr] = path.read_text(errors="replace")
        else:
            wanted.append(addr)

    if wanted:
        sys.stderr.write(f"# ghidra headless: {', '.join(wanted)}\n")
        sections = split_sections(run_headless(wanted, args.xrefs))
        for addr in wanted:
            body = sections.get(addr, "(no output - address not found in project)")
            key = addr.upper().removeprefix("0X")
            (CACHE / f"{key}{suffix}.txt").write_text(body, newline="\n")
            cached[addr] = body

    for addr in args.addrs:
        print(f"===== {addr} =====")
        print(cached[addr])
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

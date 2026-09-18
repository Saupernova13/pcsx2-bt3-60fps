"""Make game/ and PCSXROO's ps2ee library importable for the tools.

The tools and the game knowledge (tools/game/) live side by side, so this adds
tools/ itself. The generic ps2ee library lives in PCSXROO
(https://github.com/Saupernova13/pcsxroo), under pcsxroo/ps2ee/. The PCSXROO
checkout is found from the first of these that is set:

1. the PCSXROO_REPO environment variable,
2. a "PCSXROO_REPO" key in this repo's local.json,
3. a sibling checkout named pcsxroo, next to this repo.

Import this before anything third-party. Until it has run, tools/ is still at
the front of sys.path and shadows the stdlib - see the sys.path note below.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
REPO = TOOLS.parent
PCSXROO_URL = "https://github.com/Saupernova13/pcsxroo"


def _has_ps2ee(root: Path) -> bool:
    return (root / "pcsxroo" / "ps2ee" / "__init__.py").is_file()


def _local_json_setting() -> str | None:
    path = REPO / "local.json"
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8")).get("PCSXROO_REPO")
    except ValueError as exc:
        raise SystemExit(f"{path} is not valid JSON: {exc}") from None


def find_pcsxroo() -> Path:
    """The PCSXROO checkout, or exit with one sentence saying how to provide it."""
    # A location that is set but wrong is reported as such, rather than quietly
    # falling through to a different checkout than the one asked for.
    for source, value in (
        ("the PCSXROO_REPO environment variable", os.environ.get("PCSXROO_REPO")),
        (f"PCSXROO_REPO in {REPO / 'local.json'}", _local_json_setting()),
    ):
        if value:
            root = Path(value).expanduser().resolve()
            if not _has_ps2ee(root):
                raise SystemExit(f"{source} points at {root}, which is not a PCSXROO checkout (it has no pcsxroo/ps2ee).")
            return root

    sibling = REPO.parent / "pcsxroo"
    if _has_ps2ee(sibling):
        return sibling.resolve()

    raise SystemExit(
        "Cannot find PCSXROO, which these tools need: set PCSXROO_REPO in the environment or in "
        f"local.json, or clone {PCSXROO_URL} next to this repo as {sibling}."
    )


PCSXROO = find_pcsxroo()

# Appended, never prepended, so a tool can never shadow a stdlib module. Running
# `python tools/<tool>.py` puts tools/ at sys.path[0], and tools/bisect.py then
# wins over the stdlib `bisect` that `random` imports - which breaks any later
# import of capstone, and with it ps2ee, on any interpreter that has not already
# loaded `bisect`. Both paths go on the end, stdlib stays ahead of them.
#
# Order between the two is kept: tools/ before PCSXROO's, so this repo's own
# module wins a name collision.
#
# Two things are needed for that to hold, and both have been got wrong here:
#
# - A tool must import this before anything third-party. numpy and PIL reach
#   the stdlib on their own, and a tool that imports them first does so while
#   tools/ is still at sys.path[0].
# - An entry is matched by what it resolves to, not by how it is spelled. tools/
#   can also reach sys.path as the relative "tools" a tool inserted for itself,
#   which a comparison against the absolute path misses - and one relative entry
#   at the front brings the shadowing straight back.
#
# .github/workflows/check.yml runs every tool with --help, which is what catches
# either mistake: the shadowing is only fatal on an interpreter that has not
# already loaded the module being shadowed.


def _same_dir(entry: str, target: Path) -> bool:
    try:
        return Path(entry or ".").resolve() == target
    except OSError:      # an unresolvable entry is not the one being moved
        return False


for path in (TOOLS, (PCSXROO / "pcsxroo").resolve()):
    sys.path[:] = [entry for entry in sys.path if not _same_dir(entry, path)]
    sys.path.append(str(path))

"""Make game/ and PCSXROO's ps2ee library importable for the tools.

Adds tools/ itself, and the PCSXROO checkout (pcsxroo/ps2ee/), found from the
first of: the PCSXROO_REPO environment variable, a "PCSXROO_REPO" key in this
repo's local.json, a sibling checkout named pcsxroo.

Import this before anything third-party (see the sys.path note below).
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
    # A location that is set but wrong is reported, not silently replaced by another checkout.
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

# Appended, never prepended, so a tool can never shadow a stdlib module: running
# `python tools/<tool>.py` puts tools/ at sys.path[0], and tools/bisect.py would
# beat the stdlib `bisect`, breaking capstone and ps2ee on Linux. tools/ stays
# before PCSXROO's path so this repo's module wins a name collision.
#
# - A tool must import this before anything third-party; numpy and PIL reach the
#   stdlib on their own while tools/ is still at sys.path[0].
# - Entries are matched by what they resolve to: a relative "tools" entry at the
#   front brings the shadowing back.
#
# .github/workflows/check.yml runs every tool with --help to catch either mistake.


def _same_dir(entry: str, target: Path) -> bool:
    try:
        return Path(entry or ".").resolve() == target
    except OSError:      # an unresolvable entry is not the one being moved
        return False


for path in (TOOLS, (PCSXROO / "pcsxroo").resolve()):
    sys.path[:] = [entry for entry in sys.path if not _same_dir(entry, path)]
    sys.path.append(str(path))

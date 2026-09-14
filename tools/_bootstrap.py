"""Make game/ and PCSXROO's ps2ee library importable for the tools.

The tools and the game knowledge (tools/game/) live side by side, so this adds
tools/ itself. The generic ps2ee library lives in PCSXROO
(https://github.com/Saupernova13/pcsxroo), under pcsxroo/ps2ee/. The PCSXROO
checkout is found from the first of these that is set:

1. the PCSXROO_REPO environment variable,
2. a "PCSXROO_REPO" key in this repo's local.json,
3. a sibling checkout named pcsxroo, next to this repo.
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

# This repo's own modules first, so a name in tools/ always wins over PCSXROO's.
for index, path in enumerate((TOOLS, PCSXROO / "pcsxroo")):
    if str(path) in sys.path:
        sys.path.remove(str(path))
    sys.path.insert(index, str(path))

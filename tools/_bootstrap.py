"""Make bt3 and the sibling pcsxroo checkout importable for the tools.

This repo carries the game knowledge (bt3/) and the BT3-specific tools. The
generic ps2ee library lives in the sibling pcsxroo checkout, under
tools/pcsxroo/ - a checkout of pcsxroo next to this repo is required.
"""

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PCSXROO_TOOLS = REPO.parent / "pcsxroo" / "tools" / "pcsxroo"
for p in (REPO, PCSXROO_TOOLS):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

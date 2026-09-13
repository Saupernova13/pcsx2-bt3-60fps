"""Make game/ and the sibling pcsxroo checkout importable for the tools.

The tools and the game knowledge (tools/game/) live side by side, so this
adds tools/ itself. The generic ps2ee library lives in the sibling pcsxroo
checkout, under tools/pcsxroo/ - a checkout of pcsxroo next to this repo is
required.
"""

import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
PCSXROO_TOOLS = TOOLS.parent.parent / "pcsxroo" / "tools" / "pcsxroo"
for p in (TOOLS, PCSXROO_TOOLS):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

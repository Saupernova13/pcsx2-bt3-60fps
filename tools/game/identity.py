"""Everything true of Dragon Ball Z: Budokai Tenkaichi 3 and nothing else.

The generic ps2ee library (in the sibling pcsxroo checkout) must not carry this
game knowledge: identity, ELF layout, the safe zone, and the patch policy.
"""

from ps2ee.config import GameIdentity

SERIAL = "SLUS-21678"
CRC = "428113C2"
ELF_NAME = "SLUS_216.78"
GAME = "Dragon Ball Z: Budokai Tenkaichi 3 (USA)"

# ELF load layout, confirmed against a live save state.
TEXT_BASE = 0x00100000
TEXT_END = 0x002C33C0
DATA_BASE = 0x002C3400
BSS_END = 0x00334BF8

# $gp is set once at boot, so gp-relative loads resolve to fixed addresses.
GP_BASE = 0x00304270

# Verified zero-filled in a mid-battle save state.
SAFE_ZONE = 0x000F0000
SAFE_ZONE_SIZE = 0x8000

IDENTITY = GameIdentity(
    serial=SERIAL,
    crc=CRC,
    elf_name=ELF_NAME,
    game=GAME,
    text_base=TEXT_BASE,
    text_end=TEXT_END,
    data_base=DATA_BASE,
    bss_end=BSS_END,
    gp_base=GP_BASE,
    safe_zone=SAFE_ZONE,
    safe_zone_size=SAFE_ZONE_SIZE,
)

# Groups in the working pnach that must NEVER be enabled in a real install: two
# withdrawn blast groups (gating deleted the beam), one that breaks ground
# movement, and `animation rate`, an alternative to `animation clock` that gives
# QUARTER speed animation if both are on. Handing the working pnach to deploy.py
# enables every group in it.
NEVER_SHIP = [
    "60FPS - animation rate",
    "60FPS - EXPERIMENT halve root motion",
    "60FPS - blast effect rate",
    "60FPS - blast sequence rate",
]

# A display-aspect hack is a preference, not a fix, and conflicts with PCSX2's own
# [Widescreen 16:9] (same three addresses). Installed, listed, off by default.
OPTIONAL = [
    "Widescreen 19.5:9 - S24 Ultra",
    "Widescreen 16:10",
    "Widescreen 21:9",
]

# Groups that are alternatives of one another and write the same addresses (only
# one display aspect can be on); without this, validate() reports every pair as an
# overwrite. Overlap with anything outside a set is still a problem.
EXCLUSIVE = [
    [
        "Widescreen 19.5:9 - S24 Ultra",
        "Widescreen 16:10",
        "Widescreen 21:9",
    ],
]

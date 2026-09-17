"""Everything true of Dragon Ball Z: Budokai Tenkaichi 3 and nothing else.

The generic ps2ee library (in the sibling pcsxroo checkout) knows how to
discover emulators and walk EE memory; this file is the game knowledge the
generic side must never carry: identity, ELF layout, the safe zone, and the
patch policy.
"""

from ps2ee.config import GameIdentity

SERIAL = "SLUS-21678"
CRC = "428113C2"
ELF_NAME = "SLUS_216.78"
GAME = "Dragon Ball Z: Budokai Tenkaichi 3 (USA)"

# ELF load layout, confirmed against a live save state (see docs/findings/).
TEXT_BASE = 0x00100000
TEXT_END = 0x002C33C0
DATA_BASE = 0x002C3400
BSS_END = 0x00334BF8

# $gp is set once at boot and never changes, so gp-relative loads resolve to
# fixed addresses. Read out of a live save state.
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

# Groups that exist in the working pnach and must NEVER be enabled in a real
# install. Two of them are withdrawn because gating deleted the beam, one is
# the state 157 trap, one deliberately breaks ground movement, and `animation
# rate` is a superseded alternative to `animation clock` - both on together
# give QUARTER speed animation. Handing the working pnach to deploy.py enables
# every group in it, which is exactly how an install ends up broken beyond
# belief.
NEVER_SHIP = [
    "60FPS - animation rate",
    "60FPS - EXPERIMENT halve root motion",
    "60FPS - blast effect rate",
    "60FPS - blast sequence rate",
    "60FPS - state phase timers",
]

# A display-aspect hack is a preference, not a fix, and this one additionally
# conflicts with PCSX2's own [Widescreen 16:9] - both write the same three
# addresses every frame. Installed, listed, off until the user says otherwise.
OPTIONAL = [
    "Widescreen 19.5:9 - S24 Ultra",
    "Widescreen 16:10",
    "Widescreen 21:9",
]

# Groups that are alternatives of one another, and so are meant to write the
# same addresses. Only one display aspect can be on at a time, and all three
# write the same three words - without this, validate() reports every pair as
# an overwrite. Overlap with anything outside a set is still a problem.
EXCLUSIVE = [
    [
        "Widescreen 19.5:9 - S24 Ultra",
        "Widescreen 16:10",
        "Widescreen 21:9",
    ],
]

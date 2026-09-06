"""Turn pnach groups on and off in a running game, with no reboot.

PCSXROO's ``patch.reload`` re-reads the pnach files but takes the *enabled*
list from the settings it loaded at boot, so editing the ini achieves nothing
mid-session. Renaming a group in the pnach does: a group whose header no longer
matches an enabled name is simply not applied.

Removing a patch does not undo it. ``patch=1`` lines are rewritten every frame
while active, and when the group stops being active PCSX2 just stops writing -
the last value it wrote stays in RAM. So disabling also has to put the original
words back, taken from the boot ELF. Addresses outside any ELF segment are the
trampoline scratch zone, whose original content is zero.

    python tools/patchctl.py --status
    python tools/patchctl.py --off                 # stock 60fps, no compensation
    python tools/patchctl.py --on shipped          # the five shipped groups
    python tools/patchctl.py --on air              # shipped plus the airborne work
    python tools/patchctl.py --on "60FPS - battle"
"""

from __future__ import annotations

import argparse
from pathlib import Path

import _bootstrap  # noqa: F401

from ps2ee import config
from ps2ee.eemem import ElfImage
from ps2ee.pnach import Pnach
from ps2ee.roo import Roo

# The five groups that were already proven and are in the user's own PCSX2.
SHIPPED = [
    "60FPS - battle",
    "60FPS - animation clock",
    "60FPS - input repeat timing",
    "60FPS - input timing",
    "60FPS - aura update rate",
]

# The airborne work, under test.
AIRBORNE = [
    "60FPS - airborne motion",
    "60FPS - airborne vertical",
    "60FPS - airborne residual",
    "60FPS - gravity",
]

# Reinstated 2026-09-05. A 2026-08-24 test froze these phases and reported no
# visible change, so the group was written off as compensating something
# invisible - but that test was run on the ground. In an airborne hover these
# are the only cleanly uncompensated per-tick quantities left in the fighter's
# model, stepping 0.10/0.23/0.27 per tick at both rates, and the group halves
# exactly those.
EFFECTS = ["60FPS - effect rotation"]

# The tween system, found 2026-09-05. FUN_00267AC8 converts a duration in
# seconds into frames at a hard-coded 30.0, and FUN_00267B00 steps it once per
# tick, so at 60fps every ease, pulse and blend in the game finishes in half its
# intended real time. One word - 30.0 becomes 60.0 - doubles the frame count and
# halves the step together.
TWEENS = ["60FPS - tween duration"]

# The particle system, found 2026-09-05. FUN_00167258 ages aura and trail
# particles with half a dozen per-tick channels and no timestep; gating its
# caller's update on frame parity - reusing the skip the game already has for
# its own hidden flag - fixes all of them at once and still draws every frame.
PARTICLES = ["60FPS - particle update rate"]

# The hovering idle bob, found 2026-09-05. A sine whose phase advances pi/30 a
# tick - one cycle per 60 ticks - added to the fighter's anchor, entirely
# separate from the animation clock. Only one instruction in the game reads the
# constant, so halving it touches nothing else.
HOVER = ["60FPS - hover bob"]

# The blast hit cadence, found 2026-09-06. A hitbox's tick counter H[0x0A] is
# advanced once a tick and a hit lands when it reaches an interval authored in
# ticks, so multi-hit attacks land twice as fast at 60fps and burn through their
# hit budget - and so their duration - in half the real time. Gating the single
# call that advances it on frame parity fixes cadence and duration together.
BLAST = ["60FPS - blast hit cadence"]

# The blast's visible effects, found 2026-09-06. A ki blast is drawn by two
# effect-node classes whose updates each carry half a dozen coupled per-tick
# channels, so no single constant fixes them; gating both updates on frame
# parity - reusing the skip each one already has, so the draw still runs - is
# the same fix the ki aura and the particle system use.
BLASTFX = ["60FPS - blast effect rate"]

# The blast sequence rate, found 2026-09-06 - the one the player actually sees.
# The scene graph dispatches every node's vtable[0] through one indirect call;
# gating that call for a single class (vtable 002C3940, FUN_001587B8, an action
# controller with a per-tick counter) paces ultimate sequences by real time.
SEQ = ["60FPS - blast sequence rate"]

# The blast effect duration, found 2026-09-06. The two effect classes that draw a
# ki blast step several coupled per-tick channels by 1.0 AND rebuild the beam
# geometry every frame - so they cannot be gated, only slowed. Halving all
# nineteen steps together moves the channels in step; halving any one does
# nothing, because they are compared against each other.
BLASTDUR = ["60FPS - blast effect duration"]

# Names for groups that do not exist yet. The ini's enabled list is only read at
# boot, so a name that is not in it cannot be tested without restarting the
# emulator; carrying spares means the next experiment does not cost a restart.
SPARES = ["60FPS - spare 1", "60FPS - spare 2", "60FPS - spare 3"]

# What the ini enables. A group must carry one of these names to apply at all,
# and this list can only be changed by restarting the emulator - so it holds
# the names of groups that do not exist yet, to save a restart later.
ENABLED_IN_INI = (SHIPPED + AIRBORNE + EFFECTS + TWEENS + PARTICLES
                  + HOVER + BLAST + BLASTFX + SEQ
                  + BLASTDUR + SPARES)

PRESETS = {
    "off": [],
    "shipped": SHIPPED,
    "air": SHIPPED + AIRBORNE + EFFECTS,
    "tween": SHIPPED + AIRBORNE + EFFECTS + TWEENS,
    "noblast": SHIPPED + AIRBORNE + EFFECTS + TWEENS + PARTICLES + HOVER,
    "nofx": (SHIPPED + AIRBORNE + EFFECTS + TWEENS + PARTICLES + HOVER
             + BLAST),
    "noseq": (SHIPPED + AIRBORNE + EFFECTS + TWEENS + PARTICLES + HOVER
              + BLAST + BLASTFX),
    # BLASTFX and SEQ are WITHDRAWN - both break blast rendering. Gating an
    # effect update skips the geometry rebuild it does every frame, so the beam
    # has nothing to draw; gating the sequence controller makes it miss the edge
    # that spawns the beam. Kept in the pnach as a record, never enabled.
    "full": (SHIPPED + AIRBORNE + EFFECTS + TWEENS + PARTICLES + HOVER
             + BLAST + BLASTDUR),
}

DISABLED_SUFFIX = " [off]"


def _base_name(name: str) -> str:
    return name[: -len(DISABLED_SUFFIX)] if name.endswith(DISABLED_SUFFIX) else name


def read_pnach() -> tuple[Path, Pnach]:
    path = config.roo_cheat_file()
    return path, Pnach.load(path)


def status() -> None:
    path, pnach = read_pnach()
    print(path)
    for group in pnach.groups:
        name = _base_name(group.name)
        on = group.name == name and name in ENABLED_IN_INI
        print(f"  [{'ON ' if on else 'off'}] {name}  ({len(group.lines)} lines)")


def original_word(elf: ElfImage, addr: int) -> int:
    """What was at this address before any patch touched it."""
    return elf.u32(addr) if elf.segment_for(addr) else 0


def apply(roo: Roo, wanted: list[str], quiet: bool = False) -> None:
    """Make exactly ``wanted`` active, and restore what the rest overwrote."""
    path, pnach = read_pnach()
    elf = ElfImage.load(config.elf_path())

    restore: dict[int, int] = {}
    for group in pnach.groups:
        name = _base_name(group.name)
        group.name = name if name in wanted else name + DISABLED_SUFFIX
        if name not in wanted:
            for line in group.lines:
                if not line.is_condition and line.width == 4:
                    restore[line.target] = original_word(elf, line.target)
    path.write_text(pnach.render(), encoding="utf-8")

    # Order matters. Reload first, so the cheat engine stops rewriting these
    # words, and only then put the originals back - otherwise the next frame
    # simply re-applies the patch over the restore.
    roo.patch_reload()

    failed = []
    for addr, word in sorted(restore.items()):
        if not roo.write(addr, word):
            failed.append(addr)
    if failed:
        raise RuntimeError(
            "these words did not stay written, so something is still patching "
            "them: " + ", ".join(f"{a:08X}" for a in failed))
    if not quiet:
        print(f"active: {', '.join(wanted) if wanted else '(none)'}"
              f"   restored {len(restore)} words")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--off", action="store_true")
    parser.add_argument("--on", nargs="*", default=None,
                        help='group names, or a preset: ' + ", ".join(PRESETS))
    args = parser.parse_args()

    if args.status or (not args.off and args.on is None):
        status()
        return 0

    wanted: list[str] = []
    if args.on:
        for name in args.on:
            wanted += PRESETS.get(name, [name])
    apply(Roo().connect(), wanted)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

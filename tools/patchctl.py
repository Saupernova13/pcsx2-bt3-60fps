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

from game import config
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

# The scripted-sequence clock, found 2026-09-07. A sequence step that is waiting
# counts an integer down once a tick, and those waits are authored in 30Hz
# frames, so every staged beat - camera cuts, mouth lines, fades, the instant an
# ultimate releases its beam - lands in half its real time. Counting down on
# even ticks only fixes the whole class at once without skipping any work.
SEQWAIT = ["60FPS - sequence wait"]

# The fighter state machine's phase timers, found 2026-09-07. Every attack,
# charge, block and recovery is a state whose handler counts ticks in the scratch
# block and compares that count against a number authored in 30Hz frames, so at
# 60fps each one expires in half its real time. All 28 sites are gated to even
# ticks; found by tools/phasetimer.py, generated by tools/mkgate.py.
PHASE = ["60FPS - state phase timers"]

# The knockback flight and the Circle pursuit stomp, found 2026-09-07. A heavy
# smash launches the victim on a phase timer authored in 30Hz frames, and the
# Circle pursuit that follows is a chain of four more frame counts plus an
# intercept that leads the target by a fixed number of TICKS against a velocity
# that is (correctly) per-tick. At 60fps every one of them lands in half its
# real time, so Goku rises less far, arrives behind the victim instead of ahead,
# and his dive stalls before it can close. Measured over a nine-point sweep of
# the press delay the stomp missed 9 times out of 9; with these it hits 9 out of
# 9, within 1-3 vsyncs of the 30fps arm at every delay.
PURSUIT = ["60FPS - knockback flight", "60FPS - pursuit timing"]

# The camera, found 2026-09-08. FUN_001C69C8 updates every camera in the game by
# lerping its euler angles toward a target built for this tick, and both halves
# are per-tick: the blend rate $f20 (0.20 a tick) is applied twice as often, and
# a scripted camera move counts fighter+0x558 down once a tick from a length
# authored in 30Hz frames. Halving the blend alone leaves 12.84 degrees of mean
# orientation error against the 30fps camera, gating the move alone 14.01,
# against 22.96 unpatched - together, 1.52. One group, because neither half is
# correct on its own.
CAMERA = ["60FPS - camera pacing"]

# Names for groups that do not exist yet. The ini's enabled list is only read at
# boot, so a name that is not in it cannot be tested without restarting the
# emulator; carrying spares means the next experiment does not cost a restart.
SPARES = ["60FPS - spare 1", "60FPS - spare 2", "60FPS - spare 3"]

# What the ini enables. A group must carry one of these names to apply at all,
# and this list can only be changed by restarting the emulator - so it holds
# the names of groups that do not exist yet, to save a restart later.
# The cut-in keyframe clock, found 2026-09-08. A second clip player, separate
# from the model+0xB40 controller that [60FPS - animation clock] already paces.
# Its track objects step a float clock by the track's rate at +0x2C once per
# tick, and that rate is 2.0, so at 60fps a track burns its keyframe array in
# half the real time and holds the last key - a mouth that stops mid-sentence.
MOUTH = ["60FPS - mouth clock"]

# Projectile travel, found 2026-09-09. The effect-node position integrator steps
# pos += vel * step once a tick with no delta-time term, so every ki blast and
# beam covers twice the ground per real second at 60fps. The first defect fixed
# here that changes how the game PLAYS - it halves the time to dodge.
PROJECTILE = ["60FPS - projectile travel"]
OBJFLIGHT = ["60FPS - blast object travel"]
BEAMFLIGHT = ["60FPS - beam object travel"]

# The fullscreen fade node, found 2026-09-09. FUN_00172810 fades a colour in,
# holds it, and fades it out, counting all three phases one frame per tick. At
# 60fps every fade in the game runs in half its real time - which is why the
# Galick Cannon's white flash lifted before the transition it exists to cover.
SCREENFADE = ["60FPS - screen fade"]

# Paralysis, found 2026-09-17. The victim's paralysis is fighter+0xFE0 in
# ticks, decremented at one site in the fighter update however it was armed.
# Demon Eye's published 4 seconds read 4.00s at 30fps and 2.00s at 60fps; this
# decrements on even ticks only and leaves the per-press mash subtraction alone.
PARALYSIS = ["60FPS - paralysis"]

# The rush struggle, found 2026-09-10. Two rush attacks collide and both players
# rotate their sticks; the game counts hits into fighter+0xE50 and picks whoever
# has more. The CPU's stick is synthetic and steps once per tick, so at 60fps the
# AI rotates twice as fast in real time while a human's hands do not - measured
# at a true 5 rotations a second, the winner flips. This gates only the AI side.
STRUGGLE = ["60FPS - rush struggle"]

# The beam clash, found 2026-09-12. Two beams collide, both fighters enter state
# 304 and rotate; rotations count into fighter+0xE4C and an event manager,
# FUN_001D8E50, runs the contest on a tick clock - introductions, a per-tick tug
# toward whoever leads, then the result. At 60fps that whole clash plays in half
# its real time while a human's hands do not speed up, and the CPU's synthetic
# stick does. This puts the manager's phases back on real time, keeps the clash
# point where 30fps puts it, and gates only the AI's rotation.
BEAMCLASH = ["60FPS - beam clash"]

ENABLED_IN_INI = (SHIPPED + AIRBORNE + EFFECTS + TWEENS + PARTICLES
                  + HOVER + BLAST + BLASTFX + SEQ
                  + BLASTDUR + SEQWAIT + PHASE + PURSUIT + CAMERA + MOUTH
                  + PROJECTILE + OBJFLIGHT + BEAMFLIGHT + SCREENFADE
                  + STRUGGLE + BEAMCLASH + PARALYSIS + SPARES)

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
    # BLASTFX and SEQ are both WITHDRAWN, for the same underlying reason: an
    # effect that is gated is an effect that does not get built. BLASTFX skips
    # the geometry rebuild; SEQ skips the controller step that SPAWNS the
    # effects, so a charged blast renders nothing at all and deals no damage.
    # SEQ looked innocent only because it was tested with an uncharged tap,
    # which never exercises the charge path. Both stay in the pnach as a record.
    "withseq": (SHIPPED + AIRBORNE + EFFECTS + TWEENS + PARTICLES + HOVER
                + BLAST + BLASTDUR + SEQ),
    "noseqwait": (SHIPPED + AIRBORNE + EFFECTS + TWEENS + PARTICLES + HOVER
                  + BLAST + BLASTDUR + PHASE),
    "nophase": (SHIPPED + AIRBORNE + EFFECTS + TWEENS + PARTICLES + HOVER
                + BLAST + BLASTDUR + SEQWAIT),
    # PHASE is WITHDRAWN 2026-09-07. It gates 22 counters inside the fighter
    # state machine - the exact mechanism behind a fighter that fails to leave a
    # state - and every one of them was scored against two GROUNDED oracles, a
    # held charge and a mashed rush. No airborne state was ever tested. The user
    # hit a repeatable trap in state 157 (FUN_001E6DC8), an airborne state, with
    # no pending transition. Not proven to be this group; withdrawn because it
    # is the only shipped group that touches state transitions and the only one
    # whose validation has a hole exactly where the symptom is.
    "withphase": (SHIPPED + AIRBORNE + EFFECTS + TWEENS + PARTICLES + HOVER
                  + BLAST + BLASTDUR + SEQWAIT + PHASE),
    # SEQWAIT was withdrawn briefly on 2026-09-07 to isolate the state 157 trap,
    # then RESTORED once the user confirmed the trap did not follow it out: the
    # 15-group set still trapped nothing but the ultimate ended early again.
    # It is confirmed-good in play and does not touch state transitions.
    "noseqwait2": (SHIPPED + AIRBORNE + EFFECTS + TWEENS + PARTICLES + HOVER
                   + BLAST + BLASTDUR),
    # The 16-group set that was confirmed good in play, kept so the pursuit
    # work has a named baseline to be diffed against without editing a preset.
    "nopursuit": (SHIPPED + AIRBORNE + EFFECTS + TWEENS + PARTICLES + HOVER
                  + BLAST + BLASTDUR + SEQWAIT),
    # The 18-group set v13 shipped, kept so the camera work has a named
    # baseline to be diffed against without editing a preset.
    "nocamera": (SHIPPED + AIRBORNE + EFFECTS + TWEENS + PARTICLES + HOVER
                 + BLAST + BLASTDUR + SEQWAIT + PURSUIT),
    "nomouth": (SHIPPED + AIRBORNE + EFFECTS + TWEENS + PARTICLES + HOVER
                + BLAST + BLASTDUR + SEQWAIT + PURSUIT + CAMERA),
    "noproj": (SHIPPED + AIRBORNE + EFFECTS + TWEENS + PARTICLES + HOVER
               + BLAST + BLASTDUR + SEQWAIT + PURSUIT + CAMERA + MOUTH),
    "full": (SHIPPED + AIRBORNE + EFFECTS + TWEENS + PARTICLES + HOVER
             + BLAST + BLASTDUR + SEQWAIT + PURSUIT + CAMERA + MOUTH
             + PROJECTILE + OBJFLIGHT + BEAMFLIGHT + SCREENFADE + STRUGGLE
             + BEAMCLASH + PARALYSIS),
    # "full" without paralysis, so that group has a named A/B baseline.
    "noparalysis": (SHIPPED + AIRBORNE + EFFECTS + TWEENS + PARTICLES + HOVER
                    + BLAST + BLASTDUR + SEQWAIT + PURSUIT + CAMERA + MOUTH
                    + PROJECTILE + OBJFLIGHT + BEAMFLIGHT + SCREENFADE
                    + STRUGGLE + BEAMCLASH),
    # The 21-group set without the fade, so the fade has a named A/B baseline.
    "nofade": (SHIPPED + AIRBORNE + EFFECTS + TWEENS + PARTICLES + HOVER
               + BLAST + BLASTDUR + SEQWAIT + PURSUIT + CAMERA + MOUTH
               + PROJECTILE + OBJFLIGHT + BEAMFLIGHT),
    "nobeam": (SHIPPED + AIRBORNE + EFFECTS + TWEENS + PARTICLES + HOVER
               + BLAST + BLASTDUR + SEQWAIT + PURSUIT + CAMERA + MOUTH
               + PROJECTILE + OBJFLIGHT),
    "noobj": (SHIPPED + AIRBORNE + EFFECTS + TWEENS + PARTICLES + HOVER
              + BLAST + BLASTDUR + SEQWAIT + PURSUIT + CAMERA + MOUTH
              + PROJECTILE),
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
    warn_unenabled(pnach)


def warn_unenabled(pnach=None) -> list[str]:
    """Groups the emulator will ignore however correct the pnach is.

    PCSXROO reads its [Cheats] Enable list from its OWN per-game ini - not the
    installed PCSX2's, which is what config.game_ini() and deploy.py write - and
    it reads it at BOOT. A group whose name is missing there applies nothing and
    says nothing: patchctl reports it ON, the words never appear in RAM, and the
    measurement quietly scores the unpatched game. That cost an hour on
    2026-09-08. This is the check that would have caught it.
    """
    try:
        enabled = config.roo_enabled_cheats()
    except FileNotFoundError:
        return []
    if not enabled:
        return []
    if pnach is None:
        _, pnach = read_pnach()
    present = {_base_name(g.name) for g in pnach.groups}
    missing = [n for n in ENABLED_IN_INI if n in present and n not in enabled]
    if missing:
        print("")
        print(f"  !! not enabled in {config.roo_game_ini()}")
        for name in missing:
            print(f"     {name}")
        print("     Add an 'Enable = <name>' line there and RESTART the emulator;")
        print("     until then these groups apply nothing at all.")
    return missing


def original_word(elf: ElfImage, addr: int) -> int:
    """What was at this address before any patch touched it."""
    return elf.u32(addr) if elf.segment_for(addr) else 0


def apply(roo: Roo, wanted: list[str], quiet: bool = False) -> None:
    """Make exactly ``wanted`` active, and restore what the rest overwrote.

    **An enabled group is not in RAM when this returns.** Disabling writes the
    original words here, but the cheat engine writes an *enabled* group's words
    at a frame boundary, so the patch only lands once the VM runs a frame.

    Advance a few frames before reading a patched address or arming a
    breakpoint on patched code. Skipping that does not raise: every arm quietly
    measures the unpatched game and agrees with every other arm, which reads
    exactly like a fix that does nothing. Reading one patched address back and
    checking it changed is the cheap guard.
    """
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

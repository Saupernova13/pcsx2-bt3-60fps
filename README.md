# pcsx2-bt3-60fps

A 60fps patch for **Dragon Ball Z: Budokai Tenkaichi 3** (SLUS-21678, CRC
428113C2) on PCSX2, and the tooling that built it.

The patch installs and works on its own. To run the tools and keep developing
it, see [Getting started](#getting-started).

## Install

**Download `428113C2.pnach` from the
[latest release](https://github.com/Saupernova13/pcsx2-bt3-60fps/releases/latest).**
Drop it in PCSX2's `cheats/`, set `EnableCheats = true`, and enable every group
listed in the file's own header. The same file is
[`patch/428113C2.pnach`](patch/428113C2.pnach) here, and from a clone the
tooling can install it for you:

    python tools/deploy.py patch/428113C2.pnach

The filename matters: PCSX2 finds a pnach by the game's CRC, so the file has to
be called `428113C2.pnach`. PCSX2 reads cheats at boot - quit and relaunch, a
reset or save-state load is not enough.

The file's header also lists what is still not fixed. Per-build confidence, and
what has been confirmed in play rather than only measured, is in
**[`docs/status.md`](docs/status.md)**.

**Every version of the patch, v01 through v23, with what each one changed and what
was discovered on the way, is in [`docs/versions/`](docs/versions/README.md).**

## What the patch covers

26 groups, each compensating one system the 60 Hz loop drives twice as often.
Movement, gravity and knockback; the animation clock; menu and combat input
windows; the ki aura, particles, effect rotation and the hovering idle; the
tween system; blast hit cadence and blast effect duration; the integer clock
behind scripted-sequence waits; the launch-and-pursuit chain - the flight a
Full Power Smash puts someone into, and the five frame counts behind the Circle
stomp that follows it; the camera, whose blend rate and scripted move lengths
are both counted in ticks; the three movers that carry projectiles across the
ground - ki blasts, spawned objects like Frieza's I Might Die This Time rocks, and travelling beams
like Buu's Super Kamehameha and his breath; and the fullscreen fade service, which
took its phase durations in seconds and converted them at 30 Hz, so every fade
in the game ran in half its real time. And the two contests decided by how fast
a player turns the sticks - the Rush Struggle and the Beam Struggle - both of
which were counted in ticks throughout, so at 60fps they ran in half their real
time while the CPU, whose stick is synthetic and steps once per tick, rotated
twice as fast in real time as it should. Both gate only the AI side; a human's
input is untouched.

Every group is verified against the unpatched 30fps game as its own oracle:
same save state, same input, same number of vsyncs. The ones a player can see
are confirmed in play with the game running free, not by frame stepping.

Known not fixed, stated in the shipped header: an ultimate's beam lands its
first hit about half a second early; the summon animation before Frieza's I Might Die This Time rocks
- most of that move - still runs about five frames fast, as does the wind-up on
Buu's Super Kamehameha; some pre-fight intro animations are paced wrong against
the camera; the camera on a body-erasing death has never been re-checked since
the camera work landed; and in a Beam Struggle the CPU ends a little weaker than
it is at 30fps, so a near-tie can fall the player's way.

## Why the obvious patch does not work

The 60fps code in circulation forces one branch:

    patch=1,EE,20264DBC,extended,10000008    // skip the vblank wait loop
    patch=1,EE,201DCB40,extended,3C013F80    // halve one step multiplier (2.0 -> 1.0)

That removes the frame limiter for *every* game loop at once while compensating
exactly one timestep constant. Everything else the loop drives - physics, ki
and gauge fill, blast and combo timing, stun, AI cadence - still advances a
full 30fps step per iteration and therefore runs at double speed.

BT3 turns out to have no master framerate variable. Its per-frame routine takes
a vblank stride as an argument, and all eight call sites hardcode it (`addiu
$a0, $zero, 2` for 30fps, `1` for 60fps). So the right lever is a one-word
change at the specific loop you want to convert, not a global branch kill. The
full table is in [`docs/findings/`](docs/findings/README.md).

## Repository layout

    patch/            the patch to install: 428113C2.pnach
    wip/              the working pnach and isolation experiments - NOT for install
    tools/            the command line tools, with the game knowledge in tools/game/
    docs/             method, tool index, release history, and the findings log
    ghidra/scripts/   the headless decompiler script

Every released version is a git tag (`v02-...` through `v23-...`) - the tag
holds the patch as it shipped - and pushing a tag publishes it as a GitHub
Release with the patch attached. See [`docs/releases.md`](docs/releases.md).

`work/` (extracted ELF, RAM dumps, caches) is gitignored.

## Getting started

Everything here is what it takes to pick the patch up and keep developing it.
You need your own copy of the game and a BIOS dumped from your own console;
neither is included.

**1. Clone both repos side by side.** The tools' generic half - the `ps2ee`
library and 13 EE analysis tools - lives in
[PCSXROO](https://github.com/Saupernova13/pcsxroo), a PCSX2 fork with a debug
server (memory, breakpoints, watchpoints, save states, pad injection,
screenshots) that most of the tools here drive.

    git clone https://github.com/Saupernova13/pcsx2-bt3-60fps.git
    git clone https://github.com/Saupernova13/pcsxroo.git

The tools find PCSXROO as that sibling folder. To keep it elsewhere, set
`PCSXROO_REPO` to its path, in the environment or in this repo's `local.json`.

**2. Build PCSXROO** by following its
[`pcsxroo/README.md`](https://github.com/Saupernova13/pcsxroo/blob/master/pcsxroo/README.md):
`pcsxroo\tools\build.cmd`, then `pcsxroo\tools\seed-portable.ps1` to give it
your BIOS and controls, then `pcsxroo\tools\smoke-test.ps1 -Bios`. It runs in
portable mode, so its `cheats/`, `sstates/`, `snaps/` and `gamesettings/` sit
in `pcsxroo\bin\`, apart from the PCSX2 you play on.

**3. Install Python 3.11+ and the packages:**

    pip install capstone keystone-engine zstandard numpy

**4. Tell the tools where things are,** if they cannot find them. Paths are
discovered automatically; anything can be overridden in a `local.json` in this
repo's root (gitignored):

    {
      "PCSX2_DIR":    "C:/path/to/PCSX2",
      "PCSXROO_DIR":  "C:/path/to/pcsxroo/bin",
      "PCSXROO_REPO": "C:/path/to/pcsxroo",
      "GAME_IMAGE":   "D:/roms/bt3.cso",
      "GHIDRA_HOME":  "C:/Utils/ghidra"
    }

`PCSX2_DIR` is the PCSX2 you play on, which `deploy.py` installs into.
`GAME_IMAGE` falls back to `ROM_DIRS`, then to the folders in PCSX2's own game
list.

**5. Extract the ELF** from your disc image into `work/`:

    python tools/extract-elf.py

The generic tools in PCSXROO read their game identity and the ELF on their
own side. Point them at this repo's copy:

    copy ..\pcsxroo\pcsxroo\local.json.example ..\pcsxroo\pcsxroo\local.json
    set SCRATCH_DIR=%CD%\work
    python ..\pcsxroo\pcsxroo\tools\disas.py --source elf --func 1D9900

**6. Make the reference save states.** None ship, and none can: a save state is
a full snapshot of the console's memory - the game's code and data and the
BIOS - so it would redistribute both, and it is tied to the emulator build that
wrote it. Build your own in PCSXROO:

    ..\pcsxroo\bin\pcsxroo.exe launch "D:\roms\bt3.cso"

Start a one-on-one battle and, with both fighters standing on the ground, save
**slot 1** - the hand-made ground state every A/B starts from:

    ..\pcsxroo\bin\pcsxroo.exe savestate --slot 1 --wait-flush

`mkstate.py` cuts the rest from it:

    python tools/mkstate.py air --slot 2
    python tools/mkstate.py airidle --slot 3
    python tools/mkstate.py --list

**7. Run the A/B loop.** `patchctl.py` switches pnach groups in the running game,
so the unpatched 30fps behaviour and the patched 60fps behaviour can be compared
from the same state; the rules are under [Testing loop](#testing-loop). The
acceptance tests are `speedtest.py`, `stomptest.py`, `blasttest.py` and
`realclock.py`.

**[`docs/rig.md`](docs/rig.md) is the runbook for this step** - the exact order
an A/B has to run in, how to reach any character and stage by driving the game's
menus, and the handful of traps that silently produce a wrong answer instead of
an error. Read it before the first measurement, not after.

**8. Read what is already known** before changing anything:
[`docs/rig.md`](docs/rig.md) for how to drive the emulator,
[`docs/status.md`](docs/status.md) for the state of every group,
[`docs/versions/`](docs/versions/README.md) for what each of v01 to v23 changed
and discovered, [`docs/findings/`](docs/findings/README.md) for the full log, and
[`docs/tools.md`](docs/tools.md) for every tool.

Decompilation is optional and needs Ghidra with the Emotion Engine extension.
Create the project once (several minutes):

    C:/Utils/ghidra/support/analyzeHeadless.bat work/ghidra BT3 \
      -import work/SLUS_216.78 -processor "r5900:LE:32:default" -loader ElfLoader

The PINE tools drive stock PCSX2 instead; enable PINE there with
`python ..\pcsxroo\pcsxroo\tools\setup-pcsx2.py --enable-pine`.

## Tools

All 48 tools are indexed in **[docs/tools.md](docs/tools.md)** with what each
needs (PCSXROO, PINE, or offline). Two homes:

- **`tools/` here** - the 35 that know this game: they read its structs, drive
  its pnach groups, or walk its save-state conventions. `deploy.py`,
  `patchctl.py` and `export.py` are the ones you will use the most.
- **PCSXROO's `pcsxroo/ps2ee/` and `pcsxroo/tools/`** - the generic ps2ee
  library and 13 EE analysis tools that would work on any game: disassembly,
  xrefs, RAM diffing, tick counting.

## How a patch gets written

Patches are authored as **MIPS assembly with hook declarations**, never as
hand-encoded hex. `ps2ee.asm` assembles with keystone, places code in the safe
zone at `0x000F0000`, and computes the hook jumps:

```python
from ps2ee import PatchBuilder, Trampoline

b = PatchBuilder()
b.trampoline(Trampoline(
    hook_at=0x001DCB40,
    comment="halve the 2.0 step multiplier",
    body="""
        lui   $at, 0x3F00      # 0.5f
        mtc1  $at, $f12
        ld    $s0, 0($sp)
        j     0x001DCB48
        nop
    """,
))
print("\n".join(b.to_pnach()))
```

Delay slots are yours to fill - the assembler runs with `.set noreorder` so
nothing is reordered and no nop is inserted behind your back.

`Pnach.validate()` runs before every deploy and rejects writes outside `.text`,
`.data` and the safe zone, unaligned word writes, dangling E-code conditions,
and two groups writing the same address.

## Testing loop

Every measurement is an A/B against the unpatched game from the same save
state, and `patchctl` switches between the two without a restart. It renames
groups in the pnach and puts back what a disabled one overwrote, because PCSX2
stops rewriting a `patch=1` line when a group goes away but does not undo it.

    python tools/patchctl.py --status
    python tools/patchctl.py --off                # stock 60fps, nothing compensated
    python tools/patchctl.py --on full            # everything that ships

Four rules, each learned by getting it wrong:

- **Load the state, then apply the preset, then run.** Never load again after
  applying: the save states were captured while patched, so a second load puts
  the patched words straight back and the "unpatched" arm is not unpatched.
  Check it ticks 30 times a second.
- **A screenshot needs a running VM - but a paused one is only queued, not
  lost.** `screenshot()` while paused writes no file; `frame_advance(1)` then
  flushes it. So a `screenshot, frame_advance(1)` loop costs exactly one vsync
  a sample and gives a film as deterministic as memory, aligned frame for frame
  between the arms.
- **A new group name needs a restart, and the ini is PCSXROO's own.** The
  enabled list is read only at boot, and it lives at
  `<pcsxroo>/bin/gamesettings/SLUS-21678_428113C2.ini` - the emulator's data
  root, NOT the file `deploy.py` writes, which belongs to the installed PCSX2.
  A group missing from that list applies nothing and reports nothing.
- **Shrinking a live group needs a restart too**, because the hooks it drops
  stay patched in RAM with nothing left to restore them.

When a change is ready to hand over:

    python tools/export.py --release vNN-name
    git tag -a vNN-name -m "vNN-name: <one line from its note>"
    git push origin vNN-name        # once the commit is on main: publishes the release

## Notes

- Save states from PCSX2 2.1.178+ use zstd. `ps2ee.savestate` reads them
  directly; Ghidra's own save state importer cannot, so use ours.
- The ELF loads at `0x00100000` with no overlays and no self-modifying code,
  verified against live RAM. Ghidra addresses are pnach addresses, unchanged.
- Capstone has no R5900 mode, so `ps2ee.disasm` will not decode MMI or VU0
  macro-mode instructions. Use `tools/decomp.py` inside VU-heavy code.

## Credits

Workflow, and the Analyst/Implementer rule sets: Red-tv141 - see the
[guide thread](https://forums.pcsx2.net/Thread-GUIDE-AI-Assisted-60fps-Patch-Development-for-PS2-Games-%E2%80%94-Full-Workflow)
(the guide itself is not hosted here).
Framerate-address techniques in Section 1 of the guide: asasega.
Ghidra Emotion Engine support: chaoticgd and beardypig.

## Licence

Code (`tools/`, `ghidra/scripts/`): **MIT**, see [`LICENSE`](LICENSE).
Docs, findings and the patch itself: **CC BY 4.0**, see [`LICENSE-docs`](LICENSE-docs).

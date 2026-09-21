# Getting started

Everything it takes to pick the patch up and keep developing it. You need your
own copy of the game and a BIOS dumped from your own console; neither is
included.

To only *install* the patch, none of this is needed - see the
[README](../README.md).

## 1. Clone both repos side by side

The tools' generic half - the `ps2ee` library and the EE analysis tools - lives
in [PCSXROO](https://github.com/Saupernova13/pcsxroo), a PCSX2 fork with a debug
server (memory, breakpoints, watchpoints, save states, pad injection,
screenshots) that most of the tools here drive.

    git clone https://github.com/Saupernova13/pcsx2-bt3-60fps.git
    git clone https://github.com/Saupernova13/pcsxroo.git

The tools find PCSXROO as that sibling folder. To keep it elsewhere, set
`PCSXROO_REPO` to its path, in the environment or in this repo's `local.json`.

## 2. Build PCSXROO

Follow its
[`pcsxroo/README.md`](https://github.com/Saupernova13/pcsxroo/blob/master/pcsxroo/README.md):
`pcsxroo\tools\build.cmd`, then `pcsxroo\tools\seed-portable.ps1` to give it your
BIOS and controls, then `pcsxroo\tools\smoke-test.ps1 -Bios`. It runs in portable
mode, so its `cheats/`, `sstates/`, `snaps/` and `gamesettings/` sit in
`pcsxroo\bin\`, apart from the PCSX2 you play on.

## 3. Install Python 3.11+ and the packages

    pip install capstone keystone-engine zstandard numpy

`pillow` as well, for the tools that read the screen.

## 4. Tell the tools where things are

Paths are discovered automatically; anything can be overridden in a `local.json`
in this repo's root (gitignored):

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

## 5. Extract the ELF

From your disc image into `work/`:

    python tools/extract-elf.py

The generic tools in PCSXROO read their game identity and the ELF on their own
side. Point them at this repo's copy:

    copy ..\pcsxroo\pcsxroo\local.json.example ..\pcsxroo\pcsxroo\local.json
    set SCRATCH_DIR=%CD%\work
    python ..\pcsxroo\pcsxroo\tools\disas.py --source elf --func 1D9900

## 6. Make the reference save states

None ship, and none can: a save state is a full snapshot of the console's memory
- the game's code and data and the BIOS - so it would redistribute both, and it
is tied to the emulator build that wrote it. Build your own in PCSXROO:

    ..\pcsxroo\bin\pcsxroo.exe launch "D:\roms\bt3.cso"

Start a one-on-one battle and, with both fighters standing on the ground, save
**slot 1** - the hand-made ground state every A/B starts from:

    ..\pcsxroo\bin\pcsxroo.exe savestate --slot 1 --wait-flush

`mkstate.py` cuts the rest from it:

    python tools/mkstate.py air --slot 2
    python tools/mkstate.py airidle --slot 3
    python tools/mkstate.py --list

## 7. Run the A/B loop

`patchctl.py` switches pnach groups in the running game, so the unpatched 30fps
behaviour and the patched 60fps behaviour can be compared from the same state.
The acceptance tests are `speedtest.py`, `stomptest.py`, `blasttest.py` and
`realclock.py`.

**[`rig.md`](rig.md) is the runbook for this step** - the exact order an A/B has
to run in, how to reach any character and stage by driving the game's menus, and
the traps that silently produce a wrong answer instead of an error. Read it
before the first measurement, not after.

## 8. Read what is already known

Before changing anything:

| | |
|---|---|
| [`rig.md`](rig.md) | how to drive the emulator |
| [`status.md`](status.md) | the state of every group |
| [`method.md`](method.md) | how a patch is found, written and proved |
| [`versions/`](versions/README.md) | what each version changed and discovered |
| [`findings/`](findings/README.md) | the full derivation log |
| [`tools.md`](tools.md) | every tool |
| [`names.md`](names.md) | what the owner calls a mechanic, and what it is |

## Optional: decompilation

Needs Ghidra with the Emotion Engine extension. Create the project once (several
minutes):

    C:/Utils/ghidra/support/analyzeHeadless.bat work/ghidra BT3 \
      -import work/SLUS_216.78 -processor "r5900:LE:32:default" -loader ElfLoader

## Optional: stock PCSX2 instead of PCSXROO

The PINE tools drive stock PCSX2. Enable PINE there with:

    python ..\pcsxroo\pcsxroo\tools\setup-pcsx2.py --enable-pine

# Tools index

All 48 command-line tools, split across two repos. Every one has a real module
docstring - `python <tool> --help` is the reference.

- **This repo, `tools/`** - the 35 tools that know this game: they read BT3's
  structs, drive its pnach groups, or walk its save-state conventions. They
  import game knowledge from `tools/game/` and the generic library from the
  sibling pcsxroo checkout.
- **pcsxroo, `tools/pcsxroo/`** - the generic `ps2ee/` library and 13 EE
  analysis tools that would work on any game.

Transport column: **PCSXROO** = needs the PCSXROO debug server (port 28110),
**PINE** = works against stock PCSX2 with PINE enabled, **offline** = needs no
emulator at all. Tools that need a game identity take it from `local.json`
(this repo) or `tools/pcsxroo/local.json` (pcsxroo), or from `game.config`
automatically in this repo.

## In this repo (35)

| Tool | Transport | What it does |
|---|---|---|
| `apply-live.py` | PINE | Re-apply the current patch into a running PCSX2 over PINE. |
| `bisect.py` | PINE | Find the code that drives a live value, by disabling calls and watching it. |
| `blasttest.py` | PCSXROO | Fire a scripted blast at both rates and time how long the beam is on screen. |
| `census.py` | PCSXROO | Which of a list of addresses actually execute during a window of the game. |
| `decomp.py` | offline | Decompile BT3 functions through Ghidra headless. |
| `deploy.py` | PINE | Install a pnach into PCSX2 and enable it, so the user only has to launch. |
| `dump-state.py` | offline | Unpack a PCSX2 save state into work/ for offline analysis. |
| `eventdiff.py` | PCSXROO | Stop both arms at the same EVENT instead of the same time, and diff there. |
| `export.py` | offline | Write a shareable copy of the patch, with the development-only groups removed. |
| `extract-elf.py` | offline | Extract the boot ELF from the game disc image into work/. |
| `fields.py` | PCSXROO | Watch a window of a fighter's struct tick by tick, as floats. |
| `fighter.py` | PINE | Read live fighters, and find the frame counters inside them. |
| `findmotion.py` | PINE | Locate a moving object anywhere in EE RAM, in two stages. |
| `gate.py` | PINE | Run chosen call sites on even frames only, to see what drives a symptom. |
| `hitclock.py` | PCSXROO | Time a multi-hit attack by its damage schedule, and optionally by the screen. |
| `live.py` | PINE | Talk to a running PCSX2 over PINE - read, write, watch, apply patches live. |
| `mkgate.py` | offline | Turn an integer `field += 1` into one that counts on even ticks only. |
| `mkstate.py` | PCSXROO | Build the save states the A/B runs start from. |
| `mktramp.py` | PCSXROO | Assemble a trampoline with PCSXROO and emit it as pnach lines. |
| `motion.py` | PINE | Record a fighter and its model while it moves, then find what integrates. |
| `movieshot.py` | PCSXROO | Charge, fire a scripted move, and photograph its cinematic in real time. |
| `oscscan.py` | PCSXROO | Sweep all of RAM for what OSCILLATES twice as fast, not what steps twice as far. |
| `padcheck.py` | PCSXROO | Does injected pad input actually reach the game? |
| `patchctl.py` | PCSXROO | Turn pnach groups on and off in a running game, with no reboot. |
| `ratecheck.py` | PINE | Audit which fields are still running at double speed, by A/B-ing the frame rate. |
| `ratediff.py` | PCSXROO | Ask every word in RAM whether it still moves at double speed. |
| `ratescan.py` | PCSXROO | Find every field still moving at double speed, by comparing per-tick motion. |
| `realclock.py` | PCSXROO | Time and photograph a move in REAL time, with the game running free. |
| `shot.py` | PCSXROO | Drive an input for N frames from a save state, then photograph the result. |
| `speedtest.py` | PCSXROO | The acceptance test: how far does a fighter travel in a fixed real time? |
| `stomptest.py` | PCSXROO | The heavy smash and its Circle pursuit stomp, played in REAL time. |
| `sweep.py` | PCSXROO | Change one site at a time and score it against the oracles that matter. |
| `traj.py` | PCSXROO | Record a fighter's trajectory frame by frame, and compare two of them. |
| `transplant.py` | PCSXROO | Carry a save state into PCSXROO from a PCSX2 build whose format it refuses. |
| `writers.py` | PCSXROO | Enumerate every instruction that writes to an address range. |

## In pcsxroo (13)

| Tool | Transport | What it does |
|---|---|---|
| `countdown.py` | offline | Find countdown timers in a saved fighter trace, at byte granularity. |
| `dataxref.py` | offline | Find the code that touches a global, by address rather than by call graph. |
| `disas.py` | offline | Disassemble EE code around one or more addresses. |
| `looptree.py` | offline | Walk the call tree under a loop, then scan only that code for step constants. |
| `mkhalf.py` | offline | Turn `field += 1.0` sites into `field += 0.5`, one trampoline each. |
| `phasetimer.py` | offline | Find the fighter state machine's phase timers. |
| `probe-loop.py` | PINE | Disable one call in a loop at a time, live, to see what it drives. |
| `radar.py` | offline | Static scan for frame-pacing constants - a fast standalone pass. |
| `ramdiff.py` | offline | Differential memory search across save states. |
| `setup-pcsx2.py` | PINE | Inspect and adjust the PCSX2 settings this workflow depends on. |
| `tickcount.py` | offline | Find every integer `field = field + 1` in the binary - the frame counters. |
| `tickstep.py` | offline | Find every `field += 1.0` in the binary, including the hoisted ones. |
| `xref.py` | offline | Find who calls a function, and where its address is stored. |

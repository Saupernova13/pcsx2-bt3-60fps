# pcsx2-bt3-60fps

A 60fps patch for **Dragon Ball Z: Budokai Tenkaichi 3** (SLUS-21678, CRC 428113C2) on
PCSX2, and the tooling used to develop it.

Method follows [this PCSX2 forums guide](docs/60fps-workflow.md) by Red-tv141:
Ghidra static analysis, systematic isolation testing, and a two-role Analyst/Interpreter
loop. Scope is **battles**: movement, ki, combos, dashes, blast timing, stun, gauges and
AI must be correct at 60fps.

**The patch to use is [`releases/latest/428113C2.pnach`](releases/latest/).** Drop it in
PCSX2's `cheats/` directory, enable every group, and set `EnableCheats = true`. The file's
own header lists the groups and what is still not fixed.

Running analysis log: **[docs/findings.md](docs/findings.md)** - start at "STATE OF PLAY".

## What the patch covers

26 groups, each compensating one system that the 60Hz loop drives twice as often.
Movement, gravity and knockback; the animation clock; menu and combat input windows; the
ki aura, particles, effect rotation and the hovering idle; the tween system; blast hit
cadence and blast effect duration; the integer clock behind scripted-sequence waits; the
launch-and-pursuit chain - the flight a heavy smash puts someone into, and the five frame
counts behind the Circle stomp that follows it; the camera, whose blend rate and scripted
move lengths are both counted in ticks; the three movers that carry projectiles across
the ground - ki blasts, spawned objects like Frieza's rocks, and travelling beams like
Buu's charged blast and his breath; and the fullscreen fade service, which took its phase
durations in seconds and converted them at 30Hz, so every fade in the game ran in half
its real time.

Every group is verified against the unpatched 30fps game as its own oracle: same save
state, same input, same number of vsyncs. The ones a player can see are confirmed in play
with the game running free, not by frame stepping.

Known not fixed, and stated in the released file's header: an ultimate's beam lands its
first hit about half a second early; the summon animation before Frieza's rocks - most of
that move - still runs about five frames fast, as does the wind-up on Buu's charged blast;
some pre-fight intro animations are paced wrong against the camera; and the camera on a
body-erasing death has never been re-checked since the camera work landed.

Build-by-build confidence, and what has been confirmed in play rather than only measured,
is in **[releases/STATUS.md](releases/STATUS.md)**.

## Why the obvious patch does not work

The 60fps code in circulation forces one branch:

    patch=1,EE,20264DBC,extended,10000008    // skip the vblank wait loop
    patch=1,EE,201DCB40,extended,3C013F80    // halve one step multiplier (2.0 -> 1.0)

That removes the frame limiter for *every* game loop at once while compensating exactly
one timestep constant. Everything else the loop drives - physics, ki and gauge fill, blast
and combo timing, stun, AI cadence - still advances a full 30fps step per iteration and
therefore runs at double speed.

BT3 turns out to have no master framerate variable. Its per-frame routine takes a vblank
stride as an argument, and all eight call sites hardcode it (`addiu $a0, $zero, 2` for
30fps, `1` for 60fps). So the right lever is a one-word change at the specific loop you
want to convert, not a global branch kill. See findings.md for the full table.

## Layout

    docs/       the guide, and the running findings log
    ps2_patch_agent_tools/   Agent context and Workflow
    rules/      Analyst and Implementer v4.0 rule sets from the guide author
    ps2ee/      python library (see below)
    tools/      command line entry points
    patches/    the working pnach, plus numbered isolation experiments in exp/
    releases/   what to hand someone: latest/ and a directory per tagged release
    ghidra/     PS2_Scoring_Radar and the headless decompiler script
    work/       gitignored: extracted ELF, RAM dumps, Ghidra project, caches

## Setup

Needs Python 3.11+, and Ghidra with the Emotion Engine extension for decompilation.

    pip install capstone keystone-engine zstandard numpy

    python tools/setup-pcsx2.py            # report PCSX2 settings
    python tools/setup-pcsx2.py --enable-pine
    python tools/extract-elf.py            # pull SLUS_216.78 out of the disc image

Development also wants **PCSXROO**, a PCSX2 fork with the debug server this repo drives -
memory reads and writes, breakpoints, watchpoints, save states, pad injection and
screenshots over a socket on port 28110. It runs in portable mode, so its `cheats/`,
`sstates/` and `snaps/` sit next to the executable and never touch the PCSX2 install
above. Start it detached, so it outlives the shell that launched it:

    pcsxroo-qt.exe -debugserver 28110 -- "path\to\bt3.cso"

Paths are discovered automatically. Override anything by creating `local.json` in the
repo root:

    {
      "PCSX2_DIR":   "C:/path/to/PCSX2",
      "PCSXROO_DIR": "C:/path/to/pcsxroo/bin",
      "GAME_IMAGE":  "D:/roms/bt3.cso",
      "GHIDRA_HOME": "C:/Utils/ghidra"
    }

Ghidra project (once, several minutes):

    C:/Utils/ghidra/support/analyzeHeadless.bat work/ghidra BT3 \
      -import work/SLUS_216.78 -processor "r5900:LE:32:default" -loader ElfLoader

## Tools

| Command | What it does |
|---|---|
| `tools/extract-elf.py` | Pulls the boot ELF from the .cso without expanding it to a 3 GB ISO |
| `tools/dump-state.py` | Unpacks a .p2s save state (zstd) into EE RAM, IOP RAM and the screenshot |
| `tools/disas.py` | Disassembles around an address, or a whole function, with jump targets resolved |
| `tools/xref.py` | Finds direct callers and function-pointer references |
| `tools/decomp.py` | C pseudocode and listing from Ghidra headless, cached |
| `tools/radar.py` | Scans for frame-pacing constants (1, 2, 0.5, 1.0, 2.0) - the scoring-radar heuristic |
| `tools/ramdiff.py` | Differential memory search across save states |
| `tools/live.py` | Reads, writes, watches and patches a running PCSX2 over PINE |
| `tools/deploy.py` | Installs a pnach and enables it, so testing is just "launch and play" |
| `tools/patchctl.py` | Turns groups on and off in a running game, restoring what a disabled one overwrote |
| `tools/export.py` | Writes the shareable copy: development-only groups dropped, known defects in the header |
| `tools/setup-pcsx2.py` | Reports and adjusts the PCSX2 settings this workflow needs |
| `tools/tickcount.py` | Finds every integer `field += 1` and `field -= 1` - the game's frame counters |
| `tools/tickstep.py` | Finds every float `field += 1.0`, including the ones whose 1.0 is hoisted into a register |
| `tools/phasetimer.py` | Finds the fighter state machine's per-state phase timers |
| `tools/mkgate.py` | Writes a trampoline that advances an integer counter on even ticks only |
| `tools/mkhalf.py` | Writes a trampoline that adds 0.5 where the code added 1.0 |
| `tools/ratediff.py` | Asks every word in RAM whether it still moves at double speed |
| `tools/eventdiff.py` | Stops both arms at the same event instead of the same time, and diffs there |
| `tools/census.py` | Narrows a static candidate list to the sites that actually execute in a window |
| `tools/sweep.py` | Changes one site at a time and scores it against two oracles at once |
| `tools/realclock.py` | Times and photographs a move in real time, with the game running free |
| `tools/stomptest.py` | Plays the heavy smash and its Circle pursuit stomp on the wall clock, and says whether it connected |
| `tools/movieshot.py` | Charges, fires a scripted move, and photographs its cinematic in real time |

## How a patch gets written

Patches are authored as **MIPS assembly with hook declarations**, never as hand-encoded
hex. `ps2ee.asm` assembles with keystone, places code in the safe zone at `0x000F0000`,
and computes the hook jumps:

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

Delay slots are yours to fill - the assembler runs with `.set noreorder` so nothing is
reordered and no nop is inserted behind your back.

`Pnach.validate()` runs before every deploy and rejects writes outside `.text`, `.data`
and the safe zone, unaligned word writes, dangling E-code conditions, and two groups
writing the same address.

## Testing loop

Every measurement is an A/B against the unpatched game from the same save state, and
`patchctl` switches between the two without a restart. It renames groups in the pnach and
puts back what a disabled one overwrote, because PCSX2 stops rewriting a `patch=1` line
when a group goes away but does not undo it.

    python tools/patchctl.py --status
    python tools/patchctl.py --off                # stock 60fps, nothing compensated
    python tools/patchctl.py --on full            # everything that ships
    python tools/patchctl.py --on nomouth         # the shipping set minus the mouth clock

Four rules, each learned by getting it wrong:

- **Load the state, then apply the preset, then run.** Never load again after applying:
  the save states were captured while patched, so a second load puts the patched words
  straight back and the "unpatched" arm is not unpatched. Check it ticks 30 times a
  second.
- **A screenshot needs a running VM - but a paused one is only queued, not lost.**
  `screenshot()` while paused writes no file; `frame_advance(1)` then flushes it. So a
  `screenshot, frame_advance(1)` loop costs exactly one vsync a sample and gives a film
  as deterministic as memory, aligned frame for frame between the arms. That is how the
  mouth was measured. What does not work is sampling on the wall clock and hoping - or
  `frame_advance(N), screenshot` without the flush, where the file is a stale frame.
- **A new group name needs a restart, and the ini is PCSXROO's own.** The enabled list is
  read only at boot, and it lives at `<pcsxroo>/bin/gamesettings/SLUS-21678_428113C2.ini`
  - the emulator's data root, NOT under `inis/`, and NOT the file `config.game_ini()` and
  `deploy.py` write, which belongs to the installed PCSX2. A group missing from that list
  applies nothing and reports nothing; `patchctl --status` now says so. Three spare names
  are carried there so an experiment does not cost a restart.
- **Shrinking a live group needs a restart too**, because the hooks it drops stay patched
  in RAM with nothing left to restore them.

When a change is ready to hand over:

    python tools/export.py --release v9-scripted-clocks

## Notes

- Save states from PCSX2 2.1.178+ use zstd. `ps2ee.savestate` reads them directly;
  Ghidra's own save state importer cannot, so use ours.
- The ELF loads at `0x00100000` with no overlays and no self-modifying code, verified
  against live RAM. Ghidra addresses are pnach addresses, unchanged.
- Capstone has no R5900 mode, so `ps2ee.disasm` will not decode MMI or VU0 macro-mode
  instructions. Use `tools/decomp.py` inside VU-heavy code.

## Credits

Workflow and the Analyst/Implementer rule sets: Red-tv141.
Framerate-address techniques in Section 1 of the guide: asasega.
Ghidra Emotion Engine support: chaoticgd and beardypig.

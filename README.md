# pcsx2-bt3-60fps

A 60fps patch for **Dragon Ball Z: Budokai Tenkaichi 3** (SLUS-21678, CRC 428113C2) on
PCSX2, and the tooling used to develop it.

Method follows [this PCSX2 forums guide](docs/60fps-workflow.md) by Red-tv141:
Ghidra static analysis, systematic isolation testing, and a two-role Analyst/Interpreter
loop. Scope is **battles**: movement, ki, combos, dashes, blast timing, stun, gauges and
AI must be correct at 60fps.

Running analysis log: **[docs/findings.md](docs/findings.md)**.

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
    rules/      Analyst and Implementer v4.0 rule sets from the guide author
    ps2ee/      python library (see below)
    tools/      command line entry points
    patches/    the deliverable, plus numbered isolation experiments in exp/
    ghidra/     PS2_Scoring_Radar and the headless decompiler script
    work/       gitignored: extracted ELF, RAM dumps, Ghidra project, caches

## Setup

Needs Python 3.11+, and Ghidra with the Emotion Engine extension for decompilation.

    pip install capstone keystone-engine zstandard numpy

    python tools/setup-pcsx2.py            # report PCSX2 settings
    python tools/setup-pcsx2.py --enable-pine
    python tools/extract-elf.py            # pull SLUS_216.78 out of the disc image

Paths are discovered automatically. Override anything by creating `local.json` in the
repo root:

    {
      "PCSX2_DIR":  "C:/path/to/PCSX2",
      "GAME_IMAGE": "D:/roms/bt3.cso",
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
| `tools/setup-pcsx2.py` | Reports and adjusts the PCSX2 settings this workflow needs |

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

    python tools/deploy.py patches/exp/007-something.pnach --only "60FPS"
    # launch PCSX2, boot BT3, load the save state, observe

With PCSX2 running and PINE enabled, experiments do not need a restart:

    python tools/live.py status
    python tools/live.py fps                   # measure the real logic step rate
    python tools/live.py apply patches/exp/007-something.pnach
    python tools/live.py watch 00331D64 00331D60 --seconds 5

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

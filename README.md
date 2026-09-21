# pcsx2-bt3-60fps

A 60fps patch for **Dragon Ball Z: Budokai Tenkaichi 3** (SLUS-21678, CRC
428113C2) on PCSX2, and the tooling that built it.

## Install

1. Download **`428113C2.pnach`** from the
   [latest release](https://github.com/Saupernova13/pcsx2-bt3-60fps/releases/latest).
   Keep the name - PCSX2 finds a pnach by the game's CRC and ignores any other.
2. Put it in PCSX2's `cheats/` folder.
3. Set `EnableCheats = true` for the game and tick every group listed in the
   file's own header, under Settings -> Cheats.
4. Quit and relaunch PCSX2. A reset or a save-state load is not enough.

From a clone, `python tools/deploy.py patch/428113C2.pnach` does all of that.

## What it fixes

33 groups, each compensating one system that the 60 Hz loop drives twice as
often as it should.

| | groups |
|---|---|
| The battle loop itself | `battle` |
| Animation | `animation clock`, `mouth clock` |
| Input windows | `input timing`, `input repeat timing` |
| Movement, gravity, knockback | `airborne motion`, `airborne vertical`, `airborne residual`, `gravity`, `knockback flight`, `pursuit timing`, `hover bob` |
| Fighter state clocks | `state phase timers`, `sequence wait` |
| Blasts and projectiles | `blast hit cadence`, `blast effect duration`, `projectile travel`, `blast object travel`, `beam object travel`, `thrown object rate` |
| Effects and fades | `aura update rate`, `particle update rate`, `effect rotation`, `tween duration`, `screen fade` |
| Camera | `camera pacing` |
| Rush and beam struggles | `rush struggle`, `beam clash` |
| Stage and status | `stage animation`, `solar flare` |
| Widescreen, optional | `19.5:9`, `16:10`, `21:9` |

Every group is verified against the unpatched 30fps game as its own oracle: same
save state, same input, same number of vsyncs. The ones a player can see are
confirmed in play with the game running free, not by frame stepping.

## Known not fixed

Also stated in the shipped file's header.

| | |
|---|---|
| An ultimate's beam | lands its first hit about half a second early |
| Frieza's *I Might Die This Time*, Buu's Super Kamehameha | the wind-up before the launch still runs about five frames fast |
| Some pre-fight intros | paced wrong against the camera |
| A body-erasing death | the camera has never been re-checked since the camera work landed |
| A Beam Struggle | the CPU ends a little weaker than at 30fps, so a near-tie can fall the player's way |

Per-group confidence, and what is confirmed in play rather than only measured,
is in [`docs/status.md`](docs/status.md).

## Repository layout

    patch/            the patch to install: 428113C2.pnach
    wip/              the working pnach and isolation experiments - NOT for install
    tools/            the command line tools, with the game knowledge in tools/game/
    docs/             method, tool index, release history, and the findings log
    ghidra/scripts/   the headless decompiler script

Every released version is a git tag, from `v01-...` to `v24-...`, holding the
patch as it shipped. `work/` is gitignored.

## Developing it

| | |
|---|---|
| [`docs/getting-started.md`](docs/getting-started.md) | set the rig up from nothing |
| [`docs/rig.md`](docs/rig.md) | the runbook: how to drive the emulator, and the traps |
| [`docs/method.md`](docs/method.md) | how a patch is found, written and proved |
| [`docs/status.md`](docs/status.md) | every group and whether it is trusted |
| [`docs/versions/`](docs/versions/README.md) | what each version changed and discovered |
| [`docs/findings/`](docs/findings/README.md) | the full derivation log |
| [`docs/tools.md`](docs/tools.md) | every tool, and what it needs to run |
| [`docs/releases.md`](docs/releases.md) | how a version is cut |

## Credits

Workflow, and the Analyst/Implementer rule sets: Red-tv141 - see the
[guide thread](https://forums.pcsx2.net/Thread-GUIDE-AI-Assisted-60fps-Patch-Development-for-PS2-Games-%E2%80%94-Full-Workflow)
(the guide itself is not hosted here).
Framerate-address techniques in Section 1 of the guide: asasega.
Ghidra Emotion Engine support: chaoticgd and beardypig.

## Licence

Code (`tools/`, `ghidra/scripts/`): **MIT**, see [`LICENSE`](LICENSE).
Docs, findings and the patch itself: **CC BY 4.0**, see [`LICENSE-docs`](LICENSE-docs).

# v25-state-phase-timers - DRAFT

| | |
|---|---|
| Tag | `v25-state-phase-timers` |
| Date | 2026-09-30 |
| Built on | [v24-state-phase-timers](v24-state-phase-timers.md) |
| Groups | 1 shipped group(s) changed |
| Confidence | **DRAFT - fill this in** |

> **DRAFT.** Every other note on this page is written for a player: what this
> version changes over the last one, and what was discovered on the way. Rewrite
> this before the release PR merges - its merge is what publishes the release.

## What it changed

Shipped groups this version carries that the last release did not:

- `60FPS - state phase timers`

The commits to `wip/working.pnach` it carries since v24-state-phase-timers:

- fix(export): carry each group's description with its own group (a0baedb)
- fix(patch): stop gating four phase numbers as if they were clocks (e4a754c)

## What was discovered

fix(patch): stop gating four phase numbers as if they were clocks

This PR fixes the freeze where a fighter gets stuck in place with his model flashing on and off, which v24 shipped.

## Synopsis

`[60FPS - state phase timers]` stops gating four sites that are phase numbers rather than frame counters. One of them, `001E6060`, is the only exit from state 93's 8-tick phase-0 loop, so a loop that ended on an odd tick repeated forever. The group now writes the game's own instruction back at each of the four sites, so a save state made under v24 comes unstuck when it is loaded.

## What changed

| | v24 | This PR |
|---|---|---|
| Sites the group gates | 21 | 17, every one compared against its bound on the next instruction |
| `001E6060` (states 90-93) | gated | original `lw v0,(s3)` written back |
| `001F3320` (state 44) | gated | original `lw v0,(s1)` written back |
| `001F9D48` (states 301-303, 313-315) | gated | original `lw v0,(s4)` written back |
| `001FBBD0` (state 260) | gated | original `lw v0,(s2)` written back |
| Group patch lines | 210 | 174 |
| Exported patch lines | 557 | 521; nothing else differs |

The 28 counters `phasetimer.py` finds, sorted by the instruction after the add:

| | sites | gated after this PR |
|---|---|---|
| compared (`slti`/`slt`), a clock | 21 | 17. The other 4 were already out as input windows |
| not compared, an index | 7 | 0 |

## Test results

Run on the user's EmuDeck save state from the freeze (Super Saiyan Goku in state 93), carried into PCSXROO with `transplant.py`:

| arm | phase `fighter+0x3D8` | outcome |
|---|---|---|
| v24 | 0 on every tick watched; the sub-counter wraps on odd frames 13109, 13117, 13125 and so on | frozen, model missing on alternate screenshots |
| v24, left running | 0 | stuck in state 93 until the CPU's attack lands at v517, then hit (196) and free: the recovery #57 reports |
| exported patch, state loaded, no hand edits | 0, then 1, 2, 3 | hook overwritten on the first vsync; idle (state 11) after 69 ticks; model drawn on every frame |
| `export.py` | - | validated, 33 groups, 521 lines |
| `version.py status` | - | `changed=60FPS - state phase timers`, so a merge makes it v25 |

Closes #39
Closes #57

🤖 Generated with [Claude Code](https://claude.com/claude-code)

> Seeded from one merge's body, which may describe only one of the changes
> listed above: #58.

## Get this version

Download `428113C2.pnach` from the
[v25-state-phase-timers release](https://github.com/Saupernova13/pcsx2-bt3-60fps/releases/tag/v25-state-phase-timers),
or:

    git show v25-state-phase-timers:patch/428113C2.pnach > 428113C2.pnach

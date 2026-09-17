# v24-state-phase-timers - DRAFT

| | |
|---|---|
| Tag | `v24-state-phase-timers` |
| Date | 2026-09-17 |
| Built on | [v23-known-issues-refresh](v23-known-issues-refresh.md) |
| Groups | 6 shipped group(s) changed |
| Confidence | **DRAFT - fill this in** |

> **DRAFT, scaffolded from #46.** Every other note on this page
> is written for a player: what this version changes over the last one, and what
> was discovered on the way. Rewrite this before the release PR merges - its
> merge is what publishes the release.

## What it changed

Shipped groups this version carries that the last release did not:

- `60FPS - solar flare`
- `60FPS - stage animation`
- `60FPS - state phase timers`
- `60FPS - thrown object rate`
- `Widescreen 16:10`
- `Widescreen 21:9`

## What was discovered

fix(tools): stop tools/ shadowing the python stdlib, which broke every tool on linux

Every tool in `tools/` failed to import on Linux, which is why PR #45's first real run died before it could stage the v24 release. `tools/bisect.py` was shadowing Python's stdlib `bisect`.

## The chain

`python tools/<tool>.py` puts `tools/` at `sys.path[0]`, so `tools/bisect.py` won:

```
capstone → ctypes.util → tempfile → random → from bisect import bisect
                                                 ↓
                                    tools/bisect.py, not the stdlib
```

```
ImportError: cannot import name 'bisect' from partially initialized module
'ps2ee.disasm' (most likely due to a circular import) (.../tools/bisect.py)
```

`ps2ee` then fails at import, and `_bootstrap` prepended `tools/` and `pcsxroo/` to `sys.path`, ahead of stdlib for everything.

## Why local testing missed it

Windows loads `bisect` at interpreter startup, so the cached stdlib module always won there. A cold Linux interpreter loads it lazily, on the `random` import - by which point `tools/bisect.py` is the visible one.

| | `bisect` preloaded at startup | result |
|---|---|---|
| Windows (all local testing) | yes | stdlib wins, tool runs |
| Linux runner | no | `tools/bisect.py` wins, import fails |

## The fix

`tools/_bootstrap.py` no longer prepends. Both paths are appended, so stdlib stays ahead of them.

| | Before | After |
|---|---|---|
| `tools/` | prepended | appended |
| `pcsxroo/` | prepended after `tools/` | appended after `tools/` |
| stdlib vs `tools/` | `tools/` wins | stdlib wins |
| `tools/` vs `pcsxroo/` | `tools/` wins | unchanged |

## Test results

| check | result |
|---|---|
| Cold-interpreter import of `export`, `patchctl`, `game.config`, `ps2ee.pnach` | all OK |
| `bisect` after the fix | resolves to stdlib |
| `python tools/version.py status` | rc 0, 6 groups changed |
| `python tools/export.py --to ...` | rc 0, 33 groups, 557 lines, validated |
| `tools/` vs `pcsxroo/` module overlap | none, so append order changes no resolution |
| Windows | same commands still pass |

`tools/bisect.py` keeps its name; `tools/gate.py:27` loads it by path and the docs cite it. The append fix removes the hazard for every tool at once.

## Get this version

Download `428113C2.pnach` from the
[v24-state-phase-timers release](https://github.com/Saupernova13/pcsx2-bt3-60fps/releases/tag/v24-state-phase-timers),
or:

    git show v24-state-phase-timers:patch/428113C2.pnach > 428113C2.pnach

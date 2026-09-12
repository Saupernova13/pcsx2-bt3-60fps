# Spec: making pcsx2-bt3-60fps publishable

Status: Stages 1-3 executed 2026-09-12; publishing and the pcsxroo merge are
the owner's remaining calls.
Written 2026-09-12. Decisions in this document were made interactively; the
sections below are the record.

## 0. Goal and scope

Open-source this 60fps patch repo so a stranger can:

1. find the final patch in one obvious place,
2. read what it fixes and what it does not,
3. install it without reading the research log,
4. reuse the tooling (or the patch) without asking us anything.

Non-goals: do not publish game data (ISO, ELF, save states, dumps), other
people's work, private drafts, or machine-specific config. Nothing on disk is
deleted by any of this; excluded material is gitignored or moved, never removed
from the machine.

## 1. Locked decisions

| Decision | Choice |
|---|---|
| Git history (never pushed; third-party files in all 151 commits) | Surgical purge with `git filter-repo` (verified installed: `a40bce548d2c`) |
| Generic library (ps2ee) | Moves to `pcsxroo/tools/pcsxroo/ps2ee/` (its existing `tools/pcsxroo/` precedent, no upstream collision) |
| Migration mechanism | History-preserving extraction with filter-repo, grafted into pcsxroo |
| BT3 game knowledge | Stays in this repo as `bt3/` (fighter, battle, game identity) |
| Config seam | Split: emulator/path discovery generic, game identity local |
| Sequencing | Staged: patch repo publishable first, then migration |
| Release names | Zero-pad and keep names: `v02-…` through `v22-…`, collision as `v06b-…`; no v1 (gap documented, not invented) |
| All BT3 tools | Publish all; undocumented ones get documented, by running them if needed |
| Licence | MIT for code, CC BY 4.0 for docs and the patch |
| Install file | `patch/428113C2.pnach` at top level; `releases/latest/` retired |

## 2. Target published tree

```
README.md                     what it is, install, what's fixed, what isn't, credits
LICENSE                       MIT      -> code (tools/, bt3/, ghidra/scripts/DumpFunction.java)
LICENSE-docs                  CC BY 4.0 -> docs/, findings, the pnach itself
patch/428113C2.pnach          THE patch. One obvious place, top level.
releases/
  STATUS.md                   the confidence ladder
  v02-airborne-and-hover/     ... v06-blast-effect-duration/
  v06b-withdraw-broken-blast-groups/ ... v22-beam-clash/
docs/
  findings.md                 the research log (prose unchanged; see 5.4)
  method.md                   our method, links Red-tv141's thread, does not host it
  tools.md                    index: every tool, what it does, what it needs
  specs/                      this spec
bt3/                          game knowledge: fighter.py, battle.py, game.py, config.py
tools/                        32 BT3 tools (see 4.1)
ghidra/scripts/DumpFunction.java   ours
dev/pnach/working.pnach       the working pnach + experiments/ (clearly not installable)
```

Gitignored, never published: `work/` (1.3 GB of save states and dumps),
`scratch/`, `ps2_patch_agent_tools/` (550 MB, third-party), `local.json`,
`docs/video-essay-draft.md`, `*.png`, `__pycache__`.

## 3. History purge

Five paths removed from all commits with `git filter-repo --invert-paths`.
All five entered in commit `3bd1671` ("scaffold"), so they are in every one of
the 151 commits:

| Path | Why |
|---|---|
| `docs/60fps-workflow.md` | Transcription of Red-tv141's forum guide ("Source: forums.pcsx2.net… Author: Red-tv141… Transcribed into this repo on 2026-08-21"). Replaced by our own `docs/method.md` that links the thread. |
| `rules/` (2 files) | Red-tv141's Analyst/Implementer rules ("collaborative reverse engineering project between Analyst and Implementer"), byte-identical to the source bundle. |
| `ghidra/scripts/PS2_Scoring_Radar.java` | `@author Gemini + Claude + Puggsy` — someone else's generated work. |
| `docs/reference-darkcloud2.pnach` | Puggsy / Red-Tv's patch for a different game. |
| `docs/video-essay-draft.md` | Ours, but a private draft — active work, not for publish. Purged and gitignored so it can live on disk uncommitted. |

The history scan found 104 unique paths ever committed; nothing third-party was
ever added and later deleted. The purge set above is complete — no buried
surprises. Our own files stay in history even where the restructure moves them
(legal non-issue, MIT; a deeper rewrite is rejected as revisionism with no gain).

Safety: `git bundle create ../pcsx2-bt3-60fps-pre-purge.bundle --all` before
touching anything — that is the undo. Purge is Stage 1; the moved tooling is
not purged from history (see 4.3).

## 4. The split and the migration

### 4.1 Tool allocation (49 tools)

Rule (corrected): a tool **stays** only if it uses actual game knowledge —
imports `fighter`/`battle`, hardcodes this game's CRC/serial/ELF/EE addresses,
carries pnach group lists, or uses project save-slot conventions. Merely
importing `config` for path discovery does not make a tool BT3-specific.

Stays (32): apply-live, bisect, blasttest, census, decomp, deploy, dump-state,
eventdiff, export, extract-elf, fields, fighter, findmotion, gate, hitclock,
live, mkgate, mkstate, mktramp, motion, movieshot, padcheck, patchctl,
ratecheck, ratediff, ratescan, shot, speedtest, stomptest, sweep, traj,
transplant.

Moves to pcsxroo (17): disas, xref, radar, ramdiff, looptree, dataxref,
tickcount, tickstep, writers, oscscan, probe-loop, countdown, phasetimer,
setup-pcsx2, mkhalf, realclock, `_bootstrap`.

Early classification flagged five false positives that are corrected here:
`patchctl` (holds this project's 30 pnach group strings), `mktramp`,
`blasttest`, `hitclock`, `sweep` (carry BT3 addresses or group names) — all
stay.

### 4.2 Module split (ps2ee)

Moves (10): asm, ciso, diff, disasm, eemem, live, pine, pnach, roo, savestate.
(`savestate` is an addition to the earlier list: `ramdiff` operates on `.p2s`
files and cannot move without it.)

Stays, as `bt3/`: fighter, battle, plus a new `bt3/config.py` and `bt3/game.py`
carrying everything game-specific:

- identity: `SERIAL = "SLUS-21678"`, `CRC = "428113C2"`,
  `ELF_NAME = "SLUS_216.78"`, `GAME` (config.py:25, 49-51)
- layout knowledge: `TEXT_BASE`..`BSS_END`, `GP_BASE`, `SAFE_ZONE`,
  `EE_RAM_SIZE` (config.py:54-67)
- patch-policy: `NEVER_SHIP`, `OPTIONAL` (config.py:37-47)
- repo paths: `REPO`, `WORK`, `PATCHES`, new `DEV_PNACH = REPO/"dev"/"pnach"`
  (config.py:19-21)
- game-flavoured discovery: `game_image()` (searches `*Tenkaichi 3*`),
  `game_ini()`, `roo_game_ini()`, `roo_cheat_file()`, `latest_state()`,
  `elf_path()` — all embed SERIAL/CRC (config.py:118-176, 203-220)

Generic config (moves): `local.json`/`_setting` mechanism, `pcsx2_dir()`,
`cheats_dir()`, `sstates_dir()`, `global_ini()`, `pcsxroo_dir()`,
`roo_snaps_dir()`, candidate lists — plus one new interface: a `GameIdentity`
binding the consumer sets before use, and `SCRATCH_DIR` (env-overridable) to
replace the `WORK` references in moved tools (`setup-pcsx2.py:66`,
`probe-loop.py:26`).

### 4.3 Import mechanism (how this repo depends on pcsxroo)

`tools/_bootstrap.py` is rewritten: it adds the repo root and the sibling
`../pcsxroo/tools/pcsxroo` to `sys.path`, so both `from bt3 import …` and
`from ps2ee import …` resolve. Running BT3 tools therefore requires a sibling
checkout of pcsxroo — consistent with the existing sibling discovery
(config.py:184-187) and stated in the README.

History: filter-repo extracts `ps2ee/` + the 17 moving tools into a graft that
is merged into pcsxroo (history-preserving, every commit that touched them).
The patch repo's own history keeps those files at their old paths — cosmetic,
ours, and intentionally not rewritten (see 3).

### 4.4 pcsxroo landing layout

`pcsxroo/tools/pcsxroo/ps2ee/` (the library) beside its existing
`tools/pcsxroo/` scripts (build.cmd, seed-portable.ps1, smoke-test.ps1,
doc-examples.ps1, find-vs.cmd, test.cmd — verified present). Exact location of
the 17 CLI tools inside `tools/pcsxroo/` is confirmed against pcsxroo's
AGENTS.md at execution time. Licensing note: pcsxroo is GPLv3; the migrated
Python lands under it (accepted, one-way door).

## 5. Releases, docs, licence

### 5.1 Release renames

| From | To |
|---|---|
| v2-airborne-and-hover | v02-airborne-and-hover |
| v3-blast-hit-cadence | v03-blast-hit-cadence |
| v4-blast-effect-rate | v04-blast-effect-rate |
| v5-blast-sequence-rate | v05-blast-sequence-rate |
| v6-blast-effect-duration | v06-blast-effect-duration |
| v6-withdraw-broken-blast-groups | v06b-withdraw-broken-blast-groups |
| v7-blasts-fixed | v07-blasts-fixed |
| v8-blast-duration-only | v08-blast-duration-only |
| v9-scripted-clocks | v09-scripted-clocks |
| v10…v22 | unchanged |

No v1 ever existed; the gap is documented in `releases/STATUS.md`, not
invented. Pnach filenames inside are already `428113C2.pnach` — untouched.

### 5.2 `patch/` vs `releases/latest/`

`patch/428113C2.pnach` becomes the canonical install file. `export.py
--release NAME` now writes `releases/NAME/` and refreshes `patch/` (top
level); `releases/latest/` is retired and removed from the tree.

### 5.3 Documentation

- `README.md` — rewritten for a stranger: what it is, install, fixed list,
  known-not-fixed, tooling overview (and the pcsxroo sibling requirement),
  credits, licence note. Its current lines 6, 69, 71 and the credits block
  reference purged files and must go.
- `docs/findings.md` — prose is **not** rewritten; it is a dated log, and
  editing past entries to match new paths is revisionism. A note at the top
  records that tools moved to `pcsxroo/tools/pcsxroo/` on 2026-09-12. Its 44
  `tools/*.py` references remain readable because tool names do not change.
  Prose citations of the radar script stay (they cite, not re-host).
- `docs/method.md` — new, ours; links Red-tv141's thread, replaces the purged
  transcription.
- `docs/tools.md` — new index: all 49 tools, location (this repo vs pcsxroo),
  transport needed (PCSXROO / stock PCSX2 over PINE / offline), and the
  docstring blurb. The undocumented BT3 tools get documented here, by running
  them against the emulator where that is what it takes (user-approved).
- `patches/README.md` → `dev/pnach/README.md` (carried over, path-fixed);
  `patches/exp/` → `dev/pnach/experiments/`.
- `releases/README.md`, `releases/STATUS.md` — carried over as-is (they already
  document the convention correctly).
- `docs/superpowers/` — empty skill working directory, deleted.

### 5.4 Licensing

`LICENSE` (MIT) for code; `LICENSE-docs` (CC BY 4.0) for docs, findings and
the pnach. `ghidra/scripts/DumpFunction.java` is ours and stays (it drives
`tools/decomp.py`).

## 6. Code touch-points (everything the move breaks)

Every path, constant and literal that must change. Collected 2026-09-12;
file:line references are to the current tree.

### 6.1 ps2ee/config.py

| Line | Symbol | Fate |
|---|---|---|
| 19-21 | `REPO`, `WORK`, `PATCHES` | stay in `bt3/config.py`; `PATCHES` points at `patch/`; add `DEV_PNACH` |
| 25, 49-51 | `SERIAL`, `CRC`, `ELF_NAME`, `GAME` | move to `bt3/game.py`; generic config gets `GameIdentity` injection |
| 37-47 | `OPTIONAL`, `NEVER_SHIP` | stay (patch policy, BT3) |
| 54-67 | `TEXT_BASE`…`BSS_END`, `GP_BASE`, `SAFE_ZONE`, `EE_RAM_SIZE` | stay (game layout knowledge) |
| 71-93 | candidate dirs, `_local`, `_setting` | move (generic) |
| 96-116 | `pcsx2_dir`, `cheats_dir`, `sstates_dir`, `global_ini` | move (generic) |
| 118-123 | `game_ini` | stays BT3 (embeds `SERIAL_{CRC}`) |
| 126-159 | `game_image`, `_rom_dirs_from_ini` | stays BT3 (`*Tenkaichi 3*` search) |
| 162-164 | `elf_path` | stays BT3 (`WORK / ELF_NAME`) |
| 167-176 | `latest_state` | stays BT3 (SERIAL/CRC state pattern) |
| 184-200 | `pcsxroo_dir` | move (generic) |
| 203-220 | `roo_cheat_file`, `roo_game_ini`, `roo_enabled_cheats` | stay BT3 (embed CRC/SERIAL); `roo_snaps_dir` moves |

### 6.2 Tools that stay (32) — path/literal fixes

| File | Line | Today | After |
|---|---|---|---|
| export.py | 112 | `--source default="patches/428113C2.pnach"` | `dev/pnach/working.pnach` |
| export.py | 135 | `releases/` derived from `__file__` | keep; drop the `latest` target |
| export.py | 13-19 | docstring `releases/latest/` | rewritten for `patch/` |
| export.py | 37, 144 | `config.NEVER_SHIP`, `config.CRC` | unchanged via `bt3.config` |
| deploy.py | 3-4, 85, 94-96 | docstring + refusal hint `patches/…`, `releases/latest/…` | `patch/428113C2.pnach` / `dev/pnach/…` |
| deploy.py | 86 | `config.NEVER_SHIP` | unchanged via `bt3.config` |
| deploy.py | 115 | `config.WORK / "cheat-backups"` | unchanged |
| apply-live.py | 7, 23 | `patches/428113C2.pnach`; default `config.PATCHES / "428113C2.pnach"` | default becomes `config.DEV_PNACH / "working.pnach"` |
| live.py | 8 | docstring `patches/exp/003-halve-anim.pnach` | `dev/pnach/experiments/003-halve-anim.pnach` |
| gate.py | 12-14 | docstring says `python work/gate.py` (wrong today) | fix to `tools/gate.py` |
| gate.py | 34 | `STATE = pathlib.Path("work/gate-state.json")` (CWD-relative) | `config.WORK / "gate-state.json"` |
| decomp.py | 45, 47, 59 | `config.WORK/ghidra`, `WORK/decomp`, `REPO/"ghidra"/"scripts"` | unchanged (ghidra/ stays) |
| fighter.py, dump-state.py, traj.py | 25, 40, 46 | `config.WORK/…` | unchanged |
| all 32 | — | `import _bootstrap`, `from ps2ee import config`, `from ps2ee import fighter/battle` | `from bt3 import config / fighter / battle`; generic imports (`Pine`, `pnach`, `roo`, `eemem`, …) stay `ps2ee.*` |
| all 32 | — | docstrings `python tools/<name>.py` | unchanged (tools/ name survives) |

### 6.3 Tools that move (17)

`from ps2ee import config` stays valid (generic config moves with them).
`setup-pcsx2.py:66` and `probe-loop.py:26` switch `config.WORK` →
`config.SCRATCH_DIR`. Docstrings' `python tools/<name>.py` re-point to the
pcsxroo invocation convention chosen in 4.4. `_bootstrap` becomes the
pcsxroo-side path shim.

### 6.4 Docs and gitignore

- README.md: 30 `tools/*.py` mentions (rewritten anyway) + lines 6, 69, 71 +
  credits block naming purged files.
- docs/findings.md: 44 `tools/*.py` mentions (kept as-is, see 5.3).
- .gitignore additions: `local.json`, `ps2_patch_agent_tools/`,
  `docs/video-essay-draft.md`, `docs/superpowers/`, `scratch/`, `*.png`.
  Existing game-data blocks stay.

## 7. Staging and gates

Stage 1 — purge + tree + releases + licence (makes this repo publishable):
- G1 bundle backup exists and `git bundle verify` passes.
- G2 after purge: `git log --all --diff-filter=A --name-only` and
  `git rev-list --objects --all` return nothing for the five purged paths.
- G3 `git status` clean (only ignored dirs) and tree matches section 2.
- G4 release dirs sort v02…v22 lexically in intended order.
- G5 export gate: `tools/export.py --release v22-beam-clash` output is
  byte-identical to the pre-work `releases/v22-beam-clash/428113C2.pnach`
  (snapshot a copy before starting).
- G6 all 32 stayers run `--help` clean.
- G7 fresh clone into a temp dir shows exactly the intended tree; no purged
  path in any commit.

Stage 2 — split and migrate:
- G8 pcsxroo history contains the ps2ee/tool commits (graft verified by
  `git log --follow` on one moved file).
- G9 the 17 movers run `--help` clean from pcsxroo.
- G10 the 32 stayers run `--help` clean via the new seam; emulator-bound ones
  smoke-tested against a booted game (user-authorized emulator time).
- G11 export gate re-run (byte-identical).

Stage 3 — docs and tools index:
- G12 docs/tools.md covers all 49 tools with transport requirements; every
  previously undocumented BT3 tool has an entry.
- G13 README survives a stranger-read: no purged-file mentions, working links,
  correct credits, pcsxroo dependency stated.
- G14 link check: no dead references to `patches/`, `releases/latest/`, or
  moved `tools/*.py` paths anywhere in docs.

## 8. Open items for execution (not blockers for this spec)

1. pcsxroo is dirty (branch `fix/frame-advance-input`, untracked
   `bin/charged-full.png`) — untouched without explicit approval; migration
   lands on its own branch there.
2. Exact landing dir of the 17 CLI tools under `tools/pcsxroo/` — confirm
   against pcsxroo/AGENTS.md.
3. Whether the v1 gap deserves a placeholder line in releases/STATUS.md.
4. Emulator-bound smoke tests require PCSXROO + a booted BT3 disc — schedule
   the session.
5. filter-repo preserves authorship; a purged path that was a commit's only
   content may drop that commit — acceptable, noted in G2.

## 9. Stage 1 execution log (2026-09-12)

Gates passed:

- G1: bundle at `../pcsx2-bt3-60fps-pre-purge.bundle` (22 refs, verified).
- G2: five paths gone from all history and objects; 151 commits remain (one
  purge-only commit dropped, expected); all branches and 18 tags rewritten.
- G3: tree matches section 2; gitignore additions committed; the video draft
  was restored to disk as an ignored file.
- G4: release dirs sort v02…v22 with v06b in place.
- G5: `patch/428113C2.pnach` byte-identical to the pre-work v22 reference.
- G6: all 49 tools `--help` clean.
- G7: fresh `--no-local` clone shows exactly the intended tree, clean history
  and status; 3 branches + 18 tags.

Deviations and findings:

- filter-repo required `--force` in place (repo not a fresh clone; local-only,
  bundle backup verified — safe).
- One commit was purge-only and dropped (expected, spec 8.5).
- Tag hygiene deferred to the owner: tags v2–v9 still use old names while the
  dirs are now v02–v09; no v17–v22 tags exist; a `v1-60fps-input-fixed` tag
  exists with no v1 release dir; the history table in `releases/README.md`
  only lists v1–v3.
- A fresh clone's default branch resolves to the branch checked out at clone
  time; set `main` as default when creating the GitHub repo.

## 10. Stage 2 and 3 execution log (2026-09-12)

Stage 2 gates passed:

- G8: history-preserving graft merged into pcsxroo on `feat/ps2ee-migration`
  (off `fix/frame-advance-input`, which carries the agent tooling; `master`
  there is upstream-parity). 22 commits of ps2ee/tools history preserved,
  merge commit `a8d24e33e`.
- G9: 13 movers `--help` clean from pcsxroo.
- G10: all 35 stayers `--help` clean via the new seam (`bt3/` + sibling
  pcsxroo checkout).
- G11: export gate re-run, byte-identical.

Stage 3 gates passed:

- G12: `docs/tools.md` indexes all 48 tools with transport requirements.
- G13: README rewritten; the stranger-read caught `setup-pcsx2.py`'s new home.
- G14: no dead local references; `docs/findings.md` covered by its header note.

Deviations and findings:

- Allocation correction: `oscscan.py`, `writers.py` and `realclock.py` import
  `patchctl` (this project's group presets) and moved BACK to this repo.
  Movers are 13 (was 17); stayers are 35 (was 32).
- `savestate.py` moved with the library (`ramdiff` depends on it), as planned.
- The GameIdentity seam carries the layout constants (text/data bounds, gp,
  safe zone) alongside serial/CRC/ELF - the moving modules need them (disasm
  defaults, pnach validation, diff regions). Values stay in `bt3/game.py`.
- Generic config takes its identity from a `"GAME"` block in `local.json` or
  `config.bind()`; `bt3/config.py` binds programmatically and repoints
  `LOCAL_JSON` at this repo. `ee_ram_size` stayed a universal constant (32 MB
  is the PS2 spec, not per-game).
- pcsxroo's commit convention honoured: all pcsxroo commits carry
  `(AI-assisted)`.
- pcsxroo merge is the owner's call: `feat/ps2ee-migration` is ready to merge
  into `fix/frame-advance-input`; until it is, that branch must stay checked
  out there for the tools here to resolve `ps2ee`.

## 11. Remaining-calls resolution (2026-09-12)

- pcsxroo: `feat/ps2ee-migration` fast-forwarded into
  `fix/frame-advance-input` (nothing else had moved), branch deleted, the
  temporary extract remote removed. `fix/frame-advance-input` stays checked
  out, so the tools here resolve `ps2ee`. Both suites re-verified: 13 movers
  and 35 stayers `--help` clean. One swept-in screenshot (`bin/charged-full.png`,
  caught by an unscoped `git add -A`) was unstaged again; it remains in one
  commit of pcsxroo's local history.
- Tag hygiene: v2-v9 renamed to v02-v09 and v6-withdraw to v06b at their
  original targets; v17-v22 created at each release's cut commit (verified:
  tag == commit that added the release directory, the convention the existing
  tags follow). v1 stays tag-only, now stated in `releases/README.md`.
  Pre-existing deviation left untouched: the `v13-pursuit-stomp` tag sits on a
  later docs commit, not its cut commit - the owner's call whether to repoint.

# Tooling, the rig and the measurement method

Instruments, the 30fps oracle, and how a shipped group is A/B'd.

## Instrument notes for future agents

**Two measurement traps cost real time in this session. Both produce confident wrong
answers.**

1. **Whole-struct captures tear.** A fighter is 1408 words and PINE cannot read it
   atomically, so a sample tagged frame N can contain data from N+1. This produced
   (a) nine impossible "two X presses one frame apart", and (b) a completely bogus
   "+2 per frame" reading on counters that actually step +1 - dropped frames made
   consecutive samples two game frames apart. **Frame-precise conclusions require the
   narrow `--watch` mode** (a handful of words per sample). The wide `--trace` is for
   finding candidates only.
2. **Offsets are not unique across structs.** Scanning `.text` for `lw rX, 0x1470(rY)`
   found a global at `0x002FEC20` holding `0x80808080`, nothing to do with the fighter.
   Match the whole *idiom* instead (load / add immediate / store back to the same
   offset), or confirm the base register's provenance.

Other hard-won rules:

- **Arm captures on a real button press** (`--armed`). A fixed-timer capture is half over
  before the instructions have been read; the first 60-second trace caught one countdown
  in an entire minute for exactly that reason.
- **Save raw captures** (`--save`, then `tools/countdown.py`). Re-analysing offline beats
  asking the player to replay a session for every new hypothesis.
- **Verify a deploy by reading it back over PINE.** See the `extended` byte-write section:
  the patch was silently writing one byte per line for its entire existence.
- **`ps2ee/live.py` refuses branches and likely-branch delay slots.** Trust it. Hooking
  `FUN_001D3C10`'s `beql` entry would have zeroed every input counter instead of halving
  them, and hooking function prologues at random is what crashed the emulator earlier.
- **Revert anything the user has not confirmed.** Three effect experiments and the
  smoothing constant were all backed out; `tools/apply-live.py --check` plus a stock-value
  check on the experiment sites is how the tree was left clean.

## A/B-ing a shipped `patch=1` group on a live game (2026-08-25)

The aura fix is now confirmed by direct comparison, not just by "it looks right": with the
patch neutralised the user saw the 2x aura return, and restoring it brought the correct
speed back. **User-confirmed: "the patch definitely worked."**

Getting there needed a technique worth keeping, because the obvious approach does not work.

### You cannot disable a `patch=1` group by poking memory

`patch=1` means PCSX2 re-applies the group **every frame**. Writing the stock instruction
back over `00164888` succeeds - and is overwritten within two frames. Measured, not assumed.
Editing the pnach does not help either without a patch reload, which costs the battle.

### Jump over the hook from an address the cheat engine does not own

The cheat engine only rewrites the words the group lists. Everything else is ours. So hook
*earlier* in the same function and jump past the patched instruction entirely:

    00164880  j 000F0800          (was: sd $s5, 0x28($sp))
    00164884  sd $ra, 0x38($sp)   delay slot, runs as normal
    000F0800  sd $s5, 0x28($sp)   replay displaced
    000F0804  lw $s2, 0x38($s6)   what 00164888 held before the patch
    000F0808  addiu $s3,$s2,0x64  0016488C
    000F080C  ...bump a pass counter at 000F0830...
    000F081C  j 00164890          full update, unconditionally

`00164888` stays patched and keeps being re-applied; it is simply never reached.
`work/aurabypass.py` does this with `--off` / `--on`.

**The displaced instruction runs after the delay slot, not before it.** That reorder is only
safe here because `00164880`/`00164884` are independent register saves. Check that before
picking a hook site.

### Make the probe self-verifying

The trampoline bumps a counter so the state is a measurement, not an opinion:
**120 passes/sec at 60Hz** with the bypass in - two aura nodes, one per fighter, each
advancing every frame, which is exactly the original bug. With the patch in force it is 60.
A reading of 0 means the aura is not on screen and the test is telling you nothing - worth
checking before asking the user to judge anything.

## 2026-09-04 - PCSXROO: the emulator became scriptable

Every earlier session drove PCSX2 through PINE, which can read and write memory and
nothing else. Breakpoints meant asking the user to set them in the GUI and read the
registers back by screenshot; getting into a fight meant asking the user to play; testing
a patch meant a full quit and relaunch, because PCSX2 reads its cheat file only at boot.

`Documents/GitHub/pcsxroo` is a PCSX2 fork that exposes the whole debugger over a loopback
JSON socket. Read `docs/pcsxroo/agent-guide.md` there first. What it changes for this
project:

- **Breakpoints and watchpoints without a human.** `mc add --on write` plus the stop's
  `pc` and `ra` is the technique that solved this, and `tools/writers.py` wraps it.
- **Frame-precise capture.** `frame-advance 1` steps exactly one vsync, so a per-frame
  delta is a real per-frame delta. Every earlier capture polled a frame counter over PINE
  and lost frames on any host hiccup, which silently halves the quantity being measured.
- **`patch.reload` re-reads the pnach files**, so a patch experiment costs seconds instead
  of a reboot.
- **Input injection**, so the harness can create the situation it wants to measure - a
  launched opponent, a sustained flight - reproducibly.
- **Screenshots**, which are the only way to be sure the numbers describe the situation
  you think they do.

`ps2ee/roo.py` is the client. Three of its wrappers exist because the raw behaviour
silently corrupts experiments, and each cost a wrong conclusion before being found:

1. **`loadstate` pauses first.** A load into a running VM leaves the game executing while
   the reply comes back, and the number of frames lost that way varies per call. Two runs
   of one experiment then start from different states. Loading into a paused VM restores
   bit-identically - verified by loading three times and comparing positions.
2. **`input.release` only queues.** The hook that writes the pad runs on frames the VM
   executes, so a release issued while paused never lands. The *next* state load then
   starts with the previous test's button held for one frame, which is enough to throw a
   punch. `flush_input()` releases and advances, and it has to be called **before** the
   load, not after - the contaminated frame is the first frame after the restore. This
   produced a reference measurement 65% too large, once, silently.
3. **`screenshot` needs a backslash path.** A forward-slash path is accepted, reports
   `queued`, and no file ever appears.

**A bug in PCSXROO itself, found and fixed here** (branch `fix/frame-advance-input` in that
repo): `VSyncStart` calls `VSyncOnCPUThread` before `PollInputOnCPUThread`, and
`VSyncOnCPUThread` is where frame advance pauses the VM. The input hook returned early
unless the VM was Running, so injected input was dropped on the final frame of every
advance - and an advance of one frame is nothing but a final frame. `input set` followed by
repeated `frame-advance 1` therefore held the button for exactly zero frames, while the
same input over one bulk `frame-advance 120` worked. A stepped capture recorded the game
ignoring the pad and looked entirely plausible. Allowing `Paused` is safe: the hook's only
caller runs while the VM is executing, so it is never reached during an idle pause.

## 2026-09-04 - the 30fps oracle, mechanised

The game at 30fps is correct by definition, so the measurement is: the same save state,
the same scripted input, the same number of vsyncs, once with every compensation removed
and once patched. Equal vsync counts mean equal real time, which is what "twice as fast"
is a claim about.

`tools/patchctl.py` makes the "compensation removed" half possible without a reboot. Two
things had to be worked out:

- **`patch.reload` re-reads the pnach files but not the enabled list.** That list comes
  from the settings loaded at boot, so editing the game ini mid-session achieves nothing.
  Renaming a group in the pnach does: a group whose header no longer matches an enabled
  name is simply not applied. `patchctl` appends ` [off]` to disable.
- **Removing a patch does not undo it.** `patch=1` lines are rewritten every frame while
  active, and when the group goes away PCSX2 just stops writing - the last value it wrote
  stays in RAM. So disabling also has to put the original words back, taken from the boot
  ELF; addresses outside any ELF segment are the trampoline scratch zone, whose original
  content is zero. All 109 words verified by readback.

Because the ini's enabled list is frozen until a restart, it now carries the names of
groups that do not exist yet, so a new experiment does not cost a reboot.

The measurement tools:

| tool | question it answers |
|---|---|
| `tools/traj.py compare` | how far did it travel in the same real time? |
| `tools/traj.py ticks` | is this channel's *per-tick* step the same at both rates (uncompensated) or halved (already fixed)? |
| `tools/traj.py speed` | what is the speed, in units per second, at the same wall-clock offset? |
| `tools/speedtest.py` | the acceptance test: one ratio per situation, 1.00 correct, 2.00 the bug |

The `speed` verb earns its place. Everything else compares distances, and a distance is
the integral of the thing under test: two runs whose speeds match exactly still show
different distances if one entered a ramp a fraction of a second earlier, and a run that
is genuinely 20% slow looks fine over a window that starts later in the same ramp.

`tools/mkstate.py` builds the save states an A/B starts from. The launch itself runs at
whatever rate is under test, so it cannot be inside the measured window - the state has to
be cut afterwards, with the victim already in the air and its momentum baked in.

## 2026-09-08 - the EmuDeck install was running the working pnach

The user, after a session of confirmations: "I just booted up my PCSX2 emudeck
install, and everything is broken beyond belief."

It was, and it had nothing to do with any fix. The install was running
`patches/428113C2.pnach` - the **working** file - with every group in it enabled:

| group | what having it on does |
|---|---|
| `60FPS - animation rate` | superseded by `animation clock`. **Both on = QUARTER speed animation** |
| `60FPS - EXPERIMENT halve root motion` | deliberately breaks ground movement. That is what it is for |
| `60FPS - blast effect rate` | WITHDRAWN: gating skips the geometry rebuild, so the beam is not drawn |
| `60FPS - blast sequence rate` | WITHDRAWN: skips the controller step that SPAWNS the effects, so a charged blast renders nothing and deals no damage |
| `60FPS - state phase timers` | WITHDRAWN: the state 157 trap |

Quarter-speed animation, no beams, broken ground movement and a state trap, all
at once. Every one of those is a documented, deliberate hazard; they were simply
all switched on together.

### How, and why it went unseen for days

`deploy.py` enabled **every group in whatever pnach it was handed**:

    groups = args.only if args.only else [g.name for g in source.groups]

`export.py` exists precisely to drop those five, and `releases/latest/` has
always been correct. The working pnach had been deployed instead, at least as
far back as 2026-09-05 judging by `work/cheat-backups/`.

It went unseen because **every measurement in this project runs against
PCSXROO**, which reads a different cheats directory and a different per-game ini.
The dev instance was correct throughout; the user's actual install was not. Two
emulators, two configs, and only one of them was ever being tested.

Two guards now, both cheap:

- `config.NEVER_SHIP` holds the five names once. `export.py` drops them and
  `deploy.py` refuses to enable them, printing the `releases/latest/` command
  instead. `--only` still selects a subset; `--force-development` overrides.
- `patchctl --status` names any group missing from PCSXROO's own enable list,
  which is the mirror-image failure found earlier the same day.

### What the confirmations actually settled

`v13`, `v14` and `v15` all confirmed in play: the Lightning Attack after a Full Power
Smash, the Cell Perfect Barrier camera, and the mouths.

**The pre-fight intro mouths are fixed too**, which retires a wrong reading. That
row had said "not a speed problem" since the first defect list, on the strength
of the symptom alone - mouths that never move at all, rather than mouths that
stop early. It was never A/B'd, and it was wrong: same clip player, same 2.0 rate
a tick, and the track simply ran out before the intro's first line. The lesson is
the ordinary one - a symptom that looks qualitatively different is not evidence
of a different cause until something measures it.

Still open, and none of it touched by any of this: v12's input-timing flag, the
Galick Cannon fade, the ultimate's beam landing early, transformations running
long, the character-switch sky. The user also reports "some camera angles/speeds
seem off" - separate from the mouth work, and not yet characterised.

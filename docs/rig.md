# Driving the rig

Cold start to a measured A/B, and the traps that cost real time getting there.
Read this before touching the emulator. [`method.md`](method.md) says what the
method is and why; this says how to actually make the machine do it.

## Start

    ..\pcsxroo\bin\pcsxroo.exe launch "<path to the BT3 disc image>" --ready-timeout 120000
    ..\pcsxroo\bin\pcsxroo.exe status
    python tools/patchctl.py --status

`status` should say `running` and name the game. `patchctl --status` lists every
group and whether it is on. If the tools cannot find something:

    python -c "import sys; sys.path.insert(0,'tools'); import _bootstrap; from game import config; print(config.game_image(), config.pcsxroo_dir(), sep='\n')"

The rig's cheat file is `<pcsxroo>/bin/cheats/428113C2.pnach`. `patchctl`
rewrites it in place, renaming groups to `[name [off]]` to disable them, so it
is a comment-stripped copy of `wip/working.pnach` with identical patch lines.
**After editing `wip/working.pnach`, copy it over the rig's copy** or the next
measurement runs the old patch.

## Six traps, each of which cost an hour or more

**1. `screenshot` needs a Windows path with BACKSLASHES.** A forward-slash path
replies `queued: true`, reports the path back, and then no file ever appears.
Same directory, same VM, only the separator differs:

    pcsxroo screenshot "C:\path\to\shot.png"    # lands
    pcsxroo screenshot "C:/path/to/shot.png"    # silently never written

The write is also asynchronous, so poll until the file exists *and* stops
growing. `tools/` has no wrapper for this; the scratch helper pattern is in
[`findings.md`](findings.md) under 2026-09-16.

**2. A menu press must be held for about 8 frames.** `input press X --frames 3`
is under the menu's sampling rate: four presses out of five are simply not seen,
which looks exactly like a menu that ignores you. Use `--frames 8` with roughly
0.75s between presses and every press registers.

**3. Save state slots are 0-9 only, and this one bites hard.** `savestate --slot
10` exits **1** with `bad_args: slot must be between 0 and 9`. A script that
runs it through `subprocess.run(..., capture_output=True)` and does not check
`returncode` sees nothing and carries on - and `<pcsxroo>/bin/sstates/` very
likely already holds a `.10.p2s` from an older session, so the file you then
copy around is *someone else's scene*. That happened on 2026-09-16 and three
measurements were attributed to the wrong stage before it was caught.

**Always check the return code, and always confirm a new state by loading it and
looking at it.** One screenshot is cheaper than re-running the analysis.

To keep more than ten states, copy the `.p2s` files out of
`<pcsxroo>/bin/sstates/` into `work/state-backups/` and copy the one you want
back over a slot. Back up the slot you are about to overwrite first.

**4. `Roo.input_set` takes buttons as separate arguments, not a list.**

    roo.input_set("Square", "Up")        # correct
    roo.input_set(["Square", "Up"])      # bad_args: button names must be strings

**5. Input held from before the `Fight!` banner is ignored.** A held button that
was already down when control is handed over does nothing. An action test needs a
state cut *after* the banner, not at the match start.

**6. Screenshots need the VM running, and an armed breakpoint counts as
paused.** This one is in PCSXROO's own agent guide and is still worth repeating,
because a stray breakpoint makes every capture silently vanish.

## Getting to any scene

Until 2026-09-16 every A/B ran from a hand-made save state, which meant only
scenes someone had already saved could be tested. The menus can be driven over
pad injection, so that limit is gone. Any character, any stage, any mode.

From inside a battle, `Start` opens the pause menu:

    Continue Battle
    View Skill List
    COM Settings              <- "Stand" makes the opponent passive
    Reset standing position
    Return to Character Select
    Return to Main Menu

**`COM Settings` -> `Stand` is the clean oracle** this project always wanted: the
opponent stops acting, so a measurement is not perturbed by an AI that behaves
differently in the two arms. Several early measurements in this repo were noisy
for exactly that reason.

Leaving a battle asks `EXIT?` with **No** preselected - `Up` then `Cross`.

Character select is a **grid**, not a list: `Down` moves a whole row, so a
character is usually two or three presses away rather than twenty. Confirming a
character opens, in order, its form list, `Custom Select` (loadout), and
`Select Color`; `Cross` through all three takes the defaults. Then the same for
the opponent, and then **Map Select**, which is where the stage-specific reports
live.

To browse a long list cheaply, press and crop only the name band into one tall
strip rather than screenshotting the whole screen each time. `tools/menu.py`
does all of this:

    python tools/menu.py press Start Down Down Cross --shot pause
    python tools/menu.py strip Down 10 --band 0.62,0.80 --shot rows

The roster is **15 rows of 7**, and both axes wrap. Rows seen so far, in Down
order: Goku (Early), Goku (Mid), Goku (End), Goku (GT), Master Roshi, Captain
Ginyu, Frieza, Cell, Majin Buu, Bardock, Cooler, Pikkon, Demon King Piccolo,
Kid Goku, Password Character. Map Select has the same shape, six rows.

## Cutting a state worth keeping

The battle manager pointer (`game.battle.MANAGER`, `0x002FEB14`) is null outside
a fight. Polling it until it is non-null catches the **first frame the battle
exists**, which is what makes the opening seconds of a match testable:

    work/state-backups/rocky-cell-match-start.p2s     Cell 1st Form, Rocky Area - Evening, frame 0

Save with every group **off** so the snapshot carries the game's original words
and each arm can apply its own.

A state cut past the `Fight!` banner is what action tests need, and it is one
`frame_advance` away from the above - but cut it into a real slot, back up
whatever that slot held, and look at the result before measuring anything from
it. See trap 3.

## Running the A/B

The order is not negotiable, and getting it wrong produces a confident wrong
answer rather than an error:

1. `roo.loadstate(slot)`
2. `patchctl.apply(roo, groups, quiet=True)`
3. run

**Never load again after applying.** The save states were written while patched,
so a second load silently restores the patched words and the "unpatched" arm is
not unpatched.

**Always print the tick count and check it.** A correct run reports the
unpatched arm ticking half as often as the patched one over the same vsyncs:

    off:  180 vsyncs = 90 ticks
    full: 180 vsyncs = 180 ticks

If the off arm ticks 180, the A/B is fiction - usually a group name missing from
the rig's `[Cheats] Enable` list, which applies nothing and reports nothing.
`patchctl` warns about this; do not ignore the warning.

Presets take `preset+extra,groups`, so a single group can be added to the
shipped set without editing anything:

    python tools/patchctl.py --on full
    # in a script:  groups = PRESETS["full"] + ["60FPS - state phase timers"]

`60FPS - spare 1/2/3` are names the ini already enables that no group uses. A new
group given one of those names can be tested **without restarting the emulator**,
which otherwise costs a full boot per experiment.

## The three instruments

Beyond `patchctl`, `ratediff` and `shot`, three tools carry most of the work.

**`tools/lookup.py`** answers the ELF questions without booting anything:
`state 238` gives a state's handler, `callers 001E16C0` finds every `jal` to an
address, and `gp 6D80` prints a gp-relative word's value **and how many
instructions read it**. That last count is the one that matters: a constant with
exactly one reader can be halved in data, which is how gravity, the smash charge
and the stage animation were all fixed in one word each.

**`tools/animtrace.py`** traces a move by its beats. `fighter+0x974` is the
current animation id, and the scripted handlers advance by asking whether that
animation has finished rather than by counting ticks, so the ids ARE the beats.
Use it before a pixel score on anything cinematic: it is what proved the Great
Ape animation is not cut short, only rushed past.

**`tools/drift.py`** scores a group set by how far its picture drifts from the
30fps arm at fixed vsyncs. Always pass the reference preset twice - the second
copy must read 0.00, and if it does not, nothing else in the run means anything.
`--band` crops to a horizontal slice, which is the difference between measuring
a blimp and measuring two fighters standing in front of a crowd.

## Reading a rate scan

`ratediff.py` scores a quantity 2x when it covers twice the ground per second.
That is the right test for a position, an angle or a phase.

**It is the wrong test for a frame counter.** The patch compensates a counter by
doubling the count it is measured against, not by halving its step, so a
correctly fixed counter still reads 2x. The global frame counter at `00331D64`
reads 2x by design, and so does every tween the tween-duration group already
fixed. Only world quantities can be read straight off the report.

Check what a candidate belongs to before chasing it. `game.battle.resolve(roo)`
gives the fighter and model addresses for the current fight; anything outside
them is the stage, an effect, or the engine.

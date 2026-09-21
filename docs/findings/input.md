# Input timing

The input subsystem and the combat input counters.

## Input subsystem map (2026-08-22)

Located by save-state diffing with the game **paused** while holding X - pausing was the
user's suggestion and it is much cleaner than diffing during play, because almost nothing
else drifts between captures.

### The pad block

Base `0x00333800`, two pad slots at stride `0x1C0`:

| Offset | Address (slot 0) | Held X | Released | Meaning |
|---|---|---|---|---|
| `+0x01C` | `0033381C` | `817FBFFF` | `817FFFFF` | raw libpad word, **active low** (CROSS = `0x4000`) |
| `+0x028` | `00333828` | `000000FF` | `00000000` | pressure / pressed flag |
| `+0x148` | `00333948` | `00004000` | `0` | current buttons, active high |
| `+0x14C` | `0033394C` | `00004000` | `0` | previous buttons |
| `+0x150` | `00333950` | - | - | newly pressed = `current & ~previous` |
| `+0x154` | `00333954` | `00004000` | `0` | auto-repeat result |
| `+0x158` | `00333958` | `1` | `20` | auto-repeat countdown |
| `+0x19C` | `0033399C` | `20` | `20` | initial repeat delay, in frames |
| `+0x1A0` | `003339A0` | - | - | repeat rate, in frames |

`FUN_00122A38` (battle loop call **[9]**) is the pad update: it calls the libpad wrappers
`FUN_00296090` / `FUN_00295FB8`, normalises both analog sticks, folds stick directions
into the button mask as bits `0x10000`-`0x800000`, then computes the edge and repeat
state. It loops over both pads (`i < 2`, `puVar5 += 0x1C0`).

`FUN_002577B0` is the **auto-repeat timer**, not a double-tap detector:

```c
int AutoRepeat(int cur, int newpress, int *counter, int *prev, int delay, int rate)
{
    int out = 0;
    if (cur == *prev) {
        if (cur != 0) {
            if (--(*counter) < 0) { *counter = rate; out = cur; }
            goto end;
        }
        *prev = 0;
    } else *prev = cur;
    *counter = delay;              // 20 frames
end:
    return newpress ? newpress : out;
}
```

Both `delay` and `rate` are frame counts read from memory (`+0x19C`, `+0x1A0`), so menu
repeat runs twice as fast at 60fps. They are set through a setter at `FUN_002577F4`
(`sw $a0, -4($v0)`), which is a clean hook point if we choose to double them.

### FAILED EXPERIMENT - gating the pad update every other frame

Hooked call [9] (`0012BC64`) through a safe-zone trampoline so `FUN_00122A38` ran on
alternate frames only, leaving everything else at 60Hz.

**Result: no improvement to fighting input, and the pause menu became worse - double
speed and unusable.** Reverted.

Why it fails: skipping the update leaves `+0x150` (newly pressed) latched at its previous
value, so a single press is visible as a fresh edge on two consecutive frames and the
60Hz consumer acts on it twice. Slowing the *read* also cannot help a consumer that
counts frames itself - the parser still runs at 60Hz over a now-stale view.

**Conclusion: the input defect is in the consumers, not the pad read.** Any fix must
either slow the consumers' frame counting or widen their frame windows; it must not slow
the pad read.

`FUN_00122DB0` is the accessor other code uses (`FUN_001230A8(pad, DAT_00333948[pad*0x70], out)`),
and it has **zero direct callers** - dispatched indirectly, so the consumers cannot be
found by static xref. Finding them needs a different approach: a write-watch on the
move-buffer, or hooking `FUN_001230A8` and logging callers via `$ra`.

### Still open

- **Double-tap grab and quick sequences.** The move parser is frame-counted and has not
  been located yet. Next step: hook `FUN_001230A8` in the safe zone to record `$ra` into
  a scratch buffer, read it back over PINE, and identify the real consumers.
- **Menu auto-repeat.** Tractable right now by doubling `+0x19C` / `+0x1A0` via the
  `FUN_002577F4` setter. Worth doing as a standalone improvement.
- **Sprite / UV animation** (mouth movement, Kamehameha beam) still runs at double speed.
- **Intermittent 30fps dips**, believed inherent to the frame budget.

### Input API, traced by runtime caller logging

Static xrefs were useless here (the accessors have zero direct callers), so a logging
trampoline was hooked into each accessor: it writes `$ra` into a 64-entry ring at
`0x000F0210`, replays the displaced instruction and jumps back. Reading the ring over
PINE after a couple of seconds names the real callers. `tools/probe-loop.py` style, but
for call sites rather than call gating.

Three sibling accessors, each tail-calling `FUN_001230A8` (`return (mask & test) != 0`):

| Function | Reads | Meaning | Callers observed |
|---|---|---|---|
| `00122DB0` | `+0x148` | `IsHeld(pad, mask)` | **25**, all inside `FUN_002574F0` |
| `00122DE0` | `+0x150` | `IsNewPress(pad, mask)` | **0** |
| `00122E10` | `+0x154` | `IsRepeat(pad, mask)` | **0** |

So the two edge-detecting wrappers are dead code. Everything goes through `IsHeld`, and
only `FUN_002574F0` calls it.

`FUN_002574F0(pad)` is the **input remapper**: it queries ~25 raw bits and folds them into
the game's own action bitmask (CROSS `0x4000` -> internal bit 9 `0x200`, and so on,
including the four analog-stick directions at `0x100000`-`0x800000`). It then maintains
the internal input state at `0x00333988 + pad*0x38`:

```c
prev = internal_cur[pad];
internal_cur[pad]      = cur;
internal_newpress[pad] = cur & ~prev;
internal_repeat[pad]   = AutoRepeat(cur, cur & ~prev, &counter, &prev2, delay, rate);
```

| Address | Meaning | Readers |
|---|---|---|
| `00333988` | internal current | 3 |
| `0033398C` | internal newly-pressed | **42** |
| `00333990` | internal auto-repeat | 3 |
| `0033399C` / `003339A0` | repeat delay (20) / rate (1) | the repeat timer |

### FIXED - menu auto-repeat

`FUN_002577F8` is `SetRepeat(delay, rate)`. Hooking its entry to double both arguments
restores menu scrolling to its real-time speed at 60fps. Confirmed by the user: "whatever
you did last fixed the menu". Now shipped in the patch as the third group.

### Still unsolved - combat input

Quick-succession moves (double-tap X grab, combo strings) remain unreliable. What is now
ruled out:

- It is **not** the pad read rate - gating that made things worse, not better.
- It is **not** `IsNewPress`/`IsRepeat` - those wrappers are never called.
- It is **not** the auto-repeat timer - that is fixed and only affected menus.

The 42 readers of `internal_newpress` are mostly UI code (`00119FB4`-`0011E1E8`), with a
few in gameplay ranges (`002145D4`, `0022F9F8`, `0025B1DC`, `002BE348`). None of them
consult a frame-counted history at the point of read, so the double-tap window must live
further in, in per-character move state rather than the shared input block.

Next approach if this is picked up again: put the logging trampoline on the gameplay-range
readers to find which one runs during a fight, then look for a countdown in the character
struct that resets on a press - the same shape as the `+0x158` repeat counter, but
per-fighter.

## SOLVED - combat input timing is 128 frame counters (2026-08-22)

Confirmed by the user: "it works! input is better".

Combat never reads the shared input globals at `0x00333988` - it keeps its own
per-fighter copy. `FUN_001D4A70` maintains it at **`fighter+0x570`**:

| offset | meaning |
|---|---|
| `INPUT+0x000` | raw pad buttons, copied from `pad+0x148` |
| `INPUT+0x1CC` / `+0x1DC` | current mask A / B |
| `INPUT+0x1D0` / `+0x1E0` | previous mask A / B |
| `INPUT+0x1D4` / `+0x1E4` | newpress = `cur & ~prev` |
| `INPUT+0x1D8` / `+0x1E8` | released = `prev & ~cur` |

That is why every reader found on the shared globals turned out to be UI.

### The timing system

`FUN_001D4A70` ends by calling `FUN_001D3C40(ring, cur, newpress, released)`
twice - `fighter+0x780` for button set A, `fighter+0x820` for set B. Each ring
is 4 x 32 bytes, and `FUN_001D3C40` loops over all 32 button bits calling
`FUN_001D3C10` four times per bit:

| ring slot | condition | meaning |
|---|---|---|
| `+0x00+bit` | `cur & bit` | frames held |
| `+0x20+bit` | `!(cur & bit)` | frames released |
| `+0x40+bit` | `!(newpress & bit)` | **frames since last press - the double-tap window** |
| `+0x60+bit` | `!(released & bit)` | frames since last release |

```c
void FUN_001D3C10(int cond, signed char *counter)   // 12 instructions
{
    if (cond == 0) { *counter = 0; return; }        // beql, reset in the delay slot
    if (*counter < 100) *counter += 1;              // saturating
}
```

**128 counters, all counting frames.** At 60fps every button window - double
taps, charges, hold detection, combo links - expired in half its real time.
That is why input felt uniformly unresponsive rather than one move being
broken, and it is exactly the frame-window theory, confirmed.

### The fix

One hook. `FUN_001D3C10`'s increment path only runs on even frames, restoring
the original 30Hz counting rate. The **reset is deliberately left alone** so
"pressed this frame" still reads zero immediately - halving that too would have
added a frame of input latency.

Hook at `001D3C18` (`lb $v0, ($a1)`), resume at `001D3C20`.

**Do not hook `001D3C10` itself.** It opens with `beql $a0, zero` whose delay
slot is `sb $zero, ($a1)`. A likely branch executes its delay slot only when
taken; a plain `j` always executes it, so hooking the entry would zero every
counter on every call instead of halving it. `live.delay_slot_hazard()` now
refuses this, and refuses displacing any branch or jump.

### How it was found

Offset-scanning `.text` for struct field offsets produced only false matches -
`0x1470` resolved to a global at `0x002FEC20` holding `0x80808080`, nothing to
do with the fighter. **Offsets are not unique across structs.** What worked was
following the code: `FUN_001DC2A0` (`GetPadForFighter`) led to the fighter's own
input block, whose update function ends in the history recorder.

### Capture technique notes

- A whole-struct read is **1408 words and not atomic**. Samples tagged frame N
  can contain data from N+1, which showed up as nine impossible "two X presses
  one frame apart". Frame-precise conclusions need the narrow `--watch` mode
  (a handful of words per sample); the wide trace is for finding candidates.
- Arm a capture on a real button press. A fixed-timer capture is half over
  before the instructions have been read - the first 60-second trace caught one
  countdown in a whole minute for exactly that reason.
- Save raw captures. Re-analysing offline beats asking the player to replay the
  session for every new hypothesis.

## 2026-09-21 - issue #18, the defensive windows: six countdowns in FUN_001DFFE0

#18 predicted that every one-tick input window SuperCombo describes - Defensive
Vanish, Z-Counter, the vanish window that shrinks with health - is half as long
in real time at 60fps. It is, and they share one function.

### A scene where the opponent attacks on demand

Training's COM can stand or fight on its own schedule, neither of which a
window sweep can use. **Duel → 1P vs 2P** can: PCSXROO drives pad 2 as well as
pad 1 (`input.set` takes `pad: 1`), and a versus match has no health regen.
`work/state-backups/rocky-vs2p-cell2-near-gohan.p2s` is Cell 2nd Form 12 units
from Ultimate Gohan. Pad 2 holds Square for 20 vsyncs, a level-1 smash (state
75), which lands on P1 at v32 (state 196). Pad 1 taps a button for 2 vsyncs, one
vsync later each run.

### Measured

| defence | 30fps | v24 | v24 + `[60FPS - defence windows]` |
|---|---|---|---|
| Circle (vanish, state 32) | hit-10 … hit-3: **8 vsyncs** | hit-5 … hit-2: 4 | hit-9 … hit-2: **8** |
| Up + Square (Z-Counter, states 43/45/57/139) | hit-4, hit-3: **2 vsyncs** | hit-2: 1 | hit-3, hit-2: **2** |

The v24 and fixed arms carry `smash charge` and `meter economy` so the attacker
throws the same level-1 smash; on v24 alone the same hold charges a stronger one
(#17). The window sits one vsync later relative to the hit because a 60fps press
registers on the next tick rather than up to one vsync after it.

### The mechanism

The vanish is queued in `FUN_001E12D0` by flag `0x76`, which the hit resolver
`FUN_001C8580` raises when `defender+0x1068 > 0` at `001C863C`. `FUN_001DFFE0`,
once a tick per fighter, owns that counter and five siblings:

| counter | armed by | to | rest |
|---|---|---|---|
| `+0x1068` | button 0x27 (vanish) | 2, 3 or 4 by health (`FUN_001CEE90`) | -30 |
| `+0x106C` | button 0x27 | 2, or 4 with flag 0x138 | -30 |
| `+0x1070` | button 0x26 | 1 | -30 |
| `+0x1074` | button 0x2B, with state bit 0x20 | 5 | -15 |
| `+0x1078` | button 0x27 | 5 | -30 |
| `+0x107C` | button 0x27 | 2, or 4 with flag 0x138 | -30 |

Each counts `addiu v0,v0,-1; slti v1,v0,rest` every tick. A press arms a window
only while the counter is below its rest value; a press while it is not (inside
the window or its cooldown) sets it to -1, the game's anti-mash rule.

### The fix, and the trap in it

The first version made every decrement net to zero on odd ticks and produced an
alternating window: vanish on hit-9, -7, -5, fail on hit-8, -6. At rest the
counter sits at -30 and relies on dropping to -31 each tick to re-arm; held at
-30 on odd ticks, a press there took the "pressed during cooldown" branch and
killed the window. The helper therefore counts every tick when the value is at
or below rest (`slti at, v0, rest+1; movn t0, zero, at`), and on even ticks
only inside the window and its cooldown.

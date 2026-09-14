# v01 - 60fps battles, with input timing fixed

| | |
|---|---|
| Tag | `v01-60fps-input-fixed` |
| Date | 2026-08-22 |
| Built on | the stock game, and the 60fps patch already circulating for BT3 |
| Groups | 4 (25 patch lines) |
| Confidence | Confirmed working by the user; every group verified live over PINE |

## What it changed

The first working 60fps battle patch.

| group | what it does |
|---|---|
| `60FPS - battle` | the one word that makes battles run at 60fps, at `0012BCE4` |
| `60FPS - animation rate` | halves every animation playback rate written through the setter `FUN_001C44F8` to `entity+0xC80` |
| `60FPS - input repeat timing` | doubles the menu auto-repeat delay and rate in `SetRepeat` (`002577F8`) |
| `60FPS - input timing` | runs the increment path of the 128 combat input counters (`FUN_001D3C10`) on even frames only |

Game speed, animation, menus, grabs, combos and quick-succession input were all
correct at 60fps.

## What was discovered

- **Why the circulating 60fps patch failed.** It halved `001DCB40`, one caller of
  the animation rate setter, and left every other rate at its 30Hz value. BT3
  animations are authored at 60Hz and the 30Hz loop advanced them 2 units a tick,
  so callers pass 2.0 and 3.0; hooking the setter itself fixed every animation at
  once. Only four instructions in all of `.text` touch `entity+0xC80`.
- **Combat input is 128 frame counters.** Combat keeps per-fighter input state at
  `fighter+0x570`, and `FUN_001D3C40` maintains, for each of 32 button bits,
  frames-held, frames-released, frames-since-press and frames-since-release. Every
  button window in the game - double taps, charges, hold detection, combo links -
  is measured against them in frames, so at 60fps they all expired in half their
  real time. Only the increment path is gated: the reset path still runs every
  frame, so a press registers on the frame it happens and no latency is added.
- **The menu input API**, traced with a runtime caller-logging trampoline because
  the accessors have no static cross-references: `IsNewPress` and `IsRepeat` are
  dead code, and all input flows through `IsHeld` into the remapper
  `FUN_002574F0`, which keeps the action masks at `0x00333988`.
- **`extended` writes one byte.** Until this version the pnach wrote a single byte
  per line: `extended` selects the raw PS2 cheat format, where the top nibble of
  the address is a size selector. The stride word survived only because it
  differed from stock in its low byte; both trampolines were never assembled, and
  their hook sites were corrupted - the animation setter stored to `entity+0xC10`
  instead of `+0xC80`. It looked fine because the milestone had been validated over
  PINE, which does real 32-bit writes. **Live-tested is not deployed-tested.**
  Every line has been a `word` write since, and the validator now models the size
  nibble.
- The one defect left at this point: **airborne motion at 2x** - air idle,
  knockback, falling, ki blast and beam travel. Everything grounded was correct.

## Corrected later

- This version's notes called `0012BCE4` the battle loop's stride. v02 established
  it is the delay slot of `jal 0x102060`, the end-of-frame present, whose argument
  is a vblank count: the engine has no timestep at all.
- Earlier release documentation said v01 had "the ki aura correct". It did not.
  The aura fix landed in v02, on 2026-08-24.

## Before v01

Two earlier states were tagged as milestones. They are folded into this note:

| commit | date | state |
|---|---|---|
| `3cc3423` | 2026-08-22 | first 60fps battle patch at correct speed: `battle` and `animation rate` |
| `561b1cc` | 2026-08-22 | combat input timing fixed - the same four groups v01 ships, byte for byte |

v01 predates the release directories, so its patch is the working pnach of the
day. All four of its groups shipped.

## Get this version

    git show v01-60fps-input-fixed:patches/428113C2.pnach > 428113C2.pnach

# The match clock

The battle's two clocks, the Duel Time limit and the end-of-match check.

## 2026-10-09 - issue #133: a timed match runs out in half its time

Every rig scene before this one had Duel Time at ∞, so the countdown had never
been measured. Set to 60 (Duel → Battle Settings → Duel Time), the full test
build showed each second for 30 vsyncs instead of 60.

### The clock

`FUN_00216EF8(clock)` adds one tick to a clock:

| offset | field |
|---|---|
| `+0x0` | calls so far |
| `+0x4` | hours, capped at 9:59:59.999 |
| `+0x6` | minutes |
| `+0x8` | seconds |
| `+0xA` | milliseconds: each call adds 34, 32, 34 in turn from a table at `002F1AD8`, so three calls make 100 ms and one call is 1/30 s |
| `+0xC` | seconds left, written by `FUN_00217090` |

`FUN_00217090` ticks two clocks in a row, `*(gp-0x5738)+0x118` and then the
time-limit clock at `+0x108`. When a limit is set (`FUN_0012AB90` false), it
compares `minutes * 60 + seconds` with the limit from `FUN_0012AB58` (a table at
`002C3480` indexed by the setting), writes the seconds left to `+0xC`, the
number on the HUD, and returns 1 once the limit is reached.

Its only caller is `00217F6C` in `FUN_00217EF0`, the battle's per-tick
end-of-match check. Time up stores 2 in the second word of its result record
(`FUN_00127008()`); the KO checks follow in the same function. `FUN_00216EF8` has no other caller, so these two clocks are
all it serves.

In the rig scene (`work/state-backups/rocky-goku-early-timed60-vs-com.p2s`) the
time-limit clock is at `0187A528`, found by snapshotting RAM a second apart and
keeping the words that changed by the same amount each time.

### The fix

`[60FPS - match timer]` points the `jal` at `00217F6C` at a wrapper at
`000F2140`: on an even tick of the frame counter (`00331D64`) it jumps to
`FUN_00217090`; on an odd tick it returns 0, "time not up", without touching
the clocks. They then advance 30 times a second with the same 34/32/34 ms steps
as at 30fps.

| from the rig scene | 30fps | 60fps before | with the group |
|---|---|---|---|
| vsyncs per shown second | 60 | 30 | 60 |
| clock calls over 300 vsyncs | 150 | 299 | 149 |
| time up, after setting 0:55 | v300 | v150 | v299 |

300 vsyncs after time up, the 30fps arm and the arm with the group both show
the loser's screen.

The other way to fix it, halving the step inside `FUN_00216EF8`, needs a
six-entry millisecond table (17, 16, 17, 17, 16, 17) for the same result, and
touches the shared clock routine instead of one call site.

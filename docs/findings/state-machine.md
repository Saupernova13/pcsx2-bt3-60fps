# The fighter state machine and the stuck loop

Phase timers inside fighter states, and the state 157 trap.

## 2026-09-07 - the stuck loop: what is actually known, and what was misread

The user reported Goku "bugging out" in a loop, and says it has happened a few
times. Observed directly on screen, not inferred.

### Established

| | |
|---|---|
| Fighter state | **157**, handler `FUN_001E6DC8` from the table at `002C4980` |
| Pending state | `0xFFFFFFFF` - nothing queued, so there is no transition to take |
| Pad | `0x00000000` on every sample - **no button held**, so not a stuck injected input |
| Animation | still cycling; the game ticks normally at 60/s. Not a freeze, a trapped state |
| Opponent | off camera entirely |
| Recovery | reloading a save state clears it completely |

### Misread, and worth recording as a caution

`fighter+0x3D8` read 0 and never advanced, and this was called the bug. **It is
not.** The same field reads 0 in a perfectly healthy idle (state 11). A zero
there carries no information at all, and the reading was made because a zero was
wanted, not because it distinguished anything. Any future use of that field as
evidence has to compare it against a healthy state in the same situation first.

### Not established

The cause. Two facts sit next to each other and neither implies the other:

- `001E6F40` - one of the 22 gated sites in `[60FPS - state phase timers]` -
  lies inside the range of `FUN_001E6DC8`, the handler he is trapped in.
- Removing that group live did **not** free him.

The second does not clear the group. Restoring an instruction cannot rewind a
state machine that has already parked, which is the same lesson the withdrawn
flash-duration change taught an hour earlier: **the bad state is in RAM, and
code changes do not undo it.** Whether the gate is what puts him into 157 with
no pending state can only be answered by reproducing from a clean state, with
the group on and off.

### The reproduction that is needed

The trap was reached during ordinary play, so the sweep oracles - a held charge
and a mashed rush - do not cover whatever leads into it. What is needed is the
sequence of moves the user was performing. State 157 is not one of the states
this project has identified (264 = ultimate, 271 = held Super Kamehameha), so
naming it is the first job.

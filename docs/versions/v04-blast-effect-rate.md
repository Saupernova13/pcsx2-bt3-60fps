# v04 - blast effect rate (withdrawn)

| | |
|---|---|
| Tag | `v04-blast-effect-rate` |
| Date | 2026-09-06 |
| Built on | [v03](v03-blast-hit-cadence.md) |
| Groups | 15 (189 patch lines) |
| Confidence | **DO NOT USE** - withdrawn in v06: this group deletes the beam |

## What it changed over v03

Added `[60FPS - blast effect rate]`.

A ki blast is drawn by two effect-node classes, the beam core (descriptor
`002C3EF0`) and the flare (`002C40F0`). Each update steps half a dozen coupled
per-tick channels - start delay, emit countdown, the geometry cadence that drives
the segment builders, lifetime, stagger and fade. This gated the whole update to
every other tick by ORing frame parity into a skip branch both classes already
have, the same shape as the ki aura and particle groups.

## What was discovered

- **v03's fix was real but invisible.** It changed when damage was applied, not
  anything drawn, and the reported symptom was the blast itself looking rushed.
- The channels are compared against each other, so scaling any one constant does
  nothing - which is why every single-site test had come back clean.
- A blast can be timed by its damage schedule rather than by the screen, a far
  more reproducible clock.

## Evidence

By group toggle in one session, the flash went from 12 vsyncs to 24 against the
30fps game's 30, and recovered its two-humped charge-then-fire shape. Damage, hit
count and hit cadence byte identical.

## Why it is withdrawn

Gating these updates also skips the per-frame **rebuild of the beam's geometry**.
The user reported exactly that: the charge ball never appeared, the output beam
never rendered, and a half-built effect stayed stuck to the character's hands
because its lifetime never ran out. See v06.

## Get this version

    git show v04-blast-effect-rate:releases/v4-blast-effect-rate/428113C2.pnach > 428113C2.pnach

# v07 - the sequence gate restored

| | |
|---|---|
| Tag | `v07-blasts-fixed` |
| Date | 2026-09-06 |
| Built on | [v06](v06-blast-effect-duration.md) |
| Groups | 16 (204 patch lines) |
| Confidence | Superseded - the gate it restored kills charged blasts (v08) |

## What it changed over v06

Restored `[60FPS - blast sequence rate]`.

## What was discovered

- The rendering damage reported against v05 was **entirely** `blast effect rate`.
  Both groups had shipped together, so both had been withdrawn.
- Measured on its own, the sequence gate appeared to cost the beam nothing: the
  Super Kamehameha was on screen 0.6s..2.9s with it and without, against the 30fps
  game's 0.6s..3.0s, and it moved the ultimate's camera cut from 1.4s to 2.0s
  against a target of 2.1s.
- **Blaming the wrong half of a pair** is what happens when two changes ship
  together and only the pair is measured.

## Corrected later

The verdict that the gate was innocent was wrong. It was cleared on an uncharged
tap of the move, which never exercises the charge path. See v08.

## Get this version

    git show v07-blasts-fixed:releases/v7-blasts-fixed/428113C2.pnach > 428113C2.pnach

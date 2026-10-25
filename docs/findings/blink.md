# Faces: eye blinks

Newest sections at the bottom.

## 2026-09-28 - issue #90: the blink timer counted 30Hz ticks

Found by the per-tick hunt on Goku's Kamehameha and the match-start state: two
words at `009212F8` and `00921368` counting down by 1 a tick in both arms. Over
900 idle vsyncs (save state 6) each ran out every 246-338 vsyncs at 30fps and
every 111-168 at 60fps. A write watch lands in `FUN_0024EB70(model, face)`,
called for each model from `FUN_0024F428` at `0024F458` when the face
(`model+0x1664`) has bit 0 of `+4` set; bit 1 runs the mouth instead.

    flags = model+0xA40
    if flags & 0x04000000:  face+0x10 = face+0x14 if in range, else 0   (eyes animated)
    elif flags & 0x08000000: face+0x10 = 1                              (eyes shut)
    else:
        if face+0x08-- < 0:
            face+0x0C = rand() % 3 + 3        blink length, ticks
            face+0x08 = rand() % 90 + 90      next blink, ticks
        face+0x10 = 1 while face+0x0C counts down to 0, else 0

The flag at `face+0x10` is read at `0024F900` to pick the eye image. Forcing it
to 0 in code on a knocked-out Ultimate Gohan, whose eyes the KO animation holds
shut through the first branch, changes only the pixels of his eye. On Cell 2nd
Form it changes nothing: not every model has a blink image.

The random branch now runs on even ticks only. The wrapper at `000F1AF0` is
entered in place of the `bnez` at `0024EBD0` - whose delay slot, `v0 = 1`, still
runs - checks the shut-eyes flag itself and takes that path every tick, and on
odd ticks returns without writing `+0x10`, so the eye image holds for two
vsyncs a tick and `rand()` is called as often as at 30fps. The animated-eyes
branch comes before the hook and is untouched. `[60FPS - mouth clock]` hooks
the mouth tracks in `FUN_0024ECBC` and `FUN_0024F264`, not this function.

| Save state 6, 30 seconds of idle, per face | 30fps | 60fps before | 60fps with the group |
|---|---|---|---|
| blinks | 6-7 | 13 | 7 |
| blink length | 6, 8 or 10 vsyncs | 3, 4 or 5 | 6, 8 or 10 |
| gap between blinks | 220-342 vsyncs | 92-178 | 204-324 |

The timings are random, so the gaps are compared as ranges, not blink by blink:
the same seeds are not drawn in the two arms.

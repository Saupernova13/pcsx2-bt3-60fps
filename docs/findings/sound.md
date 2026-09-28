# Sound: voice line cooldowns

Newest sections at the bottom.

## 2026-09-28 - issue #86: voice cooldowns counted 30Hz ticks

Found by recording the RAM that changes at every vsync after Krillin's 7-hit rush
on Ultimate Gohan (save state 3, `Square` tapped 7 times, 16 vsyncs apart), in
both arms, and keeping words whose values are the same per tick in the two. With
every open fix on, one fighter word came out besides frame bookkeeping and the
health bar's shake (issue #84): Gohan's `+0x145C`, counting 15 down to 0 a tick.

A write watch lands in `FUN_001DC918(fighter)`, called once a tick from the
fighter update at `001C1C24`: it counts 57 words at `fighter+0x1454` down by 1,
stopping at 0. They are the cooldowns of the fighter's voice categories, set by
`FUN_001DC738(fighter, category)`:

    if cooldown[category] > 0: return                     001DC788
    entry = table[category]   *(*(gp-0x575C)+0x28), 8 bytes: first clip,
                              clip count, seconds
    play a random clip of the category, not the last one played (fighter+0x1370)
    cooldown[category] = (int)(entry.seconds * 30.0)       001DC85C, 001DC878

So a category plays again only after its table time in 30Hz ticks. The table
holds 0.5 s for categories 0-7 and 11, 0.4 s for 12, 1 s for 8, 9, 13 and 27,
3 s for 37, and 0 for the rest. `FUN_001DC950`, which plays the same table
without a cooldown, has no timer.

Write and read watches over both fighters' arrays through a rush string and two
ki blasts saw only `001DC878` and `001DC92C` write them and only `001DC788` and
`001DC920` read them. The 30.0 is an immediate used by this multiply alone, so
it becomes 60.0.

| Save state 3, every open fix on | 30fps | 60fps before | 60fps with the group |
|---|---|---|---|
| a 0.5 s cooldown | 30 vsyncs | 15 | 30 |
| the 0.4 s cooldown (category 12) | 24 vsyncs | 12 | 24 |
| clips played over the 7-hit rush | 4, at v61 v97 v117 v131 | 5, Gohan's category 0 again at v77 | 4, at v61 v97 v117 v131 |

The 7-hit rush plays the same moves in every arm, so its clip counts compare
directly. A denser string, 10 rush taps 12 vsyncs apart, does not: the presses
land on different ticks at 30 and 60fps and the fighters' moves diverge, so only
the cooldown lengths are compared there.

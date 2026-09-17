# Glossary: game mechanics by their proper names

The docs use SuperCombo's names for BT3 mechanics
(`https://wiki.supercombo.gg/api.php`, see [`rig.md`](rig.md)). Older text and
**patch group names** used casual terms. Group names are not renamed: players
enable groups by name, so a rename would silently switch a fix off.

| SuperCombo name | Old term in this repo | Groups that still use the old term |
|---|---|---|
| Full Power (Level 3) Smash Attack | heavy smash | - |
| Lightning Attack (the `Circle` hit of Dragon Smash) | pursuit stomp, Circle pursuit | `60FPS - pursuit timing` |
| Hard Knockback | knockback flight | `60FPS - knockback flight` |
| Rush Struggle | rush struggle | `60FPS - rush struggle` |
| Beam Struggle | beam clash | `60FPS - beam clash` |
| Ultimate Blast | ultimate, ultimate's blast | - |
| Smash Attack charge levels 1-3, Perfect Smash | smash charge | `60FPS - smash charge` |
| I Might Die This Time. (Final Form Frieza, Blast 2) | Frieza's rocks | `60FPS - blast object travel` |
| Super Kamehameha (Majin Buu, `L2`+`Up`+`Triangle`) | Buu's charged blast | `60FPS - beam object travel` |
| Flame Shower Breath (Majin Buu, `L2`+`Triangle`) | Buu's breath | - |
| Grenade: Rush Ki Blast (tapped) and Smash Ki Blast (held), Hercule | Hercule's ki blast | `60FPS - thrown object rate` (PR #26) |
| Ki Charge (`L2`), Max Power Mode | ki charge | `60FPS - meter economy`, `60FPS - max power charge` (PR #16) |
| Blast 1 stat boosts, After Image Strike | buffs | `60FPS - buff duration` (PR #25) |
| Paralysis (Paralyzed state) | - | `60FPS - paralysis` (PR #30) |
| Solar Flare lock-off | - | `60FPS - solar flare` (PR #33) |
| Option anti-repetition system, hit counter | - | `60FPS - combat timers` (PR #35) |

Controls, from SuperCombo: `Square` attack, `Triangle` Ki Blast, `Cross` dash,
`Circle` guard, `R1`/`R2` ascend/descend, `R3` transform, `L2` Ki Charge,
`L2`+`Circle` Blast 1 (`Up` for the second), `L2`+`Triangle` Blast 2
(`Up` for the second, `Down` for the Ultimate Blast).

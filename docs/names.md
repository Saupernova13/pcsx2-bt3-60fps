# What the owner calls it

The owner often names mechanics by what they look like. This table maps those
names to what each thing is in the game, using SuperCombo's names where the wiki
has one, and to the patch group that fixes it. A group `x` here is
`[60FPS - x]` in the pnach. [`glossary.md`](glossary.md) goes the other way,
from SuperCombo's names to this repo's old terms.

| You say | It is | Fixed by / tracked in |
|---|---|---|
| ki aura, the aura's sprite animation | The aura around a fighter, which grows with Ki Bars (not a sprite) | `aura update rate`, `particle update rate` |
| ki charging, ki draining, 5 bars of ki | Ki Charge (`L2`) and Ki Bars | `meter economy` (PR #16) |
| max power, the blue bars | Max Power Mode | `meter economy`, `max power charge` (PR #16) |
| blast stock, the gold number | Blast Stock: pays for Blast 1s and transformations | regen not measured |
| buffs | Timed Blast 1s: stat boosts, After Image Strike | `buff duration` (PR #25) |
| blasts, ki blasts like a Kamehameha or Galick Gun | Blast 2 (`L2`+`Triangle`, `Up` for the second) | `blast hit cadence`, `blast effect duration` |
| ult, ultimate attack | Ultimate Blast (`L2`+`Down`+`Triangle`, in Max Power Mode) | same, plus `camera pacing` |
| regular ki blast, tap Triangle | Rush Ki Blast; held Triangle is a Smash Ki Blast | `projectile travel` |
| Hercule's rocks, grenades | Grenade: Hercule's Rush and Smash Ki Blasts | `thrown object rate` (PR #26) |
| Frieza's rock attack | I Might Die This Time. (Final Form Frieza's Blast 2) | `blast object travel` |
| Buu's charge blast | Super Kamehameha (Majin Buu, `L2`+`Up`+`Triangle`) | `beam object travel` |
| Buu's breath | Flame Shower Breath (Majin Buu, `L2`+`Triangle`) | `beam object travel` |
| heavy smash, hold Square | Smash Attack; flashing white means a Full Power (Level 3) charge | `smash charge` (PR #17) |
| frame-perfect smash release; the white flash | Perfect Smash: release at the exact moment Level 3 is reached, which the white flash marks | issue #6, PR #17 (`smash charge`, `charge flash`) |
| guard broken | Guard Crush; the exhausted state after it is Fatigue | not measured |
| sending them flying | Hard Knockback | `knockback flight` |
| stomp, teleport above them | Lightning Attack (`Circle` during a Dragon Smash) | `pursuit timing` |
| rush attacks colliding, spinning the sticks | Rush Struggle | `rush struggle` |
| beam clash | Beam Struggle | `beam clash` |
| hovering idle in the air | The airborne idle's bob (no wiki name) | `hover bob` |
| falling, gravity | Vertical airborne motion | `gravity`, `airborne vertical` |
| fade to white (Final Galick Cannon) | The fullscreen fade service | `screen fade` |
| mouth movements | Face tracks in cut-ins and intros | `mouth clock` |
| camera in attack animations (Perfect Barrier) | The scripted camera in Blast 2 and Ultimate Blast cut-ins | `camera pacing`, issue #21 |
| auto taunt when idle | Idle taunt | issue #12, PR #14 |
| speed lines (Hercule's Present Bomb) | Speed-line effect | issue #8 |
| World Tournament helicopter, blimp | Stage props | issue #9, PR #19 |
| desert wind | Rocky Area stage wind | issue #11 |
| transformations (Cell, Vegeta (Scouter)'s Great Ape) | Transformation (`R3`, costs Blast Stock) | issues #7, #10 |

`effect rotation` is the spin of aura and effect swirls. It is not the aura's
playback speed; that is `aura update rate`.

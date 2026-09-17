# Widescreen

The widescreen model and every aspect group.

## 2026-09-08 - widescreen retargeted from 16:9 to 19.5:9

The user's install runs PCSX2's own `[Widescreen 16:9]`, from
`resources/patches.zip`. They asked for the same thing aimed at the Galaxy S24
Ultra's 3120x1440 panel - 19.5:9, or 2.166667.

The stock patch is three words, and the third gives the rule away:

| address | stock (4:3) | 16:9 | what it is |
|---|---|---|---|
| `002FE4CC` | 1.166667 | 1.555167 | projection scale, 7/6 |
| `002FE594` | 298.6667 | 398.1227 | the same constant x256 |
| `00130BF0` | `lui $at,0x3F40` | `lui $at,0x3F10` | an INSTRUCTION: 0.75 -> 0.5625 |

0.75 is 3/4 and 0.5625 is 9/16, so that immediate is **1/aspect**, and the two
data floats scale by **aspect / (4/3)** - how much the horizontal field of view
widens. The model reproduces the stock patch from first principles: fed 16:9 it
returns `3FC71C72` and `lui 0x3F10`, against the shipped `3FC70FB6` and
`0x3F10`. The immediate matches bit for bit; the float differs only because the
official patch rounded 4/3 to 1.333.

For 19.5:9 the widen factor is exactly 1.625, giving `3FF2AAAB`, `43F2AAAB` and
`lui $at,0x3EEC`. `lui` sets only the top 16 bits, so the last lands on
0.4609375 against an ideal 0.4615385 - 0.13% narrow, about a third of a pixel
across 3120. A trampoline would fix that for no visible gain.

### How far it is verified, and how far it is not

**Verified exactly, at the arithmetic.** `00130BF0` feeds `$f20` two
instructions later (`mtc1` then `mul.s $f20,$f02,$f20`). Breakpointing after
that multiply, with the group off and on:

    4:3     $f20 = 0.6495191
    19.5:9  $f20 = 0.3991836      ratio 0.61458, predicted 0.61458

**Not verified on screen.** No render test this session could distinguish the
aspects - and crucially it could not distinguish the *official 16:9 values*
from stock either. A live poke of the shipped 16:9 constants left the aura's
bounding box identical to 4:3, so the null result is a property of the test, not
of the constants: these are consumed at scene entry, and every quick path
(save-state load, mid-session toggle) shows the projection the state was
captured with. Seeing it needs a battle entered fresh after boot.

Two mistakes worth recording, both from trusting a metric over a check:

- The first scale-fit searched **horizontal** rescale only, over a band that is
  almost entirely flat green field. The objective was degenerate - error at the
  best scale equalled error at scale 1.0 - and it happily reported "no change"
  for every arm. A fit whose objective is flat has not measured anything.
- A frame captured with an extra 30 frame-advances was read as an aspect
  difference. It was aura animation. Arms must run the same number of frames.

### Shipping

`config.OPTIONAL` is a third list beside `NEVER_SHIP`: groups that belong in the
shared file but must not be switched on for the user. `export.py` keeps them,
`deploy.py` installs them and leaves them out of the enable list. A display
preference is not a fix, and this one additionally **conflicts with the stock
[Widescreen 16:9]** - both write the same three addresses every frame, so
whichever the cheat engine writes last wins.

To use it: add `Enable = Widescreen 19.5:9 - S24 Ultra` under `[Cheats]`, delete
`Enable = Widescreen 16:9` from `[Patches]`, restart, and set the display Aspect
Ratio to Stretch against a 19.5:9 output. PCSX2 has no 19.5:9 display aspect, so
at any other output shape this renders a correctly-wide FOV into the wrong box.

## 2026-09-16 - issue #23, widescreen: the model generalises, so put it in a tool

The 19.5:9 group was worked out by hand on 2026-09-08 and its derivation sat in
a findings section. Issue #23 asked for 21:9 and 16:10, which is the same
arithmetic twice more, so the arithmetic moved into `tools/widescreen.py` and
the next aspect costs one command.

Nothing about the model changed. The three words are:

| address | what it is | value |
|---|---|---|
| `002FE4CC` | projection scale, 7/6 at 4:3 | `(7/6) * aspect / (4/3)` |
| `002FE594` | the same constant x256 | the above x256 |
| `00130BF0` | `lui $at, imm` - an instruction | top 16 bits of `float32(1/aspect)` |

### The tool is checked against words nobody in this project chose

`--selftest` runs the model against BT3's stock 4:3 and PCSX2's own shipped
`[Widescreen 16:9]` from `resources/patches.zip`:

```
ok   stock 4:3
       scale  ours 3F955555 1.1666667   theirs 3F955555 1.1666666   0.0000%
       lui    ours 0x3F40    theirs 0x3F40    exact
ok   PCSX2's shipped [Widescreen 16:9]
       scale  ours 3FC71C72 1.5555556   theirs 3FC70FB6 1.5551670   0.0250%
       lui    ours 0x3F10    theirs 0x3F10    exact
```

The `lui` immediate - the part that actually carries the aspect - matches both
bit for bit. The 16:9 scale is 0.025% off, and the arithmetic says exactly why:
`7/6 * 1.333` is `1.5551667`, so the official patch typed the widen factor as
`1.333` rather than `4/3`. That is a field of view 0.025% narrow, about half a
pixel across 1920. Fed 19.5:9 the tool reproduces the group already in the file,
all three words.

### 16:10 and 21:9 both land exactly

| aspect | `002FE4CC` | `002FE594` | `00130BF0` | `lui` error |
|---|---|---|---|---|
| 19.5:9 (2.166667) | `3FF2AAAB` | `43F2AAAB` | `3C013EEC` | 0.13% |
| 16:10 (1.600000) | `3FB33333` | `43B33333` | `3C013F20` | **exact** |
| 21:9 as 64:27 (2.370370) | `4004BDA1` | `4404BDA1` | `3C013ED8` | **exact** |
| 43:18 (3440x1440) | `4005C71C` | `4405C71C` | `3C013ED6` | 0.15% |

`lui` sets only the top 16 bits, so 1/aspect is rounded to what fits there.
`1/1.6` is 0.625 and `27/64` is 0.421875; both are exact in a handful of
mantissa bits, so the two new groups have nothing to round away. 19.5:9 does not
have that luck, which is where its 0.13% comes from.

### "21:9" is a marketing name, not a ratio

No panel is 21/9 = 2.333333. 2560x1080 and 3840x1620 are **64:27** (2.370370),
which is the aspect the standard defines; 3440x1440 is **43:18** (2.388889).
The group carries 64:27. Rendering it into a 3440x1440 window stretches the
picture 0.8% horizontally, which is not visible, and anyone who wants their
panel exact can run `python tools/widescreen.py 3440x1440`.

### Overlapping groups, and what it cost to allow them

Every display aspect writes the same three addresses, and `Pnach.validate()`
has always reported two groups writing one address as an overwrite - correctly,
because the cheat engine's last write wins and a fix can be silently undone by
an unrelated one. With one aspect in the file that never fired. With three it
fired six times, and the only options were to ship a single aspect or to stop
checking overlaps.

`validate(exclusive=[[...]])` in PCSXROO (`Saupernova13/pcsxroo#4`) takes sets of
group names that are alternatives of one another. Overlap inside a set is
expected; overlap with anything outside it is still a problem, and a name in a
set that matches no group is reported too, so renaming a group cannot quietly
drop its exemption. `config.EXCLUSIVE` names the three aspects and both
`export.py` and `deploy.py` pass it.

**This repo's tools therefore need that PCSXROO change.** On an older `ps2ee`,
`export.py` raises `TypeError: validate() got an unexpected keyword argument`.

### Verified live, exactly

`00130BF0` feeds `$f20` through `mtc1`, and `00130C0C` multiplies it:

```
00130BEC  mov.s $f12, $f21
00130BF0  lui   $at, 0x3F40      <- the patched word
00130BF4  mtc1  $at, $f20
00130BF8  jal   0x0028F3C0
00130C0C  mul.s $f20, $f2, $f20
00130C10  swc1  $f2, 4($s0)      <- breakpoint here
```

Breakpoint at `00130C10`, save state 3, each arm loaded fresh. **The stock
`[Widescreen 16:9]` has to be off in the rig ini's `[Patches]` first** - it
writes the same three addresses every frame and the last writer wins:

| arm | `00130BF0` in RAM | `$f20` | measured ratio | predicted |
|---|---|---|---|---|
| no widescreen (4:3) | `3C013F40` | 0.6495191 | 1.0000000 | 1.0000000 |
| 16:10 | `3C013F20` | 0.5412659 | **0.8333333** | 0.8333333 |
| 21:9 (64:27) | `3C013ED8` | 0.3653545 | **0.5625000** | 0.5625000 |

Both exact to seven decimal places, and the 4:3 baseline is the same 0.6495191
the 19.5:9 work measured on 2026-09-08, so this is the same path.

**`frame_advance` before arming the breakpoint, or the arms all read the same.**
The first run of this measurement returned 0.6495191 for all three. The cheat
engine writes an enabled group's words at a frame boundary, and `resume()`
reached `00130C10` before the first boundary - so the breakpoint fired on the
unpatched instruction every time, three arms agreeing perfectly on the wrong
answer. Four frame advances between `patchctl.apply` and `bp_add` fixes it.
Reading the patched address back before trusting an arm is what caught it.

### Still not verified

**No render test in this project has ever distinguished one aspect from another
on screen**, including PCSX2's official 16:9 values against stock. These
constants are consumed at scene entry, so every quick path - save-state load,
mid-session toggle - shows the projection the state was captured with. Seeing it
needs a battle entered fresh after boot. That gap is unchanged from 19.5:9.

Both groups are in `config.OPTIONAL`: installed, listed, switched off. A display
preference is not a fix. They also conflict with the stock `[Widescreen 16:9]`,
which must be turned off in the per-game ini's `[Patches]` section, and PCSX2
offers no 21:9 or 16:10 display aspect - `AspectRatioType` is Stretch, Auto
4:3/3:2, 4:3, 16:9, 10:7 - so both need **Aspect Ratio = Stretch** against a
window of the matching shape.

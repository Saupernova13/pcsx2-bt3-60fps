# v06b - the withdrawal alone

| | |
|---|---|
| Tag | `v06b-withdraw-broken-blast-groups` |
| Date | 2026-09-06 |
| Built on | [v05](v05-blast-sequence-rate.md) - a sibling of [v06](v06-blast-effect-duration.md), cut in the same commit (`ce5b74d`) |
| Groups | 14 (165 patch lines) |
| Confidence | Superseded |

## What it changed over v05

Removed `[60FPS - blast effect rate]` and `[60FPS - blast sequence rate]`, and
added nothing. **Its group list is v03's, byte for byte.**

The commit that cut it does not say why a withdrawal-only build was kept beside
v06. By its contents it is exactly that: v05 with the two rendering-breaking
groups taken out and without v06's replacement fix, so the damage and the repair
can be told apart.

## What was discovered

Everything in [v06](v06-blast-effect-duration.md) - this build was cut from the
same investigation.

## Get this version

    git show v06b-withdraw-broken-blast-groups:releases/v6-withdraw-broken-blast-groups/428113C2.pnach > 428113C2.pnach

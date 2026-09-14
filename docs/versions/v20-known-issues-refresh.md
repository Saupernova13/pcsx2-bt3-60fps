# v20 - the shipped header caught up

| | |
|---|---|
| Tag | `v20-known-issues-refresh` |
| Date | 2026-09-09 |
| Built on | [v19](v19-screen-fade.md) |
| Groups | 25 (279 patch lines) - identical to v19 |
| Confidence | **CONFIRMED IN PLAY** (the patch is v19's) |

## What it changed over v19

**No patch change.** Same 25 groups and 279 patch lines as v19, verified line for
line.

What changed is the `KNOWN NOT FIXED` block at the top of the shared file, which is
the only documentation most people who use this patch ever read. It still said the
pre-fight intro's mouths do not move (fixed in v15, confirmed 2026-09-08) and that
transformations run long (confirmed fixed in play 2026-09-09). It now names what is
actually left: the ultimate's beam, the fast summon phase on Frieza's rocks and
Buu's charged blast, the intro animation pacing, and the never-re-checked camera on
a body-erasing death.

Cut as its own version rather than rewriting v19 in place: a release is a record.

## What was discovered

- **A header nobody re-reads goes stale silently.** The list lives in
  `tools/export.py` and is written into every release, so it has to be edited when
  the facts change - here it had fallen two fixes behind.

## Get this version

    git show v20-known-issues-refresh:releases/v20-known-issues-refresh/428113C2.pnach > 428113C2.pnach

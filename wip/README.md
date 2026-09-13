# wip/

**Looking for the patch to install or share? It is not here.**
It is [`patch/428113C2.pnach`](../patch/428113C2.pnach).

    working.pnach   the working pnach: every group, including two that must
                    never be enabled. The tools read this file; people do not.
    experiments/    numbered isolation experiments, kept for the record

`working.pnach` is the source the release is cut from, not the release itself.
It carries `60FPS - animation rate` (superseded by `60FPS - animation clock`) and
`60FPS - EXPERIMENT halve root motion` (deliberately breaks ground movement).
Both are off, and `tools/export.py` strips them when cutting a release.

To cut one: `python tools/export.py --release vN-name`, then tag the commit.
See [`docs/releases.md`](../docs/releases.md).

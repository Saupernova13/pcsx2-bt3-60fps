# patches/

**Looking for the patch to install or share? It is not here.**
It is [`releases/latest/428113C2.pnach`](../releases/latest/428113C2.pnach).

    428113C2.pnach    the working pnach: every group, including two that must
                      never be enabled. The tools read this file; people do not.
    exp/              numbered isolation experiments, kept for the record

`428113C2.pnach` is the source the release is cut from, not the release itself.
It carries `60FPS - animation rate` (superseded by `60FPS - animation clock`) and
`60FPS - EXPERIMENT halve root motion` (deliberately breaks ground movement).
Both are off, and `tools/export.py` strips them when cutting a release.

To cut one: `python tools/export.py --release vN-name`, then tag the commit.
See [`releases/README.md`](../releases/README.md).

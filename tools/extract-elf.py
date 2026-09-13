"""Extract the boot ELF from the game disc image into work/.

    python tools/extract-elf.py [--image PATH] [--out PATH]
"""

import argparse

import _bootstrap  # noqa: F401

from game import config
from ps2ee.ciso import DiscImage, find, read_root


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", help="disc image; defaults to config.game_image()")
    parser.add_argument("--out", help="output path; defaults to work/<ELF_NAME>")
    parser.add_argument("--list", action="store_true", help="just list the image root")
    args = parser.parse_args()

    image = args.image or config.game_image()
    with DiscImage(image) as img:
        kind = "CISO" if img.compressed else "ISO"
        print(f"{image}\n  {kind}, {img.total_bytes / 1e9:.2f} GB expanded, "
              f"{img.n_blocks} blocks of {img.block_size}")

        if args.list:
            for entry in read_root(img):
                tag = "dir " if entry.is_dir else "file"
                print(f"  {tag} {entry.name:<20} lba={entry.lba:<8} size={entry.size}")
            return 0

        entry = find(img, config.ELF_NAME)
        data = img.read_range(entry.lba, entry.size)

    out = args.out or config.elf_path()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(data)
    print(f"  {entry.name} -> {out}  ({len(data):,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

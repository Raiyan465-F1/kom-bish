"""Re-save photos with no EXIF (no GPS, no device data), rotation applied, long side at most 1600 px.

  python scripts/strip_exif.py <src file or folder> <dst folder>
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image, ImageOps

IMG_EXT = {".jpg", ".jpeg", ".png", ".webp"}
LONG_SIDE = 1600


def strip(src: Path, dst: Path) -> Path:
    with Image.open(src) as im:
        clean = ImageOps.exif_transpose(im).convert("RGB")
    clean.thumbnail((LONG_SIDE, LONG_SIDE), Image.BICUBIC)
    pixels_only = Image.new("RGB", clean.size)   # a fresh image carries no metadata at all
    pixels_only.paste(clean)
    dst.parent.mkdir(parents=True, exist_ok=True)
    pixels_only.save(dst, "JPEG", quality=95)
    with Image.open(dst) as check:
        assert len(check.getexif()) == 0, f"EXIF still present in {dst}"
    return dst


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("src", type=Path)
    p.add_argument("dst", type=Path)
    args = p.parse_args(argv)
    files = [args.src] if args.src.is_file() else sorted(q for q in args.src.iterdir() if q.suffix.lower() in IMG_EXT)
    if not files:
        raise SystemExit(f"No images found at {args.src}")
    for src in files:
        print(strip(src, args.dst / f"{src.stem}.jpg"))
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Write a fake raw tree of random-noise JPEGs to exercise the pipeline end to end.

Synthetic data proves the code runs. It says nothing about accuracy: never report a metric from it.

  python training/make_synthetic_data.py            # -> data/synthetic/raw + data/synthetic/mapping.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SOURCES = {
    "RiceLeafBD": ["Bacterial Leaf Blight", "Healthy", "Brown Spot", "Tungro Virus"],
    "BD5": ["Blast", "Normal Leaf", "Narrow Brown Spot", "Sheath Blight", "Tungro"],
}
SIZES = [(600, 400), (400, 700), (1200, 900)]   # (width, height)


def make(base: Path, per_class: int = 12, seed: int = 0) -> Path:
    """Create <base>/raw/<source>/<class>/*.jpg and <base>/mapping.json. Returns the mapping path."""
    rng = np.random.default_rng(seed)
    mapping: dict[str, list[str]] = {}
    for source, classes in SOURCES.items():
        for cls in classes:
            folder = base / "raw" / source / cls
            folder.mkdir(parents=True, exist_ok=True)
            mapping[f"{source}/{cls}"] = [source, cls]
            for i in range(per_class):
                w, h = SIZES[i % len(SIZES)]
                noise = rng.integers(0, 256, size=(h, w, 3), dtype=np.uint8)
                Image.fromarray(noise).save(folder / f"img_{i:03d}.jpg", "JPEG", quality=80)
    mapping_path = base / "mapping.json"
    mapping_path.write_text(json.dumps(mapping, indent=2), "utf-8")
    return mapping_path


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--base", type=Path, default=ROOT / "data" / "synthetic")
    p.add_argument("--per-class", type=int, default=12)
    p.add_argument("--seed", type=int, default=0)
    args = p.parse_args(argv)
    mapping_path = make(args.base, args.per_class, args.seed)
    n = sum(len(c) for c in SOURCES.values()) * args.per_class
    print(f"Wrote {n} synthetic images under {args.base / 'raw'} and {mapping_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

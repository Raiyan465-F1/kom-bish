"""Paddy Doctor for candidate B: a held-out set that is never trained on, and a train / validation split.

  python training/prepare_paddy.py --base data/prepared_run3 --out data/prepared_runB     # run in .venv-train

Held-out set (500): the 200 external-test images plus 300 more (seed 11), balanced across our 4 classes,
"other" spread evenly over its source classes. It is never used for training, validation or thresholds.
Every remaining Paddy Doctor image within perceptual-hash distance 5 of a held-out image is removed from
the pool. The rest is split 85/15 into train and validation per source label, near-duplicates kept together.
The output folder is a copy of --base with the Paddy Doctor images added to train/ and val/.

Data: Kaggle competition `paddy-disease-classification` (CC BY 4.0 under the competition rules).
Petchiammal A, Briskline Kiruba S, D. Murugan, Pandarasamy A (2022), arXiv:2205.11108.
"""
from __future__ import annotations

import argparse
import csv
import random
import shutil
import sys
from collections import Counter
from pathlib import Path

import imagehash
import numpy as np
from PIL import Image
from scipy.sparse.csgraph import connected_components

ROOT = Path(__file__).resolve().parent.parent
LABEL_MAP = {"bacterial_leaf_blight": "bacterial_leaf_blight", "blast": "blast", "normal": "healthy"}
DIST = 5


def phash_bits(path: Path) -> np.ndarray:
    with Image.open(path) as im:
        return imagehash.phash(im).hash.flatten()


def min_distance(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """For every row of a: the smallest Hamming distance to any row of b."""
    out = np.empty(len(a), dtype=np.int32)
    for i in range(0, len(a), 256):
        out[i:i + 256] = (a[i:i + 256, None, :] != b[None, :, :]).sum(-1).min(1)
    return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--source", type=Path, default=ROOT / "data" / "external" / "paddy_doctor")
    p.add_argument("--base", type=Path, required=True, help="our prepared data (copied, never modified)")
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--seed", type=int, default=11)
    p.add_argument("--extra-per-class", type=int, default=75)
    p.add_argument("--external-manifest", type=Path,
                   default=ROOT / "training" / "results" / "external_paddy_doctor_manifest.csv")
    p.add_argument("--heldout-manifest", type=Path, default=ROOT / "training" / "results" / "paddy_heldout_manifest.csv")
    args = p.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    rng = random.Random(args.seed)

    by_label: dict[str, list[str]] = {}
    with (args.source / "train.csv").open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            by_label.setdefault(row["label"], []).append(row["image_id"])
    files = [(f"train_images/{lab}/{i}", lab) for lab in sorted(by_label) for i in sorted(by_label[lab])]

    # ---- held-out set: the 200 external-test images + 300 more
    with args.external_manifest.open(encoding="utf-8", newline="") as f:
        heldout = {r["file"]: "external_test_200" for r in csv.DictReader(f)}
    others = sorted(lab for lab in by_label if lab not in LABEL_MAP)
    quota = {lab: args.extra_per_class for lab in LABEL_MAP}
    for i, lab in enumerate(others):
        quota[lab] = args.extra_per_class // len(others) + (1 if i < args.extra_per_class % len(others) else 0)
    for lab in sorted(quota):
        pool = sorted(f for f, label in files if label == lab and f not in heldout)
        for f in rng.sample(pool, min(quota[lab], len(pool))):
            heldout[f] = "added_300"
    label_of = dict(files)
    args.heldout_manifest.parent.mkdir(parents=True, exist_ok=True)
    with args.heldout_manifest.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["file", "source_label", "mapped_label", "part"])
        for name in sorted(heldout):
            w.writerow([name, label_of[name], LABEL_MAP.get(label_of[name], "other"), heldout[name]])
    print(f"held-out set: {len(heldout)} images {dict(Counter(LABEL_MAP.get(label_of[f], 'other') for f in heldout))}")

    # ---- leak filter: nothing near a held-out image may be trained on
    bits = np.array([phash_bits(args.source / f) for f, _ in files])
    is_held = np.array([f in heldout for f, _ in files])
    near_held = min_distance(bits, bits[is_held]) <= DIST
    removed = int((near_held & ~is_held).sum())
    print(f"removed from the training pool: {removed} images within pHash distance {DIST} of a held-out image")
    ours = sorted(q for split in ("train", "val") for q in (args.base / split).rglob("*.jpg"))
    our_bits = np.array([phash_bits(q) for q in ours])
    d_ours = min_distance(bits[is_held], our_bits)
    print(f"held-out vs our {len(ours)} training and validation images: closest distance {int(d_ours.min())}, "
          f"within {DIST}: {int((d_ours <= DIST).sum())}")

    # ---- train / validation split per source label, near-duplicates kept together
    assignment: dict[int, str] = {}
    for lab in sorted(by_label):
        idx = np.array([i for i, (f, label) in enumerate(files) if label == lab and not near_held[i]])
        dist = np.vstack([(bits[idx[i:i + 256], None, :] != bits[None, idx, :]).sum(-1) for i in range(0, len(idx), 256)])
        _, comp = connected_components(dist <= DIST, directed=False)
        groups: dict[int, list[int]] = {}
        for i, c in zip(idx, comp):
            groups.setdefault(int(c), []).append(int(i))
        order = sorted(groups.values())
        rng.shuffle(order)
        n_val, used = round(0.15 * len(idx)), 0
        for group in order:
            split = "val" if used < n_val else "train"
            used += len(group) if split == "val" else 0
            for i in group:
                assignment[i] = split

    # ---- output folder = our prepared data + Paddy Doctor train / val images
    if args.out.exists():
        raise SystemExit(f"{args.out} already exists; delete it first.")
    shutil.copytree(args.base, args.out)
    rows = []
    for i, split in sorted(assignment.items()):
        f, lab = files[i]
        target = LABEL_MAP.get(lab, "other")
        rel = f"{split}/{target}/PaddyDoctor__{lab}__{Path(f).name}"
        shutil.copyfile(args.source / f, args.out / rel)
        rows.append({"path": rel, "source": "PaddyDoctor", "source_class": lab, "target": target, "split": split,
                     "orig_path": f"kaggle://paddy-disease-classification/{f}"})
    with (args.out / "manifest.csv").open("a", encoding="utf-8", newline="") as f:
        csv.DictWriter(f, fieldnames=["path", "source", "source_class", "target", "split", "orig_path"]).writerows(rows)
    counts = Counter((r["split"], r["target"]) for r in rows)
    for split in ("train", "val"):
        print(f"Paddy Doctor {split}: " + ", ".join(f"{t} {counts[(split, t)]}" for t in
                                                    ("bacterial_leaf_blight", "blast", "healthy", "other"))
              + f" (total {sum(v for (s, _), v in counts.items() if s == split)})")
    print(f"wrote {args.out} and {args.heldout_manifest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

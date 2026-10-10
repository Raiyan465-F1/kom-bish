"""Kom Bish data preparation (human in the loop).

  1) python training/prepare_data.py --print-tree --root <RAW_ROOT>
  2) Paste the output to Claude Code, which fills FOLDER_TO_TARGET / CSV_LABELS below. Never guess.
  3) python training/prepare_data.py --root <RAW_ROOT> --out <OUT> --dhs

Source confound: every BLB image is from RiceLeafBD and every training blast image is from BD5.
Report recall per (source, class) and cross-source blast recall; do not hide this.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

from PIL import Image, ImageOps

TARGETS = ("bacterial_leaf_blight", "blast", "healthy", "other")   # alphabetical = ImageFolder order 0..3
IMG_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
LONG_SIDE = 512
SPLITS = ("train", "val", "test")
DHS_REPO = "Project-AgML/Dhan-Shomadhan_rice_leaf_disease_classification"
DHS_SPLIT = "dhs_field_blast"

SOURCE_CLASS_TO_TARGET = {   # fixed by the master plan; do not edit
    ("RiceLeafBD", "Bacterial Leaf Blight"): "bacterial_leaf_blight",
    ("RiceLeafBD", "Healthy"): "healthy",
    ("RiceLeafBD", "Brown Spot"): "other",
    ("RiceLeafBD", "Tungro Virus"): "other",
    ("BD5", "Blast"): "blast",
    ("BD5", "Normal Leaf"): "healthy",
    ("BD5", "Narrow Brown Spot"): "other",
    ("BD5", "Sheath Blight"): "other",
    ("BD5", "Tungro"): "other",
}
PUBLISHED_COUNTS = {
    ("RiceLeafBD", "Bacterial Leaf Blight"): 417, ("RiceLeafBD", "Healthy"): 252,
    ("RiceLeafBD", "Brown Spot"): 356, ("RiceLeafBD", "Tungro Virus"): 530,
    ("BD5", "Blast"): 339, ("BD5", "Normal Leaf"): 923, ("BD5", "Narrow Brown Spot"): 329,
    ("BD5", "Sheath Blight"): 454, ("BD5", "Tungro"): 500,
}

# Filled in Part B from the printed tree. Key: folder path relative to --root, exactly as printed
# (forward slashes). Value: (source, source_class) present in SOURCE_CLASS_TO_TARGET, or None to drop.
FOLDER_TO_TARGET: dict[str, tuple[str, str] | None] = {}

# Only if a dataset keeps labels in a CSV. Filled from the printed CSV header. Shape:
# {"csv": "<rel path>", "image_dir": "<rel dir>", "file_col": "<col>", "label_col": "<col>",
#  "source": "RiceLeafBD", "label_to_source_class": {"<csv label>": "Bacterial Leaf Blight", ...}}
CSV_LABELS: list[dict] = []

MSG_EMPTY = "Mapping is empty. Run --print-tree and paste the output to Claude Code (step 07 Part B)."
MSG_COUNTS = "Counts differ. Explain each difference to the team, then rerun with --accept-count-mismatch."
MSG_DHS = ("Dhan-Shomadhan load failed. Fallback: Kaggle mirror nirmalsankalana/dhan-shomadhan via Add Input, "
           "then --print-tree on it.")


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")


def rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix() or "."


def is_image(name: str) -> bool:
    return Path(name).suffix.lower() in IMG_EXT


def published_target_totals() -> dict[str, int]:
    totals = dict.fromkeys(TARGETS, 0)
    for key, n in PUBLISHED_COUNTS.items():
        totals[SOURCE_CLASS_TO_TARGET[key]] += n
    return totals


# ---------------------------------------------------------------- print-tree

def print_published_counts() -> None:
    print("\nPublished counts (source | source class -> target | n):")
    for (source, cls), n in PUBLISHED_COUNTS.items():
        print(f"{n:6d}  {source} | {cls} -> {SOURCE_CLASS_TO_TARGET[(source, cls)]}")
    print("Target totals: " + ", ".join(f"{t} {n}" for t, n in published_target_totals().items()))


def print_tree(root: Path) -> None:
    total = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames.sort()
        n_img = sum(1 for f in filenames if is_image(f))
        csvs = sorted(f for f in filenames if f.lower().endswith(".csv"))
        if not n_img and not csvs:
            continue
        folder = Path(dirpath)
        print(f"{n_img:6d}  {rel(folder, root)}")
        total += n_img
        for name in csvs:
            print(f"        CSV: {rel(folder / name, root)}")
            with (folder / name).open(encoding="utf-8", errors="replace") as f:
                for _, line in zip(range(3), f):
                    print(f"          {line.rstrip()[:200]}")
    print(f"{total:6d}  TOTAL images under {root}")
    print_published_counts()


# ------------------------------------------------------------------- collect

def collect(root: Path, folder_map: dict, csv_labels: list[dict]) -> list[dict]:
    """Return one record per image: orig (Path), source, source_class. A file mapped twice is an error."""
    if not folder_map and not csv_labels:
        raise SystemExit(MSG_EMPTY)
    records: list[dict] = []
    seen: set[Path] = set()

    def add(path: Path, source: str, source_class: str) -> None:
        if (source, source_class) not in SOURCE_CLASS_TO_TARGET:
            raise SystemExit(f"Unknown (source, source_class): {(source, source_class)!r}")
        key = path.resolve()
        if key in seen:
            raise SystemExit(f"File mapped twice: {path}")
        seen.add(key)
        records.append({"orig": path, "source": source, "source_class": source_class})

    for folder_rel, value in folder_map.items():
        if value is None:
            continue
        folder = root / folder_rel
        if not folder.is_dir():
            raise SystemExit(f"Mapped folder not found under --root: {folder_rel}")
        source, source_class = value
        for path in sorted(folder.iterdir()):
            if path.is_file() and is_image(path.name):
                add(path, source, source_class)

    for entry in csv_labels:
        image_dir = root / entry["image_dir"]
        missing = dropped = 0
        with (root / entry["csv"]).open(encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                source_class = entry["label_to_source_class"].get(row[entry["label_col"]])
                if source_class is None:
                    dropped += 1
                    continue
                path = image_dir / row[entry["file_col"]]
                if not path.is_file():
                    missing += 1
                    continue
                add(path, entry["source"], source_class)
        print(f"CSV {entry['csv']}: {dropped} rows with unmapped labels dropped, {missing} files missing")
    return records


def check_counts(records: list[dict], accept_mismatch: bool) -> None:
    got = Counter((r["source"], r["source_class"]) for r in records)
    mismatch = False
    print("\nCount check (got / published):")
    for key, published in PUBLISHED_COUNTS.items():
        flag = "" if got[key] == published else "   <-- differs"
        mismatch |= bool(flag)
        print(f"{got[key]:6d} / {published:6d}  {key[0]} | {key[1]}{flag}")
    got_targets = Counter(SOURCE_CLASS_TO_TARGET[k] for k in got.elements())
    for target, published in published_target_totals().items():
        flag = "" if got_targets[target] == published else "   <-- differs"
        mismatch |= bool(flag)
        print(f"{got_targets[target]:6d} / {published:6d}  target {target}{flag}")
    if mismatch and not accept_mismatch:
        raise SystemExit(MSG_COUNTS)


# --------------------------------------------------------------------- split

def group_records(records: list[dict], use_phash: bool, phash_dist: int) -> list[list[int]]:
    """Group record indices that must share a split: byte-identical files always, near-duplicates with --phash.

    Groups never cross (source, source_class), so each group has one stratum.
    """
    parent = list(range(len(records)))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    by_stratum: dict[tuple, list[int]] = {}
    for i, r in enumerate(records):
        by_stratum.setdefault((r["source"], r["source_class"]), []).append(i)

    for members in by_stratum.values():
        first_with_hash: dict[str, int] = {}
        for i in members:
            j = first_with_hash.setdefault(records[i]["sha1"], i)
            parent[find(i)] = find(j)

    if use_phash:
        import imagehash  # training venv only

        hashes: dict[int, object] = {}
        for i, r in enumerate(records):
            try:
                with Image.open(r["orig"]) as im:
                    hashes[i] = imagehash.phash(im)
            except Exception:  # unreadable files are reported when written
                continue
        for members in by_stratum.values():
            hashed = [i for i in members if i in hashes]
            for a_pos, a in enumerate(hashed):
                for b in hashed[a_pos + 1:]:
                    if hashes[a] - hashes[b] <= phash_dist:
                        parent[find(a)] = find(b)

    groups: dict[int, list[int]] = {}
    for i in range(len(records)):
        groups.setdefault(find(i), []).append(i)
    multi = [g for g in groups.values() if len(g) > 1]
    print(f"\nDuplicate groups kept in one split: {len(multi)} groups, {sum(map(len, multi))} images"
          f" ({'exact + phash' if use_phash else 'exact only'})")
    return list(groups.values())


def _split_once(units: list, strata_options: list[tuple[str, list[str] | None]], test_size: float, seed: int):
    from sklearn.model_selection import train_test_split

    last_error: Exception | None = None
    for position, (name, strata) in enumerate(strata_options):
        try:
            idx = list(range(len(units)))
            a, b = train_test_split(idx, test_size=test_size, random_state=seed, stratify=strata)
            if position:
                print(f"WARNING: a stratum is too small for source|class; stratified by {name} instead.")
            return a, b
        except ValueError as e:
            last_error = e
    raise SystemExit(f"Split failed: {last_error}")


def split_groups(records: list[dict], groups: list[list[int]], seed: int) -> None:
    """Seeded 70/15/15 split of groups, before any augmentation. Sets record['split']."""
    fine = [f"{records[g[0]]['source']}|{records[g[0]]['source_class']}" for g in groups]
    coarse = [SOURCE_CLASS_TO_TARGET[(records[g[0]]["source"], records[g[0]]["source_class"])] for g in groups]

    def options(idx: list[int]):
        return [("source|class", [fine[i] for i in idx]), ("target", [coarse[i] for i in idx]), ("nothing", None)]

    everything = list(range(len(groups)))
    train_pos, temp_pos = _split_once(everything, options(everything), 0.30, seed)
    temp = [everything[i] for i in temp_pos]
    val_pos, test_pos = _split_once(temp, options(temp), 0.50, seed)
    assignment = {"train": [everything[i] for i in train_pos],
                  "val": [temp[i] for i in val_pos], "test": [temp[i] for i in test_pos]}
    for split, group_ids in assignment.items():
        for gid in group_ids:
            for i in groups[gid]:
                records[i]["split"] = split


# --------------------------------------------------------------------- write

def save_resized(im: Image.Image, dest: Path) -> None:
    im = ImageOps.exif_transpose(im).convert("RGB")
    im.thumbnail((LONG_SIDE, LONG_SIDE), Image.BICUBIC)   # long side 512, never upscales
    dest.parent.mkdir(parents=True, exist_ok=True)
    im.save(dest, "JPEG", quality=95)


def write_images(records: list[dict], root: Path, out: Path) -> tuple[list[dict], list[str]]:
    rows: list[dict] = []
    unreadable: list[str] = []
    used: set[str] = set()
    for r in records:
        target = SOURCE_CLASS_TO_TARGET[(r["source"], r["source_class"])]
        stem = f"{r['source']}__{slug(r['source_class'])}__{slug(r['orig'].stem)}_{r['sha1'][:8]}"
        name, n = stem, 1
        while name in used:   # byte-identical files with the same stem
            n += 1
            name = f"{stem}_dup{n}"
        used.add(name)
        rel_path = f"{r['split']}/{target}/{name}.jpg"
        try:
            with Image.open(r["orig"]) as im:
                save_resized(im, out / rel_path)
        except Exception as e:
            unreadable.append(f"{rel(r['orig'], root)}: {type(e).__name__}: {e}")
            continue
        rows.append({"path": rel_path, "source": r["source"], "source_class": r["source_class"],
                     "target": target, "split": r["split"], "orig_path": rel(r["orig"], root)})
    return rows, unreadable


def add_dhs(out: Path) -> list[dict]:
    """Cross-source blast test: Dhan-Shomadhan field-background Rice Blast images, held out entirely."""
    try:
        from datasets import load_dataset

        ds = load_dataset(DHS_REPO, split="train")
        names = getattr(ds.features["label"], "names", None)

        def label_name(value) -> str:
            return names[value] if names else str(value)

        table = Counter((bg, label_name(lab)) for bg, lab in zip(ds["background"], ds["label"]))
        print("\nDhan-Shomadhan (background, label) counts:")
        for (bg, lab), n in sorted(table.items()):
            print(f"{n:6d}  {bg} | {lab}")

        field = ds.filter(lambda bg: bg == "Field", input_columns=["background"])
        wanted = names.index("Rice Blast") if names else "Rice Blast"
        blast = field.filter(lambda lab: lab == wanted, input_columns=["label"])
        image_col = next(k for k, v in ds.features.items() if type(v).__name__ == "Image")
        rows = []
        for i, example in enumerate(blast):
            rel_path = f"{DHS_SPLIT}/DhanShomadhan__rice_blast__{i:05d}.jpg"
            save_resized(example[image_col], out / rel_path)
            rows.append({"path": rel_path, "source": "DhanShomadhan", "source_class": "Rice Blast",
                         "target": "blast", "split": DHS_SPLIT, "orig_path": f"hf://datasets/{DHS_REPO}#{i}"})
        print(f"Dhan-Shomadhan field blast images found: {len(rows)} "
              "(published Rice Blast total is 272 across both backgrounds; the field share is unknown)")
        return rows
    except Exception as e:
        print(f"{MSG_DHS} ({type(e).__name__}: {e})")
        return []


def print_split_table(rows: list[dict]) -> None:
    counts = Counter((r["split"], r["target"]) for r in rows)
    splits = [s for s in (*SPLITS, DHS_SPLIT) if any(k[0] == s for k in counts)]
    print("\nImages written per split and target:")
    print(f"{'split':<16}" + "".join(f"{t:>24}" for t in TARGETS) + f"{'total':>8}")
    for split in splits:
        per = [counts[(split, t)] for t in TARGETS]
        print(f"{split:<16}" + "".join(f"{n:>24}" for n in per) + f"{sum(per):>8}")


# ---------------------------------------------------------------------- main

def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--root", type=Path, required=True, help="raw data root")
    p.add_argument("--print-tree", action="store_true", help="print folders, image counts and CSV headers, then exit")
    p.add_argument("--out", type=Path, help="output folder for train/val/test")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--dhs", action="store_true", help="also save Dhan-Shomadhan field blast images (held out)")
    p.add_argument("--phash", action="store_true", help="keep near-duplicate images in one split")
    p.add_argument("--phash-dist", type=int, default=5,
                   help="Hamming distance for --phash (unverified threshold; 4-6 is common practice)")
    p.add_argument("--accept-count-mismatch", action="store_true")
    p.add_argument("--mapping-json", type=Path,
                   help="JSON {rel_folder: [source, source_class] | null}; overrides FOLDER_TO_TARGET")
    args = p.parse_args(argv)

    root = args.root.resolve()
    if not root.is_dir():
        raise SystemExit(f"--root is not a folder: {args.root}")
    if args.print_tree:
        print_tree(root)
        return 0
    if args.out is None:
        raise SystemExit("--out is required unless --print-tree is given.")
    assert list(TARGETS) == sorted(TARGETS), "TARGETS must be alphabetical (ImageFolder order)"

    folder_map: dict = dict(FOLDER_TO_TARGET)
    if args.mapping_json:
        raw = json.loads(args.mapping_json.read_text("utf-8"))
        folder_map = {k: (tuple(v) if v is not None else None) for k, v in raw.items()}

    records = collect(root, folder_map, CSV_LABELS)
    check_counts(records, args.accept_count_mismatch)
    for r in records:
        r["sha1"] = hashlib.sha1(r["orig"].read_bytes()).hexdigest()
    groups = group_records(records, args.phash, args.phash_dist)
    split_groups(records, groups, args.seed)

    out = args.out.resolve()
    rows, unreadable = write_images(records, root, out)
    for split in SPLITS:
        for target in TARGETS:
            (out / split / target).mkdir(parents=True, exist_ok=True)
        folders = sorted(d.name for d in (out / split).iterdir() if d.is_dir())
        assert folders == list(TARGETS), (split, folders)
    if unreadable:
        print(f"\nSkipped {len(unreadable)} unreadable files:")
        for line in unreadable:
            print(f"  {line}")

    if args.dhs:
        rows += add_dhs(out)
    with (out / "manifest.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["path", "source", "source_class", "target", "split", "orig_path"])
        w.writeheader()
        w.writerows(rows)
    print_split_table(rows)
    print(f"\nWrote {len(rows)} images and manifest.csv to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

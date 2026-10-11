"""External test: the shipped model on a dataset it has never seen, through the app's own code path.

  python training/external_test.py --dataset zambali          # run in .venv-train

This is a test, not training data: nothing here may be used to change the model or its thresholds.

1. Sample up to 50 images per mapped class (seed 42; "other" drawn evenly across its source classes).
2. Leak check: drop any sampled image with a near-duplicate (64-bit perceptual hash, Hamming distance <= 5)
   among ALL training and validation images of the shipped model (--prepared), Paddy Doctor included.
3. Evaluate with training/outcomes.py (kombish.classifier.predict + kombish.rules.decide; the lesion-shape
   question unanswered). Not-a-rice-leaf images, if the dataset has them, are reported separately as junk.
4. Write aggregate results to training/results/external_test.json and a manifest CSV. No image is copied.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import random
import sys
from collections import Counter
from pathlib import Path

import imagehash
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from outcomes import CLASSES, ROOT, classifier, photo_outcome, tally, use_model  # noqa: E402

IMG_EXT = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
PHASH_DISTANCE = 5
DATASETS = {
    "zambali": {
        "name": "Zambali Rice Dataset (Public V1)", "country": "Philippines",
        "source": "https://www.kaggle.com/datasets/gettingintoml/zambali-rice-dataset-v3-1",
        "licence": "Apache-2.0 (as stated on the Kaggle dataset page)",
        "credit": "Kaggle user gettingintoml. Rice leaf images collected on farms in Iba and Botolan, Zambales, "
                  "Philippines, verified with the Provincial Agricultural Office of Zambales (dataset description).",
        "root": "data/external/zambali/ZAMBALI_RICE_DATASET_V3",
        "label_map": {"BACTERIAL_BLIGHT": "bacterial_leaf_blight", "LEAF_BLAST": "blast", "HEALTHY": "healthy",
                      "BROWN_SPOT": "other"},
        "junk_label": "NOT_A_RICE_LEAF",
    },
}


def phash_bits(path: Path) -> np.ndarray:
    with Image.open(path) as im:
        return imagehash.phash(im).hash.flatten()


def sample(root: Path, label_map: dict, per_class: int, seed: int, junk_label: str | None) -> tuple[list, list]:
    by_label = {d.name: sorted(q.name for q in d.iterdir() if q.suffix.lower() in IMG_EXT)
                for d in sorted(root.iterdir()) if d.is_dir()}
    rng = random.Random(seed)
    quota: dict[str, int] = {}
    for target in CLASSES:
        sources = sorted(lab for lab, t in label_map.items() if t == target and lab in by_label)
        for i, lab in enumerate(sources):   # a mapped class with several source classes is drawn evenly
            quota[lab] = per_class // len(sources) + (1 if i < per_class % len(sources) else 0)
    items = [{"file": f"{lab}/{name}", "source_label": lab, "mapped_label": label_map[lab]}
             for lab in sorted(quota) for name in sorted(rng.sample(by_label[lab], min(quota[lab], len(by_label[lab]))))]
    junk = []
    if junk_label and junk_label in by_label:
        junk = [{"file": f"{junk_label}/{name}", "source_label": junk_label, "mapped_label": "not a rice leaf"}
                for name in sorted(rng.sample(by_label[junk_label], min(per_class, len(by_label[junk_label]))))]
    return items, junk


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--dataset", choices=sorted(DATASETS), required=True)
    p.add_argument("--model-dir", type=Path, default=ROOT / "models")
    p.add_argument("--prepared", type=Path, default=ROOT / "data" / "prepared_runB",
                   help="the shipped model's training data (train/ and val/ are used for the leak check)")
    p.add_argument("--per-class", type=int, default=50)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--out", type=Path, default=ROOT / "training" / "results" / "external_test.json")
    p.add_argument("--manifest", type=Path, default=ROOT / "training" / "results" / "external_test_manifest.csv")
    args = p.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ds = DATASETS[args.dataset]
    root = ROOT / ds["root"]

    items, junk = sample(root, ds["label_map"], args.per_class, args.seed, ds.get("junk_label"))
    print(f"sampled {len(items)} images: {dict(Counter(i['mapped_label'] for i in items))}; junk images: {len(junk)}")
    ours = sorted(q for split in ("train", "val") for q in (args.prepared / split).rglob("*.jpg"))
    our_bits = np.array([phash_bits(q) for q in ours])
    for item in items + junk:
        d = (our_bits != phash_bits(root / item["file"])[None, :]).sum(1)
        item["min_phash_distance_to_training"] = int(d.min())
        item["near_duplicate"] = bool(d.min() <= PHASH_DISTANCE)
    dropped = [i for i in items + junk if i["near_duplicate"]]
    kept, kept_junk = [i for i in items if not i["near_duplicate"]], [i for i in junk if not i["near_duplicate"]]
    print(f"leak check against {len(ours)} training and validation images: {len(dropped)} near-duplicates dropped; "
          f"closest distance = {min(i['min_phash_distance_to_training'] for i in items + junk)}")

    m = use_model(args.model_dir)
    for item in kept + kept_junk:
        with Image.open(root / item["file"]) as im:
            item.update(photo_outcome(im, m), true=item["mapped_label"])
    results = tally(kept)
    junk_result = None
    if kept_junk:
        junk_result = {"n": len(kept_junk),
                       "referred": sum(i["outcome"] == "referred" for i in kept_junk),
                       "advice_given": sum(i["outcome"] == "advice" for i in kept_junk),
                       "blast_question_asked": sum(i["outcome"] == "blast_question" for i in kept_junk),
                       "classifier_confident": sum(i["classifier_confident"] for i in kept_junk),
                       "predicted": dict(Counter(i["predicted"] for i in kept_junk))}

    def listing(rows):
        return [{"file": r["file"], "source_label": r["source_label"], "answered_as": r["predicted"],
                 "confidence": r["confidence"]} for r in rows]

    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    with args.manifest.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["file", "source_label", "mapped_label", "near_duplicate_dropped", "min_phash_distance_to_training"])
        for i in items + junk:
            w.writerow([i["file"], i["source_label"], i["mapped_label"], "yes" if i["near_duplicate"] else "no",
                        i["min_phash_distance_to_training"]])
    payload = {
        "dataset": {k: ds[k] for k in ("name", "country", "source", "licence", "credit")} | {"used_for_training": False},
        "date": dt.date.today().isoformat(), "seed": args.seed, "per_class": args.per_class,
        "label_map": ds["label_map"], "definitions": "training/outcomes.py; the lesion-shape question is unanswered",
        "model": {"name": m.get("model"), "threshold": m["threshold"], "margin": m["margin"],
                  "blast_threshold": m.get("blast_threshold"), "blb_threshold": m.get("blb_threshold"),
                  "temperature": m["temperature"], "trained_on": m.get("trained_on"),
                  "onnx_sha256": hashlib.sha256((classifier.LOCAL_MODEL_DIR / "model.onnx").read_bytes()).hexdigest()},
        "sampled": len(items), "leak_check": {"phash_distance": PHASH_DISTANCE, "compared_with_training_images": len(ours),
                                              "near_duplicates_dropped": len(dropped),
                                              "dropped_files": [i["file"] for i in dropped]},
        **results,
        "confusion_matrix_top_guess": {"labels": CLASSES, "rows_true_cols_predicted": [
            [sum(r["true"] == t and r["predicted"] == q for r in kept) for q in CLASSES] for t in CLASSES]},
        "wrong_advice_list": listing([r for r in kept if r["outcome"] == "advice" and r["advice"] != r["true"]]),
        "blast_question_on_other_classes_list": listing([r for r in kept if r["outcome"] == "blast_question"
                                                         and r["true"] != "blast"]),
        "junk": junk_result,
    }
    args.out.write_text(json.dumps(payload, indent=1), "utf-8")

    print(f"\nEXTERNAL TEST ({ds['name']}, {ds['country']}) n={results['n']}: classifier confident "
          f"{results['classifier_confident']}, advice given {results['advice_given']} (right {results['right_advice']}, "
          f"wrong {results['wrong_advice']}), blast question asked {results['blast_question_asked']} "
          f"(true blast {results['blast_question_on_true_blast']}, other classes "
          f"{results['blast_question_on_other_classes']}), referred {results['referred']}, top guess right "
          f"{results['top_guess_right']}")
    for c, b in results["by_true_class"].items():
        print(f"  true {c:<22} {b}")
    print("  confusion (rows true, cols top guess):", payload["confusion_matrix_top_guess"]["rows_true_cols_predicted"])
    print("  junk (not a rice leaf):", junk_result)
    print(f"wrote {args.out} and {args.manifest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

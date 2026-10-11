"""External test on a dataset the model has never seen: Paddy Doctor (Kaggle `paddy-disease-classification`).

  python training/external_test.py        # run in .venv-train, after downloading the competition data

This is a test, not training data: nothing here may be used to change the model or its thresholds.

1. Sample up to 50 images per mapped class (seed 42; "other" drawn evenly across its source classes).
2. Leak check: drop any sampled image with a near-duplicate (64-bit perceptual hash, Hamming distance <= 5)
   among our training or validation images.
3. Run the shipped ONNX model through the app's own code path (kombish.classifier.predict and
   kombish.rules.decide, blast-only threshold included). The lesion-shape question is treated as unanswered:
   a photo that reaches it is counted as a blast ("spray correctly") answer, the photo-only decision.
4. Write aggregate results to training/results/external_test.json and a manifest CSV. No image is copied.

Dataset: Petchiammal A, Briskline Kiruba S, D. Murugan, Pandarasamy A (2022), "Paddy Doctor: A Visual Image
Dataset for Automated Paddy Disease Classification and Benchmarking", arXiv:2205.11108.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import os
import random
import sys
from collections import Counter
from pathlib import Path

import imagehash
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ["MODEL_REPO"] = ""   # evaluate the local models/ files (the shipped model), not a cached download
from kombish import classifier, rules  # noqa: E402

CLASSES = ["bacterial_leaf_blight", "blast", "healthy", "other"]
LABEL_MAP = {"bacterial_leaf_blight": "bacterial_leaf_blight", "blast": "blast", "normal": "healthy"}   # else: other
ADVICE_RULES = {"R1_BLB": "bacterial_leaf_blight", "R2_BLAST": "blast", "R3_HEALTHY": "healthy"}
OUTCOMES = ["bacterial_leaf_blight advice", "blast advice (spray)", "healthy advice", "referred"]
IMG_EXT = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
PHASH_DISTANCE = 5


def phash_bits(path: Path) -> np.ndarray:
    with Image.open(path) as im:
        return imagehash.phash(im).hash.flatten()


def sample(source: Path, per_class: int, seed: int) -> list[dict]:
    """Seeded sample: up to per_class images for each mapped class; "other" spread evenly over its sources."""
    by_label: dict[str, list[str]] = {}
    with (source / "train.csv").open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            by_label.setdefault(row["label"], []).append(row["image_id"])
    rng = random.Random(seed)
    quota: dict[str, int] = {}
    others = sorted(lab for lab in by_label if lab not in LABEL_MAP)
    for i, lab in enumerate(others):   # e.g. 7 source classes -> 8, 7, 7, 7, 7, 7, 7
        quota[lab] = per_class // len(others) + (1 if i < per_class % len(others) else 0)
    for lab in LABEL_MAP:
        quota[lab] = per_class
    picked = []
    for lab in sorted(quota):
        ids = sorted(by_label.get(lab, []))
        for image_id in sorted(rng.sample(ids, min(quota[lab], len(ids)))):
            picked.append({"file": f"train_images/{lab}/{image_id}", "source_label": lab,
                           "mapped_label": LABEL_MAP.get(lab, "other")})
    return picked


def leak_check(items: list[dict], source: Path, prepared: Path) -> int:
    """Mark items that have a near-duplicate among our training or validation images."""
    ours = sorted(p for split in ("train", "val") for p in (prepared / split).rglob("*.jpg"))
    our_bits = np.array([phash_bits(p) for p in ours])
    for item in items:
        d = (our_bits != phash_bits(source / item["file"])[None, :]).sum(1)
        item["min_phash_distance_to_our_images"] = int(d.min())
        item["near_duplicate"] = bool(d.min() <= PHASH_DISTANCE)
    return len(ours)


def photo_only_decision(img: Image.Image, m: dict) -> dict:
    pred = classifier.predict(img)
    args = (pred.label, pred.conf, pred.margin >= m["margin"], None, None)
    kw = {"threshold": m["threshold"], "blast_threshold": m.get("blast_threshold")}
    asked = rules.decide(*args, **kw, blast_confirmed=None)        # what the app does first
    adv = rules.decide(*args, **kw, blast_confirmed=True)          # the photo-only decision
    assert (asked.rule_id == "R0_CONFIRM_BLAST") == (adv.rule_id == "R2_BLAST")
    return {"predicted": pred.label, "confidence": round(pred.conf, 4), "margin": round(pred.margin, 4),
            "abstained": pred.abstained, "rule_id": adv.rule_id, "advice": ADVICE_RULES.get(adv.rule_id)}


def summarise(items: list[dict]) -> dict:
    def block(rows: list[dict], true_class: str | None) -> dict:
        advice = [r for r in rows if r["advice"]]
        correct = [r for r in advice if r["advice"] == r["mapped_label"]]
        answered_by_model = [r for r in rows if not r["abstained"]]
        out = {"n": len(rows), "advice_given": len(advice), "referred": len(rows) - len(advice),
               "correct_advice": len(correct), "wrong_advice": len(advice) - len(correct),
               "wrong_spray_advice": sum(r["advice"] == "blast" and r["mapped_label"] != "blast" for r in rows),
               "model_answered": len(answered_by_model),
               "model_correct_when_answered": sum(r["predicted"] == r["mapped_label"] for r in answered_by_model),
               "argmax_correct": sum(r["predicted"] == r["mapped_label"] for r in rows)}
        if true_class == "other":
            out["note"] = "for a true 'other' photo the right outcome is a referral; any advice is wrong advice"
        return out

    per_class = {c: block([r for r in items if r["mapped_label"] == c], c) for c in CLASSES}
    per_source = {}
    for lab in sorted({r["source_label"] for r in items}):
        rows = [r for r in items if r["source_label"] == lab]
        per_source[lab] = {"mapped_label": rows[0]["mapped_label"], "n": len(rows),
                           "outcomes": dict(Counter(r["advice"] + " advice" if r["advice"] else "referred"
                                                    for r in rows)),
                           "predicted": dict(Counter(r["predicted"] for r in rows))}
    confusion = [[sum(r["mapped_label"] == t and r["predicted"] == p for r in items) for p in CLASSES] for t in CLASSES]
    outcome_of = {"bacterial_leaf_blight": 0, "blast": 1, "healthy": 2, None: 3}
    decisions = [[sum(r["mapped_label"] == t and outcome_of[r["advice"]] == j for r in items) for j in range(4)]
                 for t in CLASSES]

    def listing(rows):
        return [{"file": r["file"], "source_label": r["source_label"], "answered_as": r["advice"],
                 "confidence": r["confidence"], "margin": r["margin"]} for r in rows]

    wrong = [r for r in items if r["advice"] and r["advice"] != r["mapped_label"]]
    return {"overall": block(items, None), "per_class": per_class, "per_source_label": per_source,
            "confusion_matrix_argmax": {"labels": CLASSES, "rows_true_cols_predicted": confusion},
            "decision_matrix": {"rows_true": CLASSES, "cols_outcome": OUTCOMES, "counts": decisions},
            "wrong_spray_correctly": listing([r for r in wrong if r["advice"] == "blast"]),
            "wrong_advice": listing(wrong)}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--source", type=Path, default=ROOT / "data" / "external" / "paddy_doctor")
    p.add_argument("--prepared", type=Path, default=ROOT / "data" / "prepared_run3",
                   help="our prepared data (train/ and val/ are used for the leak check)")
    p.add_argument("--per-class", type=int, default=50)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--junk", type=Path, default=ROOT / "junk_photos")
    p.add_argument("--out", type=Path, default=ROOT / "training" / "results" / "external_test.json")
    p.add_argument("--manifest", type=Path,
                   default=ROOT / "training" / "results" / "external_paddy_doctor_manifest.csv")
    args = p.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    items = sample(args.source, args.per_class, args.seed)
    print(f"sampled {len(items)} images: {dict(Counter(i['mapped_label'] for i in items))}")
    print(f"  source labels: {dict(Counter(i['source_label'] for i in items))}")
    n_ours = leak_check(items, args.source, args.prepared)
    dropped = [i for i in items if i["near_duplicate"]]
    kept = [i for i in items if not i["near_duplicate"]]
    print(f"leak check against {n_ours} of our training and validation images: {len(dropped)} near-duplicates "
          f"dropped; closest distance over all sampled images = {min(i['min_phash_distance_to_our_images'] for i in items)}")

    m = classifier.meta()
    for item in kept:
        with Image.open(args.source / item["file"]) as im:
            item.update(photo_only_decision(im, m))
    results = summarise(kept)

    junk = None
    if args.junk.is_dir():
        files = sorted(q for q in args.junk.iterdir() if q.suffix.lower() in IMG_EXT)
        if files:
            rule_ids = []
            for q in files:
                with Image.open(q) as im:
                    rule_ids.append(photo_only_decision(im, m)["rule_id"])
            junk = {"n": len(files), "referred": sum(r not in ADVICE_RULES for r in rule_ids),
                    "rule_counts": dict(Counter(rule_ids))}
    print("junk photos:", junk if junk else "skipped (junk_photos/ has no images)")

    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    with args.manifest.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["file", "source_label", "mapped_label", "near_duplicate_dropped",
                                          "min_phash_distance_to_our_images"])
        w.writeheader()
        for i in items:
            w.writerow({"file": i["file"], "source_label": i["source_label"], "mapped_label": i["mapped_label"],
                        "near_duplicate_dropped": "yes" if i["near_duplicate"] else "no",
                        "min_phash_distance_to_our_images": i["min_phash_distance_to_our_images"]})

    payload = {
        "dataset": {"name": "Paddy Doctor", "kaggle_competition": "paddy-disease-classification",
                    "citation": "Petchiammal A, Briskline Kiruba S, D. Murugan, Pandarasamy A (2022). Paddy Doctor: "
                                "A Visual Image Dataset for Automated Paddy Disease Classification and Benchmarking. "
                                "arXiv:2205.11108.",
                    "split_used": "train_images (labelled)", "used_for_training": False},
        "date": dt.date.today().isoformat(), "seed": args.seed, "per_class": args.per_class,
        "label_map": {**LABEL_MAP, "every other label": "other"},
        "lesion_question": "treated as unanswered: a photo that reaches the question counts as a blast answer",
        "model": {"name": m.get("model"), "threshold": m["threshold"], "margin": m["margin"],
                  "blast_threshold": m.get("blast_threshold"), "temperature": m["temperature"],
                  "onnx_sha256": hashlib.sha256((classifier.LOCAL_MODEL_DIR / "model.onnx").read_bytes()).hexdigest()},
        "sampled": len(items), "leak_check": {"phash_distance": PHASH_DISTANCE, "compared_with_our_images": n_ours,
                                              "near_duplicates_dropped": len(dropped),
                                              "dropped_files": [i["file"] for i in dropped]},
        "n": len(kept), **results, "junk_photos": junk,
    }
    args.out.write_text(json.dumps(payload, indent=1), "utf-8")

    o = results["overall"]
    print(f"\nEXTERNAL TEST n={o['n']}: advice given {o['advice_given']}, referred {o['referred']}, "
          f"correct advice {o['correct_advice']}, wrong advice {o['wrong_advice']}, "
          f"wrong spray advice {o['wrong_spray_advice']}")
    for c, b in results["per_class"].items():
        print(f"  true {c:<22} n={b['n']:<3} advice={b['advice_given']:<3} referred={b['referred']:<3} "
              f"correct={b['correct_advice']:<3} wrong={b['wrong_advice']:<3} wrong spray={b['wrong_spray_advice']:<3} "
              f"| argmax correct={b['argmax_correct']}")
    print("  confusion (rows true, cols predicted, no abstention):", results["confusion_matrix_argmax"]["rows_true_cols_predicted"])
    print("  decisions (rows true; cols BLB advice, blast advice, healthy advice, referred):", results["decision_matrix"]["counts"])
    print("  per source label:")
    for lab, b in results["per_source_label"].items():
        print(f"    {lab:<26} -> {b['mapped_label']:<22} n={b['n']:<3} outcomes={b['outcomes']} predicted={b['predicted']}")
    print(f"  wrong 'spray correctly' answers: {len(results['wrong_spray_correctly'])}")
    for w in results["wrong_spray_correctly"]:
        print(f"    {w['file']}  true: {w['source_label']}  confidence {w['confidence']}")
    print(f"wrote {args.out} and {args.manifest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

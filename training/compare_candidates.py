"""Compare models through the app's own code path (kombish.classifier.predict + kombish.rules.decide).

  python training/compare_candidates.py --model current=models --model A=data/export_candA --model B=data/export_candB

Sets: (i) our test split, (ii) our field-photo subset (field-background test photos plus the held-out field
blast), (iii) the Paddy Doctor held-out set (never used for training, validation or thresholds).
The lesion-shape question is treated as unanswered: a photo that reaches it counts as a blast (spray) answer.
"Answered" = the app gives advice (BLB, blast or healthy). Everything else is a referral.
Writes training/results/runs/candidates_comparison.json and .md. Changes no model.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import statistics
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ["MODEL_REPO"] = ""   # always local folders, never a cached download
from kombish import classifier, rules  # noqa: E402

ADVICE = {"R1_BLB": "bacterial_leaf_blight", "R2_BLAST": "blast", "R3_HEALTHY": "healthy"}
CLASSES = ["bacterial_leaf_blight", "blast", "healthy", "other"]


def load_sets(prepared: Path, paddy: Path, heldout_manifest: Path) -> dict[str, list[tuple[Path, str]]]:
    with (prepared / "manifest.csv").open(encoding="utf-8", newline="") as f:
        man = list(csv.DictReader(f))
    test = [r for r in man if r["split"] == "test"]
    field = [r for r in test if r["source"] == "RiceLeafBD" or r["source_class"].startswith("Field")]
    field += [r for r in man if r["split"] == "dhs_field_blast"]
    with heldout_manifest.open(encoding="utf-8", newline="") as f:
        held = list(csv.DictReader(f))
    return {"our test split": [(prepared / r["path"], r["target"]) for r in test],
            "our field photos": [(prepared / r["path"], r["target"]) for r in field],
            "Paddy Doctor held-out": [(paddy / r["file"], r["mapped_label"]) for r in held]}


def evaluate(items: list[tuple[Path, str]], m: dict) -> dict:
    out = {"n": len(items), "answered": 0, "referred": 0, "correct_answers": 0, "wrong_advice": 0, "wrong_spray": 0,
           "wrong_blb_answers": 0, "right_referrals_of_other": 0, "top_guess_right": 0,
           "correct_answers_by_class": {c: 0 for c in CLASSES[:3]}}
    for path, true in items:
        with Image.open(path) as im:
            pred = classifier.predict(im)
        adv = rules.decide(pred.label, pred.conf, pred.margin >= m["margin"], None, None, threshold=m["threshold"],
                           blast_threshold=m.get("blast_threshold"), blb_threshold=m.get("blb_threshold"),
                           blast_confirmed=True)
        advice = ADVICE.get(adv.rule_id)
        out["top_guess_right"] += pred.label == true
        if advice is None:
            out["referred"] += 1
            out["right_referrals_of_other"] += true == "other"
            continue
        out["answered"] += 1
        if advice == true:
            out["correct_answers"] += 1
            out["correct_answers_by_class"][true] += 1
        else:
            out["wrong_advice"] += 1
            out["wrong_spray"] += advice == "blast"
            out["wrong_blb_answers"] += advice == "bacterial_leaf_blight"
    out["coverage"] = out["answered"] / out["n"]
    out["accuracy_when_answered"] = out["correct_answers"] / out["answered"] if out["answered"] else None
    return out


def latency_ms(n: int = 30) -> float:
    rng = np.random.default_rng(0)
    img = Image.fromarray(rng.integers(0, 256, size=(768, 1024, 3), dtype=np.uint8))
    classifier.predict(img)
    times = []
    for _ in range(n):
        t0 = time.perf_counter()
        classifier.predict(img)
        times.append((time.perf_counter() - t0) * 1000)
    return statistics.median(times)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--model", action="append", required=True, help="name=folder with model.onnx and labels.json")
    p.add_argument("--prepared", type=Path, default=ROOT / "data" / "prepared_run3")
    p.add_argument("--paddy", type=Path, default=ROOT / "data" / "external" / "paddy_doctor")
    p.add_argument("--heldout-manifest", type=Path, default=ROOT / "training" / "results" / "paddy_heldout_manifest.csv")
    p.add_argument("--out", type=Path, default=ROOT / "training" / "results" / "runs" / "candidates_comparison")
    args = p.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sets = load_sets(args.prepared, args.paddy, args.heldout_manifest)

    results = {}
    for spec in args.model:
        name, folder = spec.split("=", 1)
        classifier.LOCAL_MODEL_DIR = (ROOT / folder).resolve()
        classifier.load.cache_clear()
        m = classifier.meta()
        results[name] = {"thresholds": {k: m.get(k) for k in ("threshold", "margin", "blast_threshold", "blb_threshold")},
                         "temperature": m["temperature"], "trained_on": m.get("trained_on"),
                         "cpu_latency_ms_median": round(latency_ms(), 1),
                         "sets": {s: evaluate(items, m) for s, items in sets.items()}}
        print(f"{name}: thresholds {results[name]['thresholds']} | latency {results[name]['cpu_latency_ms_median']} ms")

    lines = ["| Model | Set | n | Answered (coverage) | Right when answered | Wrong advice | of which wrong spray | "
             "Right answers by class (BLB / blast / healthy) | CPU latency |", "|---|---|---|---|---|---|---|---|---|"]
    for name, r in results.items():
        for s, e in r["sets"].items():
            acc = "n/a" if e["accuracy_when_answered"] is None else f"{e['correct_answers']}/{e['answered']} = {e['accuracy_when_answered']:.3f}"
            by = e["correct_answers_by_class"]
            lines.append(f"| {name} | {s} | {e['n']} | {e['answered']} ({e['coverage']:.3f}) | {acc} | {e['wrong_advice']} | "
                         f"{e['wrong_spray']} | {by['bacterial_leaf_blight']} / {by['blast']} / {by['healthy']} | "
                         f"{r['cpu_latency_ms_median']} ms |")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.with_suffix(".json").write_text(json.dumps(results, indent=1), "utf-8")
    args.out.with_suffix(".md").write_text("\n".join(lines) + "\n", "utf-8", newline="\n")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())

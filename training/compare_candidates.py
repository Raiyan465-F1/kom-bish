"""Compare models through the app's own code path (definitions in training/outcomes.py).

  python training/compare_candidates.py --model "v1 (previous)=models/v1" --model A=data/export_candA --model "B (published)=models"

Sets: (i) our test split, (ii) our field-photo subset (field-background test photos plus the held-out field
blast), (iii) the Paddy Doctor held-out set (never used for training, validation or thresholds).
Writes training/results/runs/candidates_comparison.json and .md. Changes no model.
"""
from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from outcomes import ROOT, classifier, photo_outcome, tally, use_model  # noqa: E402

COLUMNS = ("| Model | Set | n | Classifier confident | Advice given | Right advice | Wrong advice | "
           "Blast question asked (true blast / other = wrong spray if \"yes\") | Referred |")


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


def row(name: str, s: str, e: dict) -> str:
    return (f"| {name} | {s} | {e['n']} | {e['classifier_confident']} ({e['classifier_confident'] / e['n']:.1%}) | "
            f"{e['advice_given']} ({e['advice_given'] / e['n']:.1%}) | {e['right_advice']} | {e['wrong_advice']} | "
            f"{e['blast_question_asked']} ({e['blast_question_on_true_blast']} / {e['blast_question_on_other_classes']}) | "
            f"{e['referred']} |")


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

    results, lines = {}, [COLUMNS, "|---|---|---|---|---|---|---|---|---|"]
    for spec in args.model:
        name, folder = spec.split("=", 1)
        m = use_model(ROOT / folder)
        entry = {"thresholds": {k: m.get(k) for k in ("threshold", "margin", "blast_threshold", "blb_threshold")},
                 "temperature": m["temperature"], "trained_on": m.get("trained_on"),
                 "cpu_latency_ms_median": round(latency_ms(), 1), "sets": {}}
        for s, items in sets.items():
            rows = []
            for path, true in items:
                with Image.open(path) as im:
                    rows.append({**photo_outcome(im, m), "true": true})
            entry["sets"][s] = tally(rows)
            lines.append(row(name, s, entry["sets"][s]))
        results[name] = entry
        print(f"{name}: thresholds {entry['thresholds']} | CPU latency {entry['cpu_latency_ms_median']} ms")
    lines += ["", "CPU latency (median of 30 predictions on a 1024x768 image): "
              + "; ".join(f"{n} {r['cpu_latency_ms_median']} ms" for n, r in results.items()) + "."]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.with_suffix(".json").write_text(json.dumps(results, indent=1), "utf-8")
    args.out.with_suffix(".md").write_text("\n".join(lines) + "\n", "utf-8", newline="\n")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())

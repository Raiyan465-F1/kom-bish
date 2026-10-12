"""Choose the BLB-only threshold on the validation split, through the app's own code path. No training.

  python training/choose_blb_threshold.py            # report only
  python training/choose_blb_threshold.py --write    # also write blb_threshold into models/labels.json

Rule: the smallest threshold, never below the general threshold, at which no BLB answer on a field-background
validation photo is wrong. If no threshold reaches 0, the smallest one with the fewest wrong answers.
Only the validation split is read: no test photo, no held-out photo, no photo from outside the dataset.
model.onnx is not touched; only the one number in labels.json changes.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from outcomes import ROOT, classifier, use_model  # noqa: E402

BLB = "bacterial_leaf_blight"


def is_field(row: dict) -> bool:
    """Same split as training/train_export.py::background_of: BD5 and the white-sheet Dhan-Shomadhan photos are not field."""
    if row["source"] in ("RiceLeafBD", "PaddyDoctor"):
        return True
    return row["source"] == "DhanShomadhan" and row["source_class"].lower().startswith("field")


def grid(start: float) -> list[float]:
    return [round(start + 0.005 * i, 3) for i in range(int((0.999 - start) / 0.005) + 1)] + [0.999]


def choose(rows: list[dict], general: float, margin: float) -> tuple[float, list[dict]]:
    """rows: validation photos predicted BLB with the margin met. Returns (threshold, one table row per threshold)."""
    table = []
    for t in grid(general):
        answered = [r for r in rows if r["conf"] >= t]
        table.append({"threshold": t, "val_blb_answers": len(answered),
                      "val_wrong": sum(r["true"] != BLB for r in answered),
                      "field_val_blb_answers": sum(r["field"] for r in answered),
                      "field_val_wrong": sum(r["field"] and r["true"] != BLB for r in answered)})
    fewest = min(r["field_val_wrong"] for r in table)
    return next(r["threshold"] for r in table if r["field_val_wrong"] == fewest), table


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--prepared", type=Path, default=ROOT / "data" / "prepared_runB")
    p.add_argument("--models", type=Path, default=ROOT / "models")
    p.add_argument("--out", type=Path, default=ROOT / "training" / "results" / "runs" / "blb_threshold_v2_1")
    p.add_argument("--write", action="store_true", help="write the chosen blb_threshold into labels.json")
    args = p.parse_args(argv)

    m = use_model(args.models)
    with (args.prepared / "manifest.csv").open(encoding="utf-8", newline="") as f:
        val = [r for r in csv.DictReader(f) if r["split"] == "val"]
    rows = []
    for r in val:
        with Image.open(args.prepared / r["path"]) as im:
            pred = classifier.predict(im)
        if pred.label == BLB and pred.margin >= m["margin"]:
            rows.append({"path": r["path"], "true": r["target"], "source": r["source"],
                         "source_class": r["source_class"], "field": is_field(r), "conf": round(pred.conf, 4)})
    chosen, table = choose(rows, m["threshold"], m["margin"])
    previous = m.get("blb_threshold")
    wrong = sorted((r for r in rows if r["true"] != BLB), key=lambda r: -r["conf"])
    result = {"rule": "smallest threshold >= the general threshold with no wrong BLB answer on field-background "
                      "validation photos; if none reaches 0, the smallest with the fewest",
              "split": "val", "val_n": len(val), "val_field_n": sum(is_field(r) for r in val),
              "general_threshold": m["threshold"], "margin": m["margin"], "previous_blb_threshold": previous,
              "chosen_blb_threshold": chosen, "table": table, "wrong_blb_predictions_on_val": wrong}
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "choice.json").write_text(json.dumps(result, indent=1), "utf-8")

    print(f"validation photos: {len(val)} ({result['val_field_n']} field); predicted BLB with the margin met: {len(rows)}")
    print("threshold | BLB answers on val | wrong on val | BLB answers on field val | wrong on field val")
    for r in table:
        mark = "  <-- chosen" if r["threshold"] == chosen else "  (previous)" if r["threshold"] == previous else ""
        print(f"  {r['threshold']:<7} | {r['val_blb_answers']:<4} | {r['val_wrong']:<3} | "
              f"{r['field_val_blb_answers']:<4} | {r['field_val_wrong']}{mark}")
    print("wrong BLB predictions on validation (confidence, true class, source):")
    for r in wrong:
        print(f"  {r['conf']:.4f}  {r['true']:<8} {r['source']}/{r['source_class']}  field={r['field']}")
    print(f"previous BLB threshold {previous} -> chosen {chosen}")
    if args.write:
        path = args.models / "labels.json"
        labels = json.loads(path.read_text("utf-8"))
        labels["blb_threshold"] = chosen
        path.write_text(json.dumps(labels, indent=1), "utf-8")
        print(f"wrote blb_threshold = {chosen} to {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

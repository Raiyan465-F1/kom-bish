"""Write the Hugging Face model card from real result files only.

  python training/make_model_card.py --license mit          # or apache-2.0: the team chooses

Reads models/labels.json and training/results/metrics.json. Writes models/README.md (uploaded with the
model) and a copy at training/model_card.md (committed). Every number comes from those files.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

from make_eval_report import ABSTAIN_SENTENCE, agronomy_status, count, prop  # noqa: E402
from prepare_data import PUBLISHED_COUNTS, SOURCE_CLASS_TO_TARGET  # noqa: E402

DHS_REPO = "Project-AgML/Dhan-Shomadhan_rice_leaf_disease_classification"


def build(labels: dict, metrics: dict, licence: str) -> str:
    t, classes, cm = metrics["test"], metrics["classes"], metrics["test"]["confusion_matrix"]
    n = t["n"]
    answered = count(t["coverage"], n)
    blb, blast, dhs = t["precision_blb_answers"], t["precision_blast_answers"], metrics.get("dhs_field_blast")
    size = labels["input_size"][1]
    short = int(size / labels["crop_pct"])
    dhs_in = metrics.get("dhs_images") or {}
    dhs_trained = not metrics.get("dhs_field_blast_is_cross_source", True)
    L = ["---", f"license: {licence}", "library_name: onnx",
         "tags: [image-classification, onnx, rice, plant-disease, bangladesh]", "---", "",
         "# Kom Bish rice-leaf classifier", ""]
    if metrics.get("smoke_run"):
        L += ["> **SMOKE RUN ON SYNTHETIC OR SUBSET DATA. NOT A RESULT. DO NOT PUBLISH.**", ""]
    L += [f"4 classes: {', '.join(f'`{c}`' for c in labels['classes'])}. Base model `{labels['model']}` "
          f"(timm, Apache-2.0 weights), fine-tuned at {size} px and exported to ONNX (single file). "
          f"Trained {labels['date']}.", "",
          "## Intended use", "",
          "The classifier picks a row in Kom Bish's hand-written rule table. It is not a diagnosis. "
          "Low-confidence results are meant to be refused (abstain) and referred to the Krishi Call Centre "
          "16123 or a Sub-Assistant Agriculture Officer. The `other` class does **not** cover non-rice photos.", "",
          "## Preprocessing (must match exactly)", "",
          f"EXIF transpose, RGB, resize shorter side to {short} ({labels['interpolation']}), centre-crop {size}, "
          f"scale to 0–1, normalise with mean {tuple(labels['mean'])} and std {tuple(labels['std'])}, NCHW float32. "
          f"Input name `{labels['onnx_input']}`, output name `{labels['onnx_output']}`.", "",
          f"Calibrated probabilities: `softmax(logits / temperature)` with temperature {labels['temperature']}. "
          f"Abstain if top-1 < {labels['threshold']} (`threshold`) or top-1 − top-2 < {labels['margin']} "
          "(`margin`). All three values are in `labels.json`.", "",
          "## Training data (CC BY 4.0, credit required)", "",
          "- RiceLeafBD, DOI 10.17632/kx9rx8p2mz.1 (please also cite arXiv 2501.08912)",
          "- RiceLeafDisease-BD5, DOI 10.17632/sjkptpgv79.2",
          (f"- Dhan-Shomadhan, DOI 10.17632/znsxdctwtt.1 (via the HF mirror `{DHS_REPO}`): **used for "
           f"training** ({dhs_in.get('train', 0)} train, {dhs_in.get('val', 0)} validation, "
           f"{dhs_in.get('test', 0)} test images; \"Rice Blast\" maps to `blast`, every other disease to "
           "`other`). Part of its field-background blast images is held out and reported below."
           if dhs_trained else
           f"- Dhan-Shomadhan, DOI 10.17632/znsxdctwtt.1: field-background rows only, **held out** as a "
           f"cross-source blast test (via the HF mirror `{DHS_REPO}`). Not used for training."), "",
          "| Source | Source class | Target class | Published n |", "|---|---|---|---|"]
    L += [f"| {s} | {c} | {SOURCE_CLASS_TO_TARGET[(s, c)]} | {k} |" for (s, c), k in PUBLISHED_COUNTS.items()]
    L += ["", "## Evaluation", "",
          "Every proportion is k/n with a Wilson 95% interval. The threshold and margin were chosen on "
          "validation only.", "",
          f"- Test images: n = {n}. Macro-F1 with no abstention: {t['macro_f1_no_abstention']:.4f}",
          f"- Coverage at the threshold (images answered): {prop(answered, n)}",
          f"- Selective accuracy (correct among answered): {prop(count(t['selective_accuracy'], answered or 0), answered)}",
          f"- Precision on BLB answers: {prop(count(blb['value'], blb['n']), blb['n'])}",
          f"- Precision on blast answers: {prop(count(blast['value'], blast['n']), blast['n'])}", ""]
    if not metrics["target_met"]:
        L += [ABSTAIN_SENTENCE, ""]
    L += ["| Class | Support | Precision | Recall | F1 |", "|---|---|---|---|---|"]
    for i, c in enumerate(classes):
        row_n, col_n = sum(cm[i]), sum(r[i] for r in cm)
        L.append(f"| {c} | {row_n} | {prop(cm[i][i], col_n)} | {prop(cm[i][i], row_n)} | {t['per_class'][c]['f1']:.3f} |")
    L += ["", "Recall per (source, class), no abstention:", "",
          "| Source | Source class | Target | Recall | Abstain rate |", "|---|---|---|---|---|"]
    L += [f"| {r['source']} | {r['source_class']} | {r['target']} | {prop(count(r['recall'], r['n']), r['n'])} | "
          f"{prop(count(r['abstain_rate'], r['n']), r['n'])} |" for r in metrics["per_source"]]
    L += [""]
    if metrics.get("by_background"):
        L += ["Recall per background (BD5 leaves lie on a white sheet, RiceLeafBD photos are taken in the "
              "field, so the background can give the class away):", "",
              "| Background | True class | Recall | Abstain rate | Answered wrong |", "|---|---|---|---|---|"]
        L += [f"| {r['background']} | {r['target']} | {prop(count(r['recall'], r['n']), r['n'])} | "
              f"{prop(count(r['abstain_rate'], r['n']), r['n'])} | "
              f"{prop(count(r['answered_wrong_rate'], r['n']), r['n'])} |" for r in metrics["by_background"]]
        L += [""]
    if dhs:
        kind = "held-out slice of a source the model has seen, not a cross-source test" if dhs_trained \
            else "cross-source"
        L += [f"Dhan-Shomadhan field blast ({kind}, n = {dhs['n']}): blast recall "
              f"{prop(count(dhs['blast_recall'], dhs['n']), dhs['n'])}; abstain rate "
              f"{prop(count(dhs['abstain_rate'], dhs['n']), dhs['n'])}.", ""]
    else:
        L += ["Dhan-Shomadhan field blast: not measured in this run, so there is no cross-source blast test.", ""]
    L += ["## Limitations", "",
          "- Every BLB image comes from one dataset (RiceLeafBD, field photos) and most blast images from "
          "another (BD5, leaves on a white sheet), so the model can learn the source or the background rather "
          "than the disease. A first run without Dhan-Shomadhan did exactly that. The per-source and "
          "per-background numbers above are the honest check.",
          "- Not tested on non-rice photos beyond the team's own junk-photo test (see the project README).",
          f"- Agronomy review: {agronomy_status()}.",
          "- No field trial.", "",
          "## Files", "", "`model.onnx`, `labels.json`."]
    return "\n".join(L) + "\n"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--license", required=True, choices=["mit", "apache-2.0"],
                   help="licence for the fine-tuned model: the team's choice, no default")
    p.add_argument("--labels", type=Path, default=ROOT / "models" / "labels.json")
    p.add_argument("--metrics", type=Path, default=ROOT / "training" / "results" / "metrics.json")
    p.add_argument("--out", type=Path, nargs="*",
                   default=[ROOT / "models" / "README.md", ROOT / "training" / "model_card.md"])
    p.add_argument("--allow-smoke", action="store_true", help="code check only; never publish the output")
    args = p.parse_args(argv)
    labels = json.loads(args.labels.read_text("utf-8"))
    metrics = json.loads(args.metrics.read_text("utf-8"))
    if metrics.get("smoke_run") and not args.allow_smoke:
        raise SystemExit("metrics.json is from a smoke run (--subset / --no-pretrained). Use the real Kaggle output.")
    card = build(labels, metrics, args.license)
    for path in args.out:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(card, "utf-8")
        print(f"Wrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

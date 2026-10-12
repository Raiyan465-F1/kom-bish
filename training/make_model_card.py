"""Write the Hugging Face model card from real result files only.

  python training/make_model_card.py --license mit          # the team chose MIT on 11 Oct 2026

Reads models/labels.json and training/results/ (metrics.json, runs/candidates_comparison.json,
runs/blb_threshold_v2_1/choice.json, external_test.json). Writes models/README.md (uploaded with the model) and
training/model_card.md (committed).
Every number comes from those files; the definitions are the ones in training/outcomes.py.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

from make_eval_report import (ABSTAIN_SENTENCE, DEFINITIONS, PUBLISHED, agronomy_status, comparison_table,  # noqa: E402
                              load, outcome_lines, prop)
from prepare_data import PUBLISHED_COUNTS, SOURCE_CLASS_TO_TARGET  # noqa: E402

DHS_REPO = "Project-AgML/Dhan-Shomadhan_rice_leaf_disease_classification"


def published_outcomes(cmp: dict | None) -> dict:
    """Outcomes of the published model through the app's code path, at the thresholds in labels.json."""
    sets = ((cmp or {}).get(PUBLISHED) or {}).get("sets") or {}
    return {"test": sets.get("our test split"), "field": sets.get("our field photos"),
            "held": sets.get("Paddy Doctor held-out")}


def framing(cmp: dict | None, ext: dict | None) -> list[str]:
    """The one-paragraph claim, every number taken from the result files."""
    o = published_outcomes(cmp)
    held = o["held"]
    if not (o["test"] and o["field"] and held and ext):
        return []

    def healthy(src: dict) -> str:
        h = src["by_true_class"]["healthy"]
        return f"{h['right_advice']} of {h['n']}"

    wrong_spray = sum(s["blast_question_on_other_classes"] for s in (o["test"], o["field"], held, ext))
    blb_asked = sum(s["blb_question_asked"] for s in (o["test"], held, ext))
    blb_not_blb = sum(s["blb_question_on_other_classes"] for s in (o["test"], held, ext))
    return [
        "**What this model is for.** Kom Bish is a safe-by-design spray adviser, and this classifier is its "
        "photo step. It recognises healthy leaves and refers unfamiliar diseases to the Krishi Call Centre 16123 "
        "or an agriculture officer; it does not diagnose. True healthy leaves given the \"no spray now\" answer: "
        f"{healthy(o['test'])} on our Bangladesh test split, {healthy(o['field'])} on our field photos, "
        f"{healthy(held)} on the Paddy Doctor held-out set (India; **same source as some training data**) and "
        f"{healthy(ext)} on the {ext['dataset']['name']} ({ext['dataset']['country']}; truly external, the rest "
        f"were referred). Wrong \"spray correctly\" advice across all of these: {wrong_spray}. Known limit: on the "
        f"external test {ext['wrong_advice']} blast leaf was told \"no spray now\". The BLB answer (\"no "
        "insecticide needed, fix the fertiliser\") is given only after the farmer answers \"yes\" to a question "
        f"about the patches: across the test split, the held-out set and the external test that question was asked "
        f"{blb_asked} times, {blb_not_blb} of them on a photo that is not BLB. Recognising diseases needs "
        "local data: on the external test almost every diseased leaf was referred, not recognised.", ""]


def build(labels: dict, metrics: dict, licence: str) -> str:
    t = metrics["test"]
    size = labels["input_size"][1]
    short = int(size / labels["crop_pct"])
    dhs_in, paddy = metrics.get("dhs_images") or {}, metrics.get("paddy_doctor_images") or {}
    cmp, ext = load("runs/candidates_comparison.json"), load("external_test.json")
    o, blb_choice = published_outcomes(cmp), load("runs/blb_threshold_v2_1/choice.json")
    if blb_choice and blb_choice["chosen_blb_threshold"] != labels.get("blb_threshold"):
        raise SystemExit("labels.json blb_threshold differs from runs/blb_threshold_v2_1/choice.json")
    L = ["---", f"license: {licence}", "library_name: onnx",
         "tags: [image-classification, onnx, rice, plant-disease, bangladesh]", "---", "",
         "# Kom Bish rice-leaf classifier", ""]
    if metrics.get("smoke_run"):
        L += ["> **SMOKE RUN ON SYNTHETIC OR SUBSET DATA. NOT A RESULT. DO NOT PUBLISH.**", ""]
    L += [f"4 classes: {', '.join(f'`{c}`' for c in labels['classes'])}. Base model `{labels['model']}` (timm, "
          f"Apache-2.0 weights), fine-tuned at {size} px and exported to ONNX (single file). Trained {labels['date']}.", "",
          *framing(cmp, ext),
          "**Versions.** The weights are version 2, frozen on 11 Oct 2026; `model.onnx` has not changed since. "
          + (f"On 12 Oct 2026 the BLB threshold in `labels.json` was raised from {blb_choice['previous_blb_threshold']} "
             f"to {blb_choice['chosen_blb_threshold']} (revision `v2.1`, this one); the 11 Oct thresholds are kept as "
             "revision `v2`. " if blb_choice else "")
          + "The previous model, trained without Paddy Doctor, is kept "
          "as revision `v1`: `hf_hub_download(repo_id, \"model.onnx\", revision=\"v1\")`.", "",
          "## Intended use", "",
          "The classifier picks a row in Kom Bish's hand-written rule table. It is not a diagnosis. Low-confidence "
          "results are refused and the farmer is referred to the Krishi Call Centre 16123 or a Sub-Assistant "
          "Agriculture Officer. It expects a **close-up of one rice leaf**. The `other` class does **not** cover "
          "non-rice photos.", "",
          "## Preprocessing and thresholds (must match exactly)", "",
          f"EXIF transpose, RGB, resize shorter side to {short} ({labels['interpolation']}), centre-crop {size}, scale "
          f"to 0–1, normalise with mean {tuple(labels['mean'])} and std {tuple(labels['std'])}, NCHW float32. Input "
          f"`{labels['onnx_input']}`, output `{labels['onnx_output']}`. Calibrated probabilities: "
          f"`softmax(logits / {labels['temperature']})`.", "",
          f"Refuse when top-1 < {labels['threshold']} (`threshold`) or top-1 − top-2 < {labels['margin']} (`margin`). "
          f"Blast is the only class that leads to spray advice, so a blast prediction is also refused below "
          f"{labels.get('blast_threshold')} (`blast_threshold`, the smallest value with no wrong blast answer on "
          "validation)."
          + (f" A BLB prediction is also refused below {labels['blb_threshold']} (`blb_threshold`, the smallest value "
             + (f"with no wrong BLB answer on the {blb_choice['val_field_n']} field-background validation photos; chosen "
                "on validation only)." if blb_choice else "chosen on validation only).")
             if labels.get("blb_threshold") is not None else "")
          + " In the Kom Bish app a blast answer additionally needs the farmer's \"yes\" to a lesion-shape question, "
          "and a BLB answer needs the farmer's \"yes\" to a question about where the patches start.", "",
          "## Training data (credit required)", "",
          "- RiceLeafBD, DOI 10.17632/kx9rx8p2mz.1, CC BY 4.0 (please also cite arXiv 2501.08912)",
          "- RiceLeafDisease-BD5, DOI 10.17632/sjkptpgv79.2, CC BY 4.0",
          f"- Dhan-Shomadhan, DOI 10.17632/znsxdctwtt.1, CC BY 4.0, via the HF mirror `{DHS_REPO}`: "
          f"{dhs_in.get('train', 0)} train, {dhs_in.get('val', 0)} validation, {dhs_in.get('test', 0)} test images "
          "(\"Rice Blast\" → `blast`, every other disease → `other`); 18 field blast photos held out."]
    if paddy.get("train"):
        L += [f"- **Paddy Doctor**, CC BY 4.0 (Kaggle competition rules, section 7.A): {paddy['train']} train and "
              f"{paddy.get('val', 0)} validation images; 500 more are held out and never trained on. Petchiammal A, "
              "Briskline Kiruba S, D. Murugan, Pandarasamy A (2022), \"Paddy Doctor: A Visual Image Dataset for "
              "Automated Paddy Disease Classification and Benchmarking\", arXiv:2205.11108. Project page: "
              "https://paddydoc.github.io/ . Data: https://www.kaggle.com/competitions/paddy-disease-classification . "
              "Bacterial leaf blight → `bacterial_leaf_blight`, blast → `blast`, normal → `healthy`, every other "
              "class → `other`."]
    L += ["", "| Source | Source class | Target class | Published n |", "|---|---|---|---|"]
    L += [f"| {s} | {c} | {SOURCE_CLASS_TO_TARGET[(s, c)]} | {k} |" for (s, c), k in PUBLISHED_COUNTS.items()]
    L += ["", f"Augmentation: {metrics.get('augmentation', 'standard')} (random zoom-out onto field backgrounds, wider "
          "crops, rotation, mild blur, JPEG re-compression, brightness and contrast jitter; no hue shift).", "",
          "## Evaluation", "", "Definitions, the same in every table:", "", *DEFINITIONS, "",
          f"**Our test split, n = {t['n']}:** macro-F1 of the top guess {t['macro_f1_no_abstention']:.4f}."]
    if o.get("test"):
        L += ["", "Outcomes through the app's code path, both confirmation questions unanswered:", "",
              *outcome_lines(o["test"])]
    if o.get("field"):
        L += ["", f"**Our field photos, n = {o['field']['n']}** (field-background test photos plus 18 held-out field "
              "blast photos):", "", *outcome_lines(o["field"])]
    if not metrics["target_met"]:
        L += ["", ABSTAIN_SENTENCE]
    if cmp:
        L += ["", "### Three models through the app's code path", "",
              "v1 = the previous model (revision `v1`); A = stronger augmentation only (not published); B = this "
              "model with its current thresholds. The table was made again on 12 Oct 2026 with the BLB question in the "
              "rule engine. The Paddy Doctor held-out set (500 photos never used for training, validation or thresholds) is "
              "the **same source as some training data** of this model, so it is not an external test.", "",
              *comparison_table(cmp)]
    if ext:
        d = ext["dataset"]
        L += ["", "### External test (a dataset the model has never seen)", "",
              f"**{d['name']} ({d['country']}), n = {ext['n']}.** Source: {d['source']}. Licence: {d['licence']}. "
              f"{d['credit']} {ext['leak_check']['near_duplicates_dropped']} near-duplicates of the training data "
              "dropped. First scored on 11 Oct 2026, after the model and thresholds were fixed; scored again on the "
              f"same sample on {ext['date']} after the BLB question and the higher BLB threshold. Nothing was changed "
              "because of this set.", "",
              *outcome_lines(ext), f"- Top guess right, no abstention: {prop(ext['top_guess_right'], ext['n'])}"]
        if ext.get("junk"):
            L += [f"- Not-a-rice-leaf images from the same dataset: {prop(ext['junk']['referred'], ext['junk']['n'])} "
                  "referred"]
    L += ["", "## Known limits", "",
          "- **Diseases are not recognised on a new source.** On the external test the model recognises healthy "
          "leaves and refers almost every diseased one. Treat a referral as the normal outcome.",
          "- **Close-up web photos of blast were not recognised.** Four textbook-style blast photos from the web "
          "(not a test set; labels not checked by an agronomist) were tried on 11 Oct 2026: none was called blast, "
          "and one was called BLB with confidence 0.940. That led to the BLB question and the higher BLB threshold.",
          "- **The Paddy Doctor held-out result is the same source as some training data.** It is not an external test.",
          f"- **Blast is rarely answered** (blast threshold {labels.get('blast_threshold')}). On our own test photos "
          "the blast question is never reached; on the Paddy Doctor held-out set it is reached for a few photos.",
          "- **Narrow brown spot leaves on a white sheet are told \"no spray now\"**: 11 of the wrong answers on our "
          "test split are BD5 narrow brown spot photos answered `healthy`.",
          "- The model was trained on close-ups of one leaf and on Paddy Doctor's wider field shots. Other framings "
          "and other countries are untested beyond the external test above.",
          "- Every BLB image in our own data comes from one dataset (field photos) and most blast images from "
          "another (leaves on a white sheet). The first model learned the background instead of the disease.",
          "- The test split was looked at while comparing training runs, so its numbers are somewhat optimistic.",
          "- BD5's official archive holds 3,150 images although its description says 2,545; we used the archive.",
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
        raise SystemExit("metrics.json is from a smoke run (--subset / --no-pretrained). Use the real training output.")
    card = build(labels, metrics, args.license)
    for path in args.out:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(card, "utf-8")
        print(f"Wrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Build training/eval_report.md and training/eval_summary.json from real result files only.

  python training/make_eval_report.py        # run in .venv

Reads training/results/metrics.json (step 10) and training/results/own_photos.json (step 20), and runs the
off-script test. Every number is copied or counted from those files; nothing is typed by hand. A metrics
file from a smoke run (--subset / --no-pretrained) is refused.
"""
from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "training" / "results"
SUMMARY_KEYS = [
    "test_n", "test_macro_f1", "temperature", "threshold", "margin", "coverage", "selective_accuracy",
    "prec_blb_answers", "prec_blb_answers_n", "prec_blast_answers", "prec_blast_answers_n", "target_met",
    "dhs_blast_n", "dhs_blast_recall", "dhs_blast_abstain_rate", "own_healthy_n", "own_healthy_false_trigger_n",
    "own_healthy_false_trigger_rate", "own_symptomatic_n", "junk_n", "junk_refused_n", "junk_refusal_rate",
    "offscript_n", "offscript_failures", "invented_doses",
    # Added after run 1: readers must know whether the dhs_blast_* numbers are a true cross-source test.
    "dhs_is_cross_source", "threshold_rule",
    # What a farmer with a field photo gets: advice (BLB, blast or healthy answer) or a referral.
    "field_n", "field_advice_given", "field_wrong_advice", "field_blast_n", "field_blast_correct_advice",
    "field_blast_referred", "field_blast_wrong_advice", "field_blb_n", "field_blb_correct_advice",
    "field_blb_referred", "field_blb_wrong_advice",
    # Spray advice is stricter: blast has its own threshold.
    "blast_threshold", "coverage_before_blast_threshold", "blast_answers_n", "blast_answers_wrong",
    "field_blast_answers_n",
]
ABSTAIN_SENTENCE = "The model abstains more than we would like."


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return float("nan"), float("nan")
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (c - h) / d, (c + h) / d


def prop(k: int | None, n: int | None) -> str:
    """'k/n = 0.xxx (95% CI a-b)', or a plain note when there is nothing to divide."""
    if n == 0:
        return "n = 0"
    if k is None or n is None:
        return "not measured"
    lo, hi = wilson(k, n)
    return f"{k}/{n} = {k / n:.3f} (95% CI {lo:.3f}–{hi:.3f})"


def count(rate: float | None, n: int) -> int | None:
    """Recover the integer count behind a stored proportion (rate = k / n exactly)."""
    return None if rate is None else int(round(rate * n))


def run_offscript() -> dict:
    """Run the off-script test in a subprocess: pass/fail from pytest, counts from run_offscript()."""
    utf8 = {"text": True, "encoding": "utf-8", "errors": "replace"}   # test output can contain Bangla
    passed = subprocess.run([sys.executable, "-m", "pytest", "-q", "tests/test_offscript.py"],
                            cwd=ROOT, capture_output=True, **utf8).returncode == 0
    out = subprocess.run(
        [sys.executable, "-c",
         "import json; from tests.test_offscript import run_offscript; r = run_offscript(); "
         "r.pop('details'); print(json.dumps(r))"],
        cwd=ROOT, capture_output=True, check=True, **utf8).stdout
    return {**json.loads(out.strip().splitlines()[-1]), "pytest_passed": passed}


def first_run_sentence() -> str:
    """What the run without Dhan-Shomadhan in training measured, read from its own metrics file."""
    path = RESULTS / "runs" / "run1_no_dhs" / "metrics.json"
    if not path.exists():
        return ""
    d = json.loads(path.read_text("utf-8")).get("dhs_field_blast")
    if not d:
        return ""
    return (f"An earlier run without them recognised {count(d['blast_recall'], d['n'])} of {d['n']} "
            "field-background blast photos (`results/runs/run1_no_dhs/metrics.json`), so they were added. ")


def agronomy_status() -> str:
    gates = ROOT / "docs" / "gates.md"
    if gates.exists():
        for line in gates.read_text("utf-8").splitlines():
            if line.lower().startswith("- agronomy review:"):
                return line.split(":", 1)[1].strip()
    return "not reviewed by an agronomist"


def build(metrics: dict, own: dict | None, off: dict, image_prefix: str) -> tuple[str, dict]:
    t, classes, cm = metrics["test"], metrics["classes"], metrics["test"]["confusion_matrix"]
    n = t["n"]
    answered = count(t["coverage"], n)
    blb, blast = t["precision_blb_answers"], t["precision_blast_answers"]
    dhs = metrics.get("dhs_field_blast")
    healthy = (own or {}).get("healthy_looking")
    symptomatic = (own or {}).get("symptomatic")
    junk = (own or {}).get("junk")

    def rate(k, total):
        return None if (k is None or not total) else k / total

    summary = {
        "test_n": n, "test_macro_f1": t["macro_f1_no_abstention"], "temperature": metrics["temperature"],
        "threshold": metrics["threshold"], "margin": metrics["margin"], "coverage": t["coverage"],
        "selective_accuracy": t["selective_accuracy"],
        "prec_blb_answers": blb["value"], "prec_blb_answers_n": blb["n"],
        "prec_blast_answers": blast["value"], "prec_blast_answers_n": blast["n"],
        "target_met": metrics["target_met"],
        "dhs_blast_n": dhs["n"] if dhs else None, "dhs_blast_recall": dhs["blast_recall"] if dhs else None,
        "dhs_blast_abstain_rate": dhs["abstain_rate"] if dhs else None,
        "own_healthy_n": healthy["n"] if healthy else None,
        "own_healthy_false_trigger_n": healthy["false_trigger_n"] if healthy else None,
        "own_healthy_false_trigger_rate": rate(healthy["false_trigger_n"], healthy["n"]) if healthy else None,
        "own_symptomatic_n": symptomatic["n"] if symptomatic else None,
        "junk_n": junk["n"] if junk else None, "junk_refused_n": junk["refused_n"] if junk else None,
        "junk_refusal_rate": rate(junk["refused_n"], junk["n"]) if junk else None,
        "offscript_n": off["n"], "offscript_failures": off["offscript_failures"],
        "invented_doses": off["invented_doses"],
        "dhs_is_cross_source": metrics.get("dhs_field_blast_is_cross_source", True),
        "threshold_rule": metrics.get("threshold_rule"),
    }
    field = (metrics.get("advice") or {}).get("field") or {}
    by_true = field.get("by_true_class") or {}
    f_blast, f_blb = by_true.get("blast") or {}, by_true.get("bacterial_leaf_blight") or {}
    summary.update({
        "field_n": field.get("n"), "field_advice_given": field.get("advice_given"),
        "field_wrong_advice": field.get("wrong_advice"),
        "field_blast_n": f_blast.get("n"), "field_blast_correct_advice": f_blast.get("correct_advice"),
        "field_blast_referred": f_blast.get("referred"), "field_blast_wrong_advice": f_blast.get("wrong_advice"),
        "field_blb_n": f_blb.get("n"), "field_blb_correct_advice": f_blb.get("correct_advice"),
        "field_blb_referred": f_blb.get("referred"), "field_blb_wrong_advice": f_blb.get("wrong_advice"),
    })
    all_blast = (((metrics.get("advice") or {}).get("all") or {}).get("by_answer") or {}).get("blast") or {}
    summary.update({
        "blast_threshold": metrics.get("blast_threshold"),
        "coverage_before_blast_threshold": (metrics.get("coverage_before_blast_threshold") or {}).get("test"),
        "blast_answers_n": all_blast.get("given"), "blast_answers_wrong": all_blast.get("wrong"),
        "field_blast_answers_n": ((field.get("by_answer") or {}).get("blast") or {}).get("given"),
    })
    assert list(summary) == SUMMARY_KEYS

    L: list[str] = ["# Kom Bish evaluation report", ""]
    if metrics.get("smoke_run"):
        L += ["> **SMOKE RUN ON SYNTHETIC OR SUBSET DATA. NOT A RESULT. DO NOT REPORT ANY NUMBER BELOW.**", ""]
    L += [f"Model `{metrics['model']}`, trained {metrics['date']}. Every proportion is shown as k/n with a "
          "Wilson 95% interval.", "",
          "## Method", "",
          "Byte-identical duplicate files were removed, and photos filed under two classes with different "
          "targets were dropped. Images were then split once, before any augmentation, into "
          "train/validation/test (70/15/15, seed 42, stratified by source and class; near-duplicate images "
          "kept in one split). One temperature "
          f"T = {metrics['temperature']:.4f}" + (" (clamped)" if metrics["temperature_clamped"] else "")
          + " was fitted on validation logits. The abstain threshold "
          f"t = {metrics['threshold']:.2f} and margin = {metrics['margin']} were chosen on validation only "
          f"(target: precision ≥ {metrics['target']['precision']} on answered images at coverage ≥ "
          f"{metrics['target']['coverage']}), never on test. The app abstains when calibrated top-1 confidence "
          "is below t or top-1 minus top-2 is below the margin, and then refers the farmer to 16123 or an officer.",
          ""]
    if metrics.get("threshold_rule"):
        L += [f"Threshold rule used: {metrics['threshold_rule']}.", ""]
    if metrics.get("blast_threshold") is not None:
        before = metrics["coverage_before_blast_threshold"]
        L += ["**Spray advice is held to a stricter standard than no-spray advice.** Blast is the only answer "
              f"that tells a farmer to spray, so it has its own threshold: {metrics['blast_threshold']}, the "
              "smallest value at which no blast answer on validation was wrong "
              f"({metrics['val_blast_answers_at_blast_threshold']} validation blast answers remain). This lowered "
              f"test coverage from {before['test']:.4f} to {t['coverage']:.4f}. Zero wrong on validation is not "
              "zero wrong everywhere: see the blast row in the tables below. In the app, a blast answer also "
              "needs the farmer's own \"yes\" to a lesion-shape question; that question cannot be measured on "
              "photo datasets and is not part of any number here.", ""]
    dhs_in = metrics.get("dhs_images") or {}
    cross_source = metrics.get("dhs_field_blast_is_cross_source", True)
    if not cross_source:
        L += [f"Dhan-Shomadhan images are part of training in this run ({dhs_in.get('train', 0)} train, "
              f"{dhs_in.get('val', 0)} validation, {dhs_in.get('test', 0)} test). " + first_run_sentence()
              + "The cost: there is no longer any blast test from a source the model has never seen.", ""]
    if not metrics["target_met"]:
        L += [f"**{ABSTAIN_SENTENCE}** No threshold met the target on validation.", ""]
    if not metrics["spray_relevant_precision_ok"]:
        L += ["**Warning:** precision on BLB or blast answers was below the target on validation. These are "
              "the costly errors.", ""]

    L += ["## 1. In-distribution test split", "",
          f"n = {n}. Macro-F1 with no abstention: **{t['macro_f1_no_abstention']:.4f}**.", "",
          "| Class | Support | Precision | Recall | F1 |", "|---|---|---|---|---|"]
    for i, c in enumerate(classes):
        row_n, col_n = sum(cm[i]), sum(r[i] for r in cm)
        L.append(f"| {c} | {row_n} | {prop(cm[i][i], col_n)} | {prop(cm[i][i], row_n)} | "
                 f"{t['per_class'][c]['f1']:.3f} |")
    L += ["", f"At t = {metrics['threshold']:.2f}, margin = {metrics['margin']}:", "",
          f"- Coverage (images answered): {prop(answered, n)}",
          f"- Selective accuracy (correct among answered): {prop(count(t['selective_accuracy'], answered or 0), answered)}",
          f"- Precision on BLB answers: {prop(count(blb['value'], blb['n']), blb['n'])}",
          f"- Precision on blast answers: {prop(count(blast['value'], blast['n']), blast['n'])}", "",
          "Abstained share by true class: " + ", ".join(
              f"{c} {'n/a' if v is None else f'{v:.3f}'}" for c, v in t["abstained_pct_by_true_class"].items()) + ".",
          "", "Confusion matrix (rows = true class, columns = predicted, no abstention):", "",
          "| true \\ predicted | " + " | ".join(classes) + " |", "|---|" + "---|" * len(classes)]
    L += [f"| {c} | " + " | ".join(str(v) for v in cm[i]) + " |" for i, c in enumerate(classes)]
    L += ["", f"![Confusion matrix]({image_prefix}confusion.png)", "",
          f"![Risk-coverage curve]({image_prefix}risk_coverage.png)", "",
          "## 2. Recall per source", "",
          "Every BLB image comes from RiceLeafBD and every training blast image from BD5, so this table shows "
          "whether one source carries the result.", "",
          "| Source | Source class | Target | Recall (no abstention) | Abstain rate |", "|---|---|---|---|---|"]
    for r in metrics["per_source"]:
        L.append(f"| {r['source']} | {r['source_class']} | {r['target']} | "
                 f"{prop(count(r['recall'], r['n']), r['n'])} | {prop(count(r['abstain_rate'], r['n']), r['n'])} |")
    if metrics.get("by_background"):
        L += ["", "### Recall per background", "",
              "BD5 leaves lie on a white sheet and RiceLeafBD photos are taken in the field, so the background "
              "can give the class away. Farmers will send field photos, so the field rows matter most. "
              "\"Answered wrong\" is the share that got a confident wrong answer instead of a referral.", "",
              "| Background | True class | Recall (no abstention) | Abstain rate | Answered wrong |",
              "|---|---|---|---|---|"]
        for r in metrics["by_background"]:
            L.append(f"| {r['background']} | {r['target']} | {prop(count(r['recall'], r['n']), r['n'])} | "
                     f"{prop(count(r['abstain_rate'], r['n']), r['n'])} | "
                     f"{prop(count(r['answered_wrong_rate'], r['n']), r['n'])} |")
    if metrics.get("advice"):
        L += ["", "### What the farmer gets (advice-level outcomes)", "",
              "A BLB, blast or healthy answer above the threshold is **advice**. An `other` answer or an "
              "abstention is a **referral** to 16123 or an officer, which is safe. **Wrong advice** is the "
              "harmful outcome: advice that does not match the true class.", ""]
        for key, title in (("field", "Field-background photos (test split plus the held-out field blast)"),
                           ("all", "All test photos (plus the held-out field blast)")):
            a = metrics["advice"].get(key)
            if not a:
                continue
            L += [f"**{title}, n = {a['n']}.** Advice given: {prop(a['advice_given'], a['n'])}. "
                  f"Wrong advice among advice given: {prop(a['wrong_advice'], a['advice_given'])}.", "",
                  "| True class | n | Correct advice | Referred | Wrong advice |", "|---|---|---|---|---|"]
            for cls, r in a["by_true_class"].items():
                correct = prop(r["correct_advice"], r["n"]) if "correct_advice" in r else "(a referral is the right outcome)"
                L.append(f"| {cls} | {r['n']} | {correct} | {prop(r['referred'], r['n'])} | "
                         f"{prop(r['wrong_advice'], r['n'])} |")
            L += ["", "Wrong among each kind of advice: " + "; ".join(
                f"{c} answers {prop(v['wrong'], v['given'])}" for c, v in a["by_answer"].items()) + ".", ""]
    title = "cross-source" if cross_source else "held-out slice of a source the model has seen"
    L += ["", f"## 3. Dhan-Shomadhan field blast ({title})", ""]
    if dhs:
        L += [f"n = {dhs['n']} field-background blast images "
              + ("from a dataset the model never trained on." if cross_source else
                 "held out from Dhan-Shomadhan. Other Dhan-Shomadhan images were used for training, so this is "
                 "**not** a cross-source test; with n this small the interval is wide."), "",
              f"- Blast recall (no abstention): {prop(count(dhs['blast_recall'], dhs['n']), dhs['n'])}",
              f"- Abstain rate: {prop(count(dhs['abstain_rate'], dhs['n']), dhs['n'])}",
              f"- Answered as blast: {prop(count(dhs['answered_as_blast'], dhs['n']), dhs['n'])}", ""]
    else:
        L += ["Not measured: the Dhan-Shomadhan images were not available in this run, so there is no "
              "cross-source blast test.", ""]
    leak_path = RESULTS / "leak_check.json"
    if leak_path.exists():
        k = json.loads(leak_path.read_text("utf-8"))
        full, clean = k["full"], k["without_leaked"]
        L += ["### Near-duplicate leak check", "",
              f"`training/check_leakage.py` compared every validation, test and held-out image with every "
              f"training image (64-bit perceptual hash, Hamming distance ≤ {k['phash_distance']}, any class, any "
              f"source). {k['leaked_test_images']} of {k['test_and_heldout_images']} test and held-out images and "
              f"{k['leaked_val_images']} of {k['val_images']} validation images have a near-duplicate in "
              "training. The shipped model through the app's own ONNX code path:", "",
              "| | Test n | Macro-F1 (no abstention) | Coverage | Selective accuracy | Field wrong advice |",
              "|---|---|---|---|---|---|"]
        for name, r in (("All test images", full), ("Without leaked test images", clean)):
            L.append(f"| {name} | {r['test_n']} | {r['macro_f1_no_abstention']:.4f} | {r['coverage']:.4f} | "
                     f"{r['selective_accuracy']:.4f} | {r['field']['wrong_advice']}/{r['field']['advice_given']} |")
        L += ["", "These ONNX-on-CPU numbers differ from the tables above (computed in PyTorch on the GPU) by one "
              "or two borderline images; the app runs the ONNX model.", ""]
        if k.get("field_wrong_advice"):
            L += ["Field photos that got wrong advice:", "", "| Photo | True class | Answered as | Confidence |",
                  "|---|---|---|---|"]
            L += [f"| `{w['photo']}` | {w['true_class']} | {w['answered_as']} | {w['confidence']} |"
                  for w in k["field_wrong_advice"]]
            L += [""]
    L += ["## 4. The team's own photos and junk photos", ""]
    if own:
        L += ["Own-photo labels are \"healthy-looking\" vs \"symptomatic\" as judged by the team, not diagnoses.", "",
              f"- Healthy-looking leaves wrongly answered as BLB or blast (false trigger): "
              f"{prop(healthy['false_trigger_n'], healthy['n'])}. Rule counts: {healthy['rule_counts']}",
              f"- Symptomatic leaves: n = {symptomatic['n']}. Rule counts: {symptomatic['rule_counts']} "
              "(no accuracy claim: there are no ground-truth labels).",
              f"- Junk photos (not rice leaves) refused with a referral: {prop(junk['refused_n'], junk['n'])}. "
              f"Rule counts: {junk['rule_counts']}", ""]
    else:
        L += ["Not measured yet: `training/results/own_photos.json` does not exist (steps 19 and 20).", ""]
    L += ["## 5. Off-script test", ""]
    if off["pytest_passed"] and off["offscript_failures"] == 0 and off["invented_doses"] == 0:
        L += [f"**0 off-script answers and 0 invented doses in {off['n']} test consultations** "
              "(`tests/test_offscript.py`): every sentence shown came from `data/rules.csv` or `data/clips.csv`.", ""]
    else:
        L += [f"**The off-script test did not pass:** {off['offscript_failures']} off-script answers and "
              f"{off['invented_doses']} answers with a forbidden term in {off['n']} test consultations "
              f"({off['wrong_rule']} with an unexpected rule).", ""]
    L += ["## Limitations", "",
          "- Source and background confound: every BLB image comes from RiceLeafBD (field photos) and most "
          "blast images from BD5 (leaves on a white sheet). A model can learn the background instead of the "
          "disease; the first run did exactly that. Sections 2 and 3 are the honest check.",
          "- BD5's official archive (version 2, SHA-256 verified) holds 3,150 images, while its own description "
          "says 2,545. We used what the archive contains (`docs/gates.md`).",
          "- Dhan-Shomadhan is in the training data, which removed the only external test: no number in this "
          "report comes from a dataset the model has never seen.",
          "- The test split was looked at during development: several training runs were compared, and the "
          "threshold rule was tightened after seeing early results (`docs/gates.md` lists every run). The "
          "numbers here are therefore somewhat optimistic. Only a new, untouched set of field photos would "
          "give a clean estimate.",
          "- With this few test images per minority class, one or two images move a recall by several points; "
          "read the intervals, not the point values.",
          "- Own-photo labels are healthy-looking vs symptomatic, not diagnoses.",
          "- The `other` class does not cover non-rice photos; section 4 is the only junk-photo test.",
          "- No field trial. Nobody checked what a farmer did after an answer.",
          f"- Agronomy review: {agronomy_status()}."]
    if not metrics["target_met"]:
        L.append(f"- {ABSTAIN_SENTENCE}")
    return "\n".join(L) + "\n", summary


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--metrics", type=Path, default=RESULTS / "metrics.json")
    p.add_argument("--own", type=Path, default=RESULTS / "own_photos.json")
    p.add_argument("--out-dir", type=Path, default=ROOT / "training")
    p.add_argument("--allow-smoke", action="store_true",
                   help="code check only: accept a smoke-run metrics file (never commit the output)")
    args = p.parse_args(argv)

    metrics = json.loads(args.metrics.read_text("utf-8"))
    if metrics.get("smoke_run") and not args.allow_smoke:
        raise SystemExit("metrics.json is from a smoke run (--subset / --no-pretrained). Use the real Kaggle output.")
    own = json.loads(args.own.read_text("utf-8")) if args.own.exists() else None
    if own is None:
        print(f"WARNING: {args.own} not found. Own-photo and junk numbers will be null (run eval_own_photos.py).")
    off = run_offscript()
    image_prefix = "results/" if args.out_dir.resolve() == (ROOT / "training").resolve() else ""
    report, summary = build(metrics, own, off, image_prefix)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "eval_report.md").write_text(report, "utf-8")
    (args.out_dir / "eval_summary.json").write_text(json.dumps(summary, indent=1), "utf-8")
    print(f"Wrote {args.out_dir / 'eval_report.md'} and eval_summary.json")
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

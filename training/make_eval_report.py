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
    passed = subprocess.run([sys.executable, "-m", "pytest", "-q", "tests/test_offscript.py"],
                            cwd=ROOT, capture_output=True, text=True).returncode == 0
    out = subprocess.run(
        [sys.executable, "-c",
         "import json; from tests.test_offscript import run_offscript; r = run_offscript(); "
         "r.pop('details'); print(json.dumps(r))"],
        cwd=ROOT, capture_output=True, text=True, check=True).stdout
    return {**json.loads(out.strip().splitlines()[-1]), "pytest_passed": passed}


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
    }
    assert list(summary) == SUMMARY_KEYS

    L: list[str] = ["# Kom Bish evaluation report", ""]
    if metrics.get("smoke_run"):
        L += ["> **SMOKE RUN ON SYNTHETIC OR SUBSET DATA. NOT A RESULT. DO NOT REPORT ANY NUMBER BELOW.**", ""]
    L += [f"Model `{metrics['model']}`, trained {metrics['date']}. Every proportion is shown as k/n with a "
          "Wilson 95% interval.", "",
          "## Method", "",
          "Images were split once, before any augmentation, into train/validation/test (70/15/15, seed 42, "
          "stratified by source and class; byte-identical images kept in one split). One temperature "
          f"T = {metrics['temperature']:.4f}" + (" (clamped)" if metrics["temperature_clamped"] else "")
          + " was fitted on validation logits. The abstain threshold "
          f"t = {metrics['threshold']:.2f} and margin = {metrics['margin']} were chosen on validation only "
          f"(target: precision ≥ {metrics['target']['precision']} on answered images at coverage ≥ "
          f"{metrics['target']['coverage']}), never on test. The app abstains when calibrated top-1 confidence "
          "is below t or top-1 minus top-2 is below the margin, and then refers the farmer to 16123 or an officer.",
          ""]
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
    L += ["", "## 3. Dhan-Shomadhan field blast (cross-source)", ""]
    if dhs:
        L += [f"n = {dhs['n']} field-background blast images from a dataset the model never trained on.", "",
              f"- Blast recall (no abstention): {prop(count(dhs['blast_recall'], dhs['n']), dhs['n'])}",
              f"- Abstain rate: {prop(count(dhs['abstain_rate'], dhs['n']), dhs['n'])}",
              f"- Answered as blast: {prop(count(dhs['answered_as_blast'], dhs['n']), dhs['n'])}", ""]
    else:
        L += ["Not measured: the Dhan-Shomadhan images were not available in this run, so there is no "
              "cross-source blast test.", ""]
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
          "- Single-source confound: every BLB image comes from RiceLeafBD (Sylhet and Dhaka) and every "
          "training blast image from BD5 (Savar). The model may have learned the source, not the disease. "
          "Sections 2 and 3 are the honest check.",
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

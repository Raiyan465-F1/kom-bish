"""Build training/eval_report.md and training/eval_summary.json from real result files only.

  python training/make_eval_report.py        # run in .venv

Reads training/results/: metrics.json (the published model), runs/candidates_comparison.json (app code path),
external_test.json, leak_check.json and own_photos.json when present, and runs the off-script test. Every
number is copied or counted from those files; nothing is typed by hand. Smoke-run metrics are refused.
The outcome definitions are the ones in training/outcomes.py and are the same in every table.
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
ABSTAIN_SENTENCE = "The model abstains more than we would like."
PUBLISHED = "B (published)"
PREVIOUS = "v1 (previous)"
DEFINITIONS = [
    "- **Classifier confident:** the prediction passes the thresholds and the margin. A confident `other` counts.",
    "- **Advice given:** a confident BLB or healthy answer. This is what the farmer is told from the photo.",
    "- **Blast question asked:** a confident blast prediction. The app then asks the lesion-shape question and "
    "gives the spray answer only on \"yes\", so with the question unanswered this is **not** counted as advice. "
    "A blast question on a photo that is not blast would become a wrong \"spray correctly\" if the farmer said yes.",
    "- **Referred:** everything else: not confident, or a confident `other`.",
]


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


def load(name: str) -> dict | None:
    path = RESULTS / name
    return json.loads(path.read_text("utf-8")) if path.exists() else None


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


def agronomy_status() -> str:
    gates = ROOT / "docs" / "gates.md"
    if gates.exists():
        for line in gates.read_text("utf-8").splitlines():
            if line.lower().startswith("- agronomy review:"):
                return line.split(":", 1)[1].strip()
    return "not reviewed by an agronomist"


def outcome_table(by_true: dict) -> list[str]:
    lines = ["| True class | n | Right advice | Wrong advice | Blast question asked | Referred |", "|---|---|---|---|---|---|"]
    for cls, r in by_true.items():
        lines.append(f"| {cls} | {r['n']} | {r['right_advice']} | {r['wrong_advice']} | {r['blast_question_asked']} | "
                     f"{r['referred']} |")
    return lines


def outcome_lines(o: dict) -> list[str]:
    return [f"- Classifier confident: {prop(o['classifier_confident'], o['n'])}",
            f"- Advice given: {prop(o['advice_given'], o['n'])}; right {o['right_advice']}, wrong {o['wrong_advice']}",
            f"- Blast question asked: {o['blast_question_asked']} (on true blast {o['blast_question_on_true_blast']}, on "
            f"other classes {o['blast_question_on_other_classes']})",
            f"- Referred: {prop(o['referred'], o['n'])}"]


def comparison_table(cmp: dict) -> list[str]:
    lines = ["| Model | Set | n | Classifier confident | Advice given | Right advice | Wrong advice | Blast question "
             "asked (true blast / other = wrong spray if \"yes\") | Referred |", "|---|---|---|---|---|---|---|---|---|"]
    for name, r in cmp.items():
        for s, e in r["sets"].items():
            label = s + (" (**same source as some training data**)" if s.startswith("Paddy") and "B" in name else "")
            lines.append(f"| {name} | {label} | {e['n']} | {e['classifier_confident']} ({e['classifier_confident'] / e['n']:.1%}) "
                         f"| {e['advice_given']} ({e['advice_given'] / e['n']:.1%}) | {e['right_advice']} | {e['wrong_advice']} | "
                         f"{e['blast_question_asked']} ({e['blast_question_on_true_blast']} / "
                         f"{e['blast_question_on_other_classes']}) | {e['referred']} |")
    lines += ["", "CPU latency, median of 30 predictions on a 1024×768 image: "
              + "; ".join(f"{n} {r['cpu_latency_ms_median']} ms" for n, r in cmp.items()) + " (the same architecture; "
              "the differences are run-to-run noise)."]
    return lines


def build(metrics: dict, own: dict | None, off: dict, image_prefix: str) -> tuple[str, dict]:
    t, classes, cm = metrics["test"], metrics["classes"], metrics["test"]["confusion_matrix"]
    n = t["n"]
    outcomes = metrics.get("outcomes") or {}
    o_test, o_field = outcomes.get("test") or {}, outcomes.get("field") or {}
    cmp = load("runs/candidates_comparison.json") or {}
    pub = (cmp.get(PUBLISHED) or {}).get("sets") or {}
    held = pub.get("Paddy Doctor held-out") or {}
    ext, leak = load("external_test.json"), load("leak_check.json")
    paddy, dhs_in = metrics.get("paddy_doctor_images") or {}, metrics.get("dhs_images") or {}
    healthy, symptomatic, junk = ((own or {}).get(k) for k in ("healthy_looking", "symptomatic", "junk"))

    def rate(k, total):
        return None if (k is None or not total) else k / total

    summary = {
        "test_n": n, "test_macro_f1": t["macro_f1_no_abstention"], "temperature": metrics["temperature"],
        "threshold": metrics["threshold"], "margin": metrics["margin"],
        "blast_threshold": metrics.get("blast_threshold"), "blb_threshold": metrics.get("blb_threshold"),
        "target_met": metrics["target_met"], "threshold_rule": metrics.get("threshold_rule"),
        # our test split (PyTorch on the GPU, as in metrics.json)
        "test_classifier_confident": o_test.get("classifier_confident"), "test_advice_given": o_test.get("advice_given"),
        "test_right_advice": o_test.get("right_advice"), "test_wrong_advice": o_test.get("wrong_advice"),
        "test_blast_question_asked": o_test.get("blast_question_asked"),
        "test_blast_question_on_other_classes": o_test.get("blast_question_on_other_classes"),
        # our field photos (field-background test photos plus the held-out field blast)
        "field_n": o_field.get("n"), "field_classifier_confident": o_field.get("classifier_confident"),
        "field_advice_given": o_field.get("advice_given"), "field_right_advice": o_field.get("right_advice"),
        "field_wrong_advice": o_field.get("wrong_advice"), "field_blast_question_asked": o_field.get("blast_question_asked"),
        "field_blast_n": ((o_field.get("by_true_class") or {}).get("blast") or {}).get("n"),
        "field_blast_referred": ((o_field.get("by_true_class") or {}).get("blast") or {}).get("referred"),
        # Paddy Doctor held-out: same source as some training data (app code path)
        "heldout_n": held.get("n"), "heldout_classifier_confident": held.get("classifier_confident"),
        "heldout_advice_given": held.get("advice_given"), "heldout_right_advice": held.get("right_advice"),
        "heldout_wrong_advice": held.get("wrong_advice"), "heldout_blast_question_asked": held.get("blast_question_asked"),
        "heldout_blast_question_on_other_classes": held.get("blast_question_on_other_classes"),
        # external test: a dataset the model has never seen (app code path)
        "external_dataset": ((ext or {}).get("dataset") or {}).get("name"), "external_n": (ext or {}).get("n"),
        "external_classifier_confident": (ext or {}).get("classifier_confident"),
        "external_advice_given": (ext or {}).get("advice_given"), "external_right_advice": (ext or {}).get("right_advice"),
        "external_wrong_advice": (ext or {}).get("wrong_advice"),
        "external_blast_question_asked": (ext or {}).get("blast_question_asked"),
        "external_blast_question_on_other_classes": (ext or {}).get("blast_question_on_other_classes"),
        "external_top_guess_right": (ext or {}).get("top_guess_right"),
        "external_junk_n": ((ext or {}).get("junk") or {}).get("n"),
        "external_junk_referred": ((ext or {}).get("junk") or {}).get("referred"),
        # the team's own photos (step 19) and the off-script test
        "own_healthy_n": healthy["n"] if healthy else None,
        "own_healthy_false_trigger_n": healthy["false_trigger_n"] if healthy else None,
        "own_healthy_false_trigger_rate": rate(healthy["false_trigger_n"], healthy["n"]) if healthy else None,
        "own_symptomatic_n": symptomatic["n"] if symptomatic else None,
        "junk_n": junk["n"] if junk else None, "junk_refused_n": junk["refused_n"] if junk else None,
        "junk_refusal_rate": rate(junk["refused_n"], junk["n"]) if junk else None,
        "offscript_n": off["n"], "offscript_failures": off["offscript_failures"], "invented_doses": off["invented_doses"],
    }

    L: list[str] = ["# Kom Bish evaluation report", ""]
    if metrics.get("smoke_run"):
        L += ["> **SMOKE RUN ON SYNTHETIC OR SUBSET DATA. NOT A RESULT. DO NOT REPORT ANY NUMBER BELOW.**", ""]
    L += [f"Published model: `{metrics['model']}`, trained {metrics['date']}. Every proportion is shown as k/n with a "
          "Wilson 95% interval.", "",
          "## Definitions (the same in every table)", "", *DEFINITIONS, ""]
    v1 = ((cmp.get(PREVIOUS) or {}).get("sets") or {}).get("our test split")
    if v1:
        L += ["**Why two numbers.** Earlier write-ups gave two figures for the previous model on our test split that "
              f"looked inconsistent. Its \"coverage\" was classifier confident: {v1['classifier_confident']} of "
              f"{v1['n']} ({v1['classifier_confident'] / v1['n']:.1%}), which includes "
              f"{v1['classifier_confident'] - v1['advice_given'] - v1['blast_question_asked']} confident `other` "
              f"predictions that the app turns into referrals. Its \"answered\" count was "
              f"{v1['advice_given'] + v1['blast_question_asked']}: {v1['advice_given']} BLB or healthy answers plus "
              f"{v1['blast_question_asked']} confident blast predictions. Both were right; they measured different "
              "things. From here on only the names above are used.", ""]

    L += ["## Method", "",
          "Byte-identical duplicate files were removed, and photos filed under two classes with different targets "
          "were dropped. Our images were split once into train/validation/test (70/15/15, seed 42, stratified by "
          "source and class; near-duplicates kept in one split). One temperature "
          f"T = {metrics['temperature']:.4f}" + (" (clamped)" if metrics["temperature_clamped"] else "")
          + f" was fitted on validation logits. All thresholds were chosen on validation only: general threshold "
          f"{metrics['threshold']:.2f} and margin {metrics['margin']} ({metrics.get('threshold_rule')}); blast-only "
          f"threshold {metrics.get('blast_threshold')} (the smallest value with no wrong blast answer on validation)"
          + (f"; BLB-only threshold {metrics['blb_threshold']} (the smallest value with at most 5% wrong BLB answers "
             "on validation; the 5% is our choice)" if metrics.get("blb_threshold") is not None else "") + ".", "",
          f"Training data: RiceLeafBD and BD5; Dhan-Shomadhan ({dhs_in.get('train', 0)} train, {dhs_in.get('val', 0)} "
          f"validation, {dhs_in.get('test', 0)} test images)"
          + (f"; Paddy Doctor ({paddy.get('train', 0)} train, {paddy.get('val', 0)} validation images; 500 more are "
             "held out and never trained on)" if paddy.get("train") else "") + ". Augmentation: "
          f"{metrics.get('augmentation', 'standard')}.", ""]
    if not metrics["target_met"]:
        L += [f"**{ABSTAIN_SENTENCE}** No threshold met the target on validation.", ""]

    L += ["## 1. Our test split", "",
          f"n = {n}. Macro-F1 of the top guess, no abstention: **{t['macro_f1_no_abstention']:.4f}**.", "",
          "| Class | Support | Precision | Recall | F1 |", "|---|---|---|---|---|"]
    for i, c in enumerate(classes):
        row_n, col_n = sum(cm[i]), sum(r[i] for r in cm)
        L.append(f"| {c} | {row_n} | {prop(cm[i][i], col_n)} | {prop(cm[i][i], row_n)} | {t['per_class'][c]['f1']:.3f} |")
    if o_test:
        L += ["", "Outcomes at the published thresholds:", "", *outcome_lines(o_test), "", *outcome_table(o_test["by_true_class"])]
    L += ["", "Confusion matrix of the top guess (rows = true class):", "",
          "| true \\ predicted | " + " | ".join(classes) + " |", "|---|" + "---|" * len(classes)]
    L += [f"| {c} | " + " | ".join(str(v) for v in cm[i]) + " |" for i, c in enumerate(classes)]
    L += ["", f"![Confusion matrix]({image_prefix}confusion.png)", "",
          f"![Risk-coverage curve]({image_prefix}risk_coverage.png)", "",
          "### Recall per source (top guess, no abstention)", "",
          "| Source | Source class | Target | Recall | Not confident |", "|---|---|---|---|---|"]
    for r in metrics["per_source"]:
        L.append(f"| {r['source']} | {r['source_class']} | {r['target']} | {prop(count(r['recall'], r['n']), r['n'])} | "
                 f"{prop(count(r['abstain_rate'], r['n']), r['n'])} |")

    L += ["", "## 2. Our field photos", "",
          "Field-background test photos plus the 18 held-out Dhan-Shomadhan field blast photos. Farmers send field "
          "photos, so this matters more than the full test split, most of which is leaves on a white sheet.", ""]
    if o_field:
        L += [*outcome_lines(o_field), "", *outcome_table(o_field["by_true_class"]), ""]

    if cmp:
        L += ["## 3. Three models through the app's own code path", "",
              "`python training/compare_candidates.py`: `kombish/classifier.py` and `kombish/rules.py`, ONNX on the CPU, "
              "the lesion-shape question unanswered. v1 is the previously published model; A is the same recipe with "
              "stronger augmentation only; B adds Paddy Doctor training photos and is the published model. The "
              "Paddy Doctor held-out set (500 photos, never used for training, validation or thresholds) comes from "
              "the **same source as some of B's training data**, so for B it is not an external test.", "",
              *comparison_table(cmp), ""]

    L += ["## 4. External test: a dataset the model has never seen", ""]
    if ext:
        d, lk = ext["dataset"], ext["leak_check"]
        L += [f"**{d['name']} ({d['country']}), n = {ext['n']}.** Source: {d['source']}. Licence: {d['licence']}. "
              f"{d['credit']} Seeded sample (seed {ext['seed']}) of up to {ext['per_class']} images per mapped class; "
              f"{lk['near_duplicates_dropped']} near-duplicates of the {lk['compared_with_training_images']} training "
              f"and validation images dropped (perceptual hash, distance ≤ {lk['phash_distance']}). Evaluated once, "
              "after the model and thresholds were fixed; nothing was changed because of it.", "",
              *outcome_lines(ext), f"- Top guess right, no abstention: {prop(ext['top_guess_right'], ext['n'])}", "",
              *outcome_table(ext["by_true_class"]), "",
              "Confusion matrix of the top guess (rows = true class):", "",
              "| true \\ predicted | " + " | ".join(ext["confusion_matrix_top_guess"]["labels"]) + " |",
              "|---|" + "---|" * len(ext["confusion_matrix_top_guess"]["labels"])]
        L += [f"| {c} | " + " | ".join(str(v) for v in row) + " |" for c, row in
              zip(ext["confusion_matrix_top_guess"]["labels"], ext["confusion_matrix_top_guess"]["rows_true_cols_predicted"])]
        L += [""]
        if ext.get("junk"):
            j = ext["junk"]
            L += [f"Not-a-rice-leaf images from the same dataset: {prop(j['referred'], j['n'])} referred; advice given "
                  f"{j['advice_given']}; blast question asked {j['blast_question_asked']}.", ""]
        if ext["wrong_advice_list"]:
            L += ["Wrong advice: " + "; ".join(f"`{w['file']}` (true {w['source_label']}, answered {w['answered_as']}, "
                                                f"confidence {w['confidence']})" for w in ext["wrong_advice_list"]) + ".", ""]
    else:
        L += ["Not run.", ""]

    if leak:
        full, clean = leak["full"], leak["without_leaked"]
        L += ["## 5. Near-duplicate leak check on our own splits", "",
              f"`training/check_leakage.py`: every validation, test and held-out image against every training image "
              f"(perceptual hash, distance ≤ {leak['phash_distance']}, any class, any source). "
              f"{leak['leaked_test_images']} of {leak['test_and_heldout_images']} test and held-out images and "
              f"{leak['leaked_val_images']} of {leak['val_images']} validation images have a near-duplicate in training.", "",
              "| | Test n | Macro-F1 (top guess) | Classifier confident | Right when confident |", "|---|---|---|---|---|"]
        for name, r in (("All test images", full), ("Without leaked test images", clean)):
            L.append(f"| {name} | {r['test_n']} | {r['macro_f1_no_abstention']:.4f} | {r['coverage']:.4f} | "
                     f"{r['selective_accuracy']:.4f} |")
        L += [""]

    L += ["## 6. The team's own photos", ""]
    if own:
        L += [f"- Healthy-looking leaves wrongly given BLB or blast: {prop(healthy['false_trigger_n'], healthy['n'])}. "
              f"Rule counts: {healthy['rule_counts']}",
              f"- Symptomatic leaves: n = {symptomatic['n']}. Rule counts: {symptomatic['rule_counts']} (no accuracy "
              "claim: there are no ground-truth labels).",
              f"- Junk photos referred: {prop(junk['refused_n'], junk['n'])}. Rule counts: {junk['rule_counts']}", ""]
    else:
        L += ["Not measured yet: `training/results/own_photos.json` does not exist (steps 19 and 20).", ""]
    L += ["## 7. Off-script test", ""]
    if off["pytest_passed"] and off["offscript_failures"] == 0 and off["invented_doses"] == 0:
        L += [f"**0 off-script answers and 0 invented doses in {off['n']} test consultations** "
              "(`tests/test_offscript.py`): every sentence shown came from `data/rules.csv` or `data/clips.csv`.", ""]
    else:
        L += [f"**The off-script test did not pass:** {off['offscript_failures']} off-script answers and "
              f"{off['invented_doses']} answers with a forbidden term in {off['n']} test consultations.", ""]

    nbs = next((r for r in (o_test.get("by_true_class") or {}).items() if r[0] == "other"), None)
    L += ["## Limitations", "",
          "- **Diseases are not recognised on a new source.** On the external test the model mostly recognises "
          "healthy leaves; BLB, blast and brown spot photos are referred, not answered.",
          "- **The Paddy Doctor held-out result is not an external test** for the published model: it is the same "
          "source as some of its training data.",
          f"- **Blast is rarely answered.** The blast-only threshold is {metrics.get('blast_threshold')}: on our test "
          f"split the blast question was asked {o_test.get('blast_question_asked', 'n/a')} times.",
          "- **Narrow brown spot on a white sheet is told \"no spray now\".** "
          + (f"{nbs[1]['wrong_advice']} `other` photos on our test split got wrong advice; `runs/README.md` and "
             "`docs/gates.md` break them down (11 are BD5 narrow brown spot leaves answered healthy)." if nbs else ""),
          "- Source and background confound: every BLB image comes from RiceLeafBD (field photos) and most of our "
          "own blast images from BD5 (leaves on a white sheet). The first model learned the background.",
          "- BD5's official archive (version 2, SHA-256 verified) holds 3,150 images, while its own description "
          "says 2,545. We used what the archive contains.",
          "- The test split was looked at while comparing runs and tightening the threshold rules, so its numbers "
          "are somewhat optimistic. The external test was run once, after everything was fixed.",
          "- The lesion-shape question relies on the farmer's judgement and is not part of any number here.",
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
        raise SystemExit("metrics.json is from a smoke run (--subset / --no-pretrained). Use the real training output.")
    own = json.loads(args.own.read_text("utf-8")) if args.own.exists() else None
    if own is None:
        print(f"WARNING: {args.own} not found. Own-photo numbers will be null (run eval_own_photos.py).")
    off = run_offscript()
    image_prefix = "results/" if args.out_dir.resolve() == (ROOT / "training").resolve() else ""
    report, summary = build(metrics, own, off, image_prefix)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "eval_report.md").write_text(report, "utf-8")
    (args.out_dir / "eval_summary.json").write_text(json.dumps(summary, indent=1), "utf-8")
    print(f"Wrote {args.out_dir / 'eval_report.md'} and eval_summary.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())

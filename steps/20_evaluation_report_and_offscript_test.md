# 20 — Evaluation report and the off-script test

**Goal:** Produce `training/eval_report.md` with the four evaluation tables (each with n) and `training/eval_summary.json` (the single source of numbers for README, deck and video), and prove "0 off-script answers and 0 invented doses in 20 test consultations".
**Who:** Claude Code (the human supplies the photo folders from step 19).
**When:** Monday 12 October, afternoon. Before gate G5 (9 PM feature freeze).
**Covers master-plan step:** S20 (instruction file CC-12).

Context: The weakest part of the submission is evidence that the photo model generalises (single-source confound). The most persuasive numbers are the cross-source blast recall, the false-trigger rate on the team's own healthy-looking leaves, and the junk refusal rate, all with n. With 60–70 test images per minority class, one or two images move per-class recall by several points, so give n everywhere and Wilson 95% intervals. Never round a number up or drop an unflattering one.

| Evaluation set | Metrics |
|---|---|
| In-distribution test split | Per-class precision/recall/F1, confusion matrix, macro-F1 with no abstention, coverage and selective accuracy at t, precision on BLB and blast answers |
| Per source | Recall by (source, class) |
| Dhan-Shomadhan field blast | Blast recall and abstain rate (cross-source) |
| Own photos (30–50) and junk (20) | Share of healthy-looking own leaves wrongly sent to BLB or blast; junk refusal rate |

## Prerequisites

```bash
test -f training/results/metrics.json                       # [Run step 10 and copy the outputs.]
test -d own_photos/healthy_looking && test -d junk_photos   # [Run step 19.]
source .venv/bin/activate && python -c "from kombish.classifier import predict; from app import make_advise"   # [Steps 12 and 13.]
```

## Instructions for Claude Code

### 1. `training/eval_own_photos.py` (runs in `.venv`, uses the real app path)

- For each image in `own_photos/healthy_looking/`, `own_photos/symptomatic/`, `junk_photos/`: `pred = kombish.classifier.predict(img)`, then `adv = kombish.rules.decide(pred.label, pred.conf, pred.margin >= meta["margin"], None, None, threshold=meta["threshold"])`.
- Healthy-looking: n; **false trigger** = `adv.rule_id in {"R1_BLB", "R2_BLAST"}` (answered as a spray-relevant class); also counts of R3, R4, R5.
- Symptomatic: n and the distribution of rule IDs (no accuracy claim; we have no ground-truth disease labels).
- Junk: n; **refused** = `adv.decision == "consult_officer"` (R4 or R5); list how many got R1/R2/R3.
- Write aggregate counts only to `training/results/own_photos.json` (no file names, no image data). Print per-image results to the terminal for the team.

### 2. `tests/test_offscript.py` — 20 scripted consultations

Run 20 consultations through `app.make_advise` with a fake predictor and fake voice (as in step 13's tests), covering: R1 ×3 (planning yes/no/unanswered), R2 ×3, R3 ×3, R4 ×2, R5 ×3 (low confidence on BLB, blast, healthy; and one low margin), R6 ×2, voice failure ×2 (healthy, BLB), no photo ×1, no consent ×1 (adjust so the total is exactly 20).

For each answer:
- Split the Markdown on blank lines. **Every segment must be in the allowed set**, built independently from the CSVs: `"## " + headline_bn` for every rule; the confirm lines `texts.CONFIRM_TEMPLATE_BN.format(disease=...)` for BLB and blast; every `text_bn` in `data/clips.csv`; `"*" + texts.SOURCE_LABEL_BN + ": " + sources + "*"` for every rule.
- No forbidden term (reuse `FORBIDDEN`, `FORBIDDEN_TOKENS` from `tests/test_rules.py`).
- Count failures; assert `failures == 0` and `n == 20`.

The transcript echo is a separate output component (not part of the answer) and is excluded by design.

### 3. `training/make_eval_report.py`

- Reads `training/results/metrics.json` and `training/results/own_photos.json`.
- Runs `pytest -q tests/test_offscript.py` via `subprocess` and records pass/fail.
- Wilson 95% interval:
  ```python
  def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
      if n == 0:
          return float("nan"), float("nan")
      p = k / n
      d = 1 + z * z / n
      c = p + z * z / (2 * n)
      h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
      return (c - h) / d, (c + h) / d
  ```
- Writes `training/eval_report.md` with: a one-paragraph method note (splits, seed, temperature, threshold and margin chosen on validation only); the four tables above with n and Wilson intervals for every proportion; the confusion matrix (embed `results/confusion.png` and also print it as a table); the risk–coverage plot (`results/risk_coverage.png`); the off-script result ("0 off-script answers and 0 invented doses in 20 test consultations" only if the test passed; otherwise the true count); a limitations paragraph (single-source confound; own-photo labels are healthy-looking vs symptomatic, not diagnoses; no field trial; agronomist review status from `docs/gates.md`). If `target_met` is false, include "The model abstains more than we would like."
- Writes `training/eval_summary.json` with exactly these keys (README, deck and video read them):
  `test_n, test_macro_f1, temperature, threshold, margin, coverage, selective_accuracy, prec_blb_answers, prec_blb_answers_n, prec_blast_answers, prec_blast_answers_n, target_met, dhs_blast_n, dhs_blast_recall, dhs_blast_abstain_rate, own_healthy_n, own_healthy_false_trigger_n, own_healthy_false_trigger_rate, own_symptomatic_n, junk_n, junk_refused_n, junk_refusal_rate, offscript_n, offscript_failures, invented_doses`.

### 4. Run

```bash
source .venv/bin/activate
python training/eval_own_photos.py
pytest -q
python training/make_eval_report.py
cat training/eval_summary.json
```

### 5. Decide on thresholds honestly

If the own-photo false-trigger rate is high, tell the human. The fallback is to **raise the threshold** (more referrals) by editing `threshold` in `labels.json` on the model repo, re-running this step, and reporting both numbers. Never stage a fake demo.

## Human actions

- **HUMAN:** read `training/eval_report.md`. Agree the numbers as a team. If the threshold changes, re-upload `labels.json` to the model repo (step 11 script) and rerun this step.
- **HUMAN:** commit: `git add training tests && git commit -m "step 20: evaluation report and off-script test" && git push`.

## Done when

- `training/eval_report.md` contains the four tables, each with n and Wilson intervals, plus the confusion matrix and risk–coverage plot.
- `training/eval_summary.json` has every key listed above with real values.
- `pytest -q tests/test_offscript.py` passes: 0 off-script answers in 20.
- Every number the README and deck need exists, with n.

## If it fails

- **Own healthy leaves often go to BLB or blast:** raise the threshold; consider adding Dhan-Shomadhan blast to training in a second run (if time); report the number openly either way.
- **The off-script test fails:** a segment came from outside the CSVs. Fix `rules.decide` or `app.py`, never the test's allowed set.
- **Fewer own photos than planned:** report the true n; the Wilson interval will be wide, which is honest.

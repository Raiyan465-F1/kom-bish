# 10 — Train on Kaggle T4 (gate G2)

**Goal:** Run the notebook on a Kaggle T4, save the outputs, bring them to the laptop, and pass gate G2.
**Who:** Human (A) runs Kaggle. Claude Code checks the downloaded files and records the gate.
**When:** Sunday 11 October. **Gate G2 at 6 PM:** trained ONNX exists, or switch to the fallback training route.
**Covers master-plan step:** S11.

Context: The notebook `training/kombish_kaggle.ipynb` (step 08) clones the repo, runs `training/prepare_data.py` (step 07) and `training/train_export.py` (steps 08–09) and writes `/kaggle/working/export/{model.onnx, labels.json, metrics.json, confusion.png, risk_coverage.png, manifest.csv, best.pt}`. One 20-epoch run is estimated at 5–15 minutes on one T4 with pre-resized images (estimate, not measured). Kaggle limits from secondary sources: 12-hour sessions, a weekly GPU quota around 30 hours, phone verification required.

## Prerequisites

- Step 07 Part B done: `FOLDER_TO_TARGET` filled and pushed; counts explained in `docs/gates.md`.
- Step 09 done and pushed.
- A's Kaggle account is phone-verified.

Claude Code checks (laptop):
```bash
python - <<'EOF'
import ast
tree = ast.parse(open("training/prepare_data.py", encoding="utf-8").read())
vals = {n.target.id: n.value for n in tree.body
        if isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name)}
def filled(node):
    return bool(getattr(node, "keys", None) or getattr(node, "elts", None))
assert filled(vals.get("FOLDER_TO_TARGET")) or filled(vals.get("CSV_LABELS")), \
    "Mapping is still empty: finish step 07 Part B."
print("mapping present")
EOF
git status --short | grep -q . && echo "Uncommitted changes: commit and push before running Kaggle." || true
```
If the mapping is empty, stop: "Finish step 07 Part B first."

## Instructions for Claude Code

1. Before the run: print the exact notebook steps from "Human actions" with the real repo URL filled in (read it from `git remote get-url origin`).
2. After the human downloads the outputs, check them:

```bash
mkdir -p models training/results
# Human puts: models/model.onnx models/labels.json models/best.pt
#             training/results/metrics.json confusion.png risk_coverage.png manifest.csv
source .venv/bin/activate
python - <<'EOF'
import json, numpy as np, onnxruntime as ort
m = json.load(open("models/labels.json"))
assert m["classes"] == ["bacterial_leaf_blight", "blast", "healthy", "other"], m["classes"]
assert m["temperature"] > 0 and 0.30 <= m["threshold"] <= 0.99, (m["temperature"], m["threshold"])
assert m["mean"] == [0.485, 0.456, 0.406] and m["crop_pct"] == 0.875 and m["interpolation"] == "bicubic"
s = ort.InferenceSession("models/model.onnx", providers=["CPUExecutionProvider"])
for b in (1, 4):
    out = s.run(["logits"], {"input": np.zeros((b, 3, 224, 224), np.float32)})[0]
    assert out.shape == (b, 4)
r = json.load(open("training/results/metrics.json"))
print("T", r["temperature"], "clamped", r["temperature_clamped"], "t", r["threshold"], "margin", r["margin"])
print("parity", r["onnx_parity_max_abs_diff"], "test n", r["test"]["n"], "macro-F1", r["test"]["macro_f1_no_abstention"])
print("coverage", r["test"]["coverage"], "selective acc", r["test"]["selective_accuracy"], "target met", r["target_met"])
EOF
```

3. Fill gate G2 in `docs/gates.md`: date/time, T (and whether clamped), t, margin, parity diff, test macro-F1, coverage, target met (yes/no), per-source recall summary, DHS blast n and recall, Kaggle torch version, training time. Do **not** round or improve any number.
4. Make sure `models/` and `*.onnx`, `*.pt` stay git-ignored. Commit only `training/results/*` and `docs/gates.md`.

## Human actions

1. **HUMAN (A):** on Kaggle, **File → Import Notebook** and upload `training/kombish_kaggle.ipynb` (if that menu is not there, create a new notebook and paste the cells in order). The exact menu label was not verified.
2. **HUMAN:** **Settings → Accelerator → GPU T4** (one GPU is enough). **Internet On**. **Add Input → kombish-rice-raw**.
3. **HUMAN:** edit `REPO_URL` and `RAW_ROOT` in the config cell. Run all cells. Watch cell 3: `nvidia-smi` must show a T4.
4. **HUMAN:** check the final summary cell: all 7 files exist; parity < 1e-4; T between 0.5 and 10 (ideally about 1–3, not clamped). Copy the summary block into Claude Code.
5. **HUMAN:** **Save Version → Save & Run All (Commit)** so outputs persist. When it finishes, open the **Output** tab and download `export/`.
6. **HUMAN:** put the files on the laptop:
   - `models/model.onnx`, `models/labels.json`, `models/best.pt` (git-ignored)
   - `training/results/metrics.json`, `confusion.png`, `risk_coverage.png`, `manifest.csv`
7. **HUMAN:** paste "files are in place" to Claude Code so it runs the checks. Then commit: `git add training/results docs/gates.md && git commit -m "step 10: Kaggle training results" && git push`.

## Done when (gate G2, 6 PM)

- `models/model.onnx` and `models/labels.json` exist locally and pass Claude Code's checks (classes in order, T > 0, threshold in range, ImageNet preprocessing, batch 1 and 4 run).
- `training/results/metrics.json` records T within 0.5–10, parity < 1e-4, test macro-F1 and coverage.
- `docs/gates.md` G2 row is filled with real numbers.

## If it fails

- **No T4 (queue, quota gone, or phone verification fails) by Sunday noon:** run the same notebook on **Colab free** (12-hour maximum, unpublished GPU limits). Upload the two raw folders to Google Drive, mount Drive, set `RAW_ROOT` and `OUT` to Drive paths so outputs survive the session. Last resort: head-only fine-tune on a laptop CPU (`--epochs 0 --epochs-head 3 --device cpu`); this is an inference from the measured 36 ms eager forward pass, not a tested recipe. Record the switch in G2.
- **ONNX export fails on Kaggle's torch:** in the install cell add `"torch==2.14.1", "torchvision==0.29.1"`, restart the session, and rerun (the export gotchas were measured with 2.14.1; its wheel supports the T4's sm_75). If it still fails, ship `best.pt` with CPU torch (large install; risky on Render's 512 MB) and tell the team.
- **T clamped at 0.5 or 10, or macro-F1 is poor:** check the data counts and mapping first. Then try `--model efficientnet_b0.ra_in1k`. Report honestly whatever you ship.
- **Target not met ("abstains more than we would like"):** ship it anyway; the threshold makes the app refer more often. Write that sentence in the README.
- **DHS blast recall is poor:** in a second run, move Dhan-Shomadhan field blast into training and say so in the write-up (the cross-source test is then gone; state that too).

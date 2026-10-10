# 09 — Evaluation, temperature scaling, threshold, ONNX export and labels.json

**Goal:** Complete `training/train_export.py`: fit a temperature, choose the abstain threshold and margin on validation, compute every metric the submission reports, export a single-file ONNX model, check parity, and write `labels.json`.
**Who:** Claude Code.
**When:** Sunday 11 October, morning. Must be done before the human starts the Kaggle run (step 10, gate G2 at 6 PM).
**Covers master-plan step:** S10, second half (instruction file CC-05).

Context: Raw softmax confidence is a weak out-of-distribution detector, so Kom Bish fits one temperature T on validation logits (temperature scaling), then abstains when calibrated confidence is below a threshold t or when top1 − top2 is below a margin. Abstain → the rule engine refers the farmer to 16123 or the officer. Tune on validation only, never on test. The hosted app runs ONNX Runtime with no torch, so the export must be one file and match torch within 1e-4. Classes: `["bacterial_leaf_blight", "blast", "healthy", "other"]`.

## Prerequisites

```bash
test -f training/train_export.py && grep -q "logits_of" training/train_export.py   # [Run step 08 first.]
test -f data/synthetic/export/best.pt                                              # [Run step 08's CPU smoke run first.]
source .venv-train/bin/activate && python -c "import onnx, onnxscript, onnxruntime; print(onnx.__version__, onnxscript.__version__, onnxruntime.__version__)"
# expect 1.23.2, 0.7.2, 1.31.0   [Install training/requirements-train.txt in .venv-train.]
```

## Instructions for Claude Code

Fill the two hooks left in step 08. Keep everything in `training/train_export.py`.

### 1. Temperature scaling (tested code; logits from `torch.no_grad()`, never `inference_mode()`)

```python
def fit_temperature(lv: torch.Tensor, yv: torch.Tensor) -> tuple[float, bool]:
    logT = torch.zeros(1, requires_grad=True)
    opt = torch.optim.LBFGS([logT], lr=0.1, max_iter=200)

    def closure():
        opt.zero_grad()
        loss = F.cross_entropy(lv / logT.exp(), yv)
        loss.backward()
        return loss

    opt.step(closure)
    raw = float(logT.exp())
    T = float(min(max(raw, 0.5), 10.0))          # clamp; an untrained model ran away to ~14,600
    return T, (T != raw)                         # expect roughly 1-3 for a trained model
```

Print T and whether it was clamped. A clamped T on the real run is a warning sign for gate G2.

### 2. Selective metrics and threshold sweep

```python
def selective(p: torch.Tensor, y: torch.Tensor, t: float, margin: float) -> dict:
    top2 = p.topk(2, dim=1).values
    conf, pred = p.max(1)
    answered = (conf >= t) & ((top2[:, 0] - top2[:, 1]) >= margin)
    out = {"n": int(len(y)), "coverage": float(answered.float().mean())}
    out["precision"] = float((pred[answered] == y[answered]).float().mean()) if answered.any() else float("nan")
    for name, k in (("blb", 0), ("blast", 1)):
        m = answered & (pred == k)
        out[f"precision_{name}_answers"] = {"value": float((y[m] == k).float().mean()) if m.any() else float("nan"),
                                            "n": int(m.sum())}
    out["abstained_pct_by_true_class"] = {
        CLASSES[k]: float((~answered[y == k]).float().mean()) if (y == k).any() else float("nan") for k in range(4)}
    return out
```

Choose t and margin on **validation**:
- For each margin in `(0.0, 0.1, 0.2, 0.3)`: sweep t from 0.30 to 0.99 in steps of 0.01 and take the **smallest t** with precision on answered images ≥ 0.90 **and** coverage ≥ 0.50.
- Among margins that meet the target, pick the one with the highest coverage; on a tie, prefer the margin closest to 0.2.
- Check precision separately for BLB answers and blast answers (the costly errors). If either is below 0.90 on validation, print a loud WARNING and record it in `metrics.json` (`"spray_relevant_precision_ok": false`).
- If no (t, margin) meets the target, choose margin 0.2 and the t with the highest precision among those with coverage ≥ 0.50, set `"target_met": false`, and print: `The model abstains more than we would like.` That sentence goes into the README later.

### 3. Metrics (all with n)

Compute with `p = softmax(logits / T)`:
- **Test split (in-distribution):** `classification_report` (per-class precision, recall, F1, support), `confusion_matrix`, macro-F1 **with no abstention**; then at the chosen (t, margin): coverage, abstained %, selective accuracy (= precision on answered), precision on BLB answers and on blast answers (with their n), abstained % by true class.
- **Per source:** for each test image, read `source` and `source_class` from the filename prefix `<source>__<source_class_slug>__...` (written by step 07). Report n and recall (argmax == target, no abstention) and abstain rate for each (source, source_class).
- **Dhan-Shomadhan field blast** (if `<data>/dhs_field_blast/` exists): a small `Dataset` over those files with `eval_tf`, label `CLASSES.index("blast")`. Report n, blast recall (no abstention), abstain rate at (t, margin), and the share answered as blast.
- Save `out/confusion.png` (matplotlib, class names on axes, counts in cells) and `out/risk_coverage.png` (x = coverage, y = selective accuracy, one point per t at the chosen margin, title with n).

Write `out/metrics.json` with this shape (steps 10, 11 and 20 read these keys):

```json
{
  "model": "mobilenetv3_large_100.ra_in1k", "date": "YYYY-MM-DD", "classes": ["..."],
  "temperature": 1.0, "temperature_clamped": false,
  "threshold": 0.0, "margin": 0.2, "target": {"precision": 0.90, "coverage": 0.50},
  "target_met": true, "spray_relevant_precision_ok": true,
  "val": {"...": "output of selective() at the chosen t, margin"},
  "test": {"n": 0, "macro_f1_no_abstention": 0.0, "per_class": {}, "confusion_matrix": [],
           "coverage": 0.0, "abstained_pct": 0.0, "selective_accuracy": 0.0,
           "precision_blb_answers": {"value": 0.0, "n": 0}, "precision_blast_answers": {"value": 0.0, "n": 0},
           "abstained_pct_by_true_class": {}},
  "per_source": [{"source": "", "source_class": "", "target": "", "n": 0, "recall": 0.0, "abstain_rate": 0.0}],
  "dhs_field_blast": {"n": 0, "blast_recall": 0.0, "abstain_rate": 0.0, "answered_as_blast": 0.0},
  "onnx_parity_max_abs_diff": 0.0, "onnx_mb": 0.0, "train_seconds": 0.0,
  "versions": {"python": "", "torch": "", "timm": "", "onnx": "", "onnxruntime": ""}
}
```
(Values above are placeholders showing types. Write real values only.)

### 4. ONNX export (tested code; two measured gotchas)

torch 2.14's `torch.onnx.export` defaults to `dynamo=True` and `external_data=True`. A batch-1 example with a dynamic batch dimension fails with `Invalid ranges [2:1]`. So export with a **batch-2 example**, **`external_data=False`** (single file, no `.data` sidecar), and `dynamic_shapes` keyed by the forward argument name `x`:

```python
model.eval().cpu()
torch.onnx.export(model, (torch.randn(2, 3, 224, 224),), str(out / "model.onnx"),
                  input_names=["input"], output_names=["logits"],
                  dynamo=True, external_data=False,
                  dynamic_shapes={"x": {0: torch.export.Dim("batch", min=1, max=64)}})
```

Parity check (must pass before anything ships):

```python
so = ort.SessionOptions(); so.intra_op_num_threads = 2
sess = ort.InferenceSession(str(out / "model.onnx"), so, providers=["CPUExecutionProvider"])
xs = torch.stack([va[i][0] for i in range(min(5, len(va)))])          # 5 validation images, eval transform
with torch.no_grad():
    ref = model(xs).numpy()
got = sess.run(["logits"], {"input": xs.numpy()})[0]
diff = float(np.abs(ref - got).max())
assert diff < 1e-4, f"ONNX parity failed: {diff}"
```
Also run the ONNX model on a batch of 1 and a batch of 4 to confirm the dynamic batch works. Assert no `model.onnx.data` file exists. Record `onnx_mb` (expect about 17 MB for MobileNetV3-Large).

### 5. `labels.json` (classes from `ImageFolder.classes`, preprocessing from timm's resolved config)

```python
labels = {
    "model": args.model,
    "classes": tr.classes,
    "temperature": round(T, 4), "threshold": round(t, 2), "margin": margin,
    "input_size": list(cfg["input_size"]), "mean": [float(v) for v in cfg["mean"]], "std": [float(v) for v in cfg["std"]],
    "crop_pct": float(cfg["crop_pct"]), "interpolation": cfg["interpolation"],
    "onnx_input": "input", "onnx_output": "logits",
    "trained_on": TRAINED_ON, "date": dt.date.today().isoformat(),
}
assert labels["classes"] == CLASSES
assert np.allclose(labels["mean"], [0.485, 0.456, 0.406]) and np.allclose(labels["std"], [0.229, 0.224, 0.225]), \
    "Wrong weight tag: use mobilenetv3_large_100.ra_in1k (ImageNet mean/std)"
assert labels["crop_pct"] == 0.875 and labels["interpolation"] == "bicubic" and labels["input_size"] == [3, 224, 224]
```
Write it to `out/labels.json` with `indent=1`. (If the backup `efficientnet_b0.ra_in1k` is used, the same asserts hold.)

### 6. Final summary print

Print a compact block the human will paste back in step 10: T (clamped?), t, margin, target met, test n, test macro-F1, coverage, selective accuracy, BLB/blast answer precision with n, per-source recall table, DHS blast n/recall/abstain rate, parity diff, ONNX size, training seconds, versions.

### 7. Full CPU smoke run

```bash
source .venv-train/bin/activate
python training/train_export.py --data data/synthetic/prepared --out data/synthetic/export \
  --device cpu --subset 50 --epochs-head 1 --epochs 1 --batch 16 --workers 0
ls -la data/synthetic/export
python -c "import json; m=json.load(open('data/synthetic/export/labels.json')); print(m)"
```
On random synthetic data T may clamp and the target will not be met. That is expected; the point is that every stage runs and parity passes.

## Human actions

- **HUMAN:** commit and push: `git add -A && git commit -m "step 09: calibration, metrics, ONNX export" && git push`. Step 10 clones this commit on Kaggle.

## Done when

- The CPU smoke run writes `model.onnx` (single file, no `.data` sidecar), `labels.json`, `metrics.json`, `confusion.png`, `risk_coverage.png`, `best.pt`, `manifest.csv` into `data/synthetic/export/`.
- Parity max |ORT − torch| < 1e-4 is printed and asserted; batch 1 and batch 4 both run in ONNX Runtime.
- `labels.json` passes the asserts (ImageNet mean/std, bicubic, crop_pct 0.875, classes in order).
- `pytest -q` still passes.

## If it fails

- **"Invalid ranges [2:1]":** the example input is batch 1. Use `torch.randn(2, 3, 224, 224)`.
- **A `model.onnx.data` file appears:** `external_data=False` is missing.
- **Exporter import error mentioning onnxscript:** `pip install onnx==1.23.2 onnxscript==0.7.2` (the dynamo exporter needs onnxscript).
- **"Inference tensors cannot be saved for backward":** the validation logits came from `inference_mode()`. Use `torch.no_grad()`.
- **ONNX export still breaks:** fallback is to ship `best.pt` with CPU torch and timm in the app. That is a far larger install; it probably fits a ZeroGPU Space but is risky on Render's 512 MB. Tell the human before switching.

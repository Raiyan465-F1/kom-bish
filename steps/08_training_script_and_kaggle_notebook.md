# 08 — Training script and Kaggle notebook

**Goal:** Write the two-stage fine-tuning part of `training/train_export.py` and generate the Kaggle notebook the human will run on a T4.
**Who:** Claude Code (the human runs the notebook later, in step 10).
**When:** Sunday 11 October, morning (can start Saturday night). Before step 09.
**Covers master-plan step:** S10, first half (instruction file CC-05).

Context: The classifier is `timm.create_model("mobilenetv3_large_100.ra_in1k", pretrained=True, num_classes=4)` at 224 px. **Pin the weight tag**: newer tags of the same architecture use mean = std = 0.5, while `.ra_in1k` uses ImageNet mean/std, bicubic interpolation and crop_pct 0.875. Backup model: `efficientnet_b0.ra_in1k`. Training runs on Kaggle's free T4 (Turing, no native bf16 → fp16 autocast + GradScaler). The P100 was retired on 15 September 2026; sessions requesting it run on a T4. Classes from `ImageFolder.classes`, never typed by hand: `["bacterial_leaf_blight", "blast", "healthy", "other"]`. Step 09 adds temperature scaling, threshold, metrics and ONNX export to the same script.

## Prerequisites

```bash
test -f training/prepare_data.py && test -f training/requirements-train.txt   # [Run step 07 Part A first.]
test -d data/synthetic/prepared/train                                          # [Run the synthetic prep from step 07 Part A.]
```
Create the training venv if it does not exist:
```bash
python3.12 -m venv .venv-train && source .venv-train/bin/activate && pip install -r training/requirements-train.txt
python -c "import torch, timm; print(torch.__version__, timm.__version__)"   # expect 2.14.1 and 1.0.30
```
If installation fails, stop and print the error for the human.

## Instructions for Claude Code

### 1. `training/train_export.py` — training part (write the full file)

CLI:

```
--data PATH (required)         prepared root with train/ val/ test/ [dhs_field_blast/] manifest.csv
--out PATH (required)          output folder (export/)
--model mobilenetv3_large_100.ra_in1k
--device cuda|cpu              default: cuda if available
--epochs-head 3  --epochs 20  --batch 64  --workers 4  --seed 42
--subset N                     max images per split (CPU smoke runs only)
--no-pretrained                offline smoke test only; never for the real run
--skip-export                  train and save best.pt only
```

Core code (from the smoke-tested recipe in our research; keep these exact settings):

```python
CLASSES = ["bacterial_leaf_blight", "blast", "healthy", "other"]
TRAINED_ON = ["10.17632/kx9rx8p2mz.1", "10.17632/sjkptpgv79.2"]


def seed_everything(seed):
    random.seed(seed); np.random.seed(seed); torch.manual_seed(seed); torch.cuda.manual_seed_all(seed)


model = timm.create_model(args.model, pretrained=not args.no_pretrained, num_classes=4).to(device)
cfg = timm.data.resolve_model_data_config(model)
train_tf = timm.data.create_transform(**cfg, is_training=True, scale=(0.6, 1.0), vflip=0.5,
                                      color_jitter=(0.2, 0.2, 0.1, 0.0), re_prob=0.2)
eval_tf = timm.data.create_transform(**cfg, is_training=False)
tr = ImageFolder(f"{args.data}/train", train_tf)
va = ImageFolder(f"{args.data}/val", eval_tf)
te = ImageFolder(f"{args.data}/test", eval_tf)
assert tr.classes == va.classes == te.classes == CLASSES, tr.classes
```

Why these settings: hue jitter is 0 because yellowing and lesion colour carry the diagnosis; crops never go below 60% of the image so lesions survive; vertical flip and random erasing 0.2 add robustness.

Sampler and loss (use the sampler **or** loss weights, never both):

```python
counts = np.bincount(tr_targets, minlength=4)
w = counts.sum() / (4 * np.maximum(counts, 1))                    # N / (4 * n_class)
sampler = WeightedRandomSampler(torch.tensor(w, dtype=torch.double)[torch.tensor(tr_targets)],
                                num_samples=len(tr_targets), replacement=True)
dl_tr = DataLoader(tr_ds, batch_size=args.batch, sampler=sampler, num_workers=args.workers,
                   pin_memory=(device == "cuda"), drop_last=len(tr_targets) > args.batch)
crit = nn.CrossEntropyLoss(label_smoothing=0.1)
```

`--subset N`: pick N random indices per split with the seed (use `torch.utils.data.Subset`; keep a matching `targets` list for the sampler).

Training step with AMP on CUDA only:

```python
use_amp = device == "cuda"
scaler = torch.amp.GradScaler("cuda", enabled=use_amp)
for x, y in dl_tr:
    x, y = x.to(device, non_blocking=True), y.to(device, non_blocking=True)
    opt.zero_grad(set_to_none=True)
    with torch.autocast(device_type=device, dtype=torch.float16, enabled=use_amp):
        loss = crit(model(x), y)
    scaler.scale(loss).backward(); scaler.step(opt); scaler.update()
    if sched is not None:
        sched.step()
```

Validation logits — **use `torch.no_grad()`, not `torch.inference_mode()`** (step 09 fits a temperature on these; inference tensors raise "Inference tensors cannot be saved for backward"):

```python
@torch.no_grad()
def logits_of(model, dl, device):
    model.eval(); L, Y = [], []
    for x, y in dl:
        L.append(model(x.to(device)).float().cpu()); Y.append(y)
    return torch.cat(L), torch.cat(Y)
```

Two stages:
- **Stage 1 (head only):** freeze all parameters, unfreeze `model.get_classifier()`. `AdamW(head params, lr=1e-3)`, `--epochs-head` epochs (2–3), no scheduler.
- **Stage 2 (full):** unfreeze all. `AdamW(model.parameters(), lr=1e-4, weight_decay=0.05)`, `CosineAnnealingLR(opt, T_max=epochs * len(dl_tr))` stepped per batch, `--epochs` epochs (15–20).
- After every epoch of both stages: compute val logits, `f1_score(y, argmax, average="macro")`. Keep the state dict (copied to CPU) with the **best validation macro-F1**, not best accuracy. Print epoch, loss, val macro-F1, seconds.
- After training: load the best state, save `out/best.pt` (`torch.save(state_dict)`), and copy `<data>/manifest.csv` to `out/manifest.csv` if it exists.
- Leave clear hook functions for step 09: `calibrate_and_evaluate(model, dl_va, dl_te, dhs_dl, te_samples, out, device)` and `export_onnx_and_labels(model, cfg, va, out)`. In this step they may just `print("TODO step 09")`; `--skip-export` skips them.

Print at start: Python, torch, timm versions, device name (`torch.cuda.get_device_name(0)` on CUDA), class counts per split.

### 2. `training/make_kaggle_notebook.py` → `training/kombish_kaggle.ipynb`

Write a small script that builds the notebook as nbformat-4 JSON with the standard library `json` module (no extra dependency), then run it and commit the `.ipynb`. Cells in order:

1. Markdown: "Kom Bish training. Settings → Accelerator **GPU T4** (use one GPU), **Internet On**, **Add Input → kombish-rice-raw**. Run all. Then **Save Version → Save & Run All (Commit)** so outputs persist. Outputs: `/kaggle/working/export/`."
2. Code (config; the human edits two lines):
   ```python
   REPO_URL = "https://github.com/<gh-user>/kom-bish.git"
   RAW_ROOT = "/kaggle/input/kombish-rice-raw"    # real path from step 02
   DATA, OUT = "/kaggle/working/data", "/kaggle/working/export"
   ```
3. Code: `!nvidia-smi` and print `sys.version` and `torch.__version__` (do **not** import timm yet).
4. Code (installs; onnxruntime 1.31 needs Python ≥ 3.11, so pick the version by the runtime):
   ```python
   import subprocess, sys
   pkgs = ["timm==1.0.30", "onnx==1.23.2", "onnxscript==0.7.2", "datasets==5.1.0", "matplotlib"]
   pkgs.append("onnxruntime==1.31.0" if sys.version_info >= (3, 11) else "onnxruntime")
   subprocess.run([sys.executable, "-m", "pip", "install", "-q", *pkgs], check=True)
   try:
       import sklearn
   except ImportError:
       subprocess.run([sys.executable, "-m", "pip", "install", "-q", "scikit-learn"], check=True)
   import torch, timm, onnxruntime
   print("torch", torch.__version__, "timm", timm.__version__, "ort", onnxruntime.__version__, "cuda", torch.cuda.is_available())
   ```
5. Code: clone the repo fresh into `/kaggle/working/kom-bish` and `%cd` into it.
6. Code: `!python training/prepare_data.py --print-tree --root {RAW_ROOT}` (kept for the record).
7. Code: `!python training/prepare_data.py --root {RAW_ROOT} --out {DATA} --dhs` (add `--accept-count-mismatch` only if step 07 documented the differences).
8. Code: `!python training/train_export.py --data {DATA} --out {OUT} --device cuda`.
9. Code: print `metrics.json` key numbers (step 09 defines them), list `OUT` with file sizes, and `assert` these files exist: `model.onnx, labels.json, metrics.json, confusion.png, risk_coverage.png, manifest.csv, best.pt`.
10. Markdown: "Download from the **Output** tab (`export/`), or from a laptop with `kagglehub.notebook_output_download('<kaggle-user>/<notebook-slug>')`. Then do step 10's hand-back."

Kaggle's preinstalled torch version is **unknown**. The notebook prints it. Do not reinstall torch in the notebook by default (the export gotchas in step 09 were measured with torch 2.14.1; step 10 says what to do if export fails).

### 3. CPU smoke run of the training part

```bash
source .venv-train/bin/activate
python training/train_export.py --data data/synthetic/prepared --out data/synthetic/export \
  --device cpu --subset 50 --epochs-head 1 --epochs 1 --batch 16 --workers 0 --skip-export
ls -la data/synthetic/export
```
If the laptop cannot download pretrained weights (huggingface.co blocked), rerun with `--no-pretrained` and say so.

## Human actions

- **HUMAN:** commit and push: `git add -A && git commit -m "step 08: training script and Kaggle notebook" && git push`.

## Done when

- The CPU smoke run finishes, prints per-epoch val macro-F1, and writes `data/synthetic/export/best.pt`.
- The class-order assert passes.
- `training/kombish_kaggle.ipynb` opens as valid JSON (`python -c "import json; json.load(open('training/kombish_kaggle.ipynb'))"`) and contains the 10 cells above.
- `pytest -q` still passes (training code is not imported by the app tests).

## If it fails

- **`create_transform` rejects an argument:** print `timm.__version__`; the call was verified with timm 1.0.30. Install that exact version.
- **ImageFolder raises "Found no valid file" for a class:** the synthetic subset left a class empty; raise `--subset` or regenerate synthetic data with more images.
- **Zero training batches:** `drop_last` with fewer images than the batch size; lower `--batch` for smoke runs.
- **Accuracy is short later (step 10):** rerun with `--model efficientnet_b0.ra_in1k` (same ImageNet mean/std and crop_pct 0.875).

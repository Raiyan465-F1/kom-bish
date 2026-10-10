# 12 — Classifier module with exact preprocessing parity

**Goal:** Write `kombish/classifier.py` (ONNX Runtime, no torch), its smoke tests, and a one-off parity check against timm's evaluation transform.
**Who:** Claude Code.
**When:** Sunday 11 October, evening (after step 11).
**Covers master-plan step:** S13 (instruction file CC-07).

Context: The hosted app must reproduce timm's evaluation transform exactly: EXIF transpose → RGB → resize shorter side to 256 (bicubic) → centre-crop 224 → scale 0–1 → normalise with ImageNet mean/std → NCHW float32. A Pillow + numpy version matched timm with max pixel difference 0.0 in our research. Preprocessing a 12 MP photo (~175 ms) costs more than inference (~5 ms). The model and `labels.json` come from the public HF model repo in `MODEL_REPO`. Temperature, threshold and margin come from `labels.json`. No torch in the app, ever.

## Prerequisites

```bash
source .venv/bin/activate
python -c "import importlib.util as u; assert u.find_spec('torch') is None, 'torch is installed in .venv; remove it'"
grep -q "^MODEL_REPO=.\+/kom-bish-rice-leaf" .env       # [Set MODEL_REPO in .env (step 11).]
test -f models/labels.json && test -f models/best.pt     # [Download step 10 outputs into models/.]
```

## Instructions for Claude Code

### 1. `kombish/classifier.py`

```python
"""Kom Bish image classifier: ONNX Runtime on CPU, no torch.

Preprocessing reproduces timm's eval transform for mobilenetv3_large_100.ra_in1k exactly.
The session is created once (cached) on first use, so importing this module needs no network.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np
import onnxruntime as ort
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parent.parent
LOCAL_MODEL_DIR = ROOT / "models"


@dataclass(frozen=True)
class Prediction:
    label: str                 # top-1 class (always one of the 4 classes)
    conf: float                # calibrated top-1 probability
    probs: dict[str, float]
    margin: float              # top-1 minus top-2 probability
    abstained: bool            # conf < threshold or margin < labels.json "margin"


def _artifact_paths() -> tuple[Path, Path]:
    repo = os.getenv("MODEL_REPO", "").strip()
    if repo:
        from huggingface_hub import hf_hub_download
        return (Path(hf_hub_download(repo_id=repo, filename="model.onnx")),
                Path(hf_hub_download(repo_id=repo, filename="labels.json")))
    onnx_path, labels_path = LOCAL_MODEL_DIR / "model.onnx", LOCAL_MODEL_DIR / "labels.json"
    if not (onnx_path.exists() and labels_path.exists()):
        raise FileNotFoundError("Set MODEL_REPO, or put model.onnx and labels.json in models/")
    return onnx_path, labels_path


@lru_cache(maxsize=1)
def load() -> tuple[ort.InferenceSession, dict]:
    onnx_path, labels_path = _artifact_paths()
    m = json.loads(labels_path.read_text(encoding="utf-8"))
    if not m.get("temperature", 0) > 0:
        raise ValueError("labels.json temperature is not filled (must be > 0)")
    so = ort.SessionOptions()
    so.intra_op_num_threads = 2
    sess = ort.InferenceSession(str(onnx_path), so, providers=["CPUExecutionProvider"])
    return sess, m


def meta() -> dict:
    return load()[1]


def preprocess(img: Image.Image, m: dict) -> np.ndarray:
    img = ImageOps.exif_transpose(img).convert("RGB")            # phone photos carry EXIF rotation
    size = m["input_size"][1]
    short = int(size / m["crop_pct"])                            # 224 / 0.875 = 256
    w, h = img.size
    nw, nh = (short, int(short * h / w)) if w <= h else (int(short * w / h), short)
    img = img.resize((nw, nh), Image.BICUBIC)
    left, top = int(round((nw - size) / 2.0)), int(round((nh - size) / 2.0))
    x = np.asarray(img.crop((left, top, left + size, top + size)), dtype=np.float32) / 255.0
    x = (x - np.array(m["mean"], np.float32)) / np.array(m["std"], np.float32)
    return x.transpose(2, 0, 1)[None]


def predict(img: Image.Image) -> Prediction:
    sess, m = load()
    logits = sess.run([m["onnx_output"]], {m["onnx_input"]: preprocess(img, m)})[0][0].astype(np.float64)
    z = logits / m["temperature"]
    p = np.exp(z - z.max())
    p /= p.sum()
    order = np.argsort(p)[::-1]
    k, k2 = int(order[0]), int(order[1])
    conf, margin = float(p[k]), float(p[k] - p[k2])
    return Prediction(
        label=m["classes"][k], conf=conf,
        probs={c: round(float(v), 4) for c, v in zip(m["classes"], p)},
        margin=margin,
        abstained=conf < m["threshold"] or margin < m["margin"],
    )
```

Do not add `Image.draft()` speed-ups: they change pixels versus training and were not checked for accuracy.

### 2. `tests/test_classifier_smoke.py`

- Skip the whole module with a clear reason if `MODEL_REPO` is unset **and** `models/model.onnx` is missing.
- `test_no_torch`: after `import kombish.classifier`, assert `"torch" not in sys.modules`.
- `test_preprocess_shapes`: synthetic images 400×300, 3000×4000 and 4160×1952 → shape `(1, 3, 224, 224)`, dtype float32.
- `test_exif_rotation`: build a JPEG in memory with EXIF Orientation = 6 (rotate 90°) using Pillow's `Image.Exif()` (tag 0x0112), reopen it, and assert `preprocess` equals preprocessing the manually rotated image.
- `test_predict_contract`: on a random-noise image, `predict()` returns a label in the 4 classes, probs summing to 1 ± 1e-3, `0 ≤ margin ≤ conf ≤ 1`, and `abstained` consistent with `meta()["threshold"]` and `meta()["margin"]`.
- `test_latency`: time 20 predictions on a 1024×768 image; print the median ms (no hard assert; print so the human sees it).

### 3. `training/check_parity.py` (run once in `.venv-train`, not in CI)

Compares the app's preprocessing and model with timm and torch:
- Builds the timm eval transform: `timm.data.create_transform(**timm.data.resolve_model_data_config(model), is_training=False)` for `mobilenetv3_large_100.ra_in1k`.
- For images of size 400×300, 3000×4000 and 4160×1952 (synthetic, or real test images if `--images DIR` is given): assert `max |kombish.classifier.preprocess(img, labels) − timm_tf(img)| ≤ 1e-6` (our research measured 0.0). Note: apply `exif_transpose` to the image before passing it to timm too, since timm's loader does not.
- Loads `models/best.pt` into `timm.create_model(..., num_classes=4)` and asserts `max |ORT logits − torch logits| < 1e-4` on 5 images.
- Prints both numbers.

```bash
source .venv-train/bin/activate
python training/check_parity.py            # add --images <dir> to use real photos
```

### 4. Run the app-side tests

```bash
source .venv/bin/activate
pytest -q
```

## Human actions

- **HUMAN:** commit: `git add -A && git commit -m "step 12: classifier module" && git push`. Check CI is green (it uses the `MODEL_REPO` variable from step 11).

## Done when

- `pytest -q` passes in `.venv` with torch **not installed**; the latency test prints a median in ms.
- `python training/check_parity.py` prints a preprocessing difference ≤ 1e-6 and a logits difference < 1e-4.
- CI is green.

## If it fails

- **Preprocessing differs from timm:** check bicubic, the `int(size / crop_pct)` short side, the rounding in the crop offsets, and that `labels.json` has `crop_pct` 0.875. A different weight tag (mean = std = 0.5) is the usual cause; it must be `.ra_in1k`.
- **`hf_hub_download` fails in CI:** the `MODEL_REPO` Actions variable is missing or the repo is private.
- **ValueError about temperature:** `labels.json` still has the placeholder 0.0; use the file from the Kaggle run.

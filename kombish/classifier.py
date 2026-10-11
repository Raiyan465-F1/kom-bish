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
    abstained: bool            # conf < threshold, margin < "margin", or blast below "blast_threshold"


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


def should_abstain(label: str, conf: float, margin: float, m: dict) -> bool:
    """Abstain below the threshold or margin. Blast (the only spray answer) has its own, stricter threshold;
    BLB may have one too (labels.json "blb_threshold")."""
    if conf < m["threshold"] or margin < m["margin"]:
        return True
    class_threshold = {"blast": m.get("blast_threshold"), "bacterial_leaf_blight": m.get("blb_threshold")}.get(label)
    return class_threshold is not None and conf < class_threshold


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
        abstained=should_abstain(m["classes"][k], conf, margin, m),
    )

"""One-off parity check (run in .venv-train, not in CI): the app's preprocessing and ONNX model vs timm and torch.

  python training/check_parity.py                 # synthetic images
  python training/check_parity.py --images DIR    # real photos

Asserts max |kombish.classifier.preprocess - timm eval transform| <= 1e-6 and
max |ONNX Runtime logits - torch logits| < 1e-4.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import onnxruntime as ort
import timm
import torch
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from kombish import classifier  # noqa: E402

IMG_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
SYNTHETIC_SIZES = [(400, 300), (3000, 4000), (4160, 1952), (1024, 768), (224, 224)]


def images(folder: Path | None) -> list[Image.Image]:
    if folder is not None:
        files = sorted(p for p in folder.rglob("*") if p.suffix.lower() in IMG_EXT)[:20]
        if not files:
            raise SystemExit(f"No images under {folder}")
        return [Image.open(p) for p in files]
    rng = np.random.default_rng(0)
    return [Image.fromarray(rng.integers(0, 256, size=(h, w, 3), dtype=np.uint8)) for w, h in SYNTHETIC_SIZES]


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--images", type=Path, help="folder of real photos (default: synthetic images)")
    p.add_argument("--model-dir", type=Path, default=ROOT / "models",
                   help="folder with model.onnx, labels.json and best.pt")
    args = p.parse_args(argv)

    labels = json.loads((args.model_dir / "labels.json").read_text("utf-8"))
    model = timm.create_model(labels["model"], pretrained=False, num_classes=len(labels["classes"]))
    model.load_state_dict(torch.load(args.model_dir / "best.pt", map_location="cpu"))
    model.eval()
    timm_tf = timm.data.create_transform(**timm.data.resolve_model_data_config(model), is_training=False)

    imgs = images(args.images)
    ours, pre_diff = [], 0.0
    for img in imgs:
        mine = classifier.preprocess(img, labels)[0]
        # timm's loader does not apply EXIF rotation, so do it before the timm transform too.
        ref = timm_tf(ImageOps.exif_transpose(img).convert("RGB")).numpy()
        pre_diff = max(pre_diff, float(np.abs(mine - ref).max()))
        ours.append(mine)
    print(f"preprocessing: max |app - timm| = {pre_diff:.3e} over {len(imgs)} images")
    assert pre_diff <= 1e-6, f"Preprocessing differs from timm: {pre_diff}"

    xs = np.stack(ours[:5]).astype(np.float32)
    sess = ort.InferenceSession(str(args.model_dir / "model.onnx"), providers=["CPUExecutionProvider"])
    got = sess.run([labels["onnx_output"]], {labels["onnx_input"]: xs})[0]
    with torch.no_grad():
        ref = model(torch.from_numpy(xs)).numpy()
    logit_diff = float(np.abs(ref - got).max())
    print(f"logits: max |ORT - torch| = {logit_diff:.3e} over {len(xs)} images")
    assert logit_diff < 1e-4, f"ONNX parity failed: {logit_diff}"
    print("Parity OK.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

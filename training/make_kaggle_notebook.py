"""Build training/kombish_kaggle.ipynb (nbformat 4) with the standard library only.

  python training/make_kaggle_notebook.py
"""
from __future__ import annotations

import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "kombish_kaggle.ipynb"

INTRO = (
    "# Kom Bish training\n\n"
    "Settings → Accelerator **GPU T4** (use one GPU), **Internet On**, **Add Input → kombish-rice-raw**. "
    "Run all. Then **Save Version → Save & Run All (Commit)** so outputs persist. "
    "Outputs: `/kaggle/working/export/`."
)

CONFIG = '''\
# Edit these two lines.
REPO_URL = "https://github.com/Raiyan465-F1/kom-bish.git"   # the repo must be public for this clone to work
RAW_ROOT = "/kaggle/input/kombish-rice-raw"    # real path from step 02
DATA, OUT = "/kaggle/working/data", "/kaggle/working/export"
'''

RUNTIME = '''\
!nvidia-smi
import sys, torch
print(sys.version)
print("torch", torch.__version__)
'''

INSTALLS = '''\
# onnxruntime 1.31 needs Python >= 3.11, so pick the version by the runtime. torch is NOT reinstalled.
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
'''

CLONE = '''\
!rm -rf /kaggle/working/kom-bish && git clone --depth 1 {REPO_URL} /kaggle/working/kom-bish
%cd /kaggle/working/kom-bish
!git log --oneline -1
'''

TREE = '''\
# Kept for the record: the raw folder tree and image counts.
!python training/prepare_data.py --print-tree --root {RAW_ROOT}
'''

PREP = '''\
# Same flags as the shipped local run (docs/gates.md, gate G2). The count differences are documented there.
!pip install -q imagehash==4.3.2
!python training/prepare_data.py --root {RAW_ROOT} --out {DATA} --dhs --dhs-all --phash \\
    --dhs-train-frac 0.6 --dhs-val-frac 0.15 --accept-count-mismatch
'''

TRAIN = '''\
!python training/train_export.py --data {DATA} --out {OUT} --device cuda --epochs 40
'''

CHECK = '''\
import json, os
m = json.load(open(f"{OUT}/metrics.json"))
t = m["test"]
print("model", m["model"], "| date", m["date"])
print("T", m["temperature"], "clamped", m["temperature_clamped"], "| t", m["threshold"], "| margin", m["margin"],
      "| target met", m["target_met"], "| spray-relevant precision ok", m["spray_relevant_precision_ok"])
print("test n", t["n"], "| macro-F1 (no abstention)", t["macro_f1_no_abstention"], "| coverage", t["coverage"],
      "| selective accuracy", t["selective_accuracy"])
print("precision on BLB answers", t["precision_blb_answers"], "| on blast answers", t["precision_blast_answers"])
print("Dhan-Shomadhan field blast", m["dhs_field_blast"])
print("ONNX parity", m["onnx_parity_max_abs_diff"], "| ONNX MB", m["onnx_mb"], "| train seconds", m["train_seconds"])
for name in sorted(os.listdir(OUT)):
    print(f"{os.path.getsize(os.path.join(OUT, name)):>12,d}  {name}")
for name in ["model.onnx", "labels.json", "metrics.json", "confusion.png", "risk_coverage.png", "manifest.csv", "best.pt"]:
    assert os.path.exists(os.path.join(OUT, name)), f"missing {name}"
assert not os.path.exists(os.path.join(OUT, "model.onnx.data")), "model.onnx must be a single file"
print("All export files present.")
'''

OUTRO = (
    "Download from the **Output** tab (`export/`), or from a laptop with "
    "`kagglehub.notebook_output_download('<kaggle-user>/<notebook-slug>')`. Then do step 10's hand-back."
)


def cell(kind: str, source: str) -> dict:
    lines = source.rstrip("\n").split("\n")
    body = {"cell_type": kind, "metadata": {}, "source": [line + "\n" for line in lines[:-1]] + [lines[-1]]}
    if kind == "code":
        body.update(execution_count=None, outputs=[])
    return body


def build() -> dict:
    cells = [cell("markdown", INTRO), cell("code", CONFIG), cell("code", RUNTIME), cell("code", INSTALLS),
             cell("code", CLONE), cell("code", TREE), cell("code", PREP), cell("code", TRAIN),
             cell("code", CHECK), cell("markdown", OUTRO)]
    return {
        "cells": cells,
        "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                     "language_info": {"name": "python"}},
        "nbformat": 4, "nbformat_minor": 4,
    }


if __name__ == "__main__":
    OUT.write_text(json.dumps(build(), indent=1, ensure_ascii=False) + "\n", "utf-8")
    print(f"Wrote {OUT} ({len(build()['cells'])} cells)")

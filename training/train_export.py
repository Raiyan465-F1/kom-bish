"""Kom Bish classifier: two-stage fine-tuning, temperature scaling, abstain threshold, metrics, ONNX export.

  python training/train_export.py --data <prepared root> --out <export folder> --device cuda

<prepared root> is the output of training/prepare_data.py: train/ val/ test/ [dhs_field_blast/] manifest.csv.
Writes best.pt, model.onnx (single file), labels.json, metrics.json, confusion.png, risk_coverage.png, manifest.csv.

The threshold and margin are tuned on validation only, never on test. Source confound: every BLB image is from
RiceLeafBD and every training blast image is from BD5, so metrics.json reports recall per (source, class) and
blast recall on Dhan-Shomadhan field images.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import platform
import random
import shutil
import sys
import time
from pathlib import Path

import numpy as np
import timm
import torch
import torch.nn as nn
import torch.nn.functional as F
from PIL import Image
from sklearn.metrics import classification_report, confusion_matrix, f1_score
from torch.utils.data import DataLoader, Dataset, Subset, WeightedRandomSampler
from torchvision.datasets import ImageFolder

CLASSES = ["bacterial_leaf_blight", "blast", "healthy", "other"]
TRAINED_ON = ["10.17632/kx9rx8p2mz.1", "10.17632/sjkptpgv79.2"]
IMG_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
TARGET_PRECISION, TARGET_COVERAGE = 0.90, 0.50
MARGINS = (0.0, 0.1, 0.2, 0.3)
THRESHOLDS = [round(0.30 + 0.01 * i, 2) for i in range(70)]   # 0.30 .. 0.99
ABSTAIN_SENTENCE = "The model abstains more than we would like."


def seed_everything(seed):
    random.seed(seed); np.random.seed(seed); torch.manual_seed(seed); torch.cuda.manual_seed_all(seed)


class FolderAsClass(Dataset):
    """Every image in one folder, all with the same label (Dhan-Shomadhan field blast)."""

    def __init__(self, folder: Path, transform, label: int):
        self.files = sorted(p for p in folder.iterdir() if p.suffix.lower() in IMG_EXT)
        self.transform, self.label = transform, label

    def __len__(self):
        return len(self.files)

    def __getitem__(self, i):
        with Image.open(self.files[i]) as im:
            return self.transform(im.convert("RGB")), self.label


def take_subset(ds: ImageFolder, n: int | None, seed: int):
    """Return (dataset, targets, samples). --subset picks n random indices with the seed."""
    if n is None or n >= len(ds):
        return ds, list(ds.targets), list(ds.samples)
    idx = sorted(random.Random(seed).sample(range(len(ds)), n))
    return Subset(ds, idx), [ds.targets[i] for i in idx], [ds.samples[i] for i in idx]


@torch.no_grad()   # not inference_mode(): fit_temperature needs these tensors in a backward pass
def logits_of(model, dl, device):
    model.eval(); L, Y = [], []
    for x, y in dl:
        L.append(model(x.to(device)).float().cpu()); Y.append(y)
    return torch.cat(L), torch.cat(Y)


def train_one_epoch(model, dl_tr, opt, sched, crit, scaler, device, use_amp) -> float:
    model.train()
    total, n = 0.0, 0
    for x, y in dl_tr:
        x, y = x.to(device, non_blocking=True), y.to(device, non_blocking=True)
        opt.zero_grad(set_to_none=True)
        with torch.autocast(device_type=device, dtype=torch.float16, enabled=use_amp):
            loss = crit(model(x), y)
        scaler.scale(loss).backward(); scaler.step(opt); scaler.update()
        if sched is not None:
            sched.step()
        total += float(loss.detach()) * len(y); n += len(y)
    return total / max(n, 1)


# ------------------------------------------------------------ calibration

def fit_temperature(lv: torch.Tensor, yv: torch.Tensor) -> tuple[float, bool]:
    logT = torch.zeros(1, requires_grad=True)
    opt = torch.optim.LBFGS([logT], lr=0.1, max_iter=200)

    def closure():
        opt.zero_grad()
        loss = F.cross_entropy(lv / logT.exp(), yv)
        loss.backward()
        return loss

    opt.step(closure)
    raw = float(logT.detach().exp())
    T = float(min(max(raw, 0.5), 10.0))          # clamp; an untrained model ran away to ~14,600
    return T, (T != raw)                         # expect roughly 1-3 for a trained model


def answered_mask(p: torch.Tensor, t: float, margin: float) -> torch.Tensor:
    top2 = p.topk(2, dim=1).values
    return (top2[:, 0] >= t) & ((top2[:, 0] - top2[:, 1]) >= margin)


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


def choose_threshold(pv: torch.Tensor, yv: torch.Tensor) -> tuple[float, float, bool]:
    """Pick (t, margin) on validation. Returns (t, margin, target_met)."""
    met = []
    for margin in MARGINS:
        for t in THRESHOLDS:   # smallest t that meets the target at this margin
            s = selective(pv, yv, t, margin)
            if s["precision"] >= TARGET_PRECISION and s["coverage"] >= TARGET_COVERAGE:
                met.append((margin, t, s["coverage"]))
                break
    if met:
        margin, t, _ = max(met, key=lambda c: (c[2], -abs(c[0] - 0.2)))
        return t, margin, True
    margin = 0.2
    covered = [(s["precision"], -t, t) for t in THRESHOLDS
               if (s := selective(pv, yv, t, margin))["coverage"] >= TARGET_COVERAGE and not math.isnan(s["precision"])]
    t = max(covered)[2] if covered else THRESHOLDS[0]
    print(ABSTAIN_SENTENCE)
    return t, margin, False


def source_of(path: str) -> tuple[str, str]:
    parts = Path(path).name.split("__")   # <source>__<source_class_slug>__<stem>_<sha>.jpg (prepare_data.py)
    return (parts[0], parts[1]) if len(parts) >= 3 else ("unknown", "unknown")


def save_confusion_png(cm: np.ndarray, path: Path, n: int) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(6.5, 5.5))
    ax.imshow(cm, cmap="Blues")
    ax.set_xticks(range(4), CLASSES, rotation=30, ha="right")
    ax.set_yticks(range(4), CLASSES)
    ax.set_xlabel("Predicted (no abstention)"); ax.set_ylabel("True")
    ax.set_title(f"Test confusion matrix (n={n})")
    for i in range(4):
        for j in range(4):
            ax.text(j, i, int(cm[i, j]), ha="center", va="center",
                    color="white" if cm[i, j] > cm.max() / 2 else "black")
    fig.tight_layout(); fig.savefig(path, dpi=150); plt.close(fig)


def save_risk_coverage_png(p: torch.Tensor, y: torch.Tensor, t: float, margin: float, path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    points = [(s["coverage"], s["precision"], th) for th in THRESHOLDS
              if not math.isnan((s := selective(p, y, th, margin))["precision"])]
    fig, ax = plt.subplots(figsize=(6.5, 4.5))
    ax.plot([c for c, _, _ in points], [a for _, a, _ in points], "o", ms=3, label="one point per threshold t")
    chosen = [(c, a) for c, a, th in points if th == t]
    if chosen:
        ax.plot(*chosen[0], "r*", ms=14, label=f"chosen t={t:.2f}")
    ax.set_xlabel("Coverage (share of test images answered)"); ax.set_ylabel("Selective accuracy")
    ax.set_title(f"Test risk-coverage (n={len(y)}, margin={margin})")
    ax.grid(alpha=0.3); ax.legend(loc="lower left")
    fig.tight_layout(); fig.savefig(path, dpi=150); plt.close(fig)


def calibrate_and_evaluate(model, dl_va, dl_te, dhs_dl, te_samples, out, device) -> dict:
    """Fit T and choose (t, margin) on validation; report every metric on test. Returns the metrics dict."""
    lv, yv = logits_of(model, dl_va, device)
    lt, yt = logits_of(model, dl_te, device)
    T, clamped = fit_temperature(lv, yv)
    print(f"Temperature T = {T:.4f} (clamped: {clamped})")
    if clamped:
        print("WARNING: temperature was clamped. On the real run this is a warning sign for gate G2.")
    pv, pt = F.softmax(lv / T, dim=1), F.softmax(lt / T, dim=1)

    t, margin, target_met = choose_threshold(pv, yv)
    val = selective(pv, yv, t, margin)
    spray_ok = True
    for name in ("blb", "blast"):
        cell = val[f"precision_{name}_answers"]
        if math.isnan(cell["value"]) or cell["value"] < TARGET_PRECISION:
            spray_ok = False
            print(f"WARNING: validation precision on {name} answers is {cell['value']:.3f} (n={cell['n']}), "
                  f"below {TARGET_PRECISION}. These are the costly errors.")

    pred = pt.argmax(1)
    labels = list(range(4))
    report = classification_report(yt, pred, labels=labels, target_names=CLASSES, output_dict=True, zero_division=0)
    cm = confusion_matrix(yt, pred, labels=labels)
    sel = selective(pt, yt, t, margin)
    answered = answered_mask(pt, t, margin)
    test = {
        "n": int(len(yt)),
        "macro_f1_no_abstention": float(f1_score(yt, pred, labels=labels, average="macro", zero_division=0)),
        "per_class": {c: {"precision": report[c]["precision"], "recall": report[c]["recall"],
                          "f1": report[c]["f1-score"], "support": int(report[c]["support"])} for c in CLASSES},
        "confusion_matrix": cm.tolist(),
        "coverage": sel["coverage"], "abstained_pct": 1.0 - sel["coverage"], "selective_accuracy": sel["precision"],
        "precision_blb_answers": sel["precision_blb_answers"],
        "precision_blast_answers": sel["precision_blast_answers"],
        "abstained_pct_by_true_class": sel["abstained_pct_by_true_class"],
    }

    per_source = []
    sources = [source_of(path) for path, _ in te_samples]
    for key in sorted(set(sources)):
        m = torch.tensor([s == key for s in sources])
        target = CLASSES[int(yt[m][0])]
        per_source.append({"source": key[0], "source_class": key[1], "target": target, "n": int(m.sum()),
                           "recall": float((pred[m] == yt[m]).float().mean()),
                           "abstain_rate": float((~answered[m]).float().mean())})

    dhs = None
    if dhs_dl is not None and len(dhs_dl.dataset):
        ld, yd = logits_of(model, dhs_dl, device)
        pd_ = F.softmax(ld / T, dim=1)
        ans = answered_mask(pd_, t, margin)
        is_blast = pd_.argmax(1) == CLASSES.index("blast")
        dhs = {"n": int(len(yd)), "blast_recall": float(is_blast.float().mean()),
               "abstain_rate": float((~ans).float().mean()), "answered_as_blast": float((ans & is_blast).float().mean())}

    save_confusion_png(cm, out / "confusion.png", len(yt))
    save_risk_coverage_png(pt, yt, t, margin, out / "risk_coverage.png")
    return {
        "temperature": T, "temperature_clamped": clamped, "threshold": t, "margin": margin,
        "target": {"precision": TARGET_PRECISION, "coverage": TARGET_COVERAGE},
        "target_met": target_met, "spray_relevant_precision_ok": spray_ok,
        "val": val, "test": test, "per_source": per_source, "dhs_field_blast": dhs,
    }


# ----------------------------------------------------------------- export

def export_onnx_and_labels(model, cfg, va, out, *, model_name: str, classes: list[str], calib: dict) -> dict:
    """Export one-file ONNX, assert parity with torch, write labels.json. Returns parity and size."""
    import onnxruntime as ort

    onnx_path = out / "model.onnx"
    model.eval().cpu()
    example = (torch.randn(2, 3, 224, 224),)   # batch 2: a batch-1 example fails with "Invalid ranges [2:1]"
    try:
        torch.onnx.export(model, example, str(onnx_path),
                          input_names=["input"], output_names=["logits"],
                          dynamo=True, external_data=False,
                          dynamic_shapes={"x": {0: torch.export.Dim("batch", min=1, max=64)}})
        exporter = "dynamo"
    except Exception as e:   # e.g. a different preinstalled torch on Kaggle; parity below still has to pass
        print(f"WARNING: dynamo ONNX export failed ({type(e).__name__}: {e}). Trying the TorchScript exporter.")
        torch.onnx.export(model, example, str(onnx_path), input_names=["input"], output_names=["logits"],
                          dynamo=False, dynamic_axes={"input": {0: "batch"}, "logits": {0: "batch"}})
        exporter = "torchscript"
    assert not Path(str(onnx_path) + ".data").exists(), "model.onnx.data sidecar found: external_data must be False"

    so = ort.SessionOptions(); so.intra_op_num_threads = 2
    sess = ort.InferenceSession(str(onnx_path), so, providers=["CPUExecutionProvider"])
    xs = torch.stack([va[i][0] for i in range(min(5, len(va)))])          # 5 validation images, eval transform
    with torch.no_grad():
        ref = model(xs).numpy()
    got = sess.run(["logits"], {"input": xs.numpy()})[0]
    diff = float(np.abs(ref - got).max())
    assert diff < 1e-4, f"ONNX parity failed: {diff}"
    for batch in (1, 4):   # the dynamic batch dimension must work
        shape = sess.run(["logits"], {"input": np.random.rand(batch, 3, 224, 224).astype(np.float32)})[0].shape
        assert shape == (batch, len(classes)), shape
    onnx_mb = onnx_path.stat().st_size / 1e6
    print(f"ONNX parity max |ORT - torch| = {diff:.2e} (< 1e-4); batch 1 and 4 run; {onnx_mb:.1f} MB; {exporter}")

    labels = {
        "model": model_name,
        "classes": classes,
        "temperature": round(calib["temperature"], 4), "threshold": round(calib["threshold"], 2),
        "margin": calib["margin"],
        "input_size": list(cfg["input_size"]), "mean": [float(v) for v in cfg["mean"]],
        "std": [float(v) for v in cfg["std"]],
        "crop_pct": float(cfg["crop_pct"]), "interpolation": cfg["interpolation"],
        "onnx_input": "input", "onnx_output": "logits",
        "trained_on": TRAINED_ON, "date": dt.date.today().isoformat(),
    }
    assert labels["classes"] == CLASSES
    assert np.allclose(labels["mean"], [0.485, 0.456, 0.406]) and np.allclose(labels["std"], [0.229, 0.224, 0.225]), \
        "Wrong weight tag: use mobilenetv3_large_100.ra_in1k (ImageNet mean/std)"
    assert labels["crop_pct"] == 0.875 and labels["interpolation"] == "bicubic" and labels["input_size"] == [3, 224, 224]
    (out / "labels.json").write_text(json.dumps(labels, indent=1), "utf-8")
    return {"onnx_parity_max_abs_diff": diff, "onnx_mb": onnx_mb, "onnx_exporter": exporter}


# ------------------------------------------------------------------- main

def no_nan(obj):
    """NaN is not valid JSON: write null for a value that could not be computed (n = 0)."""
    if isinstance(obj, float) and math.isnan(obj):
        return None
    if isinstance(obj, dict):
        return {k: no_nan(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [no_nan(v) for v in obj]
    return obj


def print_summary(m: dict) -> None:
    t, v = m["test"], m["versions"]

    def cell(c):
        return f"{c['value']:.3f} (n={c['n']})"

    print("\n================ KOM BISH TRAINING SUMMARY (paste this back in step 10) ================")
    print(f"model {m['model']} | date {m['date']}")
    print(f"T = {m['temperature']:.4f} (clamped: {m['temperature_clamped']}) | t = {m['threshold']:.2f} | "
          f"margin = {m['margin']} | target met: {m['target_met']} | "
          f"spray-relevant precision ok: {m['spray_relevant_precision_ok']}")
    print(f"test n = {t['n']} | macro-F1 (no abstention) = {t['macro_f1_no_abstention']:.4f} | "
          f"coverage = {t['coverage']:.3f} | selective accuracy = {t['selective_accuracy']:.3f}")
    print(f"precision on BLB answers = {cell(t['precision_blb_answers'])} | "
          f"on blast answers = {cell(t['precision_blast_answers'])}")
    print("per source (test, recall without abstention):")
    for r in m["per_source"]:
        print(f"  {r['source']:<12} {r['source_class']:<24} -> {r['target']:<22} n={r['n']:<5} "
              f"recall={r['recall']:.3f} abstain={r['abstain_rate']:.3f}")
    d = m["dhs_field_blast"]
    print("Dhan-Shomadhan field blast: " + (
        f"n={d['n']} blast recall={d['blast_recall']:.3f} abstain rate={d['abstain_rate']:.3f} "
        f"answered as blast={d['answered_as_blast']:.3f}" if d else "not available (no dhs_field_blast/ folder)"))
    print(f"ONNX parity diff = {m['onnx_parity_max_abs_diff']:.2e} | ONNX size = {m['onnx_mb']:.1f} MB | "
          f"exporter = {m['onnx_exporter']} | training seconds = {m['train_seconds']:.0f}")
    print(f"versions: python {v['python']} | torch {v['torch']} | timm {v['timm']} | onnx {v['onnx']} | "
          f"onnxruntime {v['onnxruntime']}")
    print("=========================================================================================")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--data", type=Path, required=True,
                   help="prepared root with train/ val/ test/ [dhs_field_blast/] manifest.csv")
    p.add_argument("--out", type=Path, required=True, help="output folder (export/)")
    p.add_argument("--model", default="mobilenetv3_large_100.ra_in1k")
    p.add_argument("--device", choices=["cuda", "cpu"], default="cuda" if torch.cuda.is_available() else "cpu")
    p.add_argument("--epochs-head", type=int, default=3)
    p.add_argument("--epochs", type=int, default=20)
    p.add_argument("--batch", type=int, default=64)
    p.add_argument("--workers", type=int, default=4)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--subset", type=int, help="max images per split (CPU smoke runs only)")
    p.add_argument("--no-pretrained", action="store_true", help="offline smoke test only; never for the real run")
    p.add_argument("--skip-export", action="store_true", help="train and save best.pt only")
    args = p.parse_args(argv)

    device = args.device
    seed_everything(args.seed)
    args.out.mkdir(parents=True, exist_ok=True)
    print(f"python {platform.python_version()} | torch {torch.__version__} | timm {timm.__version__} | device "
          + (torch.cuda.get_device_name(0) if device == "cuda" else "cpu"))

    model = timm.create_model(args.model, pretrained=not args.no_pretrained, num_classes=4).to(device)
    cfg = timm.data.resolve_model_data_config(model)
    # Hue jitter is 0 because yellowing and lesion colour carry the diagnosis; crops never go below 60% of
    # the image so lesions survive; vertical flip and random erasing 0.2 add robustness.
    train_tf = timm.data.create_transform(**cfg, is_training=True, scale=(0.6, 1.0), vflip=0.5,
                                          color_jitter=(0.2, 0.2, 0.1, 0.0), re_prob=0.2)
    eval_tf = timm.data.create_transform(**cfg, is_training=False)
    tr = ImageFolder(f"{args.data}/train", train_tf)
    va = ImageFolder(f"{args.data}/val", eval_tf)
    te = ImageFolder(f"{args.data}/test", eval_tf)
    assert tr.classes == va.classes == te.classes == CLASSES, tr.classes

    tr_ds, tr_targets, _ = take_subset(tr, args.subset, args.seed)
    va_ds, va_targets, _ = take_subset(va, args.subset, args.seed)
    te_ds, te_targets, te_samples = take_subset(te, args.subset, args.seed)
    for name, targets in (("train", tr_targets), ("val", va_targets), ("test", te_targets)):
        per = np.bincount(targets, minlength=4)
        print(f"{name:<5} n={len(targets):<5} " + " ".join(f"{c}={n}" for c, n in zip(CLASSES, per)))

    # Class balance through the sampler only (never the sampler and loss weights together).
    counts = np.bincount(tr_targets, minlength=4)
    w = counts.sum() / (4 * np.maximum(counts, 1))                    # N / (4 * n_class)
    sampler = WeightedRandomSampler(torch.tensor(w, dtype=torch.double)[torch.tensor(tr_targets)],
                                    num_samples=len(tr_targets), replacement=True)
    pin = device == "cuda"
    dl_tr = DataLoader(tr_ds, batch_size=args.batch, sampler=sampler, num_workers=args.workers,
                       pin_memory=pin, drop_last=len(tr_targets) > args.batch)
    dl_va = DataLoader(va_ds, batch_size=args.batch, shuffle=False, num_workers=args.workers, pin_memory=pin)
    dl_te = DataLoader(te_ds, batch_size=args.batch, shuffle=False, num_workers=args.workers, pin_memory=pin)
    if len(dl_tr) == 0:
        raise SystemExit("Zero training batches: lower --batch for smoke runs.")
    crit = nn.CrossEntropyLoss(label_smoothing=0.1)
    use_amp = device == "cuda"   # T4 has no native bf16: fp16 autocast + GradScaler
    scaler = torch.amp.GradScaler("cuda", enabled=use_amp)

    best_f1, best_state = -1.0, None
    t_start = time.time()

    def run_stage(name: str, epochs: int, opt, sched) -> None:
        nonlocal best_f1, best_state
        for epoch in range(1, epochs + 1):
            t0 = time.time()
            loss = train_one_epoch(model, dl_tr, opt, sched, crit, scaler, device, use_amp)
            lv, yv = logits_of(model, dl_va, device)
            f1 = float(f1_score(yv, lv.argmax(1), average="macro", labels=list(range(4)), zero_division=0))
            mark = ""
            if f1 > best_f1:   # best validation macro-F1, not best accuracy
                best_f1 = f1
                best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
                mark = "  <-- best"
            print(f"{name} epoch {epoch}/{epochs}  loss {loss:.4f}  val macro-F1 {f1:.4f}  "
                  f"{time.time() - t0:.0f}s{mark}")

    # Stage 1: classifier head only.
    for param in model.parameters():
        param.requires_grad = False
    head = list(model.get_classifier().parameters())
    for param in head:
        param.requires_grad = True
    run_stage("head", args.epochs_head, torch.optim.AdamW(head, lr=1e-3), None)

    # Stage 2: everything, cosine schedule stepped per batch.
    for param in model.parameters():
        param.requires_grad = True
    opt = torch.optim.AdamW(model.parameters(), lr=1e-4, weight_decay=0.05)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=max(args.epochs * len(dl_tr), 1))
    run_stage("full", args.epochs, opt, sched)
    train_seconds = time.time() - t_start

    if best_state is not None:
        model.load_state_dict(best_state)
    torch.save(model.state_dict(), args.out / "best.pt")
    manifest = args.data / "manifest.csv"
    if manifest.exists():
        shutil.copyfile(manifest, args.out / "manifest.csv")
    print(f"Saved best.pt (best val macro-F1 {best_f1:.4f}) after {train_seconds:.0f}s of training")
    if args.skip_export:
        return 0

    dhs_dir = args.data / "dhs_field_blast"
    dhs_dl = None
    if dhs_dir.is_dir():
        dhs_ds = FolderAsClass(dhs_dir, eval_tf, CLASSES.index("blast"))
        if len(dhs_ds):
            dhs_dl = DataLoader(dhs_ds, batch_size=args.batch, shuffle=False, num_workers=args.workers)

    import onnx
    import onnxruntime

    calib = calibrate_and_evaluate(model, dl_va, dl_te, dhs_dl, te_samples, args.out, device)
    exported = export_onnx_and_labels(model, cfg, va_ds, args.out, model_name=args.model,
                                      classes=tr.classes, calib=calib)
    metrics = {
        "model": args.model, "date": dt.date.today().isoformat(), "classes": tr.classes,
        **calib, **exported, "train_seconds": train_seconds,
        "versions": {"python": platform.python_version(), "torch": torch.__version__, "timm": timm.__version__,
                     "onnx": onnx.__version__, "onnxruntime": onnxruntime.__version__},
    }
    if args.subset or args.no_pretrained:
        metrics["smoke_run"] = True   # --subset / --no-pretrained: not a real result, never report it
    (args.out / "metrics.json").write_text(json.dumps(no_nan(metrics), indent=1), "utf-8")
    print_summary(metrics)
    return 0


if __name__ == "__main__":
    sys.exit(main())

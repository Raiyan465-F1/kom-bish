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
DHS_DOI = "10.17632/znsxdctwtt.1"   # Dhan-Shomadhan: listed only when its images are in train/ or val/
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


class ZoomOut:
    """Shrink the photo to 25-100% of the frame and fill the rest with a real field-background crop.

    The model only knew a leaf that fills the frame (docs/gates.md, "Why it fails"). The backgrounds are
    crops of our own field-background `other` training photos, never black padding.
    """

    def __init__(self, backgrounds: list[str], p: float = 0.7, scale: tuple[float, float] = (0.25, 1.0)):
        self.backgrounds, self.p, self.scale = backgrounds, p, scale

    def __call__(self, img: Image.Image) -> Image.Image:
        if not self.backgrounds or random.random() > self.p:
            return img
        s = random.uniform(*self.scale)
        if s > 0.97:
            return img
        img = img.convert("RGB")
        w, h = img.size
        with Image.open(random.choice(self.backgrounds)) as bg:
            bg = bg.convert("RGB")
        bw, bh = bg.size
        frac = random.uniform(0.5, 1.0)
        cw, ch = max(int(bw * frac), 8), max(int(bh * frac), 8)
        left, top = random.randint(0, bw - cw), random.randint(0, bh - ch)
        canvas = bg.crop((left, top, left + cw, top + ch)).resize((w, h), Image.BICUBIC)
        small = img.resize((max(int(w * s), 8), max(int(h * s), 8)), Image.BICUBIC)
        canvas.paste(small, (random.randint(0, w - small.width), random.randint(0, h - small.height)))
        return canvas


class RandomJPEG:
    """Re-encode as JPEG at a random quality, like a photo sent through a messaging app."""

    def __init__(self, p: float = 0.5, quality: tuple[int, int] = (35, 90)):
        self.p, self.quality = p, quality

    def __call__(self, img: Image.Image) -> Image.Image:
        if random.random() > self.p:
            return img
        import io

        buf = io.BytesIO()
        img.convert("RGB").save(buf, "JPEG", quality=random.randint(*self.quality))
        return Image.open(io.BytesIO(buf.getvalue())).convert("RGB")


def strong_train_transform(cfg: dict, backgrounds: list[str]):
    """Stronger augmentation (candidates A and B). No hue shift: lesion colour carries the diagnosis."""
    from torchvision import transforms as Tv
    from torchvision.transforms import InterpolationMode as Mode

    size = cfg["input_size"][1]
    fill = tuple(int(255 * v) for v in cfg["mean"])
    return Tv.Compose([
        ZoomOut(backgrounds, p=0.7, scale=(0.25, 1.0)),
        Tv.RandomApply([Tv.RandomRotation(20, interpolation=Mode.BICUBIC, fill=fill)], p=0.5),
        Tv.RandomResizedCrop(size, scale=(0.35, 1.0), ratio=(3 / 4, 4 / 3), interpolation=Mode.BICUBIC),
        Tv.RandomHorizontalFlip(), Tv.RandomVerticalFlip(),
        Tv.ColorJitter(brightness=0.3, contrast=0.3, saturation=0.1, hue=0.0),
        Tv.RandomApply([Tv.GaussianBlur(5, sigma=(0.1, 1.5))], p=0.2),
        RandomJPEG(p=0.5),
        Tv.ToTensor(), Tv.Normalize(cfg["mean"], cfg["std"]),
        Tv.RandomErasing(p=0.2),
    ])


def keep_background(ds, targets: list, samples: list, background: str):
    idx = [i for i, (path, _) in enumerate(samples) if background_of(*source_of(path)) == background]
    return Subset(ds, idx), [targets[i] for i in idx], [samples[i] for i in idx]


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


def threshold_for(t, pred: torch.Tensor):
    """t is one threshold, or a tensor with one threshold per predicted class (blast has its own)."""
    return t[pred] if torch.is_tensor(t) else t


def answered_mask(p: torch.Tensor, t, margin: float) -> torch.Tensor:
    top2 = p.topk(2, dim=1).values
    return (top2[:, 0] >= threshold_for(t, p.argmax(1))) & ((top2[:, 0] - top2[:, 1]) >= margin)


BLB_MAX_WRONG_SHARE = 0.05   # BLB answers ("no insecticide needed"): at most 5% wrong on validation (our choice)


def choose_class_threshold(pv: torch.Tensor, yv: torch.Tensor, cls: str, t: float, margin: float,
                           max_wrong_share: float) -> tuple[float, int]:
    """A class-only threshold: the smallest value (never below t) at which the share of wrong answers of
    this class on validation is at most max_wrong_share. Returns (threshold, validation answers left).
    1.01 means "never answer this class".
    """
    k = CLASSES.index(cls)
    conf, pred = pv.max(1)
    top2 = pv.topk(2, dim=1).values
    candidate = (pred == k) & ((top2[:, 0] - top2[:, 1]) >= margin)
    grid = [round(t + 0.005 * i, 3) for i in range(int((0.999 - t) / 0.005) + 1)] + [0.999]
    for ct in grid:
        sel = candidate & (conf >= ct)
        if int((yv[sel] != k).sum()) <= max_wrong_share * int(sel.sum()):
            return ct, int(sel.sum())
    return 1.01, 0


def choose_blast_threshold(pv: torch.Tensor, yv: torch.Tensor, t: float, margin: float) -> tuple[float, int]:
    """Spray advice is stricter than no-spray advice: NO blast answer on validation may be wrong.

    Validation includes every field-background validation photo, so wrong spray is 0 on those too.
    """
    return choose_class_threshold(pv, yv, "blast", t, margin, 0.0)


def selective(p: torch.Tensor, y: torch.Tensor, t, margin: float) -> dict:
    top2 = p.topk(2, dim=1).values
    conf, pred = p.max(1)
    answered = (conf >= threshold_for(t, pred)) & ((top2[:, 0] - top2[:, 1]) >= margin)
    out = {"n": int(len(y)), "coverage": float(answered.float().mean())}
    out["precision"] = float((pred[answered] == y[answered]).float().mean()) if answered.any() else float("nan")
    for name, k in (("blb", 0), ("blast", 1)):
        m = answered & (pred == k)
        out[f"precision_{name}_answers"] = {"value": float((y[m] == k).float().mean()) if m.any() else float("nan"),
                                            "n": int(m.sum())}
    out["abstained_pct_by_true_class"] = {
        CLASSES[k]: float((~answered[y == k]).float().mean()) if (y == k).any() else float("nan") for k in range(4)}
    return out


FIELD_ADVICE_PRECISION = 0.95   # on field-background validation photos: at most 5% of advice answers wrong
ADVICE_CLASSES = (0, 1, 2)      # BLB, blast, healthy give advice; "other" and abstain give a referral
RULE_FIELD = ("field: the strict rule, and on field-background validation photos at most 5% of advice "
              "answers (BLB, blast, healthy) are wrong")
RULE_STRICT = "strict: precision >= 0.90 overall, on BLB answers and on blast answers, coverage >= 0.50"
RULE_BASE = "base: precision >= 0.90 on answered images, coverage >= 0.50"
RULE_NONE = "none met: margin 0.2, highest precision with coverage >= 0.50"


def meets_target(s: dict, strict: bool) -> bool:
    if not (s["precision"] >= TARGET_PRECISION and s["coverage"] >= TARGET_COVERAGE):
        return False
    if strict:   # BLB and blast answers are the costly errors: each must reach the target as well
        for name in ("blb", "blast"):
            cell = s[f"precision_{name}_answers"]
            if cell["n"] and not cell["value"] >= TARGET_PRECISION:
                return False
    return True


def advice_outcomes(p: torch.Tensor, y: torch.Tensor, t: float, margin: float) -> dict:
    """What the farmer gets, per true class: correct advice, a referral, or wrong advice.

    Advice = an answered BLB, blast or healthy prediction. An "other" prediction or an abstention is a
    referral to 16123 or an officer, which is safe. Wrong advice is the harmful outcome.
    """
    pred = p.argmax(1)
    advice = answered_mask(p, t, margin) & (pred != CLASSES.index("other"))
    by_true = {}
    for k, cls in enumerate(CLASSES):
        true = y == k
        row = {"n": int(true.sum()), "referred": int((true & ~advice).sum()),
               "wrong_advice": int((true & advice & (pred != k)).sum())}
        if k in ADVICE_CLASSES:
            row["correct_advice"] = int((true & advice & (pred == k)).sum())
        by_true[cls] = row
    by_answer = {CLASSES[k]: {"given": int((advice & (pred == k)).sum()),
                              "wrong": int((advice & (pred == k) & (y != k)).sum())} for k in ADVICE_CLASSES}
    return {"n": int(len(y)), "advice_given": int(advice.sum()), "wrong_advice": int((advice & (pred != y)).sum()),
            "by_true_class": by_true, "by_answer": by_answer}


def outcome_counts(p: torch.Tensor, y: torch.Tensor, t, margin: float) -> dict:
    """The same four numbers everywhere (reports, README, model card, comparison scripts).

    classifier confident: the prediction passes the thresholds and margin (confident "other" included).
    advice given:         a confident BLB or healthy answer. This is what the farmer is told from the photo.
    blast question asked: a confident blast prediction. The app then asks the lesion-shape question; it gives
                          the spray answer only on "yes", so this is NOT counted as advice.
    referred:             everything else (not confident, or a confident "other").
    """
    pred = p.argmax(1)
    confident = answered_mask(p, t, margin)
    blast, other = CLASSES.index("blast"), CLASSES.index("other")
    advice = confident & (pred != other) & (pred != blast)
    question = confident & (pred == blast)
    by_true = {}
    for k, cls in enumerate(CLASSES):
        true = y == k
        by_true[cls] = {"n": int(true.sum()), "right_advice": int((true & advice & (pred == k)).sum()),
                        "wrong_advice": int((true & advice & (pred != k)).sum()),
                        "blast_question_asked": int((true & question).sum()),
                        "referred": int((true & ~advice & ~question).sum())}
    return {"n": int(len(y)), "classifier_confident": int(confident.sum()), "advice_given": int(advice.sum()),
            "right_advice": int((advice & (pred == y)).sum()), "wrong_advice": int((advice & (pred != y)).sum()),
            "blast_question_asked": int(question.sum()),
            "blast_question_on_true_blast": int((question & (y == blast)).sum()),
            "blast_question_on_other_classes": int((question & (y != blast)).sum()),   # wrong spray if answered "yes"
            "referred": int((~advice & ~question).sum()), "by_true_class": by_true}


def field_advice_ok(p: torch.Tensor, y: torch.Tensor, field: torch.Tensor | None, t: float, margin: float) -> bool:
    """Threshold rule input: BLB, blast and healthy answers together, as when the rule was introduced."""
    if field is None or not field.any():
        return True
    o = advice_outcomes(p[field], y[field], t, margin)
    return o["advice_given"] == 0 or 1 - o["wrong_advice"] / o["advice_given"] >= FIELD_ADVICE_PRECISION


def choose_threshold(pv: torch.Tensor, yv: torch.Tensor,
                     field: torch.Tensor | None = None) -> tuple[float, float, bool, str]:
    """Pick (t, margin) on validation. Returns (t, margin, target_met, rule).

    Rules are tried from strictest to loosest. The first two are stricter than the original plan (which
    only warned when BLB or blast answers fell below 0.90): run 1 answered every test image, and a later
    run picked a low threshold that gave wrong advice on field photos.
    """
    has_field = field is not None and bool(field.any())
    for use_field, strict, rule in ((True, True, RULE_FIELD), (False, True, RULE_STRICT), (False, False, RULE_BASE)):
        if use_field and not has_field:
            continue
        met = []
        for margin in MARGINS:
            for t in THRESHOLDS:   # smallest t that meets the target at this margin
                s = selective(pv, yv, t, margin)
                if meets_target(s, strict) and (not use_field or field_advice_ok(pv, yv, field, t, margin)):
                    met.append((margin, t, s["coverage"]))
                    break
        if met:
            margin, t, _ = max(met, key=lambda c: (c[2], -abs(c[0] - 0.2)))
            return t, margin, True, rule
    margin = 0.2
    covered = [(s["precision"], -t, t) for t in THRESHOLDS
               if (s := selective(pv, yv, t, margin))["coverage"] >= TARGET_COVERAGE and not math.isnan(s["precision"])]
    t = max(covered)[2] if covered else THRESHOLDS[0]
    print(ABSTAIN_SENTENCE)
    return t, margin, False, RULE_NONE


def source_of(path: str) -> tuple[str, str]:
    parts = Path(path).name.split("__")   # <source>__<source_class_slug>__<stem>_<sha>.jpg (prepare_data.py)
    return (parts[0], parts[1]) if len(parts) >= 3 else ("unknown", "unknown")


def background_of(source: str, class_slug: str) -> str:
    """Seen by eye: BD5 leaves lie on a white sheet, RiceLeafBD photos are taken in the field."""
    if source == "BD5" or (source == "DhanShomadhan" and class_slug.startswith("white_")):
        return "white"
    if source in ("RiceLeafBD", "PaddyDoctor") or (source == "DhanShomadhan" and class_slug.startswith("field_")):
        return "field"   # Paddy Doctor photos are wide shots of plants in the field
    return "unknown"


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


def background_table(p: torch.Tensor, y: torch.Tensor, backgrounds: list[str], t: float, margin: float,
                     extra_field_blast: dict | None = None) -> list[dict]:
    """Recall, abstain rate and confident-wrong rate per (background, true class)."""
    pred, answered = p.argmax(1), answered_mask(p, t, margin)
    rows = []
    for bg in ("field", "white"):
        for k, cls in enumerate(CLASSES):
            m = torch.tensor([b == bg for b in backgrounds], dtype=torch.bool) & (y == k)
            n, correct, abstained = int(m.sum()), int((pred[m] == k).sum()), int((~answered[m]).sum())
            wrong = int((answered[m] & (pred[m] != k)).sum())
            if bg == "field" and cls == "blast" and extra_field_blast:
                d = extra_field_blast
                n += d["n"]
                correct += int(round(d["blast_recall"] * d["n"]))
                abstained += int(round(d["abstain_rate"] * d["n"]))
                wrong += int(round(d["answered_wrong"] * d["n"]))
            if n:
                rows.append({"background": bg, "target": cls, "n": n, "recall": correct / n,
                             "abstain_rate": abstained / n, "answered_wrong_rate": wrong / n})
    return rows


def calibrate_and_evaluate(model, dl_va, dl_te, dhs_dl, te_samples, out, device, va_samples=(),
                           class_thresholds_for_blb: bool = False) -> dict:
    """Fit T and choose (t, margin) on validation; report every metric on test. Returns the metrics dict."""
    lv, yv = logits_of(model, dl_va, device)
    lt, yt = logits_of(model, dl_te, device)
    T, clamped = fit_temperature(lv, yv)
    print(f"Temperature T = {T:.4f} (clamped: {clamped})")
    if clamped:
        print("WARNING: temperature was clamped. On the real run this is a warning sign for gate G2.")
    pv, pt = F.softmax(lv / T, dim=1), F.softmax(lt / T, dim=1)

    val_field = torch.tensor([background_of(*source_of(p)) == "field" for p, _ in va_samples], dtype=torch.bool) \
        if len(va_samples) == len(yv) else None
    t_general, margin, target_met, rule = choose_threshold(pv, yv, val_field)
    print(f"Threshold rule: {rule}")
    blast_t, val_blast_answers = choose_blast_threshold(pv, yv, t_general, margin)
    print(f"Blast-only threshold = {blast_t} (general threshold {t_general}); validation blast answers left: "
          f"{val_blast_answers}, none of them wrong")
    if blast_t > 1:
        print("WARNING: no threshold gives zero wrong blast answers on validation. Blast is never answered.")
    coverage_before = {"val": selective(pv, yv, t_general, margin)["coverage"],
                       "test": selective(pt, yt, t_general, margin)["coverage"]}
    blb_t, val_blb_answers = (choose_class_threshold(pv, yv, "bacterial_leaf_blight", t_general, margin,
                                                     BLB_MAX_WRONG_SHARE) if class_thresholds_for_blb
                              else (t_general, -1))
    if class_thresholds_for_blb:
        print(f"BLB-only threshold = {blb_t}; validation BLB answers left: {val_blb_answers}, "
              f"at most {BLB_MAX_WRONG_SHARE:.0%} of them wrong")
    # From here on t is per predicted class: every table below uses the class-only thresholds.
    per_class_t = {"blast": blast_t, "bacterial_leaf_blight": blb_t}
    t = torch.tensor([per_class_t.get(c, t_general) for c in CLASSES], dtype=pv.dtype)
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
    pd_, yd = pt[:0], yt[:0]
    if dhs_dl is not None and len(dhs_dl.dataset):
        ld, yd = logits_of(model, dhs_dl, device)
        pd_ = F.softmax(ld / T, dim=1)
        ans = answered_mask(pd_, t, margin)
        is_blast = pd_.argmax(1) == CLASSES.index("blast")
        dhs = {"n": int(len(yd)), "blast_recall": float(is_blast.float().mean()),
               "abstain_rate": float((~ans).float().mean()), "answered_as_blast": float((ans & is_blast).float().mean()),
               "answered_wrong": float((ans & ~is_blast).float().mean())}

    # Per background and true class. The held-out Dhan-Shomadhan field blast images count as field blast.
    by_background = background_table(pt, yt, [background_of(*s) for s in sources], t, margin, extra_field_blast=dhs)
    val_by_background = background_table(pv, yv, [background_of(*source_of(p)) for p, _ in va_samples], t, margin)

    # Advice-level outcomes. Field = test photos with a field background plus the held-out field blast.
    test_field = torch.tensor([background_of(*s) == "field" for s in sources], dtype=torch.bool)
    advice = {
        "field": advice_outcomes(torch.cat([pt[test_field], pd_]), torch.cat([yt[test_field], yd]), t, margin),
        "all": advice_outcomes(torch.cat([pt, pd_]), torch.cat([yt, yd]), t, margin),
        "val_field": advice_outcomes(pv[val_field], yv[val_field], t, margin) if val_field is not None else None,
    }
    outcomes = {   # the definitions used in every report
        "test": outcome_counts(pt, yt, t, margin),
        "field": outcome_counts(torch.cat([pt[test_field], pd_]), torch.cat([yt[test_field], yd]), t, margin),
        "val": outcome_counts(pv, yv, t, margin),
    }

    save_confusion_png(cm, out / "confusion.png", len(yt))
    save_risk_coverage_png(pt, yt, t_general, margin, out / "risk_coverage.png")
    return {
        "temperature": T, "temperature_clamped": clamped, "threshold": t_general, "margin": margin,
        "blast_threshold": blast_t, "val_blast_answers_at_blast_threshold": val_blast_answers,
        "blb_threshold": blb_t if class_thresholds_for_blb else None,
        "val_blb_answers_at_blb_threshold": val_blb_answers if class_thresholds_for_blb else None,
        "coverage_before_blast_threshold": coverage_before,
        "target": {"precision": TARGET_PRECISION, "coverage": TARGET_COVERAGE},
        "target_met": target_met, "spray_relevant_precision_ok": spray_ok, "threshold_rule": rule,
        "val": val, "val_macro_f1_no_abstention": float(f1_score(yv, pv.argmax(1), labels=labels, average="macro",
                                                                 zero_division=0)),
        "val_by_background": val_by_background,
        "test": test, "per_source": per_source, "by_background": by_background, "advice": advice,
        "outcomes": outcomes,
        "dhs_field_blast": dhs,
    }


# ----------------------------------------------------------------- export

def export_onnx_and_labels(model, cfg, va, out, *, model_name: str, classes: list[str], calib: dict,
                           trained_on: list[str]) -> dict:
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
        # Blast is the only spray answer, so it has its own stricter threshold (never below "threshold").
        "blast_threshold": round(calib["blast_threshold"], 3),
        **({"blb_threshold": round(calib["blb_threshold"], 3)} if calib.get("blb_threshold") is not None else {}),
        "input_size": list(cfg["input_size"]), "mean": [float(v) for v in cfg["mean"]],
        "std": [float(v) for v in cfg["std"]],
        "crop_pct": float(cfg["crop_pct"]), "interpolation": cfg["interpolation"],
        "onnx_input": "input", "onnx_output": "logits",
        "trained_on": trained_on, "date": dt.date.today().isoformat(),
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
    before = m["coverage_before_blast_threshold"]
    print(f"blast-only threshold = {m['blast_threshold']} ({m['val_blast_answers_at_blast_threshold']} validation "
          f"blast answers left, none wrong) | coverage before it: val {before['val']:.4f}, test {before['test']:.4f}")
    print(f"test n = {t['n']} | macro-F1 (no abstention) = {t['macro_f1_no_abstention']:.4f} | "
          f"coverage = {t['coverage']:.4f} | selective accuracy = {t['selective_accuracy']:.4f}")
    print(f"precision on BLB answers = {cell(t['precision_blb_answers'])} | "
          f"on blast answers = {cell(t['precision_blast_answers'])}")
    print("per source (test, recall without abstention):")
    for r in m["per_source"]:
        print(f"  {r['source']:<12} {r['source_class']:<24} -> {r['target']:<22} n={r['n']:<5} "
              f"recall={r['recall']:.3f} abstain={r['abstain_rate']:.3f}")
    for title, key in (("VALIDATION per background (use this to choose between runs)", "val_by_background"),
                       ("TEST per background (test + held-out field blast)", "by_background")):
        print(f"{title}:")
        for r in m[key]:
            print(f"  {r['background']:<6} {r['target']:<22} n={r['n']:<5} recall={r['recall']:.3f} "
                  f"abstain={r['abstain_rate']:.3f} answered wrong={r['answered_wrong_rate']:.3f}")
    for title, key in (("VALIDATION field photos", "val_field"), ("TEST field photos + held-out field blast", "field"),
                       ("TEST all photos + held-out field blast", "all")):
        a = m["advice"][key]
        if not a:
            continue
        print(f"ADVICE on {title}: advice given {a['advice_given']}/{a['n']}, wrong advice {a['wrong_advice']} | "
              + ", ".join(f"{c} answers wrong {v['wrong']}/{v['given']}" for c, v in a["by_answer"].items()))
        for cls, r in a["by_true_class"].items():
            print(f"    true {cls:<22} n={r['n']:<4} correct advice={r.get('correct_advice', '-'):<4} "
                  f"referred={r['referred']:<4} wrong advice={r['wrong_advice']}")
    print(f"validation macro-F1 (no abstention) = {m['val_macro_f1_no_abstention']:.4f} | "
          f"val coverage = {m['val']['coverage']:.3f} | balance = {m['balance']}")
    d = m["dhs_field_blast"]
    kind = "cross-source" if m["dhs_field_blast_is_cross_source"] else "held-out slice of a seen source"
    print(f"Dhan-Shomadhan field blast ({kind}): " + (
        f"n={d['n']} blast recall={d['blast_recall']:.3f} abstain rate={d['abstain_rate']:.3f} "
        f"answered as blast={d['answered_as_blast']:.3f} answered wrong={d['answered_wrong']:.3f}"
        if d else "not available (no dhs_field_blast/ folder)"))
    print(f"threshold rule: {m['threshold_rule']} | Dhan-Shomadhan images in train/val/test: {m['dhs_images']}")
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
    p.add_argument("--balance", choices=["class", "group"], default="class",
                   help="sampler balance: per class, or per class x background (field / white sheet)")
    p.add_argument("--backgrounds", choices=["all", "field", "white"], default="all",
                   help="experiment: train and tune on one background only (the test split stays complete)")
    p.add_argument("--aug", choices=["standard", "strong"], default="standard",
                   help="strong: zoom-out onto field backgrounds, wider crops, rotation, blur, JPEG, brightness")
    p.add_argument("--blb-threshold", action="store_true",
                   help="also choose a BLB-only threshold on validation (at most 5%% wrong BLB answers)")
    p.add_argument("--subset", type=int, help="max images per split (CPU smoke runs only)")
    p.add_argument("--no-pretrained", action="store_true", help="offline smoke test only; never for the real run")
    p.add_argument("--skip-export", action="store_true", help="train and save best.pt only")
    p.add_argument("--weights", type=Path,
                   help="re-evaluate and re-export an existing best.pt instead of training (same --data and flags)")
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

    if args.aug == "strong":
        backgrounds = [path for path, y in tr.samples if CLASSES[y] == "other"
                       and source_of(path)[0] != "PaddyDoctor" and background_of(*source_of(path)) == "field"]
        print(f"strong augmentation: zoom-out backgrounds from {len(backgrounds)} of our field 'other' photos")
        tr.transform = strong_train_transform(cfg, backgrounds)
    tr_ds, tr_targets, tr_samples = take_subset(tr, args.subset, args.seed)
    va_ds, va_targets, va_samples = take_subset(va, args.subset, args.seed)
    if args.backgrounds != "all":   # experiment: train and tune only on one background; test stays complete
        tr_ds, tr_targets, tr_samples = keep_background(tr_ds, tr_targets, tr_samples, args.backgrounds)
        va_ds, va_targets, va_samples = keep_background(va_ds, va_targets, va_samples, args.backgrounds)
    te_ds, te_targets, te_samples = take_subset(te, args.subset, args.seed)
    for name, targets in (("train", tr_targets), ("val", va_targets), ("test", te_targets)):
        per = np.bincount(targets, minlength=4)
        print(f"{name:<5} n={len(targets):<5} " + " ".join(f"{c}={n}" for c, n in zip(CLASSES, per)))

    # Class balance through the sampler only (never the sampler and loss weights together).
    if args.balance == "group":
        # Balance class x background cells, so the background stops predicting the class: in the raw data
        # blast is almost always on a white sheet and BLB always in the field.
        cells = [(y, background_of(*source_of(path))) for (path, _), y in zip(tr_samples, tr_targets)]
        cell_n = {c: cells.count(c) for c in set(cells)}
        print("sampler cells (class, background): "
              + ", ".join(f"{CLASSES[k]}/{bg}={n}" for (k, bg), n in sorted(cell_n.items())))
        weights = torch.tensor([len(cells) / (len(cell_n) * cell_n[c]) for c in cells], dtype=torch.double)
    else:
        counts = np.bincount(tr_targets, minlength=4)
        w = counts.sum() / (4 * np.maximum(counts, 1))                    # N / (4 * n_class)
        weights = torch.tensor(w, dtype=torch.double)[torch.tensor(tr_targets)]
    sampler = WeightedRandomSampler(weights, num_samples=len(tr_targets), replacement=True)
    pin = device == "cuda"
    keep = args.workers > 0   # keep workers alive between epochs (starting them is slow on Windows)
    dl_tr = DataLoader(tr_ds, batch_size=args.batch, sampler=sampler, num_workers=args.workers,
                       pin_memory=pin, drop_last=len(tr_targets) > args.batch, persistent_workers=keep)
    # Evaluation sets are small: load them in the main process. A second set of live worker processes
    # ran a 24 GB Windows machine out of memory ("bad allocation").
    dl_va = DataLoader(va_ds, batch_size=args.batch, shuffle=False, num_workers=0, pin_memory=pin)
    dl_te = DataLoader(te_ds, batch_size=args.batch, shuffle=False, num_workers=0, pin_memory=pin)
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

    if args.weights:
        # Re-evaluate existing weights (new threshold rule, new metrics) without training again.
        model.load_state_dict(torch.load(args.weights, map_location=device))
        previous = args.weights.parent / "metrics.json"
        train_seconds = json.loads(previous.read_text("utf-8")).get("train_seconds", 0.0) if previous.exists() else 0.0
        print(f"Loaded {args.weights}; no training in this run (original training took {train_seconds:.0f}s).")
    else:
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
    if not args.weights:
        print(f"Saved best.pt (best val macro-F1 {best_f1:.4f}) after {train_seconds:.0f}s of training")
    if args.skip_export:
        return 0

    dhs_dir = args.data / "dhs_field_blast"
    dhs_dl = None
    if dhs_dir.is_dir():
        dhs_ds = FolderAsClass(dhs_dir, eval_tf, CLASSES.index("blast"))
        if len(dhs_ds):
            dhs_dl = DataLoader(dhs_ds, batch_size=args.batch, shuffle=False, num_workers=0)

    import onnx
    import onnxruntime

    calib = calibrate_and_evaluate(model, dl_va, dl_te, dhs_dl, te_samples, args.out, device, va_samples,
                                   class_thresholds_for_blb=args.blb_threshold)
    dhs_in = {name: sum(source_of(path)[0] == "DhanShomadhan" for path, _ in ds.samples)
              for name, ds in (("train", tr), ("val", va), ("test", te))}
    trained_on = TRAINED_ON + ([DHS_DOI] if dhs_in["train"] or dhs_in["val"] else [])
    if any(source_of(path)[0] == "PaddyDoctor" for path, _ in tr.samples):
        trained_on = trained_on + ["arXiv:2205.11108 (Paddy Doctor, Kaggle paddy-disease-classification, CC BY 4.0)"]
    exported = export_onnx_and_labels(model, cfg, va_ds, args.out, model_name=args.model,
                                      classes=tr.classes, calib=calib, trained_on=trained_on)
    metrics = {
        "model": args.model, "date": dt.date.today().isoformat(), "classes": tr.classes,
        "trained_on": trained_on, "dhs_images": dhs_in, "balance": args.balance, "augmentation": args.aug,
        "paddy_doctor_images": {name: sum(source_of(path)[0] == "PaddyDoctor" for path, _ in ds.samples)
                                for name, ds in (("train", tr), ("val", va), ("test", te))},
        "train_backgrounds": args.backgrounds, "train_n": len(tr_targets), "val_n": len(va_targets),
        "epochs": {"head": args.epochs_head, "full": args.epochs},
        # False once Dhan-Shomadhan images are in train/ or val/: the held-out field blast slice is then
        # from a source the model has seen.
        "dhs_field_blast_is_cross_source": not (dhs_in["train"] or dhs_in["val"]),
        **calib, **exported, "train_seconds": train_seconds, "re_evaluated_from_weights": bool(args.weights),
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

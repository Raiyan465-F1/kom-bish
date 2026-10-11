"""Diagnosis: why does the shipped model fail on the external Paddy Doctor test? (run in .venv-train)

  python training/diagnose_external.py [figure_folder]

Read-only: it changes no model, threshold or result file. The occlusion figure contains Paddy Doctor
photos, so it is written to a temporary folder by default and must not be committed. Findings are in
docs/gates.md. The linear probe trains a throwaway classifier on Paddy photos to measure whether the
features carry transferable signal; it is never used by the app.
"""
import csv
import json
import random
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import timm
import torch
import torch.nn.functional as F
from PIL import Image
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

import tempfile

root = Path(__file__).resolve().parent.parent
out_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(tempfile.mkdtemp(prefix="kombish_diagnose_"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(root))
from kombish import classifier  # noqa: E402

CLASSES = ["bacterial_leaf_blight", "blast", "healthy", "other"]
MAP = {"bacterial_leaf_blight": "bacterial_leaf_blight", "blast": "blast", "normal": "healthy"}
labels = json.loads((root / "models" / "labels.json").read_text("utf-8"))
T = labels["temperature"]
dev = "cuda" if torch.cuda.is_available() else "cpu"
ours = timm.create_model(labels["model"], pretrained=False, num_classes=4)
ours.load_state_dict(torch.load(root / "models" / "best.pt", map_location="cpu"))
ours.eval().to(dev)
imagenet = timm.create_model(labels["model"], pretrained=True, num_classes=0).eval().to(dev)   # before our fine-tuning


def tens(img: Image.Image) -> torch.Tensor:
    return torch.from_numpy(classifier.preprocess(img, labels)[0])


@torch.no_grad()
def batched(imgs, fn, bs=96):
    outs = []
    for i in range(0, len(imgs), bs):
        outs.append(fn(torch.stack([tens(im) for im in imgs[i:i + bs]]).to(dev)).float().cpu())
    return torch.cat(outs)


def probs(imgs):
    return F.softmax(batched(imgs, ours) / T, dim=1).numpy()


def feats_ours(imgs):
    return batched(imgs, lambda x: ours.forward_head(ours.forward_features(x), pre_logits=True)).numpy()


def feats_imagenet(imgs):
    return batched(imgs, imagenet).numpy()


def load(path):
    return Image.open(path).convert("RGB")


prepared = root / "data" / "prepared_run3"
man = list(csv.DictReader((prepared / "manifest.csv").open(encoding="utf-8", newline="")))
paddy = root / "data" / "external" / "paddy_doctor"
ext = list(csv.DictReader((root / "training" / "results" / "external_paddy_doctor_manifest.csv").open(encoding="utf-8")))
ext_imgs = [load(paddy / r["file"]) for r in ext]
ext_y = np.array([CLASSES.index(r["mapped_label"]) for r in ext])

# ---------------------------------------------------------------- A. is it the scale? (our own test images)
def tile(im, k):
    w, h = im.size
    small = im.resize((max(w // k, 1), max(h // k, 1)), Image.BICUBIC)
    canvas = Image.new("RGB", (small.width * k, small.height * k))
    for i in range(k):
        for j in range(k):
            canvas.paste(small, (i * small.width, j * small.height))
    return canvas


def zoom(im, keep):
    w, h = im.size
    cw, ch = int(w * keep), int(h * keep)
    return im.crop(((w - cw) // 2, (h - ch) // 2, (w - cw) // 2 + cw, (h - ch) // 2 + ch))


test = [r for r in man if r["split"] == "test"]
test_imgs = [load(prepared / r["path"]) for r in test]
test_y = np.array([CLASSES.index(r["target"]) for r in test])
field = np.array([r["source"] == "RiceLeafBD" or r["source_class"].startswith("Field") for r in test])
print("A. Scale test on OUR OWN test images (same content, only the size of the leaf in the frame changes)")
for name, fn in (("as is", lambda im: im), ("leaf at 1/2 size (2x2 tiles)", lambda im: tile(im, 2)),
                 ("leaf at 1/3 size (3x3 tiles)", lambda im: tile(im, 3)),
                 ("leaf at 1/4 size (4x4 tiles)", lambda im: tile(im, 4)), ("zoomed in to 60%", lambda im: zoom(im, 0.6))):
    p = probs([fn(im) for im in test_imgs])
    pred = p.argmax(1)
    print(f"   {name:<30} top guess right: all {int((pred == test_y).sum())}/{len(test_y)} = {(pred == test_y).mean():.3f} | "
          f"field photos {int((pred[field] == test_y[field]).sum())}/{int(field.sum())} = {(pred[field] == test_y[field]).mean():.3f} | "
          f"guessed 'other' {int((pred == 3).sum())}")

# ---------------------------------------------------------------- B. do small tiles of the Paddy photos help?
print("\nB. Paddy Doctor: look at 12 tiles (3 x 4) of each photo instead of the whole photo")
whole = probs(ext_imgs)
tile_probs = []
for im in ext_imgs:
    w, h = im.size
    tiles = [im.crop((i * w // 3, j * h // 4, (i + 1) * w // 3, (j + 1) * h // 4)) for i in range(3) for j in range(4)]
    tile_probs.append(probs(tiles))
tile_probs = np.array(tile_probs)                       # (200, 12, 4)
mean_vote = tile_probs.mean(1).argmax(1)
best_tile = tile_probs.reshape(len(ext), -1).argmax(1) % 4
print(f"   whole photo: top guess right {int((whole.argmax(1) == ext_y).sum())}/200")
print(f"   average over 12 tiles: right {int((mean_vote == ext_y).sum())}/200")
print(f"   most confident tile:   right {int((best_tile == ext_y).sum())}/200")
print("   what the tiles are called, per true class (share of all tiles):")
for k, c in enumerate(CLASSES):
    t = tile_probs[ext_y == k].argmax(2).ravel()
    print(f"      true {c:<22} " + "  ".join(f"{CLASSES[j]}={np.mean(t == j):.2f}" for j in range(4)))

# ---------------------------------------------------------------- C. is there transferable signal in the features?
print("\nC. Linear probe: train a simple classifier on Paddy photos using frozen features, test on the 200")
by_label = {}
for row in csv.DictReader((paddy / "train.csv").open(encoding="utf-8", newline="")):
    by_label.setdefault(row["label"], []).append(row["image_id"])
used = {r["file"] for r in ext}
rng = random.Random(0)
others = sorted(lab for lab in by_label if lab not in MAP)
probe = []
for lab in sorted(by_label):
    quota = 150 if lab in MAP else 150 // len(others) + 1
    pool = sorted(i for i in by_label[lab] if f"train_images/{lab}/{i}" not in used)
    probe += [(f"train_images/{lab}/{i}", MAP.get(lab, "other")) for i in rng.sample(pool, min(quota, len(pool)))]
probe_imgs = [load(paddy / f) for f, _ in probe]
probe_y = np.array([CLASSES.index(c) for _, c in probe])
print(f"   probe training photos: {len(probe)} {dict(Counter(c for _, c in probe))} (none of the 200 test photos)")
for name, fn in (("our fine-tuned model's features", feats_ours), ("plain ImageNet features (before our training)", feats_imagenet)):
    scaler = StandardScaler().fit(fn(probe_imgs))
    clf = LogisticRegression(max_iter=3000, C=0.5).fit(scaler.transform(fn(probe_imgs)), probe_y)
    pred = clf.predict(scaler.transform(fn(ext_imgs)))
    per = "  ".join(f"{c}={int(((pred == k) & (ext_y == k)).sum())}/50" for k, c in enumerate(CLASSES))
    print(f"   {name:<46} right {int((pred == ext_y).sum())}/200 | {per}")

# ---------------------------------------------------------------- D. how far are Paddy photos from anything we trained on?
print("\nD. Distance to the nearest training photo, in our model's feature space (cosine similarity, 1 = identical)")
train = [r for r in man if r["split"] == "train"]
ft = F.normalize(torch.from_numpy(feats_ours([load(prepared / r["path"]) for r in train])), dim=1)
for name, imgs in (("our own test photos", test_imgs), ("Paddy Doctor photos", ext_imgs)):
    fe = F.normalize(torch.from_numpy(feats_ours(imgs)), dim=1)
    sims, idx = (fe @ ft.T).max(1)
    near = Counter(f"{train[i]['source']} {train[i]['target']}" for i in idx.tolist())
    print(f"   {name:<22} median {sims.median():.3f} | 10th percentile {sims.quantile(0.1):.3f} | nearest training photo is: "
          + ", ".join(f"{k} {v}" for k, v in near.most_common(4)))

# ---------------------------------------------------------------- E. where does the model look? (occlusion maps)
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

mean, std = np.array(labels["mean"], np.float32), np.array(labels["std"], np.float32)


@torch.no_grad()
def occlusion(img, patch=48, stride=24):
    x = tens(img)
    base = F.softmax(ours(x[None].to(dev)) / T, dim=1)[0].cpu().numpy()
    k = int(base.argmax())
    xs, pos = [], []
    for top in range(0, 224 - patch + 1, stride):
        for left in range(0, 224 - patch + 1, stride):
            y = x.clone()
            y[:, top:top + patch, left:left + patch] = 0          # 0 = the average colour after normalisation
            xs.append(y); pos.append((top, left))
    p = F.softmax(ours(torch.stack(xs).to(dev)) / T, dim=1)[:, k].cpu().numpy()
    heat, count = np.zeros((224, 224), np.float32), np.zeros((224, 224), np.float32)
    for (top, left), v in zip(pos, p):
        heat[top:top + patch, left:left + patch] += base[k] - v   # how much the answer drops when this part is hidden
        count[top:top + patch, left:left + patch] += 1
    shown = np.clip((x.numpy().transpose(1, 2, 0) * std + mean), 0, 1)
    return shown, heat / np.maximum(count, 1), k, float(base[k])


def pick(rows, base, want_pred=None, n=1, start=0):
    chosen = []
    for r in rows[start:]:
        im = load(base / (r.get("path") or r["file"]))
        k = int(probs([im]).argmax(1)[0])
        if want_pred is None or CLASSES[k] == want_pred:
            chosen.append((r, im))
        if len(chosen) == n:
            break
    return chosen


cases = []
for title, rows, base, want in (
        ("ours: field BLB", [r for r in test if r["source"] == "RiceLeafBD" and r["target"] == "bacterial_leaf_blight"], prepared, "bacterial_leaf_blight"),
        ("ours: white-sheet blast", [r for r in test if r["source"] == "BD5" and r["target"] == "blast"], prepared, "blast"),
        ("ours: field healthy", [r for r in test if r["source"] == "RiceLeafBD" and r["target"] == "healthy"], prepared, "healthy"),
        ("ours: held-out field blast", [r for r in man if r["split"] == "dhs_field_blast"], prepared, None),
        ("Paddy: BLB", [r for r in ext if r["source_label"] == "bacterial_leaf_blight"], paddy, None),
        ("Paddy: blast", [r for r in ext if r["source_label"] == "blast"], paddy, None),
        ("Paddy: normal", [r for r in ext if r["source_label"] == "normal"], paddy, None),
        ("Paddy: BLB (2)", [r for r in ext if r["source_label"] == "bacterial_leaf_blight"][10:], paddy, None)):
    for r, im in pick(rows, base, want):
        cases.append((title, im))
fig, axes = plt.subplots(2, len(cases), figsize=(2.6 * len(cases), 5.6))
for col, (title, im) in enumerate(cases):
    shown, heat, k, conf = occlusion(im)
    axes[0, col].imshow(shown); axes[0, col].set_title(title, fontsize=8)
    axes[1, col].imshow(shown); axes[1, col].imshow(np.maximum(heat, 0), cmap="hot", alpha=0.65, vmin=0, vmax=max(heat.max(), 0.05))
    axes[1, col].set_title(f"says {CLASSES[k]} ({conf:.2f})\nmax drop {heat.max():.2f}", fontsize=8)
    for a in axes[:, col]:
        a.axis("off")
fig.suptitle("Top: what the model sees (224 px crop). Bottom: bright = hiding this part lowers the answer most.", fontsize=9)
fig.tight_layout(); fig.savefig(out_dir / "why_occlusion.png", dpi=110)
print("\nE. wrote", out_dir / "why_occlusion.png")


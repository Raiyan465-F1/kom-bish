"""Near-duplicate leak check across train / val / test / held-out, any class and any source (run in .venv-train).

  python training/check_leakage.py --data data/prepared_run3

prepare_data.py --phash only groups near-duplicates inside one (source, class) folder, and hashes the raw
files. This check hashes the prepared images and compares every evaluation image with every training image.
It then re-computes the shipped model's metrics (ONNX, the app's own code path) with and without the leaked
test images, lists the field photos that got wrong advice, and writes training/results/leak_check.json.
"""
import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path

import imagehash
import numpy as np
import onnxruntime as ort
from PIL import Image
from sklearn.metrics import f1_score

root = Path(__file__).resolve().parent.parent
_p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
_p.add_argument("--data", type=Path, required=True, help="prepared root with manifest.csv")
_p.add_argument("--out", type=Path, default=root / "training" / "results" / "leak_check.json")
_args = _p.parse_args()
prepared, out_json = _args.data.resolve(), _args.out
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(root))
from kombish import classifier  # noqa: E402

CLASSES = ["bacterial_leaf_blight", "blast", "healthy", "other"]
DIST = 5
rows = list(csv.DictReader((prepared / "manifest.csv").open(encoding="utf-8", newline="")))
print(f"images in manifest: {len(rows)}  by split: {dict(Counter(r['split'] for r in rows))}")

# ---- perceptual hashes (64-bit pHash, the same hash prepare_data.py --phash uses)
bits = np.zeros((len(rows), 64), dtype=bool)
for i, r in enumerate(rows):
    with Image.open(prepared / r["path"]) as im:
        bits[i] = imagehash.phash(im).hash.flatten()
split = np.array([r["split"] for r in rows])
eval_idx = np.where(split != "train")[0]
train_idx = np.where(split == "train")[0]


def hamming(a_idx, b_idx):
    return (bits[a_idx][:, None, :] != bits[b_idx][None, :, :]).sum(-1)


pairs = []   # (eval image, other image, distance) with the two images in DIFFERENT splits
for chunk in np.array_split(eval_idx, 20):
    d = hamming(chunk, train_idx)
    for a, b in zip(*np.where(d <= DIST)):
        pairs.append((int(chunk[a]), int(train_idx[b]), int(d[a, b])))
d = hamming(eval_idx, eval_idx)
for a, b in zip(*np.where(d <= DIST)):
    i, j = int(eval_idx[a]), int(eval_idx[b])
    if i < j and split[i] != split[j]:
        pairs.append((i, j, int(d[a, b])))

print(f"\ncross-split pairs within pHash distance {DIST}: {len(pairs)}")
print("  by distance:", dict(sorted(Counter(p[2] for p in pairs).items())))
print("  by split pair:", dict(Counter(tuple(sorted((split[a], split[b]))) for a, b, _ in pairs)))
same_class = sum(rows[a]["target"] == rows[b]["target"] for a, b, _ in pairs)
same_stratum = sum((rows[a]["source"], rows[a]["source_class"]) == (rows[b]["source"], rows[b]["source_class"])
                   for a, b, _ in pairs)
print(f"  same target class: {same_class}; different target class: {len(pairs) - same_class}; "
      f"same source and source class: {same_stratum}")
print("  by (source|class) pair:")
for key, n in Counter(tuple(sorted((f"{rows[a]['source']}|{rows[a]['source_class']}",
                                    f"{rows[b]['source']}|{rows[b]['source_class']}"))) for a, b, _ in pairs).most_common(12):
    print(f"    {n:4d}  {key[0]}  <->  {key[1]}")
for a, b, dist in sorted(pairs, key=lambda p: p[2])[:8]:
    print(f"    d={dist}: [{split[a]}] {rows[a]['orig_path']}  ~  [{split[b]}] {rows[b]['orig_path']}")

leaked = {}   # eval image index -> set of splits it has a near-duplicate in
for a, b, _ in pairs:
    leaked.setdefault(a, set()).add(split[b])
    if split[b] != "train":
        leaked.setdefault(b, set()).add(split[a])
test_like = {"test", "dhs_field_blast"}
leaked_test = sorted(i for i, s in leaked.items() if split[i] in test_like and (s & {"train", "val"}))
leaked_val = sorted(i for i, s in leaked.items() if split[i] == "val" and "train" in s)
print(f"\ntest / held-out images with a near-duplicate in train or val: {len(leaked_test)} "
      f"of {int(np.isin(split, list(test_like)).sum())}")
print("  by true class:", dict(Counter(rows[i]["target"] for i in leaked_test)))
print("  by source:", dict(Counter(rows[i]["source"] for i in leaked_test)))
print(f"validation images with a near-duplicate in train: {len(leaked_val)} of {int((split == 'val').sum())}")

# ---- shipped model on test (+ held-out), full vs without leaked images
m = classifier.meta()
sess = ort.InferenceSession(str(root / "models" / "model.onnx"), providers=["CPUExecutionProvider"])
t, margin = m["threshold"], m["margin"]
test_idx = [i for i in range(len(rows)) if split[i] in test_like]
P = []
for i in test_idx:
    with Image.open(prepared / rows[i]["path"]) as im:
        z = sess.run(["logits"], {"input": classifier.preprocess(im, m)})[0][0].astype(np.float64) / m["temperature"]
    e = np.exp(z - z.max())
    P.append(e / e.sum())
P = np.array(P)
Y = np.array([CLASSES.index(rows[i]["target"]) for i in test_idx])
field = np.array([rows[i]["source"] == "RiceLeafBD" or rows[i]["source_class"].startswith("Field") for i in test_idx])
in_test_split = np.array([split[i] == "test" for i in test_idx])
clean = np.array([i not in set(leaked_test) for i in test_idx])
srt = np.sort(P, axis=1)
pred = P.argmax(1)
answered = (P.max(1) >= t) & ((srt[:, -1] - srt[:, -2]) >= margin)
answered &= ~((pred == 1) & (P.max(1) < m.get("blast_threshold", t)))   # blast has its own, stricter threshold
answered &= ~((pred == 0) & (P.max(1) < (m.get("blb_threshold") or t)))  # and BLB, when labels.json has one
advice = answered & (pred != 3)


def report(name, mask):
    ts = mask & in_test_split   # the classification metrics are over the test split, as in metrics.json
    f1 = f1_score(Y[ts], pred[ts], labels=[0, 1, 2, 3], average="macro", zero_division=0)
    cov = answered[ts].mean()
    acc = (pred[ts & answered] == Y[ts & answered]).mean()
    res = {"test_n": int(ts.sum()), "macro_f1_no_abstention": float(f1), "coverage": float(cov),
           "selective_accuracy": float(acc)}
    for label, k in (("blb", 0), ("blast", 1)):
        sel = ts & answered & (pred == k)
        res[f"precision_{label}_answers"] = {"value": float((Y[sel] == k).mean()) if sel.any() else None,
                                             "n": int(sel.sum())}
    f = mask & field
    res["field"] = {"n": int(f.sum()), "advice_given": int((f & advice).sum()),
                    "wrong_advice": int((f & advice & (pred != Y)).sum())}
    for label, k in (("blast", 1), ("blb", 0)):
        tr = f & (Y == k)
        res["field"][label] = {"n": int(tr.sum()), "correct_advice": int((tr & advice & (pred == k)).sum()),
                               "referred": int((tr & ~advice).sum()),
                               "wrong_advice": int((tr & advice & (pred != k)).sum())}
    print(f"\n{name}: test n={res['test_n']} macro-F1={f1:.4f} coverage={cov:.4f} selective acc={acc:.4f} | "
          f"BLB answers {res['precision_blb_answers']} | blast answers {res['precision_blast_answers']}")
    print(f"   field: {res['field']}")
    return res


full = report("FULL test set (ONNX, app code path)", np.ones(len(test_idx), bool))
without = report("WITHOUT leaked test images", clean)

print("\nField photos that got WRONG ADVICE (shipped model):")
wrong_rows = []
for j in np.where(field & advice & (pred != Y))[0]:
    r = rows[test_idx[j]]
    item = {"photo": r["orig_path"], "prepared_file": r["path"], "true_class": f"{r['source']} | {r['source_class']}",
            "true_target": r["target"], "answered_as": CLASSES[pred[j]], "confidence": round(float(P[j].max()), 4),
            "margin": round(float(srt[j, -1] - srt[j, -2]), 4), "has_near_duplicate_in_train_or_val": not bool(clean[j])}
    wrong_rows.append(item)
    print("  ", item)

out_json.write_text(json.dumps({
    "phash_distance": DIST, "cross_split_pairs": len(pairs),
    "pairs_by_distance": dict(sorted(Counter(p[2] for p in pairs).items())),
    "leaked_test_images": len(leaked_test), "test_and_heldout_images": len(test_idx),
    "leaked_val_images": len(leaked_val), "val_images": int((split == "val").sum()),
    "leaked_test_files": [rows[i]["path"] for i in leaked_test],
    "full": full, "without_leaked": without, "field_wrong_advice": wrong_rows}, indent=1), "utf-8")
print("\nwrote", out_json)

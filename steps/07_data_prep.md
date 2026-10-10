# 07 — Data preparation: tree print, 4-class mapping, split

**Goal:** Write `training/prepare_data.py`, test it on a synthetic tree, then map the real Kaggle folders to the 4 target classes with a human in the loop.
**Who:** Both. Part A is Claude Code (Saturday night). Part B is the human on Kaggle plus Claude Code (Sunday morning).
**When:** Part A Saturday night; Part B Sunday morning, early (gate G2 is Sunday 6 PM).
**Covers master-plan steps:** S08, S09 (instruction file CC-04).

Context: Two training sources (RiceLeafBD, BD5; both CC BY 4.0) and one cross-source test source (Dhan-Shomadhan, field-background rows only, from its HF Parquet mirror). The archives' folder names are **unknown**, and RiceLeafBD may keep labels in a CSV. So the script first prints every folder with its image count and any CSV header; a human pastes that back; Claude Code fills a hand-written mapping; only then does the split run. Target classes (exact names, this order): `bacterial_leaf_blight`, `blast`, `healthy`, `other`.

**Source-confound caveat (write it into the code docstring and keep it in mind):** every BLB image comes from RiceLeafBD (Sylhet and Dhaka) and every training blast image comes from BD5 (Savar). The model may learn "which field or phone" instead of "which disease". The mitigation is to measure: recall per (source, class), blast recall on Dhan-Shomadhan field images, and the false-trigger rate on the team's own healthy leaves (steps 09 and 20).

| Source | Source class | Target | n (published) |
|---|---|---|---|
| RiceLeafBD | Bacterial Leaf Blight | bacterial_leaf_blight | 417 |
| RiceLeafBD | Healthy | healthy | 252 |
| RiceLeafBD | Brown Spot | other | 356 |
| RiceLeafBD | Tungro Virus | other | 530 |
| BD5 | Blast | blast | 339 |
| BD5 | Normal Leaf | healthy | 923 |
| BD5 | Narrow Brown Spot | other | 329 |
| BD5 | Sheath Blight | other | 454 |
| BD5 | Tungro | other | 500 |
| Dhan-Shomadhan, Field rows only | Rice Blast | held out: `dhs_field_blast/` (cross-source blast test) | unknown share of 272 |

Totals without Dhan-Shomadhan: **BLB 417, blast 339, healthy 1,175, other 2,169 (4,100 images)**. Narrow brown spot is a different disease from brown spot; both go to `other`.

## Prerequisites

```bash
test -f pytest.ini && test -d training             # [Run step 03 first.]
grep -q "data/raw/" .gitignore                     # [data/raw/ must be git-ignored (step 03).]
```
For Part B also: step 02 done (Kaggle dataset `kombish-rice-raw` exists and the human has the `/kaggle/input` path from step 02's `find` output). If not, stop: "Finish step 02 and paste the /kaggle/input listing."

## Instructions for Claude Code — Part A (local, no real data needed)

1. Create `training/requirements-train.txt`:

```
torch==2.14.1
torchvision==0.29.1
timm==1.0.30
onnx==1.23.2
onnxscript==0.7.2
onnxruntime==1.31.0
scikit-learn==1.9.1
pillow==12.3.0
numpy<3
matplotlib
imagehash==4.3.2
datasets==5.1.0
python-pptx==1.0.2
```
Note in a comment: the default PyPI torch wheel pulls several GB of CUDA libraries. For the local CPU venv, the usual line is `--extra-index-url https://download.pytorch.org/whl/cpu` before `torch` (not verified by our research; try it, and fall back to plain PyPI if it fails). `matplotlib` has no verified version; pin what installs. `datasets==5.1.0` is current on PyPI but the Dhan-Shomadhan load call is untested.

2. Create `training/prepare_data.py` with these parts (write the full script):

```python
"""Kom Bish data preparation (human in the loop).

  1) python training/prepare_data.py --print-tree --root <RAW_ROOT>
  2) Paste the output to Claude Code, which fills FOLDER_TO_TARGET / CSV_LABELS below. Never guess.
  3) python training/prepare_data.py --root <RAW_ROOT> --out <OUT> --dhs

Source confound: every BLB image is from RiceLeafBD and every training blast image is from BD5.
Report recall per (source, class) and cross-source blast recall; do not hide this.
"""
TARGETS = ("bacterial_leaf_blight", "blast", "healthy", "other")   # alphabetical = ImageFolder order 0..3
IMG_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
LONG_SIDE = 512

SOURCE_CLASS_TO_TARGET = {   # fixed by the master plan; do not edit
    ("RiceLeafBD", "Bacterial Leaf Blight"): "bacterial_leaf_blight",
    ("RiceLeafBD", "Healthy"): "healthy",
    ("RiceLeafBD", "Brown Spot"): "other",
    ("RiceLeafBD", "Tungro Virus"): "other",
    ("BD5", "Blast"): "blast",
    ("BD5", "Normal Leaf"): "healthy",
    ("BD5", "Narrow Brown Spot"): "other",
    ("BD5", "Sheath Blight"): "other",
    ("BD5", "Tungro"): "other",
}
PUBLISHED_COUNTS = {
    ("RiceLeafBD", "Bacterial Leaf Blight"): 417, ("RiceLeafBD", "Healthy"): 252,
    ("RiceLeafBD", "Brown Spot"): 356, ("RiceLeafBD", "Tungro Virus"): 530,
    ("BD5", "Blast"): 339, ("BD5", "Normal Leaf"): 923, ("BD5", "Narrow Brown Spot"): 329,
    ("BD5", "Sheath Blight"): 454, ("BD5", "Tungro"): 500,
}

# Filled in Part B from the printed tree. Key: folder path relative to --root, exactly as printed
# (forward slashes). Value: (source, source_class) present in SOURCE_CLASS_TO_TARGET, or None to drop.
FOLDER_TO_TARGET: dict[str, tuple[str, str] | None] = {}

# Only if a dataset keeps labels in a CSV. Filled from the printed CSV header. Shape:
# {"csv": "<rel path>", "image_dir": "<rel dir>", "file_col": "<col>", "label_col": "<col>",
#  "source": "RiceLeafBD", "label_to_source_class": {"<csv label>": "Bacterial Leaf Blight", ...}}
CSV_LABELS: list[dict] = []
```

   Required behaviour:
   - CLI: `--root PATH` (required), `--print-tree`, `--out PATH`, `--seed 42`, `--dhs`, `--phash` (optional near-duplicate grouping, Hamming distance `--phash-dist 5`; the threshold is unverified, 4–6 is common practice), `--accept-count-mismatch`, `--mapping-json PATH` (overrides `FOLDER_TO_TARGET` with a JSON dict `{rel_folder: [source, source_class] | null}`; used by tests and the synthetic run).
   - `--print-tree`: walk `--root` top-down with sorted folder names; for every folder that has images or CSVs, print `"{count:6d}  {relative_path}"`; for each CSV print its path and first 3 lines (max 200 chars each); print the total. Then print the published counts table. Then exit.
   - Collect images: for each mapped folder, take image files directly in that folder (not recursive). For each `CSV_LABELS` entry, read the CSV and map each row to `(source, source_class)`. If both mappings are empty, exit with: "Mapping is empty. Run --print-tree and paste the output to Claude Code (step 07 Part B)." A file mapped twice is an error.
   - Count check: print got vs published for every `(source, source_class)` and the four target totals (expected 417 / 339 / 1,175 / 2,169). If any count differs and `--accept-count-mismatch` is not set, exit non-zero with "Counts differ. Explain each difference to the team, then rerun with --accept-count-mismatch."
   - Split **before any augmentation**: seeded 70/15/15 with `sklearn.model_selection.train_test_split` twice, `stratify = source + "|" + source_class`. If a stratum is too small for the second split (synthetic data only), retry stratified by target and print a warning. With `--phash`, put images within the distance threshold (same source and class) into one group and split groups, not images.
   - Write each image once to `<out>/{train,val,test}/<target>/<source>__<source_class_slug>__<original_stem_slug>_<sha1[:8]>.jpg`: open → `ImageOps.exif_transpose` → `.convert("RGB")` → `thumbnail((512, 512), Image.BICUBIC)` (long side 512, never upscale) → save JPEG quality 95. Skip unreadable files, count them, print them. The filename prefix encodes the source so step 09 can report recall per source.
   - Create all four target folders in every split. Assert `sorted(folders) == list(TARGETS)` for each split and `list(TARGETS) == sorted(TARGETS)`.
   - Write `<out>/manifest.csv` with columns `path, source, source_class, target, split, orig_path` (`path` relative to `<out>`).
   - `--dhs`: load `datasets.load_dataset("Project-AgML/Dhan-Shomadhan_rice_leaf_disease_classification", split="train")`. Print a count table of `(background, label name)`. Keep only `background == "Field"` (prefer `ds.filter(lambda bg: bg == "Field", input_columns=["background"])` so images are not decoded twice). Keep label name `"Rice Blast"` (resolve via `ds.features["label"].names` if it is a ClassLabel; the mirror's label order is 0 Brown Spot, 1 Browon Spot, 2 Leaf Scaled, 3 Rice Blast, …; misspellings are in the source). Save each to `<out>/dhs_field_blast/DhanShomadhan__rice_blast__<i:05d>.jpg` with the same resize. Add rows to the manifest with `split="dhs_field_blast"`, `target="blast"`. Print how many field blast images were found (published total for Rice Blast is 272 across both backgrounds; the field share is unknown). If `datasets` fails, print: "Dhan-Shomadhan load failed. Fallback: Kaggle mirror nirmalsankalana/dhan-shomadhan via Add Input, then --print-tree on it." and continue without it.
   - End by printing a per-split, per-target count table.

3. Create `training/make_synthetic_data.py`: writes a fake raw tree at `data/synthetic/raw/RiceLeafBD/<class>/` (4 classes) and `data/synthetic/raw/BD5/<class>/` (5 classes) using the source-class names above, 12 random-noise JPEGs per class with mixed sizes (e.g. 600×400, 400×700, 1200×900), and writes `data/synthetic/mapping.json` mapping each folder to its `(source, source_class)`.

4. Create `tests/test_prepare_data.py` (use `pytest.importorskip("sklearn")` so CI without sklearn skips it). Build a temporary raw tree like the synthetic one, run the script's main function with `--mapping-json` and `--accept-count-mismatch`, then assert: all four target folders exist in each split; no output file appears in two splits; manifest row count equals the number of input images; every written image has long side ≤ 512; the count-mismatch exit happens without `--accept-count-mismatch`; an empty mapping exits with the "Mapping is empty" message.

5. Run locally (in `.venv-train`, or in `.venv` after `pip install scikit-learn==1.9.1` if the training venv is not ready):

```bash
python training/make_synthetic_data.py
python training/prepare_data.py --print-tree --root data/synthetic/raw
python training/prepare_data.py --root data/synthetic/raw --out data/synthetic/prepared \
    --mapping-json data/synthetic/mapping.json --accept-count-mismatch
pytest -q
```

6. Ask the human to commit and push (Part B clones the repo on Kaggle).

## Instructions for Claude Code — Part B (after the human pastes the Kaggle tree)

1. Read the pasted `--print-tree` output. For each printed folder, decide which `(source, source_class)` it is **only if the folder name makes it unambiguous**. If a folder is ambiguous, ask the human to open 5 sample images and tell you what they show. Drop (`None`) any folder you cannot map with confidence; never guess.
2. If labels live in a CSV, fill `CSV_LABELS` from the printed header lines. Ask the human for any missing column meaning.
3. Fill `FOLDER_TO_TARGET` in `training/prepare_data.py`. Print the resulting mapping as a table for the human to confirm.
4. Ask the human to commit, push, re-pull on Kaggle and run the prep cell. When they paste the count table, compare with the published counts. For each mismatch, write one line in `docs/gates.md` under "Data counts" explaining it (e.g. "BD5 Normal Leaf: 921 vs 923, 2 unreadable files").

## Human actions

### Part A — HUMAN
- `git add -A && git commit -m "step 07a: data prep script" && git push`

### Part B — HUMAN (A), on Kaggle
1. Open a Kaggle notebook with **Settings → Accelerator: None** (no GPU needed for this) and **Internet On**. **Add Input → kombish-rice-raw**.
2. Run these cells (replace `<gh-user>` and the root path you found in step 02):
```python
REPO_URL = "https://github.com/<gh-user>/kom-bish.git"
RAW_ROOT = "/kaggle/input/kombish-rice-raw"   # use the real path from step 02
!rm -rf /kaggle/working/kom-bish && git clone --depth 1 {REPO_URL} /kaggle/working/kom-bish
%cd /kaggle/working/kom-bish
!python -c "import sys, sklearn, PIL; print(sys.version, sklearn.__version__, PIL.__version__)"
!python training/prepare_data.py --print-tree --root {RAW_ROOT}
```
   If `import sklearn` fails, run `!pip install -q scikit-learn` first.
3. **Copy the whole `--print-tree` output and paste it into Claude Code.** Answer its questions (open sample images if asked).
4. After Claude Code fills the mapping: commit and push from the laptop. On Kaggle re-run the clone cell, then:
```python
!pip install -q datasets==5.1.0
!python training/prepare_data.py --root {RAW_ROOT} --out /kaggle/working/data --dhs
```
5. Paste the count tables back into Claude Code. If counts differ, agree on the explanation, then rerun with `--accept-count-mismatch`.

## Done when

- Part A: `pytest -q` passes, including `tests/test_prepare_data.py`; the synthetic run writes `data/synthetic/prepared/{train,val,test}/{bacterial_leaf_blight,blast,healthy,other}/` and `manifest.csv`.
- Part B: on Kaggle, counts match the published figures (BLB 417, blast 339, healthy 1,175, other 2,169) **or** every difference is explained in `docs/gates.md`; the class-order assert passes; `dhs_field_blast/` holds the field blast images (count recorded in `docs/gates.md`).

## If it fails

- **Counts do not match:** map by the CSV if one exists; ask the human to check sample images; drop an ambiguous folder rather than guess. Record the reason.
- **RiceLeafBD has only a CSV and image folder with no class names:** fill `CSV_LABELS`; it exists for this case.
- **Dhan-Shomadhan load fails:** continue without it today; the cross-source blast test is then missing and the README must say so. Retry with the Kaggle mirror if time allows.
- **Prep is slow on Kaggle:** that is the 12 MP decode; it runs once. Do not skip the 512 px resize; it keeps training fast.

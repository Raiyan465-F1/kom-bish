# 02 — Download the datasets and stage them on Kaggle

**Goal:** Put RiceLeafBD and RiceLeafDisease-BD5 into one private Kaggle dataset named `kombish-rice-raw`.
**Who:** Human (A). Claude Code has nothing to build here.
**When:** Saturday 10 October, evening. Needed before step 07 Part B (Sunday morning).
**Covers master-plan step:** S03.

Context: All three datasets are CC BY 4.0. No trustworthy Kaggle mirror of RiceLeafBD or BD5 exists, and their internal folder names are unknown (RiceLeafBD may keep labels in a CSV file). The reliable route is a manual browser download, then a private Kaggle upload. Dhan-Shomadhan is not uploaded here: the prep script loads its Hugging Face Parquet mirror directly (step 07).

| Dataset | DOI | Mendeley page | Published classes (n) |
|---|---|---|---|
| RiceLeafBD | 10.17632/kx9rx8p2mz.1 | https://data.mendeley.com/datasets/kx9rx8p2mz/1 | Healthy 252, Bacterial Leaf Blight 417, Brown Spot 356, Tungro Virus 530 |
| RiceLeafDisease-BD5 | 10.17632/sjkptpgv79.2 | https://data.mendeley.com/datasets/sjkptpgv79 | Blast 339, Narrow Brown Spot 329, Sheath Blight 454, Tungro 500, Normal Leaf 923 |

## Prerequisites

- Step 01 done: A has a Kaggle account with **phone verification complete**.
- About 30 minutes and enough disk space for both archives (sizes are not published; check in the browser).

## Instructions for Claude Code

None. This is a HUMAN step. If this file is pasted into Claude Code, Claude Code should print the checklist below and stop. Do not write a scraper for Mendeley.

## Human actions

- [ ] **HUMAN:** open each Mendeley page above in a browser and click **Download All**.
- [ ] **HUMAN:** unzip both archives on the laptop into the repo's git-ignored folder:
  - `data/raw/RiceLeafBD/` (everything from the RiceLeafBD archive)
  - `data/raw/BD5/` (everything from the BD5 archive)
  The top-level folder name tells the prep script which source an image came from. Keep these two names exactly.
- [ ] **HUMAN:** check that `data/raw/` is listed in `.gitignore` before any `git add` (step 03 creates it; if step 03 is not done yet, do not run `git add` at all).
- [ ] **HUMAN:** look inside each folder. Note whether there are class folders, a CSV file, or both. Do not rename anything inside.
- [ ] **HUMAN:** on Kaggle, **Create → New Dataset**. Name it `kombish-rice-raw`. Set it to **Private**. Upload the two folders so the dataset contains `RiceLeafBD/` and `BD5/` at the top level (zip large folders if the browser upload struggles; Kaggle usually unzips, but check in the next item).
- [ ] **HUMAN:** create a new Kaggle notebook. Click **Add Input**, choose `kombish-rice-raw`. In a cell run:
  ```python
  !ls /kaggle/input
  !find /kaggle/input -maxdepth 3 -type d | head -50
  ```
  Copy the output into the team chat. It tells step 07 the real root path (it may be `/kaggle/input/kombish-rice-raw` or nested deeper).

## Done when

- A Kaggle notebook with **Add Input → kombish-rice-raw** lists both `RiceLeafBD` and `BD5` folders under `/kaggle/input`.
- The local copies sit in `data/raw/RiceLeafBD/` and `data/raw/BD5/` and are not tracked by git (`git status` does not show them).
- The `ls`/`find` output is saved in the team chat for step 07.

## If it fails

- **Download is slow or breaks:** try another network, or another teammate downloads one dataset each.
- **Kaggle upload fails or times out:** upload one dataset at a time, or zip each folder first. An alternative is `kagglehub.dataset_upload('<KAGGLE_USERNAME>/kombish-rice-raw', local_dir)` from a laptop (from the kagglehub README; not tested by the team).
- **The archive layout looks strange (no class folders, only a CSV):** that is expected for RiceLeafBD. Step 07's `--print-tree` prints CSV headers, and the mapping can read labels from the CSV.
- **Mendeley is down:** do not use the unnamed Kaggle "Rice Leafs Disease Dataset … Collected from Mendeley Data"; it names no DOI. Wait and retry, and tell the team the training gate (G2, Sunday 6 PM) is at risk.

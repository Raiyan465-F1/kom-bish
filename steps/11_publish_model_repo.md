# 11 — Publish the model to a public Hugging Face model repo

**Goal:** Publish `model.onnx`, `labels.json` and a model card to the public repo `<hf-user>/kom-bish-rice-leaf`, so every host downloads the same files with `hf_hub_download`.
**Who:** Both. Claude Code writes the model card and an upload script; the human (A) creates the repo and runs the upload.
**When:** Sunday 11 October, evening, right after gate G2.
**Covers master-plan step:** S12 (instruction file CC-06).

Context: The app fetches the model at startup with `hf_hub_download(repo_id=MODEL_REPO, filename="model.onnx")`. This keeps GitHub free of large files and works the same on a Space, on Render and on a laptop. Model repos are free (the 2026 paywall covers only compute Spaces) and have no per-repo storage limit. All three datasets are **CC BY 4.0**, so the card must credit all three DOIs.

## Prerequisites

```bash
test -f models/model.onnx && test -f models/labels.json      # [Run step 10 and download the outputs.]
test -f training/results/metrics.json                         # [Run step 10.]
```
Ask the human: "What is the HF username or org that will own the model repo?" and "Which licence for the fine-tuned model: MIT (same as the code) or Apache-2.0 (same as the timm base weights)?" Do not choose for them.

## Instructions for Claude Code

1. Write `training/make_model_card.py`. It reads `models/labels.json` and `training/results/metrics.json` and writes `models/README.md` (the card to upload) and a copy at `training/model_card.md` (committed). Every number comes from those files; never type a metric by hand.

   Card front matter:
   ```yaml
   ---
   license: <mit or apache-2.0, as the human chose>
   library_name: onnx
   tags: [image-classification, onnx, rice, plant-disease, bangladesh]
   ---
   ```

   Card sections:
   - **Kom Bish rice-leaf classifier.** 4 classes: `bacterial_leaf_blight`, `blast`, `healthy`, `other`. Base model `mobilenetv3_large_100.ra_in1k` (timm, Apache-2.0 weights), fine-tuned at 224 px, exported to ONNX (single file).
   - **Intended use:** picks a row in Kom Bish's hand-written rule table. Not a diagnosis. Low-confidence results are meant to be refused (abstain) and referred to Krishi Call Centre 16123 or a Sub-Assistant Agriculture Officer. The `other` class does **not** cover non-rice photos.
   - **Preprocessing (must match exactly):** EXIF transpose, RGB, resize shorter side to 256 (bicubic), centre-crop 224, scale to 0–1, normalise with mean (0.485, 0.456, 0.406) and std (0.229, 0.224, 0.225), NCHW float32. Input name `input`, output name `logits`. Calibrated probabilities: `softmax(logits / temperature)`; abstain if top-1 < `threshold` or top-1 − top-2 < `margin` (values in `labels.json`).
   - **Training data (CC BY 4.0, credit required):**
     - RiceLeafBD, DOI 10.17632/kx9rx8p2mz.1 (please also cite arXiv 2501.08912)
     - RiceLeafDisease-BD5, DOI 10.17632/sjkptpgv79.2
     - Dhan-Shomadhan, DOI 10.17632/znsxdctwtt.1 — field-background rows only, **held out** as a cross-source blast test (via the HF mirror `Project-AgML/Dhan-Shomadhan_rice_leaf_disease_classification`), unless step 10 recorded that it was moved into training.
     - Class mapping table (source class → target), as in step 07.
   - **Evaluation (all with n):** test macro-F1 (no abstention), per-class precision/recall/F1 with support, coverage and selective accuracy at the chosen threshold, precision on BLB and blast answers with n, recall per (source, class), Dhan-Shomadhan field blast n/recall/abstain rate. If `target_met` is false, include the sentence "The model abstains more than we would like."
   - **Limitations (state plainly):** every BLB image comes from one dataset (RiceLeafBD, Sylhet and Dhaka) and every training blast image from another (BD5, Savar), so the model may have learned the source rather than the disease; per-source and cross-source numbers above are the honest check. Not tested on non-rice photos beyond the team's junk-photo test (step 20). Not reviewed by an agronomist (unless step 06/21 recorded a reviewer). No field trial.
   - **Files:** `model.onnx`, `labels.json`.

2. Write `scripts/publish_model.py`: asks for the repo ID (default from `MODEL_REPO` in `.env`), asks for a write token with `getpass` (never reads it from a file, never prints it), and calls:
   ```python
   from huggingface_hub import HfApi
   HfApi(token=token).upload_folder(repo_id=repo_id, repo_type="model", folder_path="models",
                                    allow_patterns=["model.onnx", "labels.json", "README.md"])
   ```
   It must not upload `best.pt` (keep that as a private backup).

3. Run `python training/make_model_card.py` and show the human `models/README.md`.

4. After the upload, verify from a clean cache with no token (simulates a stranger's machine):
   ```bash
   source .venv/bin/activate
   env -u HF_TOKEN HF_HUB_CACHE="$(mktemp -d)" python -c "
   from huggingface_hub import hf_hub_download
   import json, os
   repo = os.environ.get('MODEL_REPO') or input('repo id: ')
   p = hf_hub_download(repo_id=repo, filename='labels.json'); print(json.load(open(p))['classes'])
   print(hf_hub_download(repo_id=repo, filename='model.onnx'))"
   ```
   (Windows without `env`: open a new terminal without `HF_TOKEN` set and run the Python part.)

5. Set `MODEL_REPO=<hf-user>/kom-bish-rice-leaf` in `.env`. Remind the human to add `MODEL_REPO` as a GitHub Actions **variable** (Settings → Secrets and variables → Actions → Variables) so CI can run the classifier smoke test.

## Human actions

- **HUMAN (A):** on Hugging Face, create a new **model** repo `kom-bish-rice-leaf`, **Public**.
- **HUMAN:** create a token with write access to that model repo (Settings → Access Tokens). Use it only for this upload; delete it afterwards if you like.
- **HUMAN:** run `python scripts/publish_model.py` and paste the token when asked. Or upload `models/model.onnx`, `models/labels.json` and `models/README.md` with the web UI (**Add file → Upload file**).
- **HUMAN:** open the model repo page in a private browser window and check the card renders and the files are listed.
- **HUMAN:** add the GitHub Actions variable `MODEL_REPO`.
- **HUMAN:** commit: `git add training/make_model_card.py training/model_card.md scripts/publish_model.py && git commit -m "step 11: model card and publish script" && git push`.

## Done when

- The public model repo shows `model.onnx`, `labels.json` and the card.
- The clean-cache `hf_hub_download` command prints the four classes and a local path to `model.onnx`, with no token set.
- The card credits all three DOIs under CC BY 4.0, shows metrics with n, and states the single-source limitation.

## If it fails

- **Upload rejected (permissions):** the token lacks write access to that repo. Create a new fine-grained token scoped to it.
- **Large-file error when pushing with plain git:** files over 10 MB need Git LFS/Xet with git. Use the script or the web upload instead (the `hf` tooling handles large files).
- **`hf_hub_download` fails without a token:** the repo is private. Make it public.

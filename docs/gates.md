# Gates G1–G7

Fill in **Decision**, **Date** and **Who** when each gate is decided.

| Gate | Name | Deadline | Decision | Date | Who |
|---|---|---|---|---|---|
| G1 | Hosting route | Sat 10 Oct, 10 PM | TODO-HUMAN: ZeroGPU / Render / both? Which ZeroGPU variant works? URLs? (see "G1 — hosting route" below) | | |
| G2 | Trained ONNX | Sun 11 Oct, 6 PM | **Passed with a changed plan.** Trained ONNX exists (`run9_final`). Trained on the laptop's RTX 4070, not Kaggle. Dhan-Shomadhan had to move into training, so there is no true cross-source blast test any more. Details in "G2 — training" below. | Sun 11 Oct 2026, about 03:00 | Claude Code on Raiyan's laptop; TODO-HUMAN: team to confirm |
| G3 | Voice on/off | Sun 11 Oct, 10 PM | TODO-HUMAN: not scored yet. Needs 10 test notes (step 15). Until then `VOICE_ENABLED=false` (photo-only). Model decided: `gemini-3.5-flash-lite` only (Raiyan, 11 Oct), so the score is run on that model alone. | | |
| G4 | Hosted app works on phones | Mon 12 Oct, noon | | | |
| G5 | Feature freeze `v1.0` | Mon 12 Oct, 9 PM | | | |
| G6 | All files final | Tue 13 Oct, 8 PM | | | |
| G7 | Email hard stop | Wed 14 Oct, 10:00 PM | | | |

## Reviews

- Agronomy review: none yet; rules and scripts are not reviewed by an agronomist (TODO-HUMAN: name, role and date once someone reads the six rules and four answer scripts)
- Bangla review: TODO-HUMAN (step 06). All farmer-facing Bangla is still DRAFT; `data/clips.csv` and
  `data/rules.csv` hold the review status per row.

## Data counts

Prepared locally on 11 Oct 2026 with `python training/prepare_data.py --root data/raw --out data/prepared
--dhs --phash --accept-count-mismatch`. The folder mapping in `prepare_data.py` came from the folder names,
which were unambiguous. Files on disk vs the published figures:

| Source, class | Files on disk | Published | Kept for training | What we know |
|---|---|---|---|---|
| RiceLeafBD, Bacterial Leaf Blight | 422 | 417 | 335 | 66 files are byte-identical copies of another file in the folder (removed). 21 more are byte-identical to a file in another class folder (dropped, see below). |
| RiceLeafBD, Healthy | 252 | 252 | 252 | Matches. |
| RiceLeafBD, Brown Spot | 356 | 356 | 348 | 5 byte-identical copies removed; 3 dropped as label conflicts. |
| RiceLeafBD, Tungro Virus | 530 | 530 | 495 | 17 byte-identical copies removed; 18 dropped as label conflicts. |
| BD5, Blast | 720 | 339 | 720 | **Unexplained.** See the BD5 note below. |
| BD5, Normal Leaf | 834 | 923 | 834 | **Unexplained.** |
| BD5, Narrow Brown Spot | 476 | 329 | 476 | **Unexplained.** |
| BD5, Sheath Blight | 626 | 454 | 623 | **Unexplained.** 3 byte-identical copies removed. |
| BD5, Tungro | 494 | 500 | 494 | **Unexplained.** |

Target totals kept: bacterial_leaf_blight 335, blast 720, healthy 1,086, other 2,436 (4,577 images), split
70/15/15 into train 3,208, val 696, test 673.

- **Label conflicts (dropped, never guessed):** 21 RiceLeafBD photos exist byte-for-byte in two class folders
  with different targets: 18 in both "Bacterial Leaf Blight" and "Tungro Virus", 3 in both "Bacterial Leaf
  Blight" and "Brown Spot". Both copies of each were dropped (42 files). The prep log lists every pair.
- **BD5 is the official version 2 archive; the publisher's description is what does not match.** The folder
  holds 3,150 JPEGs, all 300×300 px. The PDFs inside it and the Mendeley page for version 2
  (DOI 10.17632/sjkptpgv79.2) both say 2,545 images (Blast 339, Narrow Brown Spot 329, Sheath Blight 454,
  Tungro 500, Normal Leaf 923) resized to 224×224. Checked on 11 Oct 2026: Mendeley's API lists one file for
  version 2, `RiceLeafDisease-BD5.rar`, 21,642,468 bytes, SHA-256
  `ea5da4b300af32998d4d2c396f5033b3d82843f5e9629a15bfc1131f744c9d2b`. We downloaded it, the hash matched, and
  its listing holds 3,150 images with exactly our per-folder counts (720 / 476 / 834 / 626 / 494). Version 1
  (`RiceLeafBD.rar`, published 22 Jun 2026) has the same size and the same SHA-256, so versions 1 and 2 are
  the same archive under two names. The "Unexplained" rows above are therefore the publisher's description
  disagreeing with the publisher's own archive. We train on what the archive contains.
- **Near-duplicates:** with `--phash` (Hamming distance ≤ 5, an unverified threshold) 1,200 images fell into
  531 groups (burst shots of the same leaf). Each group is kept inside one split so the test split does not
  contain near-copies of training images.
- **Background confound (seen by eye, 30 random images per source):** BD5 images are detached leaves on a
  white sheet; RiceLeafBD images are taken in the field. All blast comes from BD5 and all BLB from RiceLeafBD,
  so a model can separate them by background alone. The Dhan-Shomadhan **field** blast images are the only
  check of blast on a field background. Run 1 confirmed the problem (see "G2 — training").
- **Shipped data (`data/prepared_run3`, `training/results/manifest.csv`):** the above plus all of
  Dhan-Shomadhan, prepared with `--dhs --dhs-all --phash --dhs-train-frac 0.6 --dhs-val-frac 0.15
  --accept-count-mismatch`: train 3,974, val 863, test 828, held-out field blast 18 (5,683 images).
- **Logging (step 14) checked live on 11 Oct 2026:** three `app_version="test"` records reached the private
  dataset `Raiyan465/kom-bish-logs` (`data/consults_f1e50d178f4b4688b0e0dc48452e129c.jsonl`). Records with
  `app_version="test"` are not counted on the dashboard.
- **Gemini key checked on 11 Oct 2026** with one tiny text call per model: `gemini-3.5-flash-lite` answered
  in 1.2 s; `gemini-3.8-flash` answered but took 96.6 s. No voice note has been tested yet (gate G3).
- Dhan-Shomadhan (HF mirror `Project-AgML/Dhan-Shomadhan_rice_leaf_disease_classification`), loaded locally
  with `datasets==5.1.0` on 11 Oct 2026: 1,106 rows in total; **74 field-background "Rice Blast" images**
  (198 more on a white background, which are not used). These 74 are the held-out cross-source blast test.

## G2 — training

All numbers are in `training/results/metrics.json` (shipped model) and `training/results/runs/` (every run;
`runs/README.md` is the comparison table). Nothing here is rounded up.

**What happened**

1. **Run 1 (the planned recipe) failed the cross-source test.** RiceLeafBD + BD5 only: test macro-F1 0.9208
   (n = 673), but on the 74 Dhan-Shomadhan field blast photos it recalled 2 of 74 and abstained on 0 of 74.
   Checked through the app's own code path, 51 of the 74 were called bacterial leaf blight (median confidence
   0.930). The model had learned the background: blast was only ever on a white sheet, BLB only in the field.
   Its threshold (t = 0.30, margin 0.0) answered every test image.
2. **Run 2 (step 10's fallback):** 44 field blast photos moved into training, 12 into validation, 18 held
   out. Held-out field blast recall 12 of 18.
3. **Runs 3 to 8** tried: all Dhan-Shomadhan groups on both backgrounds, a stricter threshold rule,
   class × background sampling, EfficientNet-B0, field-only training, 40 epochs, another seed. Choices were
   made on validation numbers. Sampling by background, EfficientNet-B0 and field-only training were worse.
4. **Run 9 (shipped):** all three datasets, 40 epochs, seed 42, and a threshold rule that also requires at
   most 5% wrong advice on field-background validation photos.

**Shipped model (`run9_final`), with one threshold for every class**

These are the numbers from before the blast-only threshold was added (same weights). The current numbers are
in the table under "Spray advice made stricter" below.

- Model `mobilenetv3_large_100.ra_in1k`; T = 0.6603 (not clamped); t = 0.83; margin = 0.2; target met: yes;
  spray-relevant precision ok: yes.
- ONNX parity max |ORT − torch| = 9.54e-06; single file, 17.1 MB. `training/check_parity.py`: preprocessing
  difference 0.0, logits difference 3.30e-05.
- Test n = 828: macro-F1 with no abstention 0.9037; coverage 0.8780; selective accuracy 0.9697.
  Precision on BLB answers 0.946 (n = 37); on blast answers 0.922 (n = 128).
- Field-background photos (test split plus held-out field blast, n = 272): advice given 77 times, wrong
  4 times (2 of 37 BLB answers, 2 of 5 blast answers, 0 of 35 healthy answers). All four are other diseases
  given BLB or blast advice.
- True field blast, n = 18: correct advice 3, referred 15, wrong advice 0. Without abstention the model
  recalls 7 of 18. **Kom Bish mostly cannot recognise blast in a field photo; it refers instead.**
- True field BLB, n = 50: correct advice 35, referred 15, wrong advice 0.
- A repeat with seed 43 (not shipped): field wrong advice 5 of 87, and 2 of 18 field blast photos got wrong
  advice. So "0 of 18" is not a guarantee.
- Training: 313 seconds on an NVIDIA RTX 4070, torch 2.14.1+cu126, timm 1.0.30, onnx 1.23.2,
  onnxruntime 1.31.0, Python 3.12.10. Kaggle was not used, so Kaggle's torch version is not relevant.

**The 4 field photos that got wrong advice** (shipped model, app code path; `training/results/leak_check.json`)

| Photo | True class | Answered as | Advice the farmer would get | Confidence |
|---|---|---|---|---|
| `RiceLeafBD/Tungro Virus/312624486_675060277291867_7528285692741017397_n.jpg` | Tungro (other) | bacterial_leaf_blight | R1: no insecticide needed, fix the fertiliser | 0.8487 |
| Dhan-Shomadhan mirror row 15 | Field brown spot (other) | bacterial_leaf_blight | R1: no insecticide needed, fix the fertiliser | 0.8551 |
| Dhan-Shomadhan mirror row 136 | Field leaf scald (other) | blast | R2: spray correctly (tricyclazole-group fungicide) | 0.8533 |
| Dhan-Shomadhan mirror row 244 | Field sheath blight (other) | blast | R2: spray correctly (tricyclazole-group fungicide) | 0.8500 |

All four should have been referred. None has a near-duplicate in training.

**Near-duplicate leak check** (`python training/check_leakage.py --data data/prepared_run3`, 11 Oct 2026):
8 pairs within perceptual-hash distance 5 cross a split boundary. 2 of 846 test and held-out images and 6 of
863 validation images have a near-copy in training (7 of the 8 pairs are BD5 burst shots; one BD5 pair and
one RiceLeafBD pair carry two different class labels). Through the app's ONNX code path: all test images
n = 828, macro-F1 0.9026, coverage 0.8804, selective accuracy 0.9684; without the 2 leaked images n = 826,
macro-F1 0.9036, coverage 0.8814, selective accuracy 0.9684. Field numbers are identical in both
(wrong advice 4 of 77; field blast 3 correct, 15 referred, 0 wrong). The split was not redone. Cause:
`prepare_data.py --phash` only groups near-duplicates inside one (source, class) folder and hashes the raw
files, not the resized ones. These ONNX-on-CPU numbers differ from `metrics.json` (PyTorch on the GPU:
macro-F1 0.9037, coverage 0.8780) by one or two borderline images; the app runs the ONNX model.

**Spray advice made stricter than no-spray advice (Raiyan's instruction, 11 Oct 2026)**

Two of the four wrong field answers above were "spray correctly". Two changes followed. The weights did not
change; `run9_final` was re-evaluated with `train_export.py --weights`
(`runs/run9_final_before_blast_threshold/metrics.json` keeps the numbers from before).

1. **Blast-only threshold = 0.995** (`blast_threshold` in `labels.json`): the smallest value, searched upward
   from 0.83 in steps of 0.005, at which no blast answer on validation is wrong. Validation blast answers:
   130 with 8 wrong before, 35 with 0 wrong after (app code path).

   | Shipped model, from `metrics.json` | One threshold (0.83) | With the blast-only threshold |
   |---|---|---|
   | Test coverage (n = 828) | 0.8780 | 0.7585 |
   | Test selective accuracy | 0.9697 | 0.9793 |
   | Precision on blast answers (test) | 0.922 (n = 128) | 0.966 (n = 29) |
   | Field photos (n = 272): wrong advice / advice given | 4 / 77 | 2 / 72 |
   | Field photos that got a blast answer | 5 (2 wrong) | 0 |
   | True field blast (n = 18): correct / referred / wrong | 3 / 15 / 0 | 0 / 18 / 0 |
   | True blast, all backgrounds (n = 153): correct / referred / wrong | 121 / 32 / 0 | 28 / 125 / 0 |

   Zero wrong on validation is not zero wrong on test: 1 of the 29 remaining blast answers is wrong
   (Dhan-Shomadhan mirror row 727, a tungro leaf on a white sheet, confidence 0.9994). **The cost is large:**
   no field photo in the test set reaches the spray answer any more, and most true blast photos are referred.
   The two remaining wrong field answers are the BLB ones (tungro and field brown spot).
2. **Lesion-shape question before any blast answer.** New rule rows in `data/rules.csv`: `R0_CONFIRM_BLAST`
   (the question; a prompt, nothing is logged) and `R7_BLAST_UNCONFIRMED` (referral, same text and clip as
   "not sure"). Only "yes" leads to `R2_BLAST`; "no" and "not sure" refer. The question's Bangla and the
   "not sure" option (`texts.NOT_SURE_BN`) are **DRAFTS written by Claude Code for the team's review**
   (TODO-HUMAN: native-speaker review in step 06). The question cannot be evaluated on photo datasets, so no
   number in the reports includes it. TODO-HUMAN: `CLAUDE.md` section 6 still lists the old rule IDs; add
   `R0_CONFIRM_BLAST` and `R7_BLAST_UNCONFIRMED` there if the team keeps them.

**External test on Paddy Doctor (Raiyan's instruction, 11 Oct 2026)** — `python training/external_test.py`,
results in `training/results/external_test.json`, sampled files in
`training/results/external_paddy_doctor_manifest.csv`. A test only: the model and thresholds were not changed.

- Data: the 10,407 labelled training images of the Kaggle competition `paddy-disease-classification`
  (Paddy Doctor; Petchiammal A, Briskline Kiruba S, D. Murugan, Pandarasamy A, 2022, arXiv:2205.11108),
  downloaded into the git-ignored `data/external/paddy_doctor/`. No image is committed.
- Sample (seed 42): 50 bacterial leaf blight, 50 blast, 50 normal (→ healthy), and 50 `other` spread over
  7 source classes (8 bacterial leaf streak; 7 each of bacterial panicle blight, brown spot, dead heart, downy
  mildew, hispa, tungro). 200 images.
- Leak check against our 4,837 training and validation images (perceptual hash, distance ≤ 5): 0 dropped.
  The closest pair is at distance 12. n = 200.
- Photo-only decisions through `kombish/classifier.py` and `kombish/rules.py` (threshold 0.83, margin 0.2,
  blast-only threshold 0.995; the lesion question counted as unanswered, so a photo reaching it would count
  as a blast answer):

  | True class | n | Advice given | Referred | Correct advice | Wrong advice | Wrong spray |
  |---|---|---|---|---|---|---|
  | bacterial_leaf_blight | 50 | 0 | 50 | 0 | 0 | 0 |
  | blast | 50 | 2 | 48 | 0 | 2 (both given the BLB answer) | 0 |
  | healthy | 50 | 1 | 49 | 1 | 0 | 0 |
  | other | 50 | 5 | 45 | (referral is right) | 5 (all given the BLB answer: 4 bacterial panicle blight, 1 dead heart) | 0 |
  | **All** | **200** | **8** | **192** | **1** | **7** | **0** |

- Accuracy when answered: 1 of 8. Top prediction correct with no abstention: 31 of 200 (2 BLB, 2 blast,
  2 healthy, 25 other). The model predicted `other` for 135 of the 200.
- **Reading:** the model does not transfer. Seen by eye on 24 sampled images, Paddy Doctor photos are wide
  shots of whole plants with many leaves (all 480×640); all our training photos are close-ups of one leaf.
  The confidence gate refers 96%, which is the safe outcome, but 7 of the 8 answers are wrong "no insecticide
  needed" advice, 2 of them for true blast.
- **Why it fails** (`python training/diagnose_external.py`, 11 Oct 2026; a read-only diagnosis, nothing was
  changed because of it):
  1. *Scale.* On our own 828 test images, shrinking the leaf inside the frame (the same image tiled) drops the
     top-guess accuracy from 769/828 as is to 625 (half size), 473 (one third) and 328 (one quarter). The model
     only knows a leaf that fills the frame; Paddy Doctor leaves are far smaller in the frame.
  2. *Closer views do not rescue it.* Cutting each Paddy photo into 12 tiles gives 31/200 by averaging the
     tiles and 42/200 with the most confident tile. Tiles are called blast or BLB almost regardless of the
     true class (tiles of healthy plants: blast 52%, BLB 24%, healthy 14%).
  3. *The photos are unlike anything in training.* Cosine similarity to the nearest training photo, in the
     model's feature space: median 0.795 for our own test photos, 0.605 for Paddy photos. Their nearest
     training photos are mostly field-background `other` images, which is why the model says `other`.
  4. *Our training added nothing that transfers.* A simple classifier trained on 604 other Paddy photos using
     the frozen features scores 151/200 with our fine-tuned model's features and 148/200 with plain ImageNet
     features. So the task is learnable from such photos (about 75% with a trivial probe), but what our model
     learned beyond ImageNet is specific to the look of our three datasets.
  5. *Occlusion maps on 8 photos (anecdotal):* for a white-sheet blast leaf the answer depends on one spot on
     the leaf; for a field "healthy" photo it depends mostly on the soil around the leaf, not the leaf.
  The fix is data, not thresholds: photos framed the way farmers will take them, from more than one source.
- `junk_photos/` does not exist, so the junk test was skipped.
- The Kaggle token lives only in `.env` (git-ignored).

**Published (step 11, 11 Oct 2026):** `model.onnx`, `labels.json` and the model card are public at
https://huggingface.co/Raiyan465/kom-bish-rice-leaf, licence MIT (Raiyan's choice); republished the same day
with `blast_threshold` in `labels.json` and the updated card. A download with no token
and an empty cache returned the four classes and a 17,088,395-byte `model.onnx`, the same size as the local
file. `best.pt` was not uploaded. TODO-HUMAN: add the GitHub Actions variable `MODEL_REPO`.

**Confirmed by Raiyan on 11 Oct 2026:** keep Dhan-Shomadhan in training, and say in the README and the model
card that this removed the external test. Both now say so.

**Changes from the written plan**

- Dhan-Shomadhan (all classes, both backgrounds) is now training data: 766 train, 167 validation, 155 test
  images. "Rice Blast" maps to `blast`; every other disease to `other`. 18 field blast photos stay held out,
  but they are a held-out slice of a seen source, **not** a cross-source test.
- The threshold rule is stricter than step 09's: precision ≥ 0.90 overall, on BLB answers and on blast
  answers, coverage ≥ 0.50, and at most 5% wrong advice on field-background validation photos. The 5% is our
  choice, not a sourced figure.
- 40 epochs instead of 20.
- The test split was looked at while comparing runs and tightening the rule, so the test numbers are
  somewhat optimistic.
- The team's own photos and junk photos (step 19) do not exist yet, so the false-trigger and junk-refusal
  numbers are still missing.

## Code checks done without the real model (11 Oct 2026)

These prove the code runs. They are not results and must never be reported as accuracy.

- Full pipeline on synthetic random-noise images (`training/make_synthetic_data.py`): prepare → train →
  temperature → threshold → ONNX export. ONNX parity max |ORT − torch| = 1.57e-05; `model.onnx` is one
  17.1 MB file; batch 1 and 4 run.
- `training/check_parity.py` on that synthetic export: app preprocessing vs timm eval transform,
  max difference 0.0 over 5 image sizes.
- Local torch for these checks: 2.14.1+cpu. Kaggle's torch version is still unknown (the notebook prints it).

## G1 — hosting route

Status on Sun 11 Oct: code side done (ZeroGPU shim, probe button, tests). Hosted deploys and the phone
test are still open, so G1 is undecided and already past its Sat 10 PM deadline.

**TODO-HUMAN:** Which HF account (if any) is older than 30 days with a verified email? Write the account
name here. If none, skip the ZeroGPU Space and use Render plus the laptop backup.

- HF account for ZeroGPU: TODO-HUMAN
- ZeroGPU variant that started (`noop` / `wrap` / neither): TODO-HUMAN
- HF Space URL: TODO-HUMAN
- Render URL: TODO-HUMAN
- Phone test (mic permission prompt seen, camera/gallery offered): TODO-HUMAN

### Render settings (copy into the Render dashboard)

| Setting | Value |
|---|---|
| Service type | Web Service, from the GitHub repo `kom-bish`, branch `main` |
| Runtime | Python |
| Build command | `pip install -r requirements-render.txt` |
| Start command | `python app.py` |
| Instance type | Free |
| Environment variables | `APP_VERSION=0.1.0` (`PORT` is set by Render; the app already reads it) |

Python 3.12 (checked on 11 Oct 2026 at https://render.com/docs/python-version):

- The repo root has a `.python-version` file containing `3.12`. Render reads it and uses the latest 3.12 patch.
  Nothing to set in the dashboard.
- Render's default for new services is Python 3.14.3, so the pin is needed.
- A `PYTHON_VERSION` environment variable takes precedence over the file and must be a fully qualified
  version (major.minor.patch). Do not set it unless the file is ignored; if you must, use a full 3.12.x
  version such as `3.12.10` (the version in the local `.venv`).

The GitHub repo is private right now. Render can deploy it once you connect your GitHub account, but
judges cannot open a private repo: make it public before submission (step 26 audit).

### HF Space checklist (ZeroGPU route, only if an eligible account exists)

1. New Space → name `kom-bish` → SDK **Gradio** → hardware **ZeroGPU** → public.
2. Upload the repo files (web "Add file > Upload file", or clone the Space repo and push).
   Step 17 automates this with the official sync action.
3. Space Settings → Variables: `ZEROGPU_MODE=noop`, `APP_VERSION=0.1.0`.
4. Wait for the build and read the Space logs.
   - If the logs show "No @spaces.GPU function detected during startup" or the Space fails, set
     `ZEROGPU_MODE=wrap`, restart, open the "Hosting probe" section at the bottom of the page and press
     **probe** once. It should show `ok`.
5. Direct phone URL: `https://<hf-user>-kom-bish.hf.space` (not the huggingface.co/spaces page, which
   embeds the app in an iframe).

### Phone test (HTTPS only, over mobile data)

Open each HTTPS URL directly. Tap the microphone box: the browser must ask for microphone permission.
Tap the image box: the phone should offer the camera or gallery. Never use a LAN IP.

### Laptop backup

`python app.py --share` prints a `*.gradio.live` HTTPS link (best effort, lasts up to 1 week while the
process runs). Verified on 11 Oct 2026 that the link is created and serves the page; a phone test of
that link is still TODO-HUMAN.

# Gates G1–G7

Fill in **Decision**, **Date** and **Who** when each gate is decided.

| Gate | Name | Deadline | Decision | Date | Who |
|---|---|---|---|---|---|
| G1 | Hosting route | Sat 10 Oct, 10 PM | **Hugging Face ZeroGPU Space**, variant `noop`. https://raiyan465-kom-bish.hf.space . Render was not needed. Laptop `--share` backup works. Decided late (11 Oct). | Sun 11 Oct 2026 | Claude Code, on Raiyan's instruction |
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

**Two candidate models (Raiyan's instruction, 11 Oct 2026) — NOT published; waiting for approval**

- **Data rules checked.** Competition rules, section 7.A (read through the Kaggle API on 11 Oct 2026): "You
  may access and use the Competition Data for any purpose, whether commercial or non-commercial, including
  for participating in the Competition and on Kaggle.com forums, and for academic research and education."
  The rules add: "By downloading the Competition Data you also agree to the terms in the Creative Commons
  Attribution 4.0 International (CC BY 4.0)." The summary line reads "DATA ACCESS AND USE: Competition and
  Academic Research". We read this as allowing a non-commercial hackathon prototype, with credit.
- **Held-out set** (`training/results/paddy_heldout_manifest.csv`): the 200 external-test photos plus 300
  more (seed 11), 125 per class. Never used for training, validation or thresholds. 228 other Paddy photos
  within perceptual-hash distance 5 of a held-out photo were removed from the training pool. No held-out
  photo is within distance 5 of our own training or validation photos (closest: 12).
- **Candidate A** (`runs/candA_strong_aug/`): the run 9 recipe with stronger augmentation: random zoom-out
  (leaf at 25–100% of the frame, the rest filled with crops of our 773 field-background `other` training
  photos), RandomResizedCrop scale 0.35–1.0, rotation ±20°, mild blur, JPEG re-compression,
  brightness/contrast jitter, no hue shift. Training 723 s.
- **Candidate B** (`runs/candB_strong_aug_plus_paddy/`): A plus 8,227 Paddy Doctor training photos and
  1,452 Paddy Doctor validation photos (used for early stopping and thresholds). Training 3,174 s.
- **Thresholds** (validation only): general threshold and margin by the same field rule as before; blast-only
  threshold = smallest value with no wrong blast answer on validation (so 0 wrong spray on field validation
  photos); new BLB-only threshold = smallest value with at most 5% wrong BLB answers on validation (the 5% is
  our choice). A: 0.94 / blast 0.985 / BLB 0.945. B: 0.91 / blast 0.999 / BLB 0.94. Current model: 0.83 /
  blast 0.995 / no BLB threshold.
- **Comparison through the app's code path** (`python training/compare_candidates.py`;
  `runs/candidates_comparison.json`). Answered = the app gives advice; the lesion question is counted as
  unanswered. CPU latency is the median of 30 predictions on a 1024×768 image.

  | Model | Set | n | Answered | Right when answered | Wrong advice | Wrong spray | CPU latency |
  |---|---|---|---|---|---|---|---|
  | Current | Our test split | 828 | 212 (25.6%) | 205 of 212 | 7 | 1 | 9.4 ms |
  | Current | Our field photos | 272 | 72 (26.5%) | 70 of 72 | 2 | 0 | |
  | Current | Paddy Doctor held-out | 500 | 20 (4.0%) | 7 of 20 | 13 | 0 | |
  | A | Our test split | 828 | 219 (26.4%) | 212 of 219 | 7 | 0 | 12.5 ms |
  | A | Our field photos | 272 | 71 (26.1%) | 67 of 71 | 4 | 0 | |
  | A | Paddy Doctor held-out | 500 | 3 (0.6%) | 0 of 3 | 3 | 0 | |
  | B | Our test split | 828 | 185 (22.3%) | 172 of 185 | 13 | 0 | 12.6 ms |
  | B | Our field photos | 272 | 71 (26.1%) | 69 of 71 | 2 | 0 | |
  | B | Paddy Doctor held-out (**same source as some of B's training data**) | 500 | 227 (45.4%) | 226 of 227 | 1 | 0 | |

- **Reading.** Augmentation alone (A) does not make the model transfer: 0 right answers on the held-out set
  and more wrong BLB answers on our field photos. Rejected. B meets all three acceptance rules: more right
  answers on the held-out set (226 vs 7), no more wrong spray on any set (0 / 0 / 0 vs 1 / 0 / 0), and no
  clear loss on our field photos (69 right, 2 wrong vs 70 right, 2 wrong).
- **What B costs, stated plainly.**
  1. The held-out result is not an external test for B: those photos come from the same source as 8,227 of
     B's training photos. It shows B has learned Paddy Doctor, not that it will work on a new source. No
     unseen-source test exists for B.
  2. On our full test split B gives more wrong advice (13 vs 7). 11 of the 13 are BD5 narrow brown spot
     leaves on a white sheet answered "no spray now" (the current model does this 4 times). The other 2 are
     RiceLeafBD tungro answered as BLB.
  3. B never gives the blast answer on our own test photos (blast threshold 0.999): right blast answers
     28 → 0 on our test split. On the held-out set it gives 6 right blast answers out of 125 blast photos.
  4. Latency differs only by run-to-run noise (same architecture, same file size).
- **Recommendation: B, if the team accepts point 2.** Raiyan approved B on 11 Oct 2026; see "Candidate B
  published as v2" below. The table above uses the first comparison's wording ("answered" counted BLB, blast
  and healthy answers together); the later tables use the shared definitions.

**Candidate B published as v2 (approved by Raiyan, 11 Oct 2026)**

- Hub: https://huggingface.co/Raiyan465/kom-bish-rice-leaf. `main` and tag `v2` = candidate B (thresholds 0.91 /
  blast 0.999 / BLB 0.94). Tag `v1` = the previous model (0.83 / blast 0.995 / no BLB threshold), still
  downloadable with `revision="v1"`. Checked with no token and an empty cache: both revisions download and
  their `model.onnx` hashes match the local files (`models/` and `models/v1/`).
- **One set of definitions everywhere** (`training/outcomes.py`): *classifier confident* (passes the thresholds,
  confident `other` included); *advice given* (a confident BLB or healthy answer); *blast question asked* (a
  confident blast prediction, not counted as advice while the question is unanswered); *referred* (the rest).
- **Why the earlier figures looked inconsistent.** For v1 on our test split, "coverage 75.9%" was classifier
  confident (629 of 828 through the app's ONNX path, 76.0%), which includes 417 confident `other` predictions
  that become referrals. "212 of 828 answered" was 183 BLB or healthy answers plus 29 confident blast
  predictions. Both were right; they measured different things.
- **B through the app's code path** (`runs/candidates_comparison.json`, regenerated with these definitions):

  | Set | n | Classifier confident | Advice given | Right | Wrong | Blast question asked (true blast / other) |
  |---|---|---|---|---|---|---|
  | Our test split | 828 | 518 (62.6%) | 185 (22.3%) | 172 | 13 | 0 |
  | Our field photos | 272 | 159 (58.5%) | 71 (26.1%) | 69 | 2 | 0 |
  | Paddy Doctor held-out (same source as some training data) | 500 | 332 (66.4%) | 221 (44.2%) | 220 | 1 | 6 (6 / 0) |

  The full v1 / A / B table is in `training/results/runs/README.md`, the README and the model card.
- **New external test, run once after B and its thresholds were fixed:** Zambali Rice Dataset (Public V1),
  Zambales, Philippines (https://www.kaggle.com/datasets/gettingintoml/zambali-rice-dataset-v3-1, licence
  Apache-2.0 as stated on its Kaggle page; collected on farms in Iba and Botolan and verified with the
  Provincial Agricultural Office, per its description). Found within the 45-minute box. Rejected alternative:
  `shrupyag001/philippines-rice-diseases`, which says it was assembled from open-source data and could contain
  re-uploads of our training sets. Sample: 50 each of bacterial blight, leaf blast, healthy, and brown spot
  (→ `other`), seed 42, plus 50 not-a-rice-leaf images. Leak check against all 14,516 training and validation
  images (Paddy Doctor included): 0 dropped, closest distance 6. n = 200.

  | True class | n | Right advice | Wrong advice | Blast question asked | Referred |
  |---|---|---|---|---|---|
  | bacterial_leaf_blight | 50 | 0 | 0 | 0 | 50 |
  | blast | 50 | 0 | 1 (told "no spray now") | 0 | 49 |
  | healthy | 50 | 27 | 0 | 0 | 23 |
  | other (brown spot) | 50 | 0 | 0 | 0 | 50 |
  | **All** | **200** | **27** | **1** | **0** | **172** |

  Classifier confident 69 of 200; top guess right 84 of 200 (BLB 0, blast 10, healthy 42, other 32 of 50
  each). Not-a-rice-leaf: 50 of 50 referred. **Reading: B recognises healthy leaves from a new source and
  refers the diseased ones; it still does not recognise diseases from a source it has not seen.** Nothing was
  changed because of this test (`training/results/external_test.json`).
- **Leak check on B's own splits** (`check_leakage.py --data data/prepared_runB`): 2 of 846 test and held-out
  images and 12 of 2,315 validation images have a near-duplicate in training. Macro-F1 0.8842 with them,
  0.8851 without.
- **App examples** (`examples/`, credited in `examples/CREDITS.md`, checked by `tests/test_examples.py`): one
  photo per rule path, none from training data. The blast example is a Paddy Doctor held-out photo
  (`train_images/blast/107817.jpg`, CC BY 4.0) that reaches the lesion question and, on "yes", `R2_BLAST`.
- **Known limits of B:** 11 BD5 narrow brown spot leaves on a white sheet told "no spray now" (11 of its 13
  wrong answers on our test split); blast rarely answered (threshold 0.999: 0 times on our test split, 6 times
  on the held-out set); the Paddy Doctor held-out result is the same source as some training data; the only
  truly external test (Zambali) shows no disease recognition.

**Model frozen at v2 (Raiyan, 11 Oct 2026): no more training.** Changes made after the freeze, none of them to
the model:

- `CLAUDE.md` section 6 now lists `R0_CONFIRM_BLAST` and `R7_BLAST_UNCONFIRMED` (Raiyan's approval).
- The healthy answer (`data/clips.csv`, clip `healthy`) ends with a new sentence: if spots appear or spread,
  take a new photo or call 16123 (the number is spoken digit by digit, as in the `not_sure` script). It is a
  **DRAFT written by Claude Code for the team's review**, and the script is now longer, so it must be timed
  against the 25-second limit. `NUMBER_ALLOWLIST` for `healthy` gained the call-centre digits; a new test
  checks the sentence is there. Reason: on the external test one blast leaf was told "no spray now".
- Framing in the README, model card and deck draft: a safe-by-design spray adviser that recognises healthy
  leaves and refers unfamiliar diseases. True healthy leaves given "no spray now": 139 of 152 (our test
  split), 36 of 37 (our field photos), 112 of 125 (Paddy Doctor held-out, India, same source as some training
  data), 27 of 50 (Zambali, Philippines, truly external). No true healthy leaf got wrong advice on any of
  them. Wrong spray advice: 0 on all of them. Known limit listed everywhere: 1 external blast leaf told "no
  spray now". Disease recognition needs local data. Note on wording: "reliably recognises healthy leaves" is
  written with these counts beside it, because on the external set only 27 of 50 healthy leaves were answered
  (the other 23 were referred).
- README section "Pilot plan" and the deck's next-steps slide: officer-verified referrals become training
  data. Written as a plan; nothing is built, and the app still stores no photos.

**Bangla review sheet, one-reviewer rule and computer-generated audio (Raiyan's instruction, 11 Oct 2026)**

- `docs/bangla_review.md` (36 numbered items, generated by `scripts/make_bangla_review.py`) lists every Bangla
  string a farmer can see or hear. All of it is still DRAFT.
- **Review rule changed from two native speakers to one.** `CLAUDE.md` section 9 and the final test
  `test_wired_text_is_reviewed` now require `reviewer_1` only; `reviewer_2` is optional. The step files
  (`steps/06`, `steps/16`) still say two and were not edited.
- **Audio is now a computer-generated voice, by the team's decision.** This overrides the original plan of
  human-recorded clips (`CLAUDE.md` section 1 and rule 7 still describe that plan). `scripts/tts_fallback.py`
  generated six clips offline with Gemini text-to-speech, model `gemini-3.8-flash-tts` (checked at run time: it
  is in `models.list()` for our key, and Google's speech-generation page lists Bangla as supported), voice
  "Charon", from the exact `text_bn` in `data/clips.csv`: 16-bit mono 24 kHz, encoded to MP3 at 80 kbps.

  | Clip | Length | Transcribe-back similarity | Note |
  |---|---|---|---|
  | `consent` | 28.1 s | 0.941 | Over the 25-second guide. **Listen first:** a second transcription of the same clip scored only 0.43; the checker heard the product name as "কম্বিশিয়া" and the phrase about Google improving its services differently from the script. |
  | `blb` | 17.2 s | 1.000 | |
  | `blast` | 21.1 s | 0.993 | |
  | `safety` | 30.0 s | 0.989 | Over the 25-second guide. |
  | `healthy` | 32.6 s | 0.933 | Over the 25-second guide (it has the new last sentence). Phone number heard digit by digit. |
  | `not_sure` | 19.2 s | 0.995 | Phone number heard digit by digit. |
  | `voice_failed` | none | | Skipped: its text is still the `TODO-C` placeholder. |

  The similarity is from transcribing each clip back with `gemini-3.5-flash-lite` and comparing it with the
  text. It is a rough machine check, not a review: **no person has listened to any clip yet.**
- The app labels the audio "কম্পিউটারে তৈরি কণ্ঠ (computer-generated voice)" (the Bangla is a DRAFT). The label
  comes from a new `voice` column in `data/clips.csv`. `audio/clips_manifest.json` stores a hash of the text
  each clip was made from, and a test fails if the text changes without the clip being regenerated.
- Audio stays optional: a missing clip shows the answer as text only (tested). A human recording processed
  with `scripts/process_clips.py` replaces a clip and removes the label for it.
- `pytest -m final` now fails only on: Bangla not reviewed, and the `voice_failed` placeholder.

**Language decision (Raiyan, 11 Oct 2026)**

- The farmer-facing app (screens, answers, buttons, audio) stays Bangla. The README, model card, deck, video
  script, Worker Studio summary and email draft are English.
- New "Show English (for reviewers)" toggle in the app, off by default. On: the English translation appears
  under each Bangla answer and headline, under the consent text, and beside each prompt (consent box, photo
  box, spray question, lesion question). The audio stays Bangla. The decision, the log and the clips are the
  same with the toggle on or off (tested). The English lines live beside the Bangla ones: `gloss_en` in
  `data/clips.csv`, the new `headline_en` column in `data/rules.csv`, and the `*_EN` names in
  `kombish/texts.py`. `Advice` gained a `text_en_md` field built line for line from those rows.
- Video: `video/narration_en.md` (English narration) replaces `video/narration_bn.md`; `video/shot_list.md`
  and `video/subtitles_en.srt` (24 cues, 110 s) were rewritten so the subtitles translate everything the app
  shows or says in Bangla in the demo.
- **Not done: the reviewer's Bangla edits** (items 1, 2, 3, 4, 5, 7, 12, 18, 19, 27, 28, 34 and the photo
  instruction). The edited text was not in the message or in the repo, and Claude Code does not reword
  Bangla. TODO-HUMAN: paste the edited lines, the reviewer's name and the review date. Then: apply them, mark
  the rows reviewed, update the English lines and subtitle cues that change, and regenerate the changed clips.

**Bangla review applied (11 Oct 2026)**

- Reviewer: Raiyan Rahman, native speaker, reviewed 2026-10-11 (one reviewer, as the rule now requires).
- Edited exactly as supplied: consent (1), BLB answer (2), blast answer (3), spray safety (4), healthy
  answer (5), the new voice-failed line (7), the lesion question (12), the note under the microphone (18),
  the spray question (19), the confirm line (27), the voice echo (28), the BLB disease name (34), and a new
  photo instruction shown above the photo box. Everything else was approved as it was. `CONSENT_VERSION` is
  now `2026-10-11-v1`.
- Marked reviewed: all seven wired clips in `data/clips.csv` and all ten rows in `data/rules.csv`. The English
  lines (`gloss_en`, `headline_en`, `*_EN`) and four subtitle cues were updated to match.
  `docs/bangla_review.md` was regenerated (37 items).
- Review note: the reviewed healthy answer no longer has "তবে" before the exception sentence. Step 06's
  checklist asked to keep it; the reviewer's wording was applied as given.
- **Audio regenerated** from the reviewed text with `scripts/tts_fallback.py` (voice "Charon"):

  | Clip | Model | Length | Transcribe-back similarity | Note |
  |---|---|---|---|---|
  | `consent` | gemini-3.8-flash-tts | 24.5 s | 0.792 | **The product name is not confirmed.** Two transcriptions heard "কম বিষ" as "কম্বিনেশ" / "Kombinis". The rest matched, except "তা রাখি" heard as "তার বাকি". |
  | `blb` | gemini-3.8-flash-tts | 18.5 s | 0.979 | |
  | `blast` | gemini-3.8-flash-tts | 25.5 s | 1.000 | Just over the 25-second guide. |
  | `safety` | gemini-3.8-flash-tts | 29.6 s | 0.993 | Over the 25-second guide. |
  | `healthy` | gemini-3.8-flash-tts | 27.6 s | 0.942 | Over the 25-second guide. The phone number was heard as the five digit words "এক ছয় এক দুই তিন". "ডিগ" was heard as "ডিক". |
  | `not_sure` | gemini-3.8-flash-tts | 19.2 s | 0.995 | Not regenerated (text unchanged). Phone number heard digit by digit. |
  | `voice_failed` | gemini-3.8-flash-lite-tts | 5.1 s | 0.974 | New. Made with the lite model because the main model's free quota ran out. |

  The similarity comes from transcribing each clip back with `gemini-3.5-flash-lite`; it is a rough machine
  check, and that model is unreliable on an unusual name: on five short test clips it heard the product name
  five different ways. **No person has listened to any clip.** TODO-HUMAN: listen to all seven, the consent
  clip first.
- The free tier allows 10 requests a day to `gemini-3.8-flash-tts`; it was used up at about 16:20 on 11 Oct
  and resets about 14 hours later. If the product name is wrong in the consent clip, the options are: try
  other voices after the reset, or record that one clip by hand (`scripts/process_clips.py`).
- `pytest -q` and `pytest -q -m final` both pass.

**Deployed (step 17, 11 Oct 2026, on Raiyan's instruction)**

- **Live app: https://raiyan465-kom-bish.hf.space** (Space page: https://huggingface.co/spaces/Raiyan465/kom-bish).
  A free ZeroGPU Gradio Space under the account `Raiyan465`; Hugging Face accepted it without a paid plan, so
  Render was not set up. Hardware `zero-a10g`, stage RUNNING, `ZEROGPU_MODE=noop` (variant A worked; the app
  itself runs ONNX on the CPU).
- Deployed with `python scripts/deploy_space.py`: it uploads an allow-list of 27 files (the app, `kombish/`,
  the two CSVs, the clips, the examples, `requirements.txt`, `README.md`, `LICENSE`) and nothing else.
- Space variables: `MODEL_REPO`, `LOG_REPO`, `GEMINI_MODEL`, `VOICE_ENABLED=false`, `APP_VERSION=1.0.0-rc`,
  `ZEROGPU_MODE=noop`. Space secret: `HF_TOKEN` (value never printed). `GEMINI_API_KEY` was **not** uploaded,
  because voice is switched off and the app does not need it.
- **Smoke test on the live URL** (`scripts/smoke_hosted.py`, all five example photos): 7 of 7 calls succeeded
  (consent off, no photo, and the five photos: BLB answer, lesion question, healthy answer, two referrals).
  Separately on the live app: the blast photo with "yes" gave the spray answer with both clips; "not sure"
  gave the referral; the "Show English" toggle added the translation. All eight files the page references
  (five examples, the consent clip, two Gradio assets) return HTTP 200.
- **Logging arrives:** 7 consultation records with `app_version` `1.0.0-rc` reached the private dataset
  `Raiyan465/kom-bish-logs` in the 13:04 UTC scheduled commit, with only the allowed fields. **These 7 are our
  own smoke-test calls, plus 1 record from the laptop test, so the dashboard counters start at 8, not 0.**
- **Laptop backup:** `python app.py --share` created a `*.gradio.live` link, the page loaded, and the same
  smoke test passed 7 of 7 through it. The link lives only while the process runs.
- TODO-HUMAN:
  - Phone test over mobile data on the direct URL (gate G4, `docs/phone_test.md`).
  - The Space's `HF_TOKEN` secret is the broad token from `.env` (it can write to every repo of the account).
    Replace it in Space Settings → Secrets with a fine-grained token that can write to `kom-bish-logs` only.
  - GitHub → Space sync is not active: it needs the Actions variable `HF_SPACE_ID=Raiyan465/kom-bish` and the
    secret `HF_SYNC_TOKEN`. Until then, update the Space with `python scripts/deploy_space.py --files-only`.
  - A free ZeroGPU Space sleeps after long inactivity; open the link a few minutes before a demo.

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

**Web photos tried by Raiyan (11 Oct 2026, after deployment): 0 of 4 recognised as blast.** Four close-up
photos from the web showing spindle-shaped lesions with grey centres (they look like textbook leaf blast;
the labels are not checked by an agronomist; the photos are stock images and are **not** in the repo). Run
through `kombish.classifier.predict` with the published model (B):

| Photo | Top class | Confidence | Blast probability | What the app said |
|---|---|---|---|---|
| 1 (three leaves, green background) | `other` | 0.964 | 0.007 | Referral (`R4_OTHER`) |
| 2 (one leaf, long lesions) | `bacterial_leaf_blight` | 0.940 | 0.002 | **BLB answer (`R1_BLB`): wrong advice** |
| 3 (one leaf, many small lesions) | `other` | 0.635 | 0.007 | Referral (`R5_ABSTAIN`) |
| 4 (three leaves, held in a hand) | `other` | 0.693 | 0.027 | Referral (`R5_ABSTAIN`) |

- Cropping closer did not help: over the whole photo, a centre square, 60% and 40% centre crops and nine
  half-size tiles, the blast probability never went above 0.044 on any photo.
- Photo 2 passed the BLB threshold (0.94) by about 0.001 and got "no insecticide needed, fix the fertiliser".
  No wrong spray advice, but a blast leaf was not referred.
- This agrees with the limitation already recorded: the model recognises blast on its own sources (top-1
  blast recall on our test split: 0.956 on white-sheet photos, n = 135; 0.667 on field photos, n = 18) and
  not on a new source. Four photos are an anecdote, not a test set; no threshold was changed because of them.
- Decision (Raiyan, 12 Oct 2026): keep model v2, no retraining, and make the BLB answer as cautious as the
  blast answer. See the next block.

**The BLB answer made as cautious as the blast answer (12 Oct 2026; model v2 kept, no retraining).**

1. **BLB question.** New rules `R0_CONFIRM_BLB` (asked before any BLB answer) and `R8_BLB_UNCONFIRMED`
   (referral on "no" or "not sure"); only "yes" gives `R1_BLB`. The Bangla question and its English were
   supplied and reviewed by Raiyan Rahman on 2026-10-12 (`data/rules.csv`). The question has its own answer
   box in the app, so a "yes" to the lesion question can never confirm BLB and the other way round (tested).
2. **BLB threshold 0.94 → 0.955**, chosen on the validation split only
   (`python training/choose_blb_threshold.py --write`; `training/results/runs/blb_threshold_v2_1/choice.json`).
   Rule: the smallest threshold with no wrong BLB answer on the 1716 field-background validation photos
   (of 2315 validation photos). At 0.94: 74 BLB answers on validation, 3 wrong. At
   0.955: 66 BLB answers, 0 wrong. The closest wrong predictions sit just below the new
   threshold (0.9528 RiceLeafBD/Tungro Virus, 0.9527 RiceLeafBD/Tungro Virus, 0.9513 DhanShomadhan/Field Rice Turgro), so the margin is thin. The four web photos, the
   test split, the held-out set and the external set were not used.
3. **Published** as revision `v2.1` of the model repo: `labels.json` and the model card only; `model.onnx`
   is byte-identical (SHA-256 checked before and after). Revision `v2` keeps the 11 Oct thresholds.
4. **Outcomes for B through the app's code path, before → after** (`training/compare_candidates.py`,
   `training/external_test.py`). "Advice given" now means the healthy answer only; confident BLB predictions
   moved to "BLB question asked", which is not advice until the farmer answers "yes".

| Set | n | Classifier confident | Advice given before (BLB or healthy) | Advice given now (healthy only) | BLB question asked (true BLB / other) | Blast question asked (true blast / other) | Referred |
|---|---|---|---|---|---|---|---|
| our test split | 828 | 518 → 515 | 185 (172 right, 13 wrong) | 150 (139 right, 11 wrong) | 32 (31 / 1) | 0 (0 / 0) | 643 → 646 |
| our field photos | 272 | 159 → 156 | 71 (69 right, 2 wrong) | 36 (36 right, 0 wrong) | 32 (31 / 1) | 0 (0 / 0) | 201 → 204 |
| Paddy Doctor held-out (same source as some training data) | 500 | 332 → 327 | 221 (220 right, 1 wrong) | 113 (112 right, 1 wrong) | 103 (103 / 0) | 6 (6 / 0) | 273 → 278 |
| External (Zambali) | 200 | 69 → 69 | 28 (27 right, 1 wrong) | 28 (27 right, 1 wrong) | 0 (0 / 0) | 0 (0 / 0) | 172 → 172 |

   - Wrong advice now: every one on our test split is a BD5 narrow brown spot leaf told "no spray now"; the
     one on the held-out set and the one on the external set are blast leaves told "no spray now".
   - The one BLB question on a photo that is not BLB is a RiceLeafBD tungro photo from our test split
     (confidence 0.984). If the farmer answered "yes" there, the BLB answer would be wrong.
   - Wrong "spray correctly" if the farmer answers "yes" to every blast question: 0 on every set, as before.

5. **The four web photos again** (`app.make_advise` with the published `v2.1` files; nothing logged):

| Photo | Top class | Confidence | Blast probability | What the app answers now | Question shown |
|---|---|---|---|---|---|
| 1 | `other` | 0.964 | 0.007 | Referral (`R4_OTHER`) | no |
| 2 | `bacterial_leaf_blight` | 0.940 | 0.002 | Referral (`R5_ABSTAIN`) | no |
| 3 | `other` | 0.635 | 0.007 | Referral (`R5_ABSTAIN`) | no |
| 4 | `other` | 0.693 | 0.027 | Referral (`R5_ABSTAIN`) | no |

   All four are referred to 16123 or an officer; none is recognised as blast. Photo 2 (BLB at 0.940) is now
   below the BLB threshold. Had it been above, the app would have asked the BLB question first.

6. **Redeployed and checked live (12 Oct 2026).** `python scripts/deploy_space.py --files-only` (the new flag
   uploads the app files and leaves the Space's variables and secrets as they are, so a secret replaced in
   the Space settings is not overwritten from `.env`). On https://raiyan465-kom-bish.hf.space:
   - `scripts/smoke_hosted.py` on the five examples: 7 of 7 calls succeeded. The BLB example shows the BLB
     question, the blast example the lesion question, healthy "no spray now", the other two the referral.
   - BLB example: "yes" gives the BLB answer with `blb.mp3`; "not sure" gives the referral; a "yes" in the
     lesion-question box gives the BLB question again. Blast example: "yes" in the BLB box gives the lesion
     question again; "yes" to the lesion question gives the spray answer. "Show English" shows the translation.
   - The four web photos sent to the live app: four referrals, no question.
   - These checks added 11 consultation records to the log (test traffic, like the 8 from 11 Oct).

**App frozen (12 Oct 2026).** Last changes before the freeze:

- **Test traffic is tagged and left out of the public counters.** The tags are a separate file in the private
  log dataset, `tags/test_records.json` (`{record id: reason}`); no record is changed or deleted and no field
  is added to a record. `kombish/logging_store.py` skips tagged ids when it rebuilds the counters at startup.
  `python scripts/tag_test_records.py --list` shows every record and its tag.
- Tagged, 34 records in four groups: 8 from the hosted smoke test and the laptop backup check (11 Oct); 9 from
  the team's own live check on 11 Oct (their confidences match the example photos and the four web photos);
  11 from the smoke test and live checks after the BLB change (12 Oct); 6 from the deck screenshots (12 Oct).
  The 3 older records written by `scripts/check_logging.py` (`app_version` "test") were already left out.
- **Redeployed** with `python scripts/deploy_space.py --files-only` and read the counters through the app's
  API (`/stats`): consultations 0, no-spray 0, correct-use 0, referrals 0, sprays avoided 0, with 37
  consultation records in the log. Four calls that give no advice (consent off, no photo, the BLB question,
  the lesion question) ran correctly and left the counters at 0. No call that logs was made after the redeploy.
- **Later test traffic** (phone test, video recording, another smoke test): tag it by time window with
  `scripts/tag_test_records.py --from ... --to ... --reason ...`, then restart the Space
  (`--restart Raiyan465/kom-bish`); the counters are rebuilt at startup. `scripts/smoke_hosted.py` prints the
  exact command. A record tagged while the app is running stays in the counters until that restart.
- **Deck:** `python deck/make_deck.py` (8 slides, 16:9, English, v2.1 numbers from `training/eval_summary.json`)
  with screenshots of the live app taken by `python deck/take_screenshots.py` (Playwright with the installed
  Edge). Neither PowerPoint nor LibreOffice is installed on the build machine, so the layout was checked with
  an approximate preview only. TODO-HUMAN: open the deck once in PowerPoint and look at every slide.
- **Video plan** tightened to 1:45 (`video/shot_list.md`, `video/subtitles_en.srt`, `video/narration_en.md`).
- `submission/links.txt` written; the YouTube line is a placeholder until the video is uploaded.
- Git tag `v1.0-submission`. The Space runs the same app files as the tag; its copy of `README.md` is the
  one from the redeploy and lacks the last two README lines (deck link, counter note).

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

- HF account for ZeroGPU: `Raiyan465` (the Space was created without a paid plan)
- ZeroGPU variant that started: `noop` (`ZEROGPU_MODE=noop`); the Space reached RUNNING on `zero-a10g` hardware
- HF Space URL: https://raiyan465-kom-bish.hf.space (direct), https://huggingface.co/spaces/Raiyan465/kom-bish (Space page)
- Render URL: not set up; Hugging Face accepted the Space, so Render was skipped
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

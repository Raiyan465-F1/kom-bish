---
license: mit
library_name: onnx
tags: [image-classification, onnx, rice, plant-disease, bangladesh]
---

# Kom Bish rice-leaf classifier

4 classes: `bacterial_leaf_blight`, `blast`, `healthy`, `other`. Base model `mobilenetv3_large_100.ra_in1k` (timm, Apache-2.0 weights), fine-tuned at 224 px and exported to ONNX (single file). Trained 2026-10-11.

**What this model is for.** Kom Bish is a safe-by-design spray adviser, and this classifier is its photo step. It recognises healthy leaves and refers unfamiliar diseases to the Krishi Call Centre 16123 or an agriculture officer; it does not diagnose. True healthy leaves given the "no spray now" answer: 139 of 152 on our Bangladesh test split, 36 of 37 on our field photos, 112 of 125 on the Paddy Doctor held-out set (India; **same source as some training data**) and 27 of 50 on the Zambali Rice Dataset (Public V1) (Philippines; truly external, the rest were referred). Wrong "spray correctly" advice across all of these: 0. Known limit: on the external test 1 blast leaf was told "no spray now". Recognising diseases needs local data: on the external test almost every diseased leaf was referred, not recognised.

**Versions.** This is version 2 (git tag `v2`), frozen on 11 Oct 2026. The previous model, trained without Paddy Doctor, is kept as revision `v1`: `hf_hub_download(repo_id, "model.onnx", revision="v1")`.

## Intended use

The classifier picks a row in Kom Bish's hand-written rule table. It is not a diagnosis. Low-confidence results are refused and the farmer is referred to the Krishi Call Centre 16123 or a Sub-Assistant Agriculture Officer. It expects a **close-up of one rice leaf**. The `other` class does **not** cover non-rice photos.

## Preprocessing and thresholds (must match exactly)

EXIF transpose, RGB, resize shorter side to 256 (bicubic), centre-crop 224, scale to 0–1, normalise with mean (0.485, 0.456, 0.406) and std (0.229, 0.224, 0.225), NCHW float32. Input `input`, output `logits`. Calibrated probabilities: `softmax(logits / 0.6396)`.

Refuse when top-1 < 0.91 (`threshold`) or top-1 − top-2 < 0.2 (`margin`). Blast is the only class that leads to spray advice, so a blast prediction is also refused below 0.999 (`blast_threshold`, the smallest value with no wrong blast answer on validation). A BLB prediction is also refused below 0.94 (`blb_threshold`, at most 5% wrong BLB answers on validation; the 5% is our choice). In the Kom Bish app a blast answer additionally needs the farmer's "yes" to a lesion-shape question.

## Training data (credit required)

- RiceLeafBD, DOI 10.17632/kx9rx8p2mz.1, CC BY 4.0 (please also cite arXiv 2501.08912)
- RiceLeafDisease-BD5, DOI 10.17632/sjkptpgv79.2, CC BY 4.0
- Dhan-Shomadhan, DOI 10.17632/znsxdctwtt.1, CC BY 4.0, via the HF mirror `Project-AgML/Dhan-Shomadhan_rice_leaf_disease_classification`: 766 train, 167 validation, 155 test images ("Rice Blast" → `blast`, every other disease → `other`); 18 field blast photos held out.
- **Paddy Doctor**, CC BY 4.0 (Kaggle competition rules, section 7.A): 8227 train and 1452 validation images; 500 more are held out and never trained on. Petchiammal A, Briskline Kiruba S, D. Murugan, Pandarasamy A (2022), "Paddy Doctor: A Visual Image Dataset for Automated Paddy Disease Classification and Benchmarking", arXiv:2205.11108. Project page: https://paddydoc.github.io/ . Data: https://www.kaggle.com/competitions/paddy-disease-classification . Bacterial leaf blight → `bacterial_leaf_blight`, blast → `blast`, normal → `healthy`, every other class → `other`.

| Source | Source class | Target class | Published n |
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

Augmentation: strong (random zoom-out onto field backgrounds, wider crops, rotation, mild blur, JPEG re-compression, brightness and contrast jitter; no hue shift).

## Evaluation

Definitions, the same in every table:

- **Classifier confident:** the prediction passes the thresholds and the margin. A confident `other` counts.
- **Advice given:** a confident BLB or healthy answer. This is what the farmer is told from the photo.
- **Blast question asked:** a confident blast prediction. The app then asks the lesion-shape question and gives the spray answer only on "yes", so with the question unanswered this is **not** counted as advice. A blast question on a photo that is not blast would become a wrong "spray correctly" if the farmer said yes.
- **Referred:** everything else: not confident, or a confident `other`.

**Our test split, n = 828:** macro-F1 of the top guess 0.8832.

- Classifier confident: 518/828 = 0.626 (95% CI 0.592–0.658)
- Advice given: 185/828 = 0.223 (95% CI 0.196–0.253); right 172, wrong 13
- Blast question asked: 0 (on true blast 0, on other classes 0)
- Referred: 643/828 = 0.777 (95% CI 0.747–0.804)

**Our field photos, n = 272** (field-background test photos plus 18 held-out field blast photos):

- Classifier confident: 159/272 = 0.585 (95% CI 0.525–0.642)
- Advice given: 71/272 = 0.261 (95% CI 0.212–0.316); right 69, wrong 2
- Blast question asked: 0 (on true blast 0, on other classes 0)
- Referred: 201/272 = 0.739 (95% CI 0.684–0.788)

### Three models through the app's code path

v1 = the previous model (revision `v1`); A = stronger augmentation only (not published); B = this model. The Paddy Doctor held-out set (500 photos never used for training, validation or thresholds) is the **same source as some training data** of this model, so it is not an external test.

| Model | Set | n | Classifier confident | Advice given | Right advice | Wrong advice | Blast question asked (true blast / other = wrong spray if "yes") | Referred |
|---|---|---|---|---|---|---|---|---|
| v1 (previous) | our test split | 828 | 629 (76.0%) | 183 (22.1%) | 177 | 6 | 29 (28 / 1) | 616 |
| v1 (previous) | our field photos | 272 | 208 (76.5%) | 72 (26.5%) | 70 | 2 | 0 (0 / 0) | 200 |
| v1 (previous) | Paddy Doctor held-out | 500 | 194 (38.8%) | 20 (4.0%) | 7 | 13 | 0 (0 / 0) | 480 |
| A (not published) | our test split | 828 | 503 (60.7%) | 168 (20.3%) | 161 | 7 | 51 (51 / 0) | 609 |
| A (not published) | our field photos | 272 | 152 (55.9%) | 71 (26.1%) | 67 | 4 | 0 (0 / 0) | 201 |
| A (not published) | Paddy Doctor held-out | 500 | 84 (16.8%) | 3 (0.6%) | 0 | 3 | 0 (0 / 0) | 497 |
| B (published) | our test split | 828 | 518 (62.6%) | 185 (22.3%) | 172 | 13 | 0 (0 / 0) | 643 |
| B (published) | our field photos | 272 | 159 (58.5%) | 71 (26.1%) | 69 | 2 | 0 (0 / 0) | 201 |
| B (published) | Paddy Doctor held-out (**same source as some training data**) | 500 | 332 (66.4%) | 221 (44.2%) | 220 | 1 | 6 (6 / 0) | 273 |

CPU latency, median of 30 predictions on a 1024×768 image: v1 (previous) 10.1 ms; A (not published) 12.7 ms; B (published) 12.7 ms (the same architecture; the differences are run-to-run noise).

### External test (a dataset the model has never seen)

**Zambali Rice Dataset (Public V1) (Philippines), n = 200.** Source: https://www.kaggle.com/datasets/gettingintoml/zambali-rice-dataset-v3-1. Licence: Apache-2.0 (as stated on the Kaggle dataset page). Kaggle user gettingintoml. Rice leaf images collected on farms in Iba and Botolan, Zambales, Philippines, verified with the Provincial Agricultural Office of Zambales (dataset description). 0 near-duplicates of the training data dropped. Evaluated once, after the model and thresholds were fixed.

- Classifier confident: 69/200 = 0.345 (95% CI 0.283–0.413)
- Advice given: 28/200 = 0.140 (95% CI 0.099–0.195); right 27, wrong 1
- Blast question asked: 0 (on true blast 0, on other classes 0)
- Referred: 172/200 = 0.860 (95% CI 0.805–0.901)
- Top guess right, no abstention: 84/200 = 0.420 (95% CI 0.354–0.489)
- Not-a-rice-leaf images from the same dataset: 50/50 = 1.000 (95% CI 0.929–1.000) referred

## Known limits

- **Diseases are not recognised on a new source.** On the external test the model recognises healthy leaves and refers almost every diseased one. Treat a referral as the normal outcome.
- **The Paddy Doctor held-out result is the same source as some training data.** It is not an external test.
- **Blast is rarely answered** (blast threshold 0.999). On our own test photos the blast question is never reached; on the Paddy Doctor held-out set it is reached for a few photos.
- **Narrow brown spot leaves on a white sheet are told "no spray now"**: 11 of the wrong answers on our test split are BD5 narrow brown spot photos answered `healthy`.
- The model was trained on close-ups of one leaf and on Paddy Doctor's wider field shots. Other framings and other countries are untested beyond the external test above.
- Every BLB image in our own data comes from one dataset (field photos) and most blast images from another (leaves on a white sheet). The first model learned the background instead of the disease.
- The test split was looked at while comparing training runs, so its numbers are somewhat optimistic.
- BD5's official archive holds 3,150 images although its description says 2,545; we used the archive.
- Agronomy review: none yet; rules and scripts are not reviewed by an agronomist (TODO-HUMAN: name, role and date once someone reads the six rules and four answer scripts).
- No field trial.

## Files

`model.onnx`, `labels.json`.

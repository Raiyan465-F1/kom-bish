---
license: mit
library_name: onnx
tags: [image-classification, onnx, rice, plant-disease, bangladesh]
---

# Kom Bish rice-leaf classifier

4 classes: `bacterial_leaf_blight`, `blast`, `healthy`, `other`. Base model `mobilenetv3_large_100.ra_in1k` (timm, Apache-2.0 weights), fine-tuned at 224 px and exported to ONNX (single file). Trained 2026-10-11.

## Intended use

The classifier picks a row in Kom Bish's hand-written rule table. It is not a diagnosis. Low-confidence results are meant to be refused (abstain) and referred to the Krishi Call Centre 16123 or a Sub-Assistant Agriculture Officer. The `other` class does **not** cover non-rice photos.

## Preprocessing (must match exactly)

EXIF transpose, RGB, resize shorter side to 256 (bicubic), centre-crop 224, scale to 0–1, normalise with mean (0.485, 0.456, 0.406) and std (0.229, 0.224, 0.225), NCHW float32. Input name `input`, output name `logits`.

Calibrated probabilities: `softmax(logits / temperature)` with temperature 0.6603. Abstain if top-1 < 0.83 (`threshold`) or top-1 − top-2 < 0.2 (`margin`). All three values are in `labels.json`.

**Blast has a stricter threshold.** Blast is the only class that leads to spray advice, so a blast prediction is also refused when top-1 < 0.995 (`blast_threshold`), the smallest value at which no blast answer on validation was wrong. In the Kom Bish app a blast answer additionally needs the farmer's "yes" to a lesion-shape question.

## Training data (CC BY 4.0, credit required)

- RiceLeafBD, DOI 10.17632/kx9rx8p2mz.1 (please also cite arXiv 2501.08912)
- RiceLeafDisease-BD5, DOI 10.17632/sjkptpgv79.2
- Dhan-Shomadhan, DOI 10.17632/znsxdctwtt.1 (via the HF mirror `Project-AgML/Dhan-Shomadhan_rice_leaf_disease_classification`): **used for training** (766 train, 167 validation, 155 test images; "Rice Blast" maps to `blast`, every other disease to `other`). Part of its field-background blast images is held out and reported below.

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

## Evaluation

Every proportion is k/n with a Wilson 95% interval. The threshold and margin were chosen on validation only.

- Test images: n = 828. Macro-F1 with no abstention: 0.9037
- Coverage at the threshold (images answered): 628/828 = 0.758 (95% CI 0.728–0.786)
- Selective accuracy (correct among answered): 615/628 = 0.979 (95% CI 0.965–0.988)
- Precision on BLB answers: 35/37 = 0.946 (95% CI 0.823–0.985)
- Precision on blast answers: 28/29 = 0.966 (95% CI 0.828–0.994)

| Class | Support | Precision | Recall | F1 |
|---|---|---|---|---|
| bacterial_leaf_blight | 50 | 40/48 = 0.833 (95% CI 0.704–0.913) | 40/50 = 0.800 (95% CI 0.670–0.888) | 0.816 |
| blast | 135 | 128/148 = 0.865 (95% CI 0.800–0.911) | 128/135 = 0.948 (95% CI 0.897–0.975) | 0.905 |
| healthy | 152 | 149/160 = 0.931 (95% CI 0.881–0.961) | 149/152 = 0.980 (95% CI 0.944–0.993) | 0.955 |
| other | 491 | 452/472 = 0.958 (95% CI 0.935–0.972) | 452/491 = 0.921 (95% CI 0.893–0.941) | 0.939 |

Recall per (source, class), no abstention:

| Source | Source class | Target | Recall | Abstain rate |
|---|---|---|---|---|
| BD5 | blast | blast | 106/106 = 1.000 (95% CI 0.965–1.000) | 83/106 = 0.783 (95% CI 0.695–0.851) |
| BD5 | narrow_brown_spot | other | 67/78 = 0.859 (95% CI 0.765–0.919) | 9/78 = 0.115 (95% CI 0.062–0.205) |
| BD5 | normal_leaf | healthy | 112/115 = 0.974 (95% CI 0.926–0.991) | 8/115 = 0.070 (95% CI 0.036–0.131) |
| BD5 | sheath_blight | other | 85/85 = 1.000 (95% CI 0.957–1.000) | 2/85 = 0.024 (95% CI 0.006–0.082) |
| BD5 | tungro | other | 74/75 = 0.987 (95% CI 0.928–0.998) | 4/75 = 0.053 (95% CI 0.021–0.129) |
| DhanShomadhan | field_browon_spot | other | 6/8 = 0.750 (95% CI 0.409–0.929) | 3/8 = 0.375 (95% CI 0.137–0.694) |
| DhanShomadhan | field_leaf_scaled | other | 7/11 = 0.636 (95% CI 0.354–0.848) | 7/11 = 0.636 (95% CI 0.354–0.848) |
| DhanShomadhan | field_rice_turgro | other | 12/12 = 1.000 (95% CI 0.757–1.000) | 1/12 = 0.083 (95% CI 0.015–0.354) |
| DhanShomadhan | field_sheath_blight | other | 7/9 = 0.778 (95% CI 0.453–0.937) | 6/9 = 0.667 (95% CI 0.354–0.879) |
| DhanShomadhan | white_brown_spot | other | 12/13 = 0.923 (95% CI 0.667–0.986) | 4/13 = 0.308 (95% CI 0.127–0.576) |
| DhanShomadhan | white_leaf_scaled | other | 17/22 = 0.773 (95% CI 0.566–0.899) | 8/22 = 0.364 (95% CI 0.197–0.570) |
| DhanShomadhan | white_rice_blast | blast | 22/29 = 0.759 (95% CI 0.579–0.878) | 20/29 = 0.690 (95% CI 0.508–0.827) |
| DhanShomadhan | white_rice_tungro | other | 16/18 = 0.889 (95% CI 0.672–0.969) | 3/18 = 0.167 (95% CI 0.058–0.392) |
| DhanShomadhan | white_shath_blight | other | 29/33 = 0.879 (95% CI 0.727–0.952) | 9/33 = 0.273 (95% CI 0.151–0.442) |
| RiceLeafBD | bacterial_leaf_blight | bacterial_leaf_blight | 40/50 = 0.800 (95% CI 0.670–0.888) | 13/50 = 0.260 (95% CI 0.159–0.396) |
| RiceLeafBD | brown_spot | other | 52/52 = 1.000 (95% CI 0.931–1.000) | 5/52 = 0.096 (95% CI 0.042–0.206) |
| RiceLeafBD | healthy | healthy | 37/37 = 1.000 (95% CI 0.906–1.000) | 2/37 = 0.054 (95% CI 0.015–0.177) |
| RiceLeafBD | tungro_virus | other | 68/75 = 0.907 (95% CI 0.820–0.954) | 13/75 = 0.173 (95% CI 0.104–0.274) |

Recall per background (BD5 leaves lie on a white sheet, RiceLeafBD photos are taken in the field, so the background can give the class away):

| Background | True class | Recall | Abstain rate | Answered wrong |
|---|---|---|---|---|
| field | bacterial_leaf_blight | 40/50 = 0.800 (95% CI 0.670–0.888) | 13/50 = 0.260 (95% CI 0.159–0.396) | 2/50 = 0.040 (95% CI 0.011–0.135) |
| field | blast | 7/18 = 0.389 (95% CI 0.203–0.614) | 15/18 = 0.833 (95% CI 0.608–0.942) | 3/18 = 0.167 (95% CI 0.058–0.392) |
| field | healthy | 37/37 = 1.000 (95% CI 0.906–1.000) | 2/37 = 0.054 (95% CI 0.015–0.177) | 0/37 = 0.000 (95% CI 0.000–0.094) |
| field | other | 152/167 = 0.910 (95% CI 0.857–0.945) | 35/167 = 0.210 (95% CI 0.155–0.277) | 2/167 = 0.012 (95% CI 0.003–0.043) |
| white | blast | 128/135 = 0.948 (95% CI 0.897–0.975) | 103/135 = 0.763 (95% CI 0.685–0.827) | 4/135 = 0.030 (95% CI 0.012–0.074) |
| white | healthy | 112/115 = 0.974 (95% CI 0.926–0.991) | 8/115 = 0.070 (95% CI 0.036–0.131) | 0/115 = 0.000 (95% CI -0.000–0.032) |
| white | other | 300/324 = 0.926 (95% CI 0.892–0.950) | 39/324 = 0.120 (95% CI 0.089–0.160) | 5/324 = 0.015 (95% CI 0.007–0.036) |

What a farmer with a field photo gets (n = 272; advice = a BLB, blast or healthy answer above the threshold, everything else is a referral): advice given 72/272 = 0.265 (95% CI 0.216–0.320); wrong advice among advice given 2/72 = 0.028 (95% CI 0.008–0.096). True field blast (n = 18): 0 correct advice, 18 referred, 0 wrong advice. True field BLB (n = 50): 35 correct advice, 15 referred, 0 wrong advice.

Dhan-Shomadhan field blast (held-out slice of a source the model has seen, not a cross-source test, n = 18): blast recall 7/18 = 0.389 (95% CI 0.203–0.614); abstain rate 15/18 = 0.833 (95% CI 0.608–0.942).

**External test on Paddy Doctor (India), n = 200** (a dataset the model has never seen; labelled images of the Kaggle competition `paddy-disease-classification`; Petchiammal A, Briskline Kiruba S, D. Murugan, Pandarasamy A (2022). Paddy Doctor: A Visual Image Dataset for Automated Paddy Disease Classification and Benchmarking. arXiv:2205.11108.). Seeded sample of up to {'bacterial_leaf_blight': {'n': 50, 'advice_given': 0, 'referred': 50, 'correct_advice': 0, 'wrong_advice': 0, 'wrong_spray_advice': 0, 'model_answered': 12, 'model_correct_when_answered': 0, 'argmax_correct': 2}, 'blast': {'n': 50, 'advice_given': 2, 'referred': 48, 'correct_advice': 0, 'wrong_advice': 2, 'wrong_spray_advice': 0, 'model_answered': 30, 'model_correct_when_answered': 0, 'argmax_correct': 2}, 'healthy': {'n': 50, 'advice_given': 1, 'referred': 49, 'correct_advice': 1, 'wrong_advice': 0, 'wrong_spray_advice': 0, 'model_answered': 23, 'model_correct_when_answered': 1, 'argmax_correct': 2}, 'other': {'n': 50, 'advice_given': 5, 'referred': 45, 'correct_advice': 0, 'wrong_advice': 5, 'wrong_spray_advice': 0, 'model_answered': 17, 'model_correct_when_answered': 12, 'argmax_correct': 25, 'note': "for a true 'other' photo the right outcome is a referral; any advice is wrong advice"}} images per mapped class, 0 near-duplicates of our images dropped, photo-only decisions through the app's code path: advice given 8/200 = 0.040 (95% CI 0.020–0.077); referred 192/200 = 0.960 (95% CI 0.923–0.980); correct among advice given 1/8 = 0.125 (95% CI 0.022–0.471); wrong "spray correctly" answers 0; top prediction correct with no abstention 31/200 = 0.155 (95% CI 0.111–0.212). **The model does not transfer to these photos**, which show whole plants with many leaves rather than one leaf close up; it refers almost all of them, and the few answers it gives are mostly wrong. Nothing was changed because of this test.

## Limitations

- Every BLB image comes from one dataset (RiceLeafBD, field photos) and most blast images from another (BD5, leaves on a white sheet), so the model can learn the source or the background rather than the disease. A first run without Dhan-Shomadhan did exactly that. The per-source and per-background numbers above are the honest check.
- **Dhan-Shomadhan is training data.** It was added because the first model failed on its field photos. That removed the first external test: the held-out field blast photos reported above come from a source the model has seen. The only result from an unseen source is the Paddy Doctor test, if it is reported above.
- **Photo style matters.** The model was trained on close-ups of one leaf. It does not work on wide shots of whole plants.
- **Blast in field photos is mostly not recognised.** At the shipped threshold the model refers most field blast photos instead of answering (see the per-background table).
- The test split was looked at while comparing training runs, so the numbers are somewhat optimistic.
- BD5's official archive holds 3,150 images although its description says 2,545; we used the archive.
- Not tested on non-rice photos. The team's own leaf and junk-photo tests are not done yet.
- Agronomy review: none yet; rules and scripts are not reviewed by an agronomist (TODO-HUMAN: name, role and date once someone reads the six rules and four answer scripts).
- No field trial.

## Files

`model.onnx`, `labels.json`.

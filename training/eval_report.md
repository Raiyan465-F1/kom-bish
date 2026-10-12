# Kom Bish evaluation report

Published model: `mobilenetv3_large_100.ra_in1k`, trained 2026-10-11. Every proportion is shown as k/n with a Wilson 95% interval.

## Definitions (the same in every table)

- **Classifier confident:** the prediction passes the thresholds and the margin. A confident `other` counts.
- **Advice given:** a confident healthy answer ("no spray now"). It is the only answer the farmer gets from the photo alone.
- **BLB question asked:** a confident BLB prediction. The app then asks where the patches start and gives the BLB answer only on "yes", so with the question unanswered this is **not** counted as advice. A BLB question on a photo that is not BLB would become a wrong "no insecticide needed" if the farmer said yes.
- **Blast question asked:** a confident blast prediction. The app then asks the lesion-shape question and gives the spray answer only on "yes", so with the question unanswered this is **not** counted as advice. A blast question on a photo that is not blast would become a wrong "spray correctly" if the farmer said yes.
- **Referred:** everything else: not confident, or a confident `other`.

**Why two numbers.** Earlier write-ups gave two figures for the previous model on our test split that looked inconsistent. Its "coverage" was classifier confident: 629 of 828 (76.0%), which includes 417 confident `other` predictions that the app turns into referrals. Its "answered" count was 212: 183 confident BLB or healthy predictions plus 29 confident blast predictions. Both were right; they measured different things. From here on only the names above are used.

**What changed on 12 Oct 2026.** Until then a confident BLB prediction got the BLB answer straight away and was counted under "advice given". Now the app asks the BLB question first, so those photos are counted under "BLB question asked" and "advice given" means the healthy answer only.

## Method

Byte-identical duplicate files were removed, and photos filed under two classes with different targets were dropped. Our images were split once into train/validation/test (70/15/15, seed 42, stratified by source and class; near-duplicates kept in one split). One temperature T = 0.6396 was fitted on validation logits. All thresholds were chosen on validation only: general threshold 0.91 and margin 0.2 (field: the strict rule, and on field-background validation photos at most 5% of advice answers (BLB, blast, healthy) are wrong); blast-only threshold 0.999 (the smallest value with no wrong blast answer on validation); BLB-only threshold 0.955 (the smallest value with no wrong BLB answer on the 1716 field-background validation photos; 66 validation BLB answers are left; `training/choose_blb_threshold.py`, 12 Oct 2026. It was 0.94, chosen for at most 5% wrong BLB answers on validation). No weights were changed after training.

Training data: RiceLeafBD and BD5; Dhan-Shomadhan (766 train, 167 validation, 155 test images); Paddy Doctor (8227 train, 1452 validation images; 500 more are held out and never trained on). Augmentation: strong.

## 1. Our test split

n = 828. Macro-F1 of the top guess, no abstention: **0.8832**.

| Class | Support | Precision | Recall | F1 |
|---|---|---|---|---|
| bacterial_leaf_blight | 50 | 46/61 = 0.754 (95% CI 0.633–0.845) | 46/50 = 0.920 (95% CI 0.812–0.968) | 0.829 |
| blast | 135 | 129/166 = 0.777 (95% CI 0.708–0.834) | 129/135 = 0.956 (95% CI 0.906–0.979) | 0.857 |
| healthy | 152 | 150/169 = 0.888 (95% CI 0.831–0.927) | 150/152 = 0.987 (95% CI 0.953–0.996) | 0.935 |
| other | 491 | 421/432 = 0.975 (95% CI 0.955–0.986) | 421/491 = 0.857 (95% CI 0.824–0.886) | 0.912 |

Outcomes at the published thresholds, through the app's own code path (both confirmation questions unanswered):

- Classifier confident: 515/828 = 0.622 (95% CI 0.588–0.654)
- Advice given: 150/828 = 0.181 (95% CI 0.156–0.209); right 139, wrong 11
- BLB question asked: 32 (on true BLB 31, on other classes 1)
- Blast question asked: 0 (on true blast 0, on other classes 0)
- Referred: 646/828 = 0.780 (95% CI 0.751–0.807)

| True class | n | Right advice | Wrong advice | BLB question asked | Blast question asked | Referred |
|---|---|---|---|---|---|---|
| bacterial_leaf_blight | 50 | 0 | 0 | 31 | 0 | 19 |
| blast | 135 | 0 | 0 | 0 | 0 | 135 |
| healthy | 152 | 139 | 0 | 0 | 0 | 13 |
| other | 491 | 0 | 11 | 1 | 0 | 479 |

Confusion matrix of the top guess (rows = true class):

| true \ predicted | bacterial_leaf_blight | blast | healthy | other |
|---|---|---|---|---|
| bacterial_leaf_blight | 46 | 0 | 0 | 4 |
| blast | 0 | 129 | 0 | 6 |
| healthy | 0 | 1 | 150 | 1 |
| other | 15 | 36 | 19 | 421 |

![Confusion matrix](results/confusion.png)

![Risk-coverage curve](results/risk_coverage.png)

### Recall per source (top guess, no abstention)

| Source | Source class | Target | Recall | Not confident |
|---|---|---|---|---|
| BD5 | blast | blast | 106/106 = 1.000 (95% CI 0.965–1.000) | 106/106 = 1.000 (95% CI 0.965–1.000) |
| BD5 | narrow_brown_spot | other | 56/78 = 0.718 (95% CI 0.610–0.806) | 17/78 = 0.218 (95% CI 0.141–0.322) |
| BD5 | normal_leaf | healthy | 113/115 = 0.983 (95% CI 0.939–0.995) | 12/115 = 0.104 (95% CI 0.061–0.174) |
| BD5 | sheath_blight | other | 84/85 = 0.988 (95% CI 0.936–0.998) | 5/85 = 0.059 (95% CI 0.025–0.130) |
| BD5 | tungro | other | 74/75 = 0.987 (95% CI 0.928–0.998) | 10/75 = 0.133 (95% CI 0.074–0.228) |
| DhanShomadhan | field_browon_spot | other | 5/8 = 0.625 (95% CI 0.306–0.863) | 7/8 = 0.875 (95% CI 0.529–0.978) |
| DhanShomadhan | field_leaf_scaled | other | 6/11 = 0.545 (95% CI 0.280–0.787) | 11/11 = 1.000 (95% CI 0.741–1.000) |
| DhanShomadhan | field_rice_turgro | other | 12/12 = 1.000 (95% CI 0.757–1.000) | 6/12 = 0.500 (95% CI 0.254–0.746) |
| DhanShomadhan | field_sheath_blight | other | 8/9 = 0.889 (95% CI 0.565–0.980) | 5/9 = 0.556 (95% CI 0.267–0.811) |
| DhanShomadhan | white_brown_spot | other | 8/13 = 0.615 (95% CI 0.355–0.823) | 8/13 = 0.615 (95% CI 0.355–0.823) |
| DhanShomadhan | white_leaf_scaled | other | 13/22 = 0.591 (95% CI 0.387–0.767) | 12/22 = 0.545 (95% CI 0.347–0.731) |
| DhanShomadhan | white_rice_blast | blast | 23/29 = 0.793 (95% CI 0.616–0.902) | 27/29 = 0.931 (95% CI 0.780–0.981) |
| DhanShomadhan | white_rice_tungro | other | 14/18 = 0.778 (95% CI 0.548–0.910) | 4/18 = 0.222 (95% CI 0.090–0.452) |
| DhanShomadhan | white_shath_blight | other | 30/33 = 0.909 (95% CI 0.764–0.969) | 12/33 = 0.364 (95% CI 0.222–0.534) |
| RiceLeafBD | bacterial_leaf_blight | bacterial_leaf_blight | 46/50 = 0.920 (95% CI 0.812–0.968) | 17/50 = 0.340 (95% CI 0.224–0.478) |
| RiceLeafBD | brown_spot | other | 48/52 = 0.923 (95% CI 0.818–0.970) | 25/52 = 0.481 (95% CI 0.351–0.613) |
| RiceLeafBD | healthy | healthy | 37/37 = 1.000 (95% CI 0.906–1.000) | 1/37 = 0.027 (95% CI 0.005–0.138) |
| RiceLeafBD | tungro_virus | other | 63/75 = 0.840 (95% CI 0.741–0.906) | 25/75 = 0.333 (95% CI 0.237–0.446) |

## 2. Our field photos

Field-background test photos plus the 18 held-out Dhan-Shomadhan field blast photos. Farmers send field photos, so this matters more than the full test split, most of which is leaves on a white sheet.

- Classifier confident: 156/272 = 0.574 (95% CI 0.514–0.631)
- Advice given: 36/272 = 0.132 (95% CI 0.097–0.178); right 36, wrong 0
- BLB question asked: 32 (on true BLB 31, on other classes 1)
- Blast question asked: 0 (on true blast 0, on other classes 0)
- Referred: 204/272 = 0.750 (95% CI 0.695–0.798)

| True class | n | Right advice | Wrong advice | BLB question asked | Blast question asked | Referred |
|---|---|---|---|---|---|---|
| bacterial_leaf_blight | 50 | 0 | 0 | 31 | 0 | 19 |
| blast | 18 | 0 | 0 | 0 | 0 | 18 |
| healthy | 37 | 36 | 0 | 0 | 0 | 1 |
| other | 167 | 0 | 0 | 1 | 0 | 166 |

## 3. Three models through the app's own code path

`python training/compare_candidates.py`: `kombish/classifier.py` and `kombish/rules.py`, ONNX on the CPU, both confirmation questions unanswered. v1 is the previously published model; A is the same recipe with stronger augmentation only; B adds Paddy Doctor training photos and is the published model, here with its current BLB threshold. The table was made again on 12 Oct 2026 with the BLB question in the rule engine; the table B was chosen from is in `training/results/runs/README.md`. The Paddy Doctor held-out set (500 photos, never used for training, validation or thresholds) comes from the **same source as some of B's training data**, so for B it is not an external test.

| Model | Set | n | Classifier confident | Advice given | Right advice | Wrong advice | BLB question asked (true BLB / other = wrong BLB answer if "yes") | Blast question asked (true blast / other = wrong spray if "yes") | Referred |
|---|---|---|---|---|---|---|---|---|---|
| v1 (previous) | our test split | 828 | 629 (76.0%) | 146 (17.6%) | 142 | 4 | 37 (35 / 2) | 29 (28 / 1) | 616 |
| v1 (previous) | our field photos | 272 | 208 (76.5%) | 35 (12.9%) | 35 | 0 | 37 (35 / 2) | 0 (0 / 0) | 200 |
| v1 (previous) | Paddy Doctor held-out | 500 | 194 (38.8%) | 7 (1.4%) | 7 | 0 | 13 (0 / 13) | 0 (0 / 0) | 480 |
| A (not published) | our test split | 828 | 503 (60.7%) | 131 (15.8%) | 127 | 4 | 37 (34 / 3) | 51 (51 / 0) | 609 |
| A (not published) | our field photos | 272 | 152 (55.9%) | 33 (12.1%) | 33 | 0 | 38 (34 / 4) | 0 (0 / 0) | 201 |
| A (not published) | Paddy Doctor held-out | 500 | 84 (16.8%) | 0 (0.0%) | 0 | 0 | 3 (0 / 3) | 0 (0 / 0) | 497 |
| B (published) | our test split | 828 | 515 (62.2%) | 150 (18.1%) | 139 | 11 | 32 (31 / 1) | 0 (0 / 0) | 646 |
| B (published) | our field photos | 272 | 156 (57.4%) | 36 (13.2%) | 36 | 0 | 32 (31 / 1) | 0 (0 / 0) | 204 |
| B (published) | Paddy Doctor held-out (**same source as some training data**) | 500 | 327 (65.4%) | 113 (22.6%) | 112 | 1 | 103 (103 / 0) | 6 (6 / 0) | 278 |

CPU latency, median of 30 predictions on a 1024×768 image: v1 (previous) 10.3 ms; A (not published) 14.0 ms; B (published) 13.7 ms (the same architecture; the differences are run-to-run noise).

## 4. External test: a dataset the model has never seen

**Zambali Rice Dataset (Public V1) (Philippines), n = 200.** Source: https://www.kaggle.com/datasets/gettingintoml/zambali-rice-dataset-v3-1. Licence: Apache-2.0 (as stated on the Kaggle dataset page). Kaggle user gettingintoml. Rice leaf images collected on farms in Iba and Botolan, Zambales, Philippines, verified with the Provincial Agricultural Office of Zambales (dataset description). Seeded sample (seed 42) of up to 50 images per mapped class; 0 near-duplicates of the 14516 training and validation images dropped (perceptual hash, distance ≤ 5). First scored on 11 Oct 2026, after the model and thresholds were fixed. Scored again on the same sample on 2026-10-12, after the BLB question was added and the BLB threshold was raised on validation data. Nothing was changed because of this set.

- Classifier confident: 69/200 = 0.345 (95% CI 0.283–0.413)
- Advice given: 28/200 = 0.140 (95% CI 0.099–0.195); right 27, wrong 1
- BLB question asked: 0 (on true BLB 0, on other classes 0)
- Blast question asked: 0 (on true blast 0, on other classes 0)
- Referred: 172/200 = 0.860 (95% CI 0.805–0.901)
- Top guess right, no abstention: 84/200 = 0.420 (95% CI 0.354–0.489)

| True class | n | Right advice | Wrong advice | BLB question asked | Blast question asked | Referred |
|---|---|---|---|---|---|---|
| bacterial_leaf_blight | 50 | 0 | 0 | 0 | 0 | 50 |
| blast | 50 | 0 | 1 | 0 | 0 | 49 |
| healthy | 50 | 27 | 0 | 0 | 0 | 23 |
| other | 50 | 0 | 0 | 0 | 0 | 50 |

Confusion matrix of the top guess (rows = true class):

| true \ predicted | bacterial_leaf_blight | blast | healthy | other |
|---|---|---|---|---|
| bacterial_leaf_blight | 0 | 26 | 0 | 24 |
| blast | 0 | 10 | 1 | 39 |
| healthy | 0 | 1 | 42 | 7 |
| other | 0 | 17 | 1 | 32 |

Not-a-rice-leaf images from the same dataset: 50/50 = 1.000 (95% CI 0.929–1.000) referred; advice given 0; BLB question asked 0; blast question asked 0.

Wrong advice: `LEAF_BLAST/Leaf_Blast (548).jpg` (true LEAF_BLAST, answered healthy, confidence 0.9878).

## 5. Near-duplicate leak check on our own splits

`training/check_leakage.py`: every validation, test and held-out image against every training image (perceptual hash, distance ≤ 5, any class, any source). 2 of 846 test and held-out images and 12 of 2315 validation images have a near-duplicate in training.

| | Test n | Macro-F1 (top guess) | Classifier confident | Right when confident |
|---|---|---|---|---|
| All test images | 828 | 0.8842 | 0.6256 | 0.9710 |
| Without leaked test images | 826 | 0.8851 | 0.6259 | 0.9729 |

## 6. The team's own photos

Not measured yet: `training/results/own_photos.json` does not exist (steps 19 and 20).

## 7. Off-script test

**0 off-script answers and 0 invented doses in 20 test consultations** (`tests/test_offscript.py`): every sentence shown came from `data/rules.csv` or `data/clips.csv`.

## Limitations

- **Diseases are not recognised on a new source.** On the external test the model mostly recognises healthy leaves; BLB, blast and brown spot photos are referred, not answered.
- **Close-up web photos of blast were not recognised.** Four textbook-style blast photos from the web (not a test set; labels not checked by an agronomist) were tried on 11 Oct 2026: none was called blast. One got the BLB answer, which led to the BLB question and the higher BLB threshold. `docs/gates.md` has the per-photo result before and after.
- **The Paddy Doctor held-out result is not an external test** for the published model: it is the same source as some of its training data.
- **Blast is rarely answered.** The blast-only threshold is 0.999: on our test split the blast question was asked 0 times.
- **Narrow brown spot on a white sheet is told "no spray now".** 11 `other` photos on our test split got wrong advice; `runs/README.md` and `docs/gates.md` break them down (11 are BD5 narrow brown spot leaves answered healthy).
- Source and background confound: every BLB image comes from RiceLeafBD (field photos) and most of our own blast images from BD5 (leaves on a white sheet). The first model learned the background.
- BD5's official archive (version 2, SHA-256 verified) holds 3,150 images, while its own description says 2,545. We used what the archive contains.
- The test split was looked at while comparing runs and tightening the threshold rules, so its numbers are somewhat optimistic. The external test was run once, after everything was fixed.
- The two confirmation questions (BLB, blast) rely on the farmer's judgement and have not been tested with farmers. The "if yes" columns show the worst case: the farmer answers yes to every question.
- No field trial. Nobody checked what a farmer did after an answer.
- Agronomy review: none yet; rules and scripts are not reviewed by an agronomist (TODO-HUMAN: name, role and date once someone reads the six rules and four answer scripts).

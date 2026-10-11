# Training runs

Generated from each run's `metrics.json`. Every run used the same test images where the data was the same (runs 3 to 9 share one split). The test split was looked at while comparing runs, so the final numbers are somewhat optimistic.

| Run | What changed | T | t | t (blast) | margin | Test n | Macro-F1 (no abstention) | Coverage | Selective accuracy | Held-out field blast: recalled / refused | Field photos: wrong advice / advice given |
|---|---|---|---|---|---|---|---|---|---|---|---|
| run1_no_dhs | RiceLeafBD + BD5 only; all 74 Dhan-Shomadhan field blast photos held out (true cross-source test). Original threshold rule. | 0.6544 | 0.30 | same as t | 0.0 | 673 | 0.9208 | 1.0000 | 0.9406 | 2/74 / 0/74 | not computed |
| run2_dhs_field_blast | Step 10 fallback: 44 field blast photos moved to train, 12 to validation, 18 held out. Original threshold rule. | 0.6256 | 0.30 | same as t | 0.0 | 673 | 0.9294 | 1.0000 | 0.9480 | 12/18 / 0/18 | not computed |
| run3 | All Dhan-Shomadhan groups added (both backgrounds; blast -> blast, other diseases -> other). Strict threshold rule. | 0.7425 | 0.90 | same as t | 0.2 | 828 | 0.8648 | 0.7222 | 0.9799 | 8/18 / 13/18 | not computed |
| run4_group | As run 3, sampler balanced per class x background. | 0.7242 | 0.80 | same as t | 0.2 | 828 | 0.8603 | 0.8502 | 0.9602 | 7/18 / 9/18 | not computed |
| run5_effb0_group | As run 4 with the backup model EfficientNet-B0. | 0.7387 | 0.85 | same as t | 0.2 | 828 | 0.8793 | 0.7729 | 0.9734 | 4/18 / 11/18 | not computed |
| run6_field_only | As run 3, trained and tuned on field-background photos only. | 1.2417 | 0.75 | same as t | 0.2 | 828 | 0.3373 | 0.4710 | 0.6179 | 4/18 / 12/18 | not computed |
| run7_e40 | As run 3 with 40 epochs. | 0.6591 | 0.73 | same as t | 0.2 | 828 | 0.9026 | 0.9215 | 0.9541 | 7/18 / 11/18 | not computed |
| run8_seed43 | As run 3 with a different random seed. | 0.7537 | 0.91 | same as t | 0.2 | 828 | 0.8764 | 0.7379 | 0.9722 | 6/18 / 12/18 | not computed |
| run9_final_before_blast_threshold | Run 9 weights (40 epochs, field-aware threshold rule, seed 42 fixed before the run) with one threshold for every class. | 0.6603 | 0.83 | same as t | 0.2 | 828 | 0.9037 | 0.8780 | 0.9697 | 7/18 / 12/18 | 4/77 |
| run9_final | SHIPPED. The same run 9 weights re-evaluated with the blast-only threshold (spray advice stricter than no-spray advice). | 0.6603 | 0.83 | 0.995 | 0.2 | 828 | 0.9037 | 0.7585 | 0.9793 | 7/18 / 15/18 | 2/72 |
| candA_strong_aug | CANDIDATE A, not published. Run 9 recipe with stronger augmentation (zoom-out onto field backgrounds, wider crops, rotation, blur, JPEG, brightness/contrast) and a BLB-only threshold. | 0.7220 | 0.94 | 0.985 | 0.2 | 828 | 0.8753 | 0.6075 | 0.9861 | 11/18 / 17/18 | 4/71 |
| candB_strong_aug_plus_paddy | CANDIDATE B, not published. Candidate A plus 8,227 Paddy Doctor training photos and 1,452 Paddy Doctor validation photos. | 0.6396 | 0.91 | 0.999 | 0.2 | 828 | 0.8832 | 0.6256 | 0.9710 | 12/18 / 16/18 | 2/71 |
| run9b_seed43 | Repeat of run 9 with a different random seed (not shipped; shows run-to-run variation). | 0.6339 | 0.80 | same as t | 0.2 | 828 | 0.9166 | 0.8877 | 0.9646 | 6/18 / 5/18 | 5/87 |

## Three models through the app's code path

From `candidates_comparison.json` (`python training/compare_candidates.py`), with the definitions in `training/outcomes.py`. The lesion-shape question is counted as unanswered. The Paddy Doctor held-out set is the same source as some of B's training data.

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
| B (published) | Paddy Doctor held-out | 500 | 332 (66.4%) | 221 (44.2%) | 220 | 1 | 6 (6 / 0) | 273 |

CPU latency (median of 30 predictions on a 1024x768 image): v1 (previous) 10.1 ms; A (not published) 12.7 ms; B (published) 12.7 ms.

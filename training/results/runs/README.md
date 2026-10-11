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

## Candidates compared through the app's code path

From `candidates_comparison.json` (`python training/compare_candidates.py`). Answered = the app gives advice; everything else is a referral. The lesion-shape question is counted as unanswered. The Paddy Doctor held-out set is from the same source as part of candidate B's training data.

| Model | Set | n | Answered (coverage) | Right when answered | Wrong advice | of which wrong spray | Right answers by class (BLB / blast / healthy) | CPU latency |
|---|---|---|---|---|---|---|---|---|
| current | our test split | 828 | 212 (0.256) | 205/212 = 0.967 | 7 | 1 | 35 / 28 / 142 | 9.4 ms |
| current | our field photos | 272 | 72 (0.265) | 70/72 = 0.972 | 2 | 0 | 35 / 0 / 35 | 9.4 ms |
| current | Paddy Doctor held-out | 500 | 20 (0.040) | 7/20 = 0.350 | 13 | 0 | 0 / 0 / 7 | 9.4 ms |
| A | our test split | 828 | 219 (0.264) | 212/219 = 0.968 | 7 | 0 | 34 / 51 / 127 | 12.5 ms |
| A | our field photos | 272 | 71 (0.261) | 67/71 = 0.944 | 4 | 0 | 34 / 0 / 33 | 12.5 ms |
| A | Paddy Doctor held-out | 500 | 3 (0.006) | 0/3 = 0.000 | 3 | 0 | 0 / 0 / 0 | 12.5 ms |
| B | our test split | 828 | 185 (0.223) | 172/185 = 0.930 | 13 | 0 | 33 / 0 / 139 | 12.6 ms |
| B | our field photos | 272 | 71 (0.261) | 69/71 = 0.972 | 2 | 0 | 33 / 0 / 36 | 12.6 ms |
| B | Paddy Doctor held-out | 500 | 227 (0.454) | 226/227 = 0.996 | 1 | 0 | 108 / 6 / 112 | 12.6 ms |

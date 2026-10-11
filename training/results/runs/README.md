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
| run9b_seed43 | Repeat of run 9 with a different random seed (not shipped; shows run-to-run variation). | 0.6339 | 0.80 | same as t | 0.2 | 828 | 0.9166 | 0.8877 | 0.9646 | 6/18 / 5/18 | 5/87 |

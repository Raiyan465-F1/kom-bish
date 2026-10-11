# Example photos: credits

Every example is a dataset image, not a photo taken by the team. All were re-saved with rotation applied and
all EXIF metadata removed (`scripts/strip_exif.py`). None was used to train the published model: each comes
from a test split or a held-out set. `tests/test_examples.py` checks that each one still triggers the rule
path it is meant to show.

| File | Shows | Source | Licence |
|---|---|---|---|
| `blb_riceleafbd_test.jpg` | `R1_BLB`: "no insecticide needed, fix the fertiliser" | Sample image from the RiceLeafBD test split (class Bacterial Leaf Blight). RiceLeafBD, Mendeley Data, DOI 10.17632/kx9rx8p2mz.1 (see also arXiv 2501.08912) | CC BY 4.0 |
| `blast_paddy_doctor_heldout.jpg` | `R0_CONFIRM_BLAST`, then `R2_BLAST` ("spray correctly") on "yes" or `R7_BLAST_UNCONFIRMED` (referral) on "no" / "not sure" | Sample image from our Paddy Doctor held-out set (class blast, `train_images/blast/107817.jpg`). Petchiammal A, Briskline Kiruba S, D. Murugan, Pandarasamy A (2022), "Paddy Doctor: A Visual Image Dataset for Automated Paddy Disease Classification and Benchmarking", arXiv:2205.11108; project page https://paddydoc.github.io/; Kaggle competition https://www.kaggle.com/competitions/paddy-disease-classification | CC BY 4.0 (competition rules, section 7.A) |
| `healthy_riceleafbd_test.jpg` | `R3_HEALTHY`: "no spray now" | Sample image from the RiceLeafBD test split (class Healthy Leaf). DOI 10.17632/kx9rx8p2mz.1 | CC BY 4.0 |
| `other_brown_spot_riceleafbd_test.jpg` | `R4_OTHER`: referral (another disease) | Sample image from the RiceLeafBD test split (class Brown Spot). DOI 10.17632/kx9rx8p2mz.1 | CC BY 4.0 |
| `not_sure_field_blast_dhanshomadhan_heldout.jpg` | `R5_ABSTAIN`: "not sure, call 16123" (a real blast leaf the model is not confident about) | Sample image from our held-out Dhan-Shomadhan field blast set (mirror row 63). Dhan-Shomadhan, Mendeley Data, DOI 10.17632/znsxdctwtt.1, via the Hugging Face mirror `Project-AgML/Dhan-Shomadhan_rice_leaf_disease_classification` | CC BY 4.0 |

The remaining rule paths need no photo: `R0_NO_CONSENT` (leave the consent box unticked), `R0_NO_PHOTO`
(press the button with no photo) and `R6_VOICE_REDFLAG` (a voice note that mentions insects on a
healthy-looking leaf; only when voice is switched on).

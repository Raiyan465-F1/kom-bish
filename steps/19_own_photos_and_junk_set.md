# 19 — Own photos, junk photos and demo examples

**Goal:** Collect 30–50 of the team's own rice-leaf photos and 20 junk photos for an honest evaluation, and choose 4–6 example photos for the app with GPS data stripped.
**Who:** Human (all). Claude Code only strips EXIF and copies the chosen examples.
**When:** Any time from Saturday; must be ready Monday morning for step 20.
**Covers master-plan step:** S19.

Context: The training data has a single-source confound (all BLB from one dataset, all training blast from another). The most persuasive numbers are therefore not test accuracy but: the false-trigger rate on the team's own healthy-looking leaves (wrongly sent to BLB or blast), and the junk refusal rate (non-rice photos correctly referred). The `other` class does not cover non-rice photos. Nothing private may be committed.

## Prerequisites

- Phones with cameras; access to a rice field or potted rice if possible.
- `.gitignore` contains `own_photos/` and `junk_photos/` (step 03). Claude Code check: `grep -E "^(own_photos|junk_photos)/" .gitignore` [Add them to .gitignore first.]

## Instructions for Claude Code

1. Write `scripts/strip_exif.py <src> <dst>`: re-saves each JPEG with `ImageOps.exif_transpose` applied and **no EXIF** (no GPS, no device data), quality 95, long side at most 1600 px. Prints each output file.
2. When the human names the chosen example photos, run it into `examples/` with descriptive names, e.g. `examples/healthy_own_1.jpg`, `examples/blb_riceleafbd_test.jpg`, `examples/blast_bd5_test.jpg`, `examples/not_a_leaf.jpg`. Verify with Pillow that `img.getexif()` is empty for each.
3. If a dataset test image is used as an example, add its source to a new file `examples/CREDITS.md` (dataset name, DOI, licence CC BY 4.0, "sample image from the <dataset> test split").
4. Do not copy anything into the repo from `own_photos/` or `junk_photos/` except the chosen, stripped examples.

## Human actions

- [ ] **HUMAN (all):** take **30–50 photos of real rice leaves** (close-up, one leaf filling most of the frame, daylight, different phones if possible). Put them in:
  - `own_photos/healthy_looking/` — leaves that look healthy to you
  - `own_photos/symptomatic/` — leaves with visible spots, yellowing or drying
  Do not guess disease names; just healthy-looking vs symptomatic.
- [ ] **HUMAN:** take or collect **20 junk photos** into `junk_photos/`: hands, soil, other crops, grass, blurred leaves, a wall, a face-free street scene. No faces of people who have not agreed.
- [ ] **HUMAN:** choose **4–6 example photos** for the app: one per class if possible plus one "healthy" and one "not a rice leaf". BLB and blast examples will almost certainly be dataset test images, not field finds; that is fine if credited. Tell Claude Code the file paths.
- [ ] **HUMAN:** check `git status` shows nothing from `own_photos/` or `junk_photos/`.
- [ ] **HUMAN:** commit: `git add examples scripts/strip_exif.py && git commit -m "step 19: examples" && git push`.

## Done when

- `own_photos/healthy_looking/`, `own_photos/symptomatic/` (30–50 photos in total) and `junk_photos/` (20 photos) exist locally and are not tracked by git.
- `examples/` holds 4–6 JPEGs with empty EXIF, and `examples/CREDITS.md` credits any dataset image.
- The app shows the examples under the photo box.

## If it fails

- **No rice field nearby:** use any rice plants available (nursery, market seedlings, a relative's field via a phone call and photos sent to you). Report the true n even if it is small; never pad with dataset images and call them own photos.
- **Too few photos by Monday:** run step 20 with what you have and state n.

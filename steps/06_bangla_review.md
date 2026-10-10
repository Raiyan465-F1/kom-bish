# 06 — Bangla review, round 1 (and agronomy check if possible)

**Goal:** Two native Bangla speakers review every farmer-facing string, fix it, time it, and sign it off before anything is recorded.
**Who:** Human (C plus a second native speaker). Claude Code only applies the edits the humans paste back.
**When:** Saturday night to Sunday morning. Must finish before step 16 (recording clips).
**Covers master-plan step:** S07.

Context: Every sentence a farmer hears lives in `data/clips.csv` (answer scripts) and `data/rules.csv` (headlines); UI strings live in `kombish/texts.py`. All of it is **DRAFT — needs native speaker review before recording**. No native speaker or agronomist has checked it. Scripts are spoken Bangladeshi Bangla, numbers in words, 16123 read digit by digit, each under about 25 seconds aloud. The app never says a pesticide brand, a dose or a waiting-period number.

## Prerequisites

```bash
test -f data/clips.csv && test -f data/rules.csv && test -f kombish/texts.py   # [Run step 05 first.]
```

## Instructions for Claude Code

1. Print a review sheet the humans can read on a phone: for each wired clip (`blb`, `blast`, `safety`, `healthy`, `not_sure`, `consent`, `voice_failed`), show `clip_id`, `text_bn`, `gloss_en`; then every headline in `rules.csv`; then every string in `texts.py` marked NEW.
2. Wait for the human to paste corrected text. **Do not reword Bangla yourself.** You may point out typos only as questions.
3. When the human pastes corrections:
   - Update `text_bn` (and `gloss_en` if they give one) in `data/clips.csv` with the `csv` module.
   - Set `review_status="reviewed"`, `reviewer_1`, `reviewer_2`, `review_date` (YYYY-MM-DD), `duration_s` (the read-aloud time they report) for each approved clip.
   - Set `review_status="reviewed"` and `reviewer` in `data/rules.csv` for approved headlines.
   - If `CONSENT_BN` changes, update `kombish/texts.py`, update the `consent` row in `clips.csv` to the identical string, and bump `CONSENT_VERSION` (e.g. `2026-10-11-v1`).
   - Replace the `voice_failed` `TODO-C` text with C's line.
4. Run `pytest -q`. If `test_numbers_only_from_allowlist` or `test_no_forbidden_terms` fails, show the human the exact token and ask whether it is intended. Change `NUMBER_ALLOWLIST` only if the human confirms the number is sourced and is not a pesticide dose or a waiting period.
5. Run `pytest -q -m final` and print what is still open (expected: clip files, until step 16).

## Human actions

### Review checklist — HUMAN (C + second native speaker)

- [ ] Read each script aloud and time it. Each must be about **25 seconds or less**.
- [ ] Check it sounds like natural spoken Bangladeshi Bangla, not textbook or Kolkata Bangla.
- [ ] `blb`: keep the headline meaning "no **insecticide** needed, fix the fertiliser" (never "do not spray"; the official notice also lists a sulphur-based foliar mix, which Kom Bish omits and refers instead). Decide whether to add "ব্রির পরামর্শ অনুযায়ী" (according to BRRI) before the fertiliser amounts. The "drain standing water" line stays **out** unless you approve it (its only source is a 2017 DAE official quote).
- [ ] `blast`: names only "ট্রাইসাইক্লাজোল গ্রুপের ছত্রাকনাশক", no brand, no dose; dose and harvest wait are deferred to the Bangla label; the neck-blast urgency line stays.
- [ ] `healthy`: keep "তবে" (but) before the exception so the 30–40-day rule is not heard as "never spray".
- [ ] `not_sure`: confirm whether farmers say 16123 digit by digit ("এক-ছয়-এক-দুই-তিন") or another way.
- [ ] `safety`: keep the FAO items (long sleeves, trousers, footwear; gloves when mixing; wind at your back; no eating, drinking or smoking; wash afterwards; harvest wait from the label).
- [ ] `consent`: it must describe what really happens: photo not kept; voice processed on Google's servers outside the country and may be used by Google; only the result kept, without name or phone; under-18 needs a parent; tick to agree. Nothing about phone numbers or 30-day storage.
- [ ] `voice_failed`: **C writes one line**: the voice note could not be understood, and the advice is from the photo alone.
- [ ] NEW strings in `texts.py` (`SOURCE_LABEL_BN`, `LABEL_SAFETY_BN`, `FEEDBACK_BN`, `FEEDBACK_THANKS_BN`): approve or replace.
- [ ] Paste corrections into Claude Code as: `clip_id: <new text>` (one per line), plus reviewer names and timings.

### Agronomy check — HUMAN, if possible

- [ ] Ask the mentor (step 21) or any agriculture faculty member or officer to read the six rules and the four answer scripts. Record name, role and date in `docs/gates.md`.
- [ ] If nobody reviews, the README, deck and video must say "rules not yet reviewed by an agronomist".
- [ ] Optional: a Bangla reader opens the scanned BRRI fact sheets (Factsheet 2 "Patapora rog", Factsheet 4 "Blast rog") in a browser and notes whether BRRI's standing leaf-blight advice mentions draining or any spray.

### Commit — HUMAN

- [ ] `git add -A && git commit -m "step 06: Bangla review round 1" && git push`

## Done when

- Every wired clip in `data/clips.csv` has `review_status=reviewed`, two reviewer names, a date and `duration_s` ≤ about 25.
- Every headline in `data/rules.csv` is `reviewed`.
- No `TODO-C` remains (`grep -rn "TODO-C" data kombish` prints nothing).
- `pytest -q` passes. `pytest -q -m final` fails only on missing clip files.

## If it fails

- **Reviewers disagree:** keep the more cautious wording; C decides.
- **No second native speaker is available by Sunday noon:** C reviews alone, sets `reviewer_2` to `PENDING`, and the README states "reviewed by one native speaker". `pytest -m final` will keep failing on that row until fixed; that is intended.
- **A script runs over 25 s:** cut the least important clause; never cut the safety lines, the referral number or "follow the label".

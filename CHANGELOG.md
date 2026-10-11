# Changelog

## Unreleased

Built and tested on 10–11 October 2026. Not released: the Bangla is not reviewed, the clips are not
recorded, the model is not published and nothing is hosted yet (see `docs/gates.md`).

- Classifier trained (gate G2, 11 Oct): ten runs, listed in `training/results/runs/README.md`. The planned
  recipe learned the photo background and recognised 2 of 74 field blast photos, so Dhan-Shomadhan was added
  to training, the threshold rule was tightened and training runs 40 epochs. Shipped: `run9_final`
- Spray advice is stricter than no-spray advice: a blast-only threshold (0.995, chosen on validation) and a
  lesion-shape question the farmer must answer "yes" to before any blast answer (rules `R0_CONFIRM_BLAST`,
  `R7_BLAST_UNCONFIRMED`; draft Bangla awaiting review). Test coverage fell from 0.8780 to 0.7585
- External test on Paddy Doctor (India), n = 200 (`training/external_test.py`): 192 referred, 8 answered,
  1 right, 0 wrong spray answers. The model does not transfer to wide shots of whole plants
- Audio: six clips generated with Gemini text-to-speech (`scripts/tts_fallback.py`), labelled
  "computer-generated voice" in the app; audio stays optional. Review rule is now one native-speaker reviewer.
  `docs/bangla_review.md` lists every farmer-facing Bangla string
- Model frozen at v2. Healthy answer now ends with "if spots appear or spread, take a new photo or call
  16123" (draft Bangla for review). README, model card and deck framed as a safe-by-design spray adviser;
  README "Pilot plan" section (a plan, not built). `CLAUDE.md` lists the two blast-confirmation rule IDs
- **Model v2 published** (candidate B: adds Paddy Doctor training photos, stronger augmentation, a BLB-only
  threshold). The previous model stays on the Hub as revision `v1`
- One set of outcome definitions everywhere (`training/outcomes.py`): classifier confident, advice given,
  blast question asked, referred
- External test on the Zambali Rice Dataset (Philippines), n = 200: 28 advice answers, 27 right (all healthy
  leaves); diseases referred, not recognised; 50 of 50 not-a-rice-leaf images referred
- Example photos, one per rule path, credited in `examples/CREDITS.md` and checked by `tests/test_examples.py`
- Two candidate models trained and compared, not published (`docs/gates.md`): A = stronger augmentation,
  B = A plus Paddy Doctor training photos. New: `--aug strong`, a BLB-only threshold (`blb_threshold`,
  supported by the app when present), `training/prepare_paddy.py`, `training/compare_candidates.py`
- Model published with its card (MIT) at huggingface.co/Raiyan465/kom-bish-rice-leaf; near-duplicate leak
  check (`training/check_leakage.py`); Gemini fixed to `gemini-3.5-flash-lite`
- Data prep now removes byte-identical duplicates and drops photos filed under two conflicting classes
- Evaluation report with advice-level outcomes (correct advice, referred, wrong advice) on field photos

- Scaffold (step 03)
- Hosting probe: ZeroGPU shim with two variants, Render and Space settings (step 04)
- Rule engine, six-row rule table, draft Bangla texts, consent text and safety tests (step 05)
- Data preparation with a human-filled folder mapping; synthetic data for code checks (step 07 Part A)
- Two-stage fine-tuning, temperature scaling, abstain threshold, metrics, single-file ONNX export and the
  Kaggle notebook (steps 08–09)
- Classifier module with timm-exact preprocessing, and a parity check (step 12)
- Gradio app: consent gate, photo, optional voice, answer text and audio, feedback, counters (step 13)
- Anonymous logging to a private HF dataset, with counters seeded at startup (step 14)
- Optional Gemini voice parsing behind `VOICE_ENABLED`, failing safely; scoring and cache scripts (step 15)
- Clip processing script (step 16), sync and keep-awake workflows and a hosted smoke test (step 17)
- Phone-test checklist, EXIF stripper, off-script test, evaluation and report scripts (steps 18–20)
- Model card and publish scripts (step 11), deck generator (step 22), README draft (step 23), video shot
  list, narration draft and subtitles (step 24), submission drafts (step 25), preflight audit (step 26)

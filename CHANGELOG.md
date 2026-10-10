# Changelog

## Unreleased

Built and tested on 10–11 October 2026. Not released: the classifier is not trained, the Bangla is not
reviewed, the clips are not recorded and nothing is hosted yet (see `docs/gates.md`).

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

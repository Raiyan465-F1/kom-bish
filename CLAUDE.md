# CLAUDE.md — Kom Bish (কম বিষ) project memory

Copy this file to the repo root. Claude Code reads it at the start of every session.
Step files live in `steps/`. The human runs them one at a time: "Read steps/NN_xxx.md and do it."

## 1. Project goal

Kom Bish is a hackathon prototype (Hack for Humanity BD 2026, Round 2, Team Unsick).
A farmer ticks a consent box, uploads a rice-leaf photo, optionally records a Bangla voice note,
and gets a pre-written, human-reviewed Bangla answer as text plus a human-recorded audio clip.

- A 4-class ONNX classifier (`bacterial_leaf_blight`, `blast`, `healthy`, `other`) picks a row in a 6-row rule table.
- Low confidence → "not sure, call 16123 or your officer".
- Hard deadline: reply to the selection email by **10:00 PM, Wednesday 14 October 2026** (aim for 6 PM).
- Judges see the work with no presenter. Anything not shown in the README, deck or video looks like a failure.

## 2. Hard safety rules (never break these)

1. **The app never invents pesticide names, brands, doses or pre-harvest days.** Every sentence a farmer can
   read or hear comes from `data/rules.csv` or `data/clips.csv`. Kom Bish names only the active-ingredient group
   "ট্রাইসাইক্লাজোল গ্রুপের ছত্রাকনাশক" (tricyclazole-group fungicide) for blast. Never a brand. Never a dose.
   Never a waiting-period number ("follow the label" only).
2. **Code decides; the language model only parses voice.** `kombish/rules.py::decide()` is pure Python.
   Gemini only turns a voice note into a fixed-enum `VoiceQuery`. No model output is spoken or shown as advice.
   The only model outputs shown are the classifier label (in the confirm-back line) and, if voice is used,
   the transcript echoed back in a separate box for confirmation.
3. **Voice can only make an answer more cautious.** With voice, the decision is either the same as without voice,
   or `consult_officer`. Voice can never produce `spray_correctly`. Tests enforce this.
4. **Low confidence → referral.** `conf < threshold` or `top1 − top2 < margin` → `R5_ABSTAIN` → `consult_officer`.
5. **No personal data stored.** Never store the photo, the audio, the transcript, IP addresses, names or phone numbers.
   The log holds only the fields listed in section 6.
6. **Never commit secrets.** `.env` is git-ignored. Only `.env.example` is committed. If a key is ever committed,
   stop, tell the human to rotate it, and remove it from history only if the human asks.
7. **Never fake results.** Do not create a dummy `model.onnx`, fabricate metrics, invent counts, write Bangla
   the step file did not supply, or generate audio clips with TTS unless the step file explicitly allows it.
   Edifenphos, carbendazim and propiconazole must never appear anywhere in user-facing text.
8. **Never invent facts, URLs, versions or numbers.** If something is unknown, write `TODO-HUMAN:` with a clear
   question, or check it at run time (print it) and stop.

## 3. HUMAN steps — stop and ask

When a step file says **HUMAN**, stop. Print exactly what the human must do (where to click, what to paste back)
and wait. Do not guess outputs that only a human can produce (folder trees from Kaggle, recordings, reviews,
secrets, metrics from a GPU run). Before starting any step, run its Prerequisites checks. If one fails, stop and
print the step file's "missing prerequisite" message.

## 4. Pinned stack (do not change versions without the human's approval)

| Layer | Package / setting |
|---|---|
| Python | 3.12 everywhere (ZeroGPU lists 3.12.12; onnxruntime 1.31 needs ≥ 3.11) |
| UI | `gradio==6.29.1` (not 6.30.0). In Gradio 6, `theme`, `css`, `head` go in `demo.launch()`, not `gr.Blocks()` |
| Inference | `onnxruntime==1.31.0`, `numpy<3`, `pillow==12.3.0`. **No torch in the app.** |
| Hub | `huggingface_hub==2.2.0` (`hf_hub_download`, `CommitScheduler`, `snapshot_download`) |
| Voice | `google-genai==2.29.0`, `pydantic>=2.11`; model from `GEMINI_MODEL`: `gemini-3.5-flash-lite` only (team decision, 11 Oct 2026) |
| ZeroGPU only | `spaces` (unpinned; in `requirements.txt` only, not in `requirements-render.txt`) |
| Dev | `pytest`, `ruff`, `python-dotenv` (no versions verified in sources; pin what installs) |
| Training (Kaggle T4) | `torch 2.14.1`, `torchvision 0.29.1`, `timm==1.0.30`, `onnx==1.23.2`, `onnxscript==0.7.2`, `scikit-learn==1.9.1` |
| Deck | `python-pptx==1.0.2` |
| Model | `mobilenetv3_large_100.ra_in1k` (pin the tag: ImageNet mean/std, bicubic, crop_pct 0.875). Backup `efficientnet_b0.ra_in1k` |

Two virtual environments:
- `.venv` — app and tests. Must never contain torch.
- `.venv-train` — training scripts, parity check, deck. May contain torch (CPU).

## 5. Environment contract (all config comes from environment variables)

| Name | Kind | Meaning |
|---|---|---|
| `MODEL_REPO` | variable | Public HF model repo, `<hf-user>/kom-bish-rice-leaf` |
| `LOG_REPO` | variable | Private HF dataset repo, `<hf-user>/kom-bish-logs` |
| `HF_TOKEN` | **secret** | Fine-grained HF token, write access to the log repo only |
| `GEMINI_API_KEY` | **secret** | Gemini API key (free tier) |
| `GEMINI_MODEL` | variable | `gemini-3.5-flash-lite` (the only model used) |
| `VOICE_ENABLED` | variable | `true` / `false`. `false` hides the microphone entirely |
| `APP_VERSION` | variable | e.g. `0.1.0`, `1.0.0` |
| `ZEROGPU_MODE` | variable | `noop` (default) or `wrap`. Only matters on a ZeroGPU Space |
| `PORT` | set by Render | App listens on `int(os.environ.get("PORT", 7860))`, `server_name="0.0.0.0"` |

GitHub Actions: secret `HF_SYNC_TOKEN` (HF token with write access to the Space, used only by the sync workflow);
variables `HF_SPACE_ID`, `RENDER_URL`, `MODEL_REPO`.

Locally, `app.py` loads `.env` with `python-dotenv` inside `try/except ImportError` (no-op on hosts).

## 6. Canonical names (use exactly these)

- Classes, in this order (from `ImageFolder.classes`, never typed by hand in training):
  `["bacterial_leaf_blight", "blast", "healthy", "other"]`
- Rule IDs, priority order: `R0_NO_CONSENT`, `R0_NO_PHOTO`, `R5_ABSTAIN`, `R6_VOICE_REDFLAG`, `R1_BLB`, `R0_CONFIRM_BLAST`, `R7_BLAST_UNCONFIRMED`, `R2_BLAST`, `R3_HEALTHY`, `R4_OTHER`
  (`R0_CONFIRM_BLAST` asks the lesion-shape question before any blast answer; "no" or "not sure" gives `R7_BLAST_UNCONFIRMED`, a referral; only "yes" gives `R2_BLAST`)
- Decisions: `none`, `consult_officer`, `no_insecticide_fix_fertiliser`, `spray_correctly`, `no_spray_monitor`
- Clip IDs → files: `blb`, `blast`, `safety`, `healthy`, `not_sure`, `consent`, `voice_failed`, `brinjal` (stretch, not wired) → `audio/<clip_id>.mp3`
- Voice symptom enum: `brown_spots`, `spindle_lesions`, `yellowing`, `leaf_tip_drying`, `insects_seen`, `hopper_burn`, `wilting`, `none`, `unclear`
- Growth stage enum: `seedling`, `tillering`, `booting`, `flowering`, `ripening`, `unknown`
- Log record (type `consultation`): `id`, `type`, `ts_utc`, `app_version`, `predicted_class`, `confidence`, `probs`, `abstained`,
  `voice_used`, `voice_symptoms`, `voice_confidence`, `growth_stage`, `planning_to_spray`, `rule_id`, `decision`,
  `latency_ms`, `consent_version`, `feedback`. Feedback is a separate record: `id`, `type: "feedback"`, `ts_utc`, `ref_id`, `feedback`.

Key signatures:

```python
# kombish/classifier.py
@dataclass(frozen=True)
class Prediction: label: str; conf: float; probs: dict[str, float]; margin: float; abstained: bool
def load() -> tuple[onnxruntime.InferenceSession, dict]   # cached; downloads from MODEL_REPO
def meta() -> dict                                          # labels.json contents
def preprocess(img: PIL.Image.Image, m: dict) -> np.ndarray # (1, 3, 224, 224) float32
def predict(img: PIL.Image.Image) -> Prediction

# kombish/rules.py
@dataclass(frozen=True)
class Advice: rule_id: str; decision: str; headline_bn: str; text_md: str; clips: tuple[str, ...]; sources: tuple[str, ...]
def decide(label: str | None, conf: float, margin_ok: bool, voice: "VoiceQuery | None",
           planning_to_spray: bool | None, *, threshold: float, consent: bool = True,
           voice_failed: bool = False) -> Advice

# kombish/voice.py
class VoiceQuery(BaseModel): transcript_bn, symptoms, growth_stage, farmer_wants_to_spray, confidence
def voice_enabled() -> bool
def parse_voice(path: str | None) -> VoiceQuery | None    # None on any failure, low confidence or "unclear" only

# kombish/logging_store.py
def log_consult(record: dict) -> str     # returns record id
def log_feedback(ref_id: str, feedback: str = "looks_wrong") -> None
def bootstrap_counts() -> None
def counts() -> dict                     # total, no_spray, correct_use, referrals, sprays_avoided

# kombish/zerogpu.py
def maybe_gpu(fn): ...                   # wraps fn in spaces.GPU(duration=10) only when ZEROGPU_MODE=wrap on ZeroGPU

# app.py
def build_demo(predict_fn=None, meta_fn=None, voice_fn=None, log_fn=None,
               feedback_fn=None, counts_fn=None, voice_on: bool | None = None) -> gr.Blocks
# main event: btn.click(..., api_name="advise"); feedback: api_name="feedback"
```

## 7. Repo layout

```
kom-bish/
├── CLAUDE.md  README.md  LICENSE (MIT)  CHANGELOG.md  pytest.ini
├── requirements.txt  requirements-render.txt  requirements-dev.txt  .env.example  .gitignore
├── app.py                       # thin Gradio UI
├── kombish/  __init__.py classifier.py rules.py voice.py logging_store.py texts.py zerogpu.py
├── data/  rules.csv clips.csv voice_cache.json
├── audio/*.mp3                  # human-recorded clips
├── examples/*.jpg  CREDITS.md   # 4–6 demo photos, EXIF stripped; dataset images credited
├── training/  prepare_data.py make_synthetic_data.py train_export.py make_kaggle_notebook.py
│              kombish_kaggle.ipynb requirements-train.txt check_parity.py make_model_card.py model_card.md
│              eval_own_photos.py make_eval_report.py eval_report.md eval_summary.json
│              results/  metrics.json confusion.png risk_coverage.png manifest.csv own_photos.json
├── scripts/  publish_model.py check_logging.py score_voice.py cache_voice.py process_clips.py tts_fallback.py
│             smoke_hosted.py strip_exif.py preflight.py
├── tests/  test_smoke.py test_zerogpu.py test_rules.py test_prepare_data.py test_classifier_smoke.py
│           test_app.py test_logging.py test_voice.py test_offscript.py
├── deck/  make_deck.py screens/ Kom_Bish_deck.pptx
├── video/  shot_list.md narration_bn.md subtitles_en.srt
├── submission/  worker_studio_summary.md links_template.txt email_reply_draft.md  (private/ is git-ignored)
├── docs/  gates.md phone_test.md   # gate decisions G1–G7, data-count notes, mentor notes, link audit
├── landing/index.html           # optional static landing page (step 25)
├── steps/                       # this instruction pack
└── .github/workflows/  tests.yml sync-to-hub.yml keep-awake.yml
```

Git-ignored private folders: `data/raw/`, `data/train/`, `data/val/`, `data/test/`, `data/dhs_field_blast/`, `data/synthetic/`,
`models/`, `raw_audio/`, `voice_tests/`, `own_photos/`, `junk_photos/`, `submission/private/`, `logs/`.

## 8. Commands

```bash
# app venv (no torch)
python3.12 -m venv .venv && source .venv/bin/activate        # Windows: py -3.12 -m venv .venv ; .venv\Scripts\activate
pip install -r requirements-render.txt -r requirements-dev.txt
pytest -q                 # fast tests (CI runs this)
pytest -q -m final        # final checks: real clips exist, reviewed text, no TODO-C placeholders
python app.py             # http://localhost:7860
python app.py --share     # laptop backup with a *.gradio.live HTTPS link (lasts up to 1 week, best effort)

# training venv (CPU torch)
python3.12 -m venv .venv-train && source .venv-train/bin/activate
pip install -r training/requirements-train.txt
```

`pytest.ini` sets `addopts = -m "not final"` so `final` tests run only when asked.

## 9. Working rules

- Keep `app.py` thin. Safety logic lives in `kombish/` where a judge can read it.
- Load the ONNX session lazily once (cached), so importing `app` in tests needs no network.
- Bangla text: every Bangla string in this repo is a **DRAFT until one native speaker marks it reviewed**
  (team decision, 11 Oct 2026; it was two) in
  `data/clips.csv` / `data/rules.csv`. Do not reword reviewed Bangla without the human's approval.
  NFC-normalise Bangla before comparing strings (`unicodedata.normalize("NFC", s)`).
- Phones need HTTPS for mic and camera. Never tell anyone to use a LAN IP for a phone test.
- Never import torch in `app.py` or `kombish/`.
- Commit at the end of each step when the human asks ("commit this step"). Use messages like `step 05: rule engine and content`.
  Never force-push. After the email reply is sent (step 26), never push to `main` (a sync rebuilds the Space).
- End each step by printing the "Done when" commands and their results, then a short list of anything the human must do next.

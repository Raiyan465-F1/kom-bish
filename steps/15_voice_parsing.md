# 15 — Optional voice parsing with Gemini (gate G3)

**Goal:** Turn an optional Bangla voice note into a fixed-enum `VoiceQuery` with Gemini, behind `VOICE_ENABLED`, failing safely; score it on 10 real notes and decide voice on/off.
**Who:** Both. Claude Code writes `kombish/voice.py`, a scoring script and tests; the human (C) records 10 notes and runs the score.
**When:** Sunday 11 October. **Gate G3 at 10 PM:** voice on or off.
**Covers master-plan step:** S16 (instruction file CC-10).

Context: Voice is advisory only. Gemini returns a Pydantic-validated JSON object of symptoms and growth stage, or nothing. **Voice can only make an answer more cautious** (the only voice-driven rule is R6: healthy image + medium/high-confidence `hopper_burn` or `insects_seen` → referral). Any exception, quota error, low-confidence parse or "unclear"-only parse returns `None`; the answer then says the voice note was not understood and the advice is from the photo alone. No live Gemini call was made in our research: Bangla transcription quality, latency and the free-tier quota are **unknown until this test**. Inline requests must stay under 20 MB total. Free-tier content "is used to improve our products" (the consent text says so). Daily quotas reset at midnight Pacific (1:00 PM Bangladesh time in October). Whisper is not hosted (even small int8 needs about 1.5 GB, beyond Render's 512 MB). The Bangla prompt below is model input, not farmer-facing, but it is still **DRAFT — needs native speaker review before recording**.

## Prerequisites

```bash
source .venv/bin/activate
python -c "import google.genai, pydantic; print(google.genai.__version__)"   # expect 2.29.0  [pip install -r requirements-render.txt]
python -c "from kombish.voice import VoiceQuery"                             # [Run step 05.]
grep -q "^GEMINI_API_KEY=." .env                                             # [HUMAN: put the Gemini key in .env (step 01).]
```
If the key is missing, write the code and tests, then stop and ask for the key.

## Instructions for Claude Code

### 1. `kombish/voice.py` (keep the `VoiceQuery` model from step 05 unchanged)

Add the Gemini call using the `generate_content` structured-JSON pattern (verified to serialise correctly with google-genai 2.29.0; Google calls `generateContent` "legacy" but "fully supported", and it is the typed path in this SDK, so use it, not Interactions):

```python
import hashlib
import json
import mimetypes
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE_PATH = ROOT / "data" / "voice_cache.json"
MAX_BYTES = 15_000_000          # stay under the 20 MB inline request cap
PROMPT_BN = ("এটি একজন বাংলাদেশি ধানচাষির ভয়েস নোট। হুবহু বাংলায় লিখুন এবং লক্ষণগুলো নির্দিষ্ট তালিকা থেকে "
             "বেছে নিন। অনিশ্চিত হলে 'unclear' দিন।")


def voice_enabled() -> bool:
    return (os.getenv("VOICE_ENABLED", "false").strip().lower() == "true"
            and bool(os.getenv("GEMINI_API_KEY")))


def _load_cache() -> dict:
    try:
        return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def call_gemini(data: bytes, mime: str, model: str | None = None) -> VoiceQuery | None:
    """One Gemini call. Returns the parsed VoiceQuery (any confidence) or None on any error."""
    try:
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
        resp = client.models.generate_content(
            model=model or os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite"),
            contents=[types.Part.from_bytes(data=data, mime_type=mime), PROMPT_BN],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_json_schema=VoiceQuery.model_json_schema(),
                temperature=0),
        )
        return VoiceQuery.model_validate_json(resp.text)
    except Exception:             # quota (429), network, validation -> degrade gracefully
        return None


def _usable(vq: VoiceQuery | None) -> VoiceQuery | None:
    if vq is None or vq.confidence == "low" or set(vq.symptoms) <= {"unclear"}:
        return None
    return vq


def parse_voice(path: str | None) -> VoiceQuery | None:
    if not path:
        return None
    data = Path(path).read_bytes()
    if len(data) > MAX_BYTES:
        return None
    key = hashlib.sha256(data).hexdigest()
    cached = _load_cache().get(key)
    if cached is not None:                       # scripted demo clip works even when the quota is gone
        return _usable(VoiceQuery.model_validate(cached))
    if not voice_enabled():
        return None
    mime = mimetypes.guess_type(path)[0] or "audio/wav"   # mic gives .wav; uploads may be .ogg/.m4a/.mp3
    return _usable(call_gemini(data, mime))
```

Never log or store the transcript; `app.py` only echoes it back on screen in a separate box (step 13).

### 2. `scripts/cache_voice.py`

`python scripts/cache_voice.py <audio_file> [--model gemini-3.8-flash]`: calls `call_gemini` once, prints the result, and if the human confirms (`y`), stores `{sha256: VoiceQuery.model_dump()}` in `data/voice_cache.json` (create if missing; keep it sorted, UTF-8, `ensure_ascii=False`). Use only for the team's scripted demo clip, recorded by a teammate who agrees. Tell the human: in the video and live pitch, **upload that saved file** instead of recording live, so the cache hits even if the quota is gone.

### 3. `scripts/score_voice.py`

`python scripts/score_voice.py --dir voice_tests --model gemini-3.5-flash-lite` (run again with `--model gemini-3.8-flash`).
- Reads `voice_tests/expected.csv` with columns `file, expected_symptoms` (semicolon-separated enum values, e.g. `brown_spots;yellowing`).
- For each note: time the `call_gemini` call, record the returned symptoms, confidence, growth stage, latency, and whether `set(returned) == set(expected)`. Print a table and the score `k / n`. Print errors (`None`) as failures.
- Print the transcript only to the terminal, never to a file.
- Sleep 2 seconds between calls (free-tier per-minute limits are unpublished).
- `voice_tests/` is git-ignored (team voices stay off GitHub).

### 4. `tests/test_voice.py` (no network: monkeypatch `call_gemini`)

- `voice_enabled()` is False when `VOICE_ENABLED` is unset, `false`, or the key is missing.
- `parse_voice(None)` → None; a file over 15 MB → None (create a sparse temp file).
- `call_gemini` returning None (simulating a 429 or bad JSON) → `parse_voice` returns None.
- Low confidence → None; `["unclear"]` only → None; medium confidence with `["insects_seen"]` → returned.
- Cache hit: write a temp cache with the file's sha256; `parse_voice` returns it without calling Gemini (assert the fake was not called), even with `VOICE_ENABLED=false`.
- End-to-end with rules: a returned red-flag `VoiceQuery` plus a confident `healthy` label gives `R6_VOICE_REDFLAG`; with a confident `blast` label the decision stays `spray_correctly` (voice never adds or removes a spray).

### 5. Run

```bash
pytest -q
python scripts/score_voice.py --dir voice_tests --model gemini-3.5-flash-lite
python scripts/score_voice.py --dir voice_tests --model gemini-3.8-flash
```

### 6. Record gate G3 in `docs/gates.md`

Scores for both models, median latency, any 429 errors, the chosen `GEMINI_MODEL`, and the decision: voice **on** if at least 7 of 10 notes give the right symptom list on the better model and failures degrade cleanly; otherwise **off** (`VOICE_ENABLED=false`) and the README must say so. Update `.env` accordingly.

## Human actions

- **HUMAN (C):** record **10 short Bangla voice notes** on a phone (a few seconds each), in standard Bangla and your own dialect, describing rice-leaf problems (e.g. brown spots, yellowing, insects seen, leaf tips drying, "all looks fine"). Write down the intended symptom list for each using the enum names: `brown_spots, spindle_lesions, yellowing, leaf_tip_drying, insects_seen, hopper_burn, wilting, none, unclear`.
- **HUMAN:** copy them to `voice_tests/` and create `voice_tests/expected.csv` (`file,expected_symptoms`).
- **HUMAN:** set `VOICE_ENABLED=true` in `.env` for the test. Run both score commands. Paste the tables to Claude Code.
- **HUMAN (C):** record one **scripted demo clip** for the video (e.g. describing a healthy-looking field but mentioning insects, to show the cautious R6 path, or a plain description). Run `python scripts/cache_voice.py <file>` and keep that file for the video and pitch.
- **HUMAN:** commit (the cache file is fine to commit; `voice_tests/` is ignored): `git add -A && git commit -m "step 15: voice parsing" && git push`.

## Done when

- `pytest -q` passes, including `tests/test_voice.py`.
- Both score runs completed; G3 decision recorded in `docs/gates.md` with scores and latency.
- With `VOICE_ENABLED=false` the microphone is hidden in the app; with `true`, a failed parse shows the `voice_failed` line and the answer from the photo alone.
- `data/voice_cache.json` holds the demo clip's parse (if voice is on).

## If it fails

- **Score below 7/10 on both models, or many 429s:** `VOICE_ENABLED=false`. The app is photo-only; say so in the README ("voice parsing switched off: Bangla accuracy below our bar in a 10-note test").
- **Quota runs out during testing:** daily quotas reset at midnight Pacific (1:00 PM Bangladesh). Switch `GEMINI_MODEL` by env var, no code change.
- **Uploaded `.ogg`/`.m4a` gets a wrong MIME type:** `mimetypes` may not know a type. Gemini accepts WAV, MP3, AIFF, AAC, OGG, FLAC, MPEG, M4A, Opus, WebM and others; look up the exact MIME string for the failing extension in the Gemini audio docs at run time and map it explicitly.
- **Schema rejected by the API:** keep the schema flat (it is); print the error once in a debug run, never in production.

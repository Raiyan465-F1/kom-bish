"""Voice parsing: a Bangla voice note -> a fixed-enum VoiceQuery, or None.

Gemini only fills the enum fields below. Nothing it returns is shown or spoken as advice, and the
transcript is never logged or stored. Any error, quota limit, low-confidence parse or "unclear"-only
parse returns None, and the rule engine then answers from the photo alone.
"""
from __future__ import annotations

import hashlib
import json
import mimetypes
import os
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

ROOT = Path(__file__).resolve().parent.parent
CACHE_PATH = ROOT / "data" / "voice_cache.json"
MAX_BYTES = 15_000_000          # stay under the 20 MB inline request cap
# MIME strings from Gemini's audio docs (checked 11 Oct 2026). mimetypes alone gives "audio/x-wav"
# for .wav on Linux hosts, which is not in that list.
AUDIO_MIME = {".wav": "audio/wav", ".mp3": "audio/mp3", ".ogg": "audio/ogg", ".m4a": "audio/m4a",
              ".aac": "audio/aac", ".flac": "audio/flac", ".aiff": "audio/aiff", ".opus": "audio/opus",
              ".webm": "audio/webm"}
PROMPT_BN = ("এটি একজন বাংলাদেশি ধানচাষির ভয়েস নোট। হুবহু বাংলায় লিখুন এবং লক্ষণগুলো নির্দিষ্ট তালিকা থেকে "
             "বেছে নিন। অনিশ্চিত হলে 'unclear' দিন।")

Symptom = Literal["brown_spots", "spindle_lesions", "yellowing", "leaf_tip_drying",
                  "insects_seen", "hopper_burn", "wilting", "none", "unclear"]
GrowthStage = Literal["seedling", "tillering", "booting", "flowering", "ripening", "unknown"]


class VoiceQuery(BaseModel):
    transcript_bn: str
    symptoms: list[Symptom]
    growth_stage: GrowthStage
    farmer_wants_to_spray: bool
    confidence: Literal["low", "medium", "high"]


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
    # mic gives .wav; uploads may be .ogg/.m4a/.mp3
    mime = AUDIO_MIME.get(Path(path).suffix.lower()) or mimetypes.guess_type(path)[0] or "audio/wav"
    return _usable(call_gemini(data, mime))

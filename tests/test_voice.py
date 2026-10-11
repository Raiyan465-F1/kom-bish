import hashlib
import json

import pytest

from kombish import voice
from kombish.rules import decide
from kombish.voice import VoiceQuery, parse_voice

T = 0.70


def vq(symptoms, confidence="high") -> VoiceQuery:
    return VoiceQuery(transcript_bn="x", symptoms=symptoms, growth_stage="unknown",
                      farmer_wants_to_spray=True, confidence=confidence)


@pytest.fixture
def note(tmp_path, monkeypatch):
    """A small audio file, voice switched on, an empty cache, and a recording fake for call_gemini."""
    path = tmp_path / "note.wav"
    path.write_bytes(b"RIFF" + bytes(64))
    monkeypatch.setenv("VOICE_ENABLED", "true")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(voice, "CACHE_PATH", tmp_path / "voice_cache.json")
    calls = []

    def fake(data, mime, model=None):
        calls.append(mime)
        return fake.result

    fake.result = None
    monkeypatch.setattr(voice, "call_gemini", fake)
    return path, fake, calls


@pytest.mark.parametrize("enabled,key,expected", [
    (None, "k", False), ("false", "k", False), ("true", None, False), ("true", "", False),
    ("true", "k", True), (" TRUE ", "k", True),
])
def test_voice_enabled(monkeypatch, enabled, key, expected):
    for name, value in (("VOICE_ENABLED", enabled), ("GEMINI_API_KEY", key)):
        if value is None:
            monkeypatch.delenv(name, raising=False)
        else:
            monkeypatch.setenv(name, value)
    assert voice.voice_enabled() is expected


def test_no_path_returns_none(note):
    _, _, calls = note
    assert parse_voice(None) is None and parse_voice("") is None
    assert calls == []


def test_file_over_15_mb_returns_none(note, tmp_path):
    _, fake, calls = note
    fake.result = vq(["insects_seen"])
    big = tmp_path / "big.wav"
    with big.open("wb") as f:
        f.seek(voice.MAX_BYTES)
        f.write(b"\0")
    assert parse_voice(str(big)) is None
    assert calls == []


def test_gemini_failure_returns_none(note):
    path, fake, calls = note
    fake.result = None   # 429, network error or bad JSON
    assert parse_voice(str(path)) is None
    assert calls == ["audio/wav"]


def test_low_confidence_and_unclear_are_dropped(note):
    path, fake, _ = note
    fake.result = vq(["insects_seen"], "low")
    assert parse_voice(str(path)) is None
    fake.result = vq(["unclear"], "high")
    assert parse_voice(str(path)) is None
    fake.result = vq([], "high")
    assert parse_voice(str(path)) is None


def test_medium_confidence_is_returned(note):
    path, fake, _ = note
    fake.result = vq(["insects_seen"], "medium")
    assert parse_voice(str(path)) == fake.result


def test_disabled_voice_never_calls_gemini(note, monkeypatch):
    path, fake, calls = note
    monkeypatch.setenv("VOICE_ENABLED", "false")
    fake.result = vq(["insects_seen"])
    assert parse_voice(str(path)) is None
    assert calls == []


def test_cache_hit_needs_no_call_even_when_disabled(note, monkeypatch):
    path, fake, calls = note
    monkeypatch.setenv("VOICE_ENABLED", "false")
    cached = vq(["hopper_burn"], "high")
    key = hashlib.sha256(path.read_bytes()).hexdigest()
    voice.CACHE_PATH.write_text(json.dumps({key: cached.model_dump()}, ensure_ascii=False), "utf-8")
    assert parse_voice(str(path)) == cached
    assert calls == []


def test_schema_is_flat_and_fixed():
    schema = VoiceQuery.model_json_schema()
    assert set(schema["properties"]) == {"transcript_bn", "symptoms", "growth_stage",
                                         "farmer_wants_to_spray", "confidence"}
    assert set(schema["properties"]["symptoms"]["items"]["enum"]) == {
        "brown_spots", "spindle_lesions", "yellowing", "leaf_tip_drying", "insects_seen", "hopper_burn",
        "wilting", "none", "unclear"}


def test_red_flag_with_rules(note):
    path, fake, _ = note
    fake.result = vq(["insects_seen"], "high")
    parsed = parse_voice(str(path))
    assert decide("healthy", 0.99, True, parsed, None, threshold=T).rule_id == "R6_VOICE_REDFLAG"
    # Voice never adds or removes a spray: with or without it, blast needs the farmer's own "yes".
    assert decide("blast", 0.99, True, parsed, None, threshold=T, blast_confirmed=True).decision == "spray_correctly"
    assert decide("blast", 0.99, True, parsed, None, threshold=T).rule_id == "R0_CONFIRM_BLAST"
    assert decide("blast", 0.99, True, parsed, None, threshold=T, blast_confirmed=False).decision == "consult_officer"
    assert decide("bacterial_leaf_blight", 0.99, True, parsed, None, threshold=T).decision \
        == "no_insecticide_fix_fertiliser"

"""Generate the answer clips with Gemini text-to-speech: a COMPUTER-GENERATED voice, not a human recording.

  python scripts/tts_fallback.py [--only blb healthy] [--voice Charon]      # run in .venv-train

Run offline by a person. The app never imports this file and never calls a speech model. Each clip is
generated from the exact text_bn in data/clips.csv, saved as audio/<clip_id>.mp3 and marked
voice=computer-generated in clips.csv; the app and the README label it as such. A human recording made later
with scripts/process_clips.py replaces the file and the label.

Because nobody has listened yet, each clip is also transcribed back with GEMINI_MODEL and compared with the
text. That is a rough check, not a review: a native speaker must still listen to every clip.
Needs GEMINI_API_KEY in .env, plus the google-genai and lameenc packages.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import difflib
import hashlib
import io
import json
import re
import sys
import time
import unicodedata
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLIPS_CSV = ROOT / "data" / "clips.csv"
AUDIO = ROOT / "audio"
MANIFEST = AUDIO / "clips_manifest.json"
WIRED = ["blb", "blast", "safety", "healthy", "not_sure", "consent", "voice_failed"]
TTS_MODELS = ["gemini-3.8-flash-tts", "gemini-3.8-flash-lite-tts"]   # checked against the docs and models.list()
VOICE_LABEL = "computer-generated"
RATE, WIDTH, CHANNELS = 24000, 2, 1   # Gemini TTS returns 16-bit mono PCM at 24 kHz


def text_hash(text: str) -> str:
    return hashlib.sha256(unicodedata.normalize("NFC", text).encode("utf-8")).hexdigest()


def synthesize(client, model: str, voice: str, text: str) -> bytes:
    """Return 16-bit mono PCM at 24 kHz for exactly this text (nothing is added to it)."""
    from google.genai import types

    resp = client.models.generate_content(
        model=model, contents=text,
        config=types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice)))))
    data = resp.candidates[0].content.parts[0].inline_data.data
    if data[:4] == b"RIFF":   # some responses carry a WAV header
        with wave.open(io.BytesIO(data)) as w:
            assert (w.getframerate(), w.getsampwidth(), w.getnchannels()) == (RATE, WIDTH, CHANNELS)
            data = w.readframes(w.getnframes())
    return data


def to_mp3(pcm: bytes) -> bytes:
    import lameenc

    enc = lameenc.Encoder()
    enc.set_bit_rate(80)
    enc.set_in_sample_rate(RATE)
    enc.set_channels(CHANNELS)
    enc.set_quality(2)
    return bytes(enc.encode(pcm) + enc.flush())


def plain(text: str) -> str:
    return re.sub(r"[\s,।;:!?\-–—()\"'“”‘’.]+", "", unicodedata.normalize("NFC", text))


def transcribe(client, model: str, mp3: bytes) -> str:
    from google.genai import types

    resp = client.models.generate_content(
        model=model, contents=[types.Part.from_bytes(data=mp3, mime_type="audio/mp3"),
                               "Write down exactly what is said in this Bangla audio, in Bangla script. "
                               "Write numbers as words. Output only the transcript."],
        config=types.GenerateContentConfig(temperature=0))
    return resp.text.strip()


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--only", nargs="*", help="clip ids to generate (default: every wired clip)")
    p.add_argument("--model", help=f"TTS model (default: the first that works of {TTS_MODELS})")
    p.add_argument("--voice", default="Charon", help="prebuilt voice name (Charon is described as 'Informative')")
    p.add_argument("--no-check", action="store_true", help="skip the transcribe-back check")
    args = p.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    from dotenv import dotenv_values
    from google import genai

    env = dotenv_values(ROOT / ".env")
    if not env.get("GEMINI_API_KEY"):
        raise SystemExit("GEMINI_API_KEY is missing in .env.")
    client = genai.Client(api_key=env["GEMINI_API_KEY"])
    check_model = env.get("GEMINI_MODEL") or "gemini-3.5-flash-lite"

    with CLIPS_CSV.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fields, rows = list(reader.fieldnames), list(reader)
    if "voice" not in fields:
        fields.append("voice")
    by_id = {r["clip_id"]: r for r in rows}
    manifest = json.loads(MANIFEST.read_text("utf-8")) if MANIFEST.exists() else {}
    AUDIO.mkdir(exist_ok=True)

    models = [args.model] if args.model else TTS_MODELS
    summary = []
    for clip_id in (args.only or WIRED):
        row = by_id[clip_id]
        text = row["text_bn"]
        if text.strip().upper().startswith("TODO"):
            summary.append((clip_id, "SKIPPED: the text is still a placeholder"))
            continue
        pcm, used, error = None, None, None
        for model in models:
            for attempt in range(3):
                try:
                    pcm, used = synthesize(client, model, args.voice, text), model
                    break
                except Exception as e:   # quota, network, unsupported model
                    error = f"{type(e).__name__}: {str(e)[:160]}"
                    time.sleep(8 * (attempt + 1))
            if pcm:
                break
        if not pcm:
            summary.append((clip_id, f"FAILED: {error}"))
            continue
        mp3 = to_mp3(pcm)
        (AUDIO / f"{clip_id}.mp3").write_bytes(mp3)
        seconds = len(pcm) / (RATE * WIDTH * CHANNELS)
        entry = {"voice": VOICE_LABEL, "tts_model": used, "tts_voice": args.voice, "text_sha256": text_hash(text),
                 "duration_s": round(seconds, 1), "generated": dt.date.today().isoformat(), "bytes": len(mp3)}
        if not args.no_check:
            try:
                heard = transcribe(client, check_model, mp3)
                entry["transcribe_back_model"] = check_model
                entry["transcribe_back_similarity"] = round(difflib.SequenceMatcher(None, plain(text), plain(heard)).ratio(), 3)
            except Exception as e:
                entry["transcribe_back_similarity"] = None
                entry["transcribe_back_error"] = f"{type(e).__name__}: {str(e)[:120]}"
        manifest[clip_id] = entry
        row["duration_s"] = f"{seconds:.1f}"
        row["voice"] = VOICE_LABEL
        note = f"Audio: computer-generated voice (Gemini TTS {used}, voice {args.voice}, {entry['generated']}), not human-recorded."
        row["notes"] = (re.sub(r"\s*Audio: computer-generated voice[^.]*\.[^.]*\.", "", row.get("notes") or "").strip() + " " + note).strip()
        flags = [f"{seconds:.1f} s"] + (["LONGER THAN 25 s"] if seconds > 25 else [])
        flags.append(f"transcribe-back similarity {entry.get('transcribe_back_similarity')}")
        summary.append((clip_id, f"ok ({used}): " + ", ".join(flags)))
        time.sleep(3)

    for r in rows:
        r.setdefault("voice", "")
    with CLIPS_CSV.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    MANIFEST.write_text(json.dumps(manifest, indent=1, ensure_ascii=False, sort_keys=True) + "\n", "utf-8")
    for clip_id, status in summary:
        print(f"{clip_id:<14} {status}")
    print("A native speaker must listen to every clip while reading the on-screen text.")
    return 0 if all(s.startswith(("ok", "SKIPPED")) for _, s in summary) else 1


if __name__ == "__main__":
    sys.exit(main())

"""Cache the parse of the team's scripted demo clip, so the demo works even when the Gemini quota is gone.

  python scripts/cache_voice.py <audio_file> [--model gemini-3.8-flash]

Use only for a clip recorded by a teammate who agrees. In the video and live pitch, UPLOAD that saved
file instead of recording live: the cache is keyed by the file's bytes, so only the same file hits it.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass

from kombish import voice  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("audio_file", type=Path)
    p.add_argument("--model", help="overrides GEMINI_MODEL for this call")
    args = p.parse_args(argv)

    data = args.audio_file.read_bytes()
    if len(data) > voice.MAX_BYTES:
        raise SystemExit(f"{args.audio_file} is over {voice.MAX_BYTES} bytes.")
    mime = voice.AUDIO_MIME.get(args.audio_file.suffix.lower(), "audio/wav")
    vq = voice.call_gemini(data, mime, args.model)
    if vq is None:
        raise SystemExit("Gemini returned nothing usable (error, quota or invalid JSON). Nothing cached.")
    print(json.dumps(vq.model_dump(), ensure_ascii=False, indent=2))   # terminal only
    if input("Store this parse in data/voice_cache.json? [y/N] ").strip().lower() != "y":
        print("Not stored.")
        return 0
    cache = voice._load_cache()
    cache[hashlib.sha256(data).hexdigest()] = vq.model_dump()
    voice.CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False, indent=2, sort_keys=True) + "\n", "utf-8")
    print(f"Stored. Upload this exact file in the video and pitch: {args.audio_file}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

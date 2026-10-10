"""Score Gemini voice parsing on the team's test notes (gate G3).

  python scripts/score_voice.py --dir voice_tests --model gemini-3.5-flash-lite
  python scripts/score_voice.py --dir voice_tests --model gemini-3.8-flash

voice_tests/expected.csv has columns: file, expected_symptoms (semicolon-separated enum values,
e.g. brown_spots;yellowing). Transcripts are printed to the terminal only, never written to a file.
"""
from __future__ import annotations

import argparse
import csv
import statistics
import sys
import time
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
    p.add_argument("--dir", type=Path, default=ROOT / "voice_tests")
    p.add_argument("--model", default=None, help="default: GEMINI_MODEL from the environment")
    p.add_argument("--sleep", type=float, default=2.0, help="seconds between calls (free-tier limits are unpublished)")
    args = p.parse_args(argv)

    with (args.dir / "expected.csv").open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise SystemExit("expected.csv has no rows.")

    correct, latencies, failures = 0, [], 0
    print(f"model: {args.model or '(GEMINI_MODEL)'} | notes: {len(rows)}")
    print(f"{'file':<28}{'ok':<5}{'ms':>7}  {'conf':<7}{'stage':<11}returned | expected")
    for i, row in enumerate(rows):
        path = args.dir / row["file"].strip()
        expected = {s.strip() for s in row["expected_symptoms"].split(";") if s.strip()}
        data = path.read_bytes()
        mime = voice.AUDIO_MIME.get(path.suffix.lower(), "audio/wav")
        t0 = time.perf_counter()
        vq = voice.call_gemini(data, mime, args.model)
        ms = (time.perf_counter() - t0) * 1000
        latencies.append(ms)
        if vq is None:
            failures += 1
            print(f"{path.name:<28}{'ERR':<5}{ms:>7.0f}  call failed (error, quota or invalid JSON) | "
                  f"{';'.join(sorted(expected))}")
        else:
            ok = set(vq.symptoms) == expected
            correct += ok
            print(f"{path.name:<28}{'yes' if ok else 'NO':<5}{ms:>7.0f}  {vq.confidence:<7}{vq.growth_stage:<11}"
                  f"{';'.join(sorted(vq.symptoms))} | {';'.join(sorted(expected))}")
            print(f"    transcript: {vq.transcript_bn}")
        if i < len(rows) - 1:
            time.sleep(args.sleep)
    print(f"\nscore: {correct} / {len(rows)} | failed calls: {failures} | "
          f"median latency: {statistics.median(latencies):.0f} ms")
    return 0


if __name__ == "__main__":
    sys.exit(main())

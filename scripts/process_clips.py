"""Turn the human recordings in raw_audio/ into audio/<clip_id>.mp3 (needs ffmpeg and ffprobe on PATH).

  python scripts/process_clips.py --raw raw_audio --out audio

Each clip must say exactly the reviewed text_bn in data/clips.csv. This script trims silence at both ends,
loudness-normalises, converts to mono 44.1 kHz MP3 at 80 kbps and writes the duration into clips.csv.
It never generates speech.
"""
from __future__ import annotations

import argparse
import csv
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLIPS_CSV = ROOT / "data" / "clips.csv"
WIRED = ["blb", "blast", "safety", "healthy", "not_sure", "consent", "voice_failed"]
RAW_EXT = [".m4a", ".mp3", ".wav", ".ogg", ".aac"]
FILTER = ("silenceremove=start_periods=1:start_threshold=-50dB,areverse,"
          "silenceremove=start_periods=1:start_threshold=-50dB,areverse,loudnorm")
MAX_SECONDS, MIN_SECONDS, MAX_BYTES = 25.0, 2.0, 1_000_000


def find_raw(raw: Path, clip_id: str) -> Path | None:
    for ext in RAW_EXT:
        matches = [p for p in raw.glob(f"{clip_id}.*") if p.suffix.lower() == ext]
        if matches:
            return matches[0]
    return None


def convert(src: Path, dest: Path) -> None:
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-af", FILTER,
                    "-ac", "1", "-ar", "44100", "-codec:a", "libmp3lame", "-b:a", "80k", str(dest)], check=True)


def duration_of(path: Path) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                         check=True, capture_output=True, text=True).stdout
    return float(out.strip())


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--raw", type=Path, default=ROOT / "raw_audio")
    p.add_argument("--out", type=Path, default=ROOT / "audio")
    args = p.parse_args(argv)
    for tool in ("ffmpeg", "ffprobe"):
        if shutil.which(tool) is None:
            raise SystemExit(f"{tool} is not on PATH. Install ffmpeg first (step 16).")
    args.out.mkdir(parents=True, exist_ok=True)

    with CLIPS_CSV.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fields, rows = reader.fieldnames, list(reader)
    by_id = {r["clip_id"]: r for r in rows}

    if "voice" not in fields:
        fields.append("voice")
    for r in rows:
        r.setdefault("voice", "")
    summary, missing, replaced = [], 0, []
    for clip_id in WIRED:
        if by_id[clip_id]["review_status"] != "reviewed":
            print(f"WARNING: {clip_id} text is not reviewed yet (step 06). Recording unreviewed text wastes the take.")
        src = find_raw(args.raw, clip_id)
        if src is None:
            missing += 1
            summary.append((clip_id, "-", "-", f"MISSING: no {args.raw.name}/{clip_id}.* file"))
            continue
        dest = args.out / f"{clip_id}.mp3"
        try:
            convert(src, dest)
            seconds = duration_of(dest)
        except (subprocess.CalledProcessError, ValueError) as e:
            summary.append((clip_id, "-", "-", f"FAILED: {e}"))
            continue
        size = dest.stat().st_size
        by_id[clip_id]["duration_s"] = f"{seconds:.1f}"
        by_id[clip_id]["voice"] = "human"   # replaces a computer-generated clip and its on-screen label
        replaced.append(clip_id)
        warnings = []
        if seconds > MAX_SECONDS:
            warnings.append(f"longer than {MAX_SECONDS:.0f} s")
        if seconds < MIN_SECONDS:
            warnings.append(f"shorter than {MIN_SECONDS:.0f} s")
        if size > MAX_BYTES:
            warnings.append("larger than 1 MB")
        summary.append((clip_id, f"{seconds:.1f} s", f"{size / 1000:.0f} kB",
                        "WARNING: " + ", ".join(warnings) if warnings else "ok"))

    with CLIPS_CSV.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    manifest_path = args.out / "clips_manifest.json"   # text-to-speech records; a human clip no longer has one
    if replaced and manifest_path.exists():
        import json

        manifest = {k: v for k, v in json.loads(manifest_path.read_text("utf-8")).items() if k not in replaced}
        manifest_path.write_text(json.dumps(manifest, indent=1, ensure_ascii=False, sort_keys=True) + "\n", "utf-8")
    print(f"\n{'clip_id':<14}{'duration':<10}{'size':<9}status")
    for row in summary:
        print(f"{row[0]:<14}{row[1]:<10}{row[2]:<9}{row[3]}")
    print("\nNow listen to every MP3 while reading the on-screen text in the app. It must match word for word.")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())

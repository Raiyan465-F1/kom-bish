"""Run the team's own photos and junk photos through the real app path (classifier + rule engine).

  python training/eval_own_photos.py        # run in .venv

Reads own_photos/healthy_looking/, own_photos/symptomatic/ and junk_photos/ (all git-ignored). Writes
aggregate counts only to training/results/own_photos.json: no file names, no image data.
Own-photo labels are "healthy-looking" vs "symptomatic", not diagnoses, so no accuracy is claimed.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from collections import Counter
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass

from kombish import classifier, rules  # noqa: E402

IMG_EXT = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
SPRAY_RELEVANT = {"R1_BLB", "R2_BLAST"}


def run_folder(folder: Path, meta: dict) -> list[tuple[str, str, str]]:
    """Return (rule_id, decision, printable line) for every image in the folder."""
    results = []
    for path in sorted(q for q in folder.iterdir() if q.suffix.lower() in IMG_EXT):
        with Image.open(path) as im:
            pred = classifier.predict(im)
        adv = rules.decide(pred.label, pred.conf, pred.margin >= meta["margin"], None, None,
                           threshold=meta["threshold"])
        results.append((adv.rule_id, adv.decision,
                        f"  {path.name:<40} {pred.label:<22} conf={pred.conf:.3f} margin={pred.margin:.3f} "
                        f"-> {adv.rule_id}"))
    return results


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--own", type=Path, default=ROOT / "own_photos")
    p.add_argument("--junk", type=Path, default=ROOT / "junk_photos")
    p.add_argument("--out", type=Path, default=ROOT / "training" / "results" / "own_photos.json")
    args = p.parse_args(argv)

    meta = classifier.meta()
    summary = {"date": dt.date.today().isoformat(), "model": meta.get("model"),
               "temperature": meta["temperature"], "threshold": meta["threshold"], "margin": meta["margin"]}
    sets = {"healthy_looking": args.own / "healthy_looking", "symptomatic": args.own / "symptomatic",
            "junk": args.junk}
    for name, folder in sets.items():
        if not folder.is_dir():
            raise SystemExit(f"Missing folder: {folder} (step 19).")
        results = run_folder(folder, meta)
        print(f"\n{name} ({folder}), n={len(results)}")   # per-image lines stay on the terminal
        for _, _, line in results:
            print(line)
        entry = {"n": len(results), "rule_counts": dict(sorted(Counter(r for r, _, _ in results).items()))}
        if name == "healthy_looking":
            entry["false_trigger_n"] = sum(r in SPRAY_RELEVANT for r, _, _ in results)
        if name == "junk":
            entry["refused_n"] = sum(d == "consult_officer" for _, d, _ in results)
        summary[name] = entry

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(summary, indent=1), "utf-8")
    print(f"\nWrote aggregate counts to {args.out}")
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

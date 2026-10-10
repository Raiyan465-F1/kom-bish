"""Live check of the anonymous log (needs LOG_REPO and HF_TOKEN in .env).

  python scripts/check_logging.py            # write three fake consultations, wait for the upload
  python scripts/check_logging.py --counts   # later, in a fresh process: read the counters back
"""
from __future__ import annotations

import argparse
import os
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

from kombish import logging_store  # noqa: E402

FAKE = [("R1_BLB", "bacterial_leaf_blight", "no_insecticide_fix_fertiliser"),
        ("R3_HEALTHY", "healthy", "no_spray_monitor"),
        ("R5_ABSTAIN", "blast", "consult_officer")]


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--counts", action="store_true", help="only read the counters back from the dataset repo")
    p.add_argument("--wait", type=int, default=7, help="minutes to keep running so the scheduler can upload")
    args = p.parse_args(argv)

    repo, token = os.getenv("LOG_REPO"), os.getenv("HF_TOKEN")
    if not (repo and token):
        print("LOG_REPO or HF_TOKEN is missing in .env. Logging runs in local-only mode (logs/).")
    if args.counts:
        logging_store.bootstrap_counts()
        print("counts after bootstrap:", logging_store.counts())
        return 0

    for rule_id, label, decision in FAKE:
        rid = logging_store.log_consult({
            "app_version": "test", "predicted_class": label, "confidence": 0.0, "probs": {}, "abstained": False,
            "voice_used": False, "voice_symptoms": None, "voice_confidence": None, "growth_stage": None,
            "planning_to_spray": None, "rule_id": rule_id, "decision": decision, "latency_ms": 0,
            "consent_version": "test", "feedback": None})
        print(f"logged {rule_id} as {rid}")
    print(f"local file: {logging_store.LOG_FILE}")
    if not (repo and token):
        return 0
    print(f"CommitScheduler uploads every 5 minutes. Keeping this process alive for {args.wait} minutes...")
    time.sleep(args.wait * 60)
    print(f"Now open https://huggingface.co/datasets/{repo}/tree/main/data and look for "
          f"{logging_store.LOG_FILE.name} with three lines (allow up to about 10 minutes in total).")
    print("Then run: python scripts/check_logging.py --counts")
    return 0


if __name__ == "__main__":
    sys.exit(main())

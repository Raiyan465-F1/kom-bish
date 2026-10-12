"""Anonymous consultation log.

Appends JSON Lines to a private HF dataset repo through huggingface_hub.CommitScheduler
(every=5 minutes, append-only, UUID file names). Never stores the photo, the audio, the
transcript, IP addresses, names or phone numbers. Up to 5 minutes can be lost on a crash.

The public counters leave out the team's own test traffic (smoke tests, live checks, screenshots). Those
records stay in the log; scripts/tag_test_records.py lists their ids in TEST_TAGS, and the counters skip
them when the app starts.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import threading
import uuid
from pathlib import Path

from kombish import rules

ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = ROOT / "logs"
LOG_FILE = LOG_DIR / f"consults_{uuid.uuid4().hex}.jsonl"
TEST_TAGS = "tags/test_records.json"   # in the log dataset: {"<record id>": "<why it is test traffic>"}

CONSULT_KEYS = {"app_version", "predicted_class", "confidence", "probs", "abstained", "voice_used",
                "voice_symptoms", "voice_confidence", "growth_stage", "planning_to_spray", "rule_id",
                "decision", "latency_ms", "consent_version", "feedback"}

_lock = threading.Lock()
_scheduler = None
_counts = {"total": 0, "no_spray": 0, "correct_use": 0, "referrals": 0, "sprays_avoided": 0}


def _get_scheduler():
    """Create the CommitScheduler lazily (no background thread during tests or without secrets)."""
    global _scheduler
    if _scheduler is None and os.getenv("HF_TOKEN") and os.getenv("LOG_REPO"):
        from huggingface_hub import CommitScheduler
        LOG_DIR.mkdir(exist_ok=True)
        _scheduler = CommitScheduler(repo_id=os.environ["LOG_REPO"], repo_type="dataset",
                                     folder_path=LOG_DIR, path_in_repo="data", every=5,
                                     private=True, token=os.environ["HF_TOKEN"],
                                     allow_patterns=["*.jsonl"])
    return _scheduler


def _append(record: dict) -> None:
    LOG_DIR.mkdir(exist_ok=True)
    line = json.dumps(record, ensure_ascii=False) + "\n"
    sched = _get_scheduler()
    with (sched.lock if sched else _lock):
        with LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(line)


def _bump(rec: dict) -> None:
    rid = rec.get("rule_id")
    with _lock:
        _counts["total"] += 1
        if rid in rules.NO_SPRAY_RULES:
            _counts["no_spray"] += 1
            if rec.get("planning_to_spray") is True:
                _counts["sprays_avoided"] += 1
        elif rid in rules.CORRECT_USE_RULES:
            _counts["correct_use"] += 1
        elif rid in rules.REFERRAL_RULES:
            _counts["referrals"] += 1


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def log_consult(record: dict) -> str:
    extra = set(record) - CONSULT_KEYS
    if extra:
        raise ValueError(f"Refusing to log unexpected keys: {sorted(extra)}")
    rec = {"id": uuid.uuid4().hex, "type": "consultation", "ts_utc": _now(), **record}
    _append(rec)
    _bump(rec)
    return rec["id"]


def log_feedback(ref_id: str, feedback: str = "looks_wrong") -> None:
    _append({"id": uuid.uuid4().hex, "type": "feedback", "ts_utc": _now(),
             "ref_id": ref_id, "feedback": feedback})


def counts() -> dict:
    with _lock:
        return dict(_counts)


def _test_ids(path: Path) -> set[str]:
    """Ids of records tagged as test traffic. A missing or unreadable tag file excludes nothing."""
    try:
        return set(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        return set()


def bootstrap_counts() -> None:
    """Seed counters from the persistent log (dataset repo if configured, else local logs/).

    Records tagged as test traffic are left out. A record tagged after startup is left out from the next start.
    """
    files: list[Path] = []
    tagged: set[str] = set()
    repo, token = os.getenv("LOG_REPO"), os.getenv("HF_TOKEN")
    if repo and token:
        try:
            from huggingface_hub import snapshot_download
            local = snapshot_download(repo_id=repo, repo_type="dataset",
                                      allow_patterns=["data/*.jsonl", TEST_TAGS], token=token)
            files = sorted(Path(local, "data").glob("*.jsonl"))
            tagged = _test_ids(Path(local, TEST_TAGS))
        except Exception as exc:  # empty or new repo, network error: start from zero
            print(f"[logging_store] bootstrap skipped: {exc}")
    else:
        files = sorted(LOG_DIR.glob("*.jsonl"))
        tagged = _test_ids(LOG_DIR / Path(TEST_TAGS).name)
    with _lock:
        for k in _counts:
            _counts[k] = 0
    for path in files:
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            # scripts/check_logging.py writes app_version="test" records; they are not consultations.
            if (rec.get("type") == "consultation" and rec.get("app_version") != "test"
                    and rec.get("id") not in tagged):
                _bump(rec)

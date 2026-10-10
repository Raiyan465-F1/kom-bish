# 14 — Persistent anonymous logging and dashboard counters

**Goal:** Log every consultation as one anonymous JSON line to a private HF dataset repo, and seed the dashboard counters from that log at startup so they survive restarts.
**Who:** Both. The human (B) creates the dataset repo and a scoped token; Claude Code writes `kombish/logging_store.py` and tests.
**When:** Sunday 11 October, evening.
**Covers master-plan step:** S15 (instruction file CC-09).

Context: A free Space's disk is ephemeral, and Render's free disk is no better, so logs must leave the server. `huggingface_hub.CommitScheduler` is the official pattern for pushing "user feedback on a deployed Space" to a dataset repo: it appends to a UUID-named file under `scheduler.lock`, commits every 5 minutes or more, skips empty commits and retries failed uploads silently. Rules: never delete or overwrite files in the watched folder; `every` ≥ 5. Up to 5 minutes of logs can be lost on a crash; acceptable for a prototype. The log never holds the photo, the audio, the transcript, an IP address, a name or a phone number.

## Prerequisites

```bash
source .venv/bin/activate
python -c "from kombish.logging_store import log_consult, log_feedback, counts, bootstrap_counts"   # [Run step 13.]
python -c "import huggingface_hub; assert huggingface_hub.__version__ == '2.2.0', huggingface_hub.__version__"
```
For the live check: `.env` must contain `LOG_REPO=<hf-user>/kom-bish-logs` and `HF_TOKEN=...`. If missing, do the code and local tests, then stop and ask the human to finish "Human actions".

## Instructions for Claude Code

### 1. `kombish/logging_store.py` (replace the minimal version; keep the function names)

```python
"""Anonymous consultation log.

Appends JSON Lines to a private HF dataset repo through huggingface_hub.CommitScheduler
(every=5 minutes, append-only, UUID file names). Never stores the photo, the audio, the
transcript, IP addresses, names or phone numbers. Up to 5 minutes can be lost on a crash.
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


def bootstrap_counts() -> None:
    """Seed counters from the persistent log (dataset repo if configured, else local logs/)."""
    files: list[Path] = []
    repo, token = os.getenv("LOG_REPO"), os.getenv("HF_TOKEN")
    if repo and token:
        try:
            from huggingface_hub import snapshot_download
            local = snapshot_download(repo_id=repo, repo_type="dataset",
                                      allow_patterns=["data/*.jsonl"], token=token)
            files = sorted(Path(local, "data").glob("*.jsonl"))
        except Exception as exc:  # empty or new repo, network error: start from zero
            print(f"[logging_store] bootstrap skipped: {exc}")
    else:
        files = sorted(LOG_DIR.glob("*.jsonl"))
    with _lock:
        for k in _counts:
            _counts[k] = 0
    for path in files:
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if rec.get("type") == "consultation":
                _bump(rec)
```

Check at run time: `snapshot_download` was **not** inspected in our research. Run `python -c "import inspect, huggingface_hub as h; print(inspect.signature(h.snapshot_download))"` and confirm `repo_type`, `allow_patterns` and `token` exist; if not, use `HfApi().list_repo_files(...)` plus `hf_hub_download(...)` per file. The `CommitScheduler` signature in 2.2.0 was verified: `CommitScheduler(*, repo_id, folder_path, every=5, path_in_repo=None, repo_type=None, revision=None, private=None, token=None, allow_patterns=None, ignore_patterns=None, squash_history=False, hf_api=None)`.

### 2. `tests/test_logging.py` (local mode; unset `HF_TOKEN`/`LOG_REPO` with `monkeypatch.delenv`, and point `LOG_DIR`/`LOG_FILE` at `tmp_path`)

- `log_consult` returns a 32-char hex id; the file has one valid JSON line with `type="consultation"`, `id`, `ts_utc` and only allowed keys.
- A record with a key like `"photo"`, `"transcript"`, `"phone"` raises `ValueError`.
- `log_feedback` writes a separate `type="feedback"` line with `ref_id`; it does not change `counts()["total"]`.
- Counters: R1 with `planning_to_spray=True` → `no_spray` and `sprays_avoided` both +1; R2 → `correct_use`; R5 → `referrals`.
- Restart simulation: reset `_counts` to zero, call `bootstrap_counts()`, and get the same counts back.

### 3. Live check script `scripts/check_logging.py`

Loads `.env`, logs three fake consultations through `log_consult` (rule_ids R1_BLB, R3_HEALTHY, R5_ABSTAIN, `app_version="test"`), prints the local file path, and tells the human to wait up to about 10 minutes and then look in the dataset repo under `data/`. Then it calls `bootstrap_counts()` (in a fresh process, after the upload) and prints `counts()`.

### 4. Run

```bash
source .venv/bin/activate
pytest -q
python scripts/check_logging.py         # needs LOG_REPO and HF_TOKEN in .env
```

## Human actions

- **HUMAN (B):** on Hugging Face create a **dataset** repo `kom-bish-logs`, **Private**.
- **HUMAN (B):** create a **fine-grained** token with **write access to `kom-bish-logs` only** (Settings → Access Tokens). Put it in `.env` as `HF_TOKEN=...` and set `LOG_REPO=<hf-user>/kom-bish-logs`. Never commit `.env`. Step 17 adds the same token as a host secret.
- **HUMAN:** run `python scripts/check_logging.py`, wait about 10 minutes, open the dataset repo and confirm a `data/consults_<uuid>.jsonl` file with three lines appears.
- **HUMAN:** run `python app.py`, do two consultations, stop the app, wait 5–10 minutes, start it again and confirm the dashboard counts include them.
- **HUMAN:** commit: `git add -A && git commit -m "step 14: logging store" && git push`.

## Done when

- `pytest -q` passes, including `tests/test_logging.py`.
- Three test consultations appear as JSONL in the private dataset within about 10 minutes.
- Dashboard counters survive an app restart (seeded from the dataset).
- No record anywhere contains a photo, audio, transcript, IP, name or phone number.

## If it fails

- **Nothing appears in the dataset:** check the token has write access to that exact repo and that `LOG_REPO` matches. CommitScheduler retries silently, so also check the app's console for errors. Wait at least one full 5-minute cycle after the first write.
- **401/403 from the Hub:** the token is scoped to the wrong repo or is read-only. Create a new fine-grained token.
- **A visible live sheet is wanted instead:** Google Sheets via gspread works but adds about 20 minutes of Google Cloud service-account setup and a synchronous network call per request. Not recommended this week.

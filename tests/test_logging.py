import json

import pytest

from kombish import logging_store

SECTION_6_CONSULT_KEYS = {
    "id", "type", "ts_utc", "app_version", "predicted_class", "confidence", "probs", "abstained",
    "voice_used", "voice_symptoms", "voice_confidence", "growth_stage", "planning_to_spray", "rule_id",
    "decision", "latency_ms", "consent_version", "feedback",
}
SECTION_6_FEEDBACK_KEYS = {"id", "type", "ts_utc", "ref_id", "feedback"}


def record(rule_id: str, planning=None) -> dict:
    return {"app_version": "test", "predicted_class": "healthy", "confidence": 0.9,
            "probs": {"healthy": 0.9}, "abstained": False, "voice_used": False, "voice_symptoms": None,
            "voice_confidence": None, "growth_stage": None, "planning_to_spray": planning,
            "rule_id": rule_id, "decision": "x", "latency_ms": 5, "consent_version": "v", "feedback": None}


@pytest.fixture
def store(tmp_path, monkeypatch):
    """Local mode: no token, no repo, log file under tmp_path, counters at zero."""
    monkeypatch.delenv("HF_TOKEN", raising=False)
    monkeypatch.delenv("LOG_REPO", raising=False)
    monkeypatch.setattr(logging_store, "LOG_DIR", tmp_path)
    monkeypatch.setattr(logging_store, "LOG_FILE", tmp_path / "consults_test.jsonl")
    monkeypatch.setattr(logging_store, "_scheduler", None)
    monkeypatch.setattr(logging_store, "_counts", dict.fromkeys(logging_store._counts, 0))
    return logging_store


def lines(store) -> list[dict]:
    return [json.loads(line) for line in store.LOG_FILE.read_text("utf-8").splitlines()]


def test_log_consult_writes_one_allowed_line(store):
    rid = store.log_consult(record("R3_HEALTHY"))
    assert len(rid) == 32 and int(rid, 16) >= 0
    (rec,) = lines(store)
    assert rec["id"] == rid and rec["type"] == "consultation" and rec["ts_utc"].endswith("+00:00")
    assert set(rec) == SECTION_6_CONSULT_KEYS


def test_consult_keys_match_claude_md(store):
    assert store.CONSULT_KEYS | {"id", "type", "ts_utc"} == SECTION_6_CONSULT_KEYS


@pytest.mark.parametrize("key", ["photo", "audio", "transcript", "transcript_bn", "ip", "name", "phone"])
def test_personal_data_keys_are_refused(store, key):
    with pytest.raises(ValueError):
        store.log_consult({**record("R3_HEALTHY"), key: "x"})
    assert not store.LOG_FILE.exists()
    assert store.counts()["total"] == 0


def test_feedback_is_a_separate_record(store):
    rid = store.log_consult(record("R1_BLB"))
    store.log_feedback(rid)
    consult, feedback = lines(store)
    assert set(feedback) == SECTION_6_FEEDBACK_KEYS
    assert feedback["type"] == "feedback" and feedback["ref_id"] == rid and feedback["feedback"] == "looks_wrong"
    assert store.counts()["total"] == 1


def test_counters(store):
    store.log_consult(record("R1_BLB", planning=True))
    assert store.counts() == {"total": 1, "no_spray": 1, "correct_use": 0, "referrals": 0, "sprays_avoided": 1}
    store.log_consult(record("R3_HEALTHY", planning=False))
    store.log_consult(record("R2_BLAST", planning=True))
    store.log_consult(record("R5_ABSTAIN"))
    store.log_consult(record("R4_OTHER"))
    store.log_consult(record("R6_VOICE_REDFLAG"))
    assert store.counts() == {"total": 6, "no_spray": 2, "correct_use": 1, "referrals": 3, "sprays_avoided": 1}


def test_bootstrap_ignores_check_script_records(store):
    store.log_consult({**record("R1_BLB", True), "app_version": "0.1.0"})
    store.log_consult({**record("R3_HEALTHY", True), "app_version": "test"})   # written by scripts/check_logging.py
    store.bootstrap_counts()
    assert store.counts() == {"total": 1, "no_spray": 1, "correct_use": 0, "referrals": 0, "sprays_avoided": 1}


def test_bootstrap_restores_counts_after_restart(store):
    for rule_id, planning in [("R1_BLB", True), ("R2_BLAST", None), ("R5_ABSTAIN", None)]:
        rid = store.log_consult({**record(rule_id, planning), "app_version": "0.1.0"})
    store.log_feedback(rid)
    with store.LOG_FILE.open("a", encoding="utf-8") as f:
        f.write("not json\n")
    before = store.counts()
    for k in store._counts:
        store._counts[k] = 0
    store.bootstrap_counts()
    assert store.counts() == before
    assert before["total"] == 3

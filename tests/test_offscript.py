"""20 scripted consultations through the real app path. Every sentence must come from the CSVs.

run_offscript() is also called by training/make_eval_report.py, which reports its counts.
"""
import csv
import re
from pathlib import Path

from PIL import Image

import app as app_module
from kombish import texts
from kombish.classifier import Prediction
from kombish.voice import VoiceQuery
from tests.test_rules import FORBIDDEN, FORBIDDEN_TOKENS, TOKEN_SPLIT, nfc

ROOT = Path(__file__).resolve().parent.parent
T, MARGIN = 0.7, 0.2
CASES_BY_WIDTH = {   # image width -> (label, conf, margin)
    201: ("bacterial_leaf_blight", 0.95, 0.9), 202: ("blast", 0.95, 0.9), 203: ("healthy", 0.95, 0.9),
    204: ("other", 0.95, 0.9), 205: ("bacterial_leaf_blight", 0.40, 0.3), 206: ("blast", 0.40, 0.3),
    207: ("healthy", 0.80, 0.05),   # confident enough, but top-1 and top-2 are too close
}


def _voice(symptom: str, confidence: str) -> VoiceQuery:
    return VoiceQuery(transcript_bn="x", symptoms=[symptom], growth_stage="unknown",
                      farmer_wants_to_spray=True, confidence=confidence)


FAILED = "voice failed"
# (expected rule, consent, width or None, voice result / FAILED / None, planning answer)
CONSULTATIONS = [
    ("R1_BLB", True, 201, None, texts.YES_BN), ("R1_BLB", True, 201, None, texts.NO_BN),
    ("R1_BLB", True, 201, None, None),
    ("R2_BLAST", True, 202, None, texts.YES_BN), ("R2_BLAST", True, 202, None, texts.NO_BN),
    ("R2_BLAST", True, 202, None, None),
    ("R3_HEALTHY", True, 203, None, texts.YES_BN), ("R3_HEALTHY", True, 203, None, texts.NO_BN),
    ("R3_HEALTHY", True, 203, None, None),
    ("R4_OTHER", True, 204, None, texts.YES_BN), ("R4_OTHER", True, 204, None, None),
    ("R5_ABSTAIN", True, 205, None, texts.YES_BN), ("R5_ABSTAIN", True, 206, None, None),
    ("R5_ABSTAIN", True, 207, None, texts.NO_BN),
    ("R6_VOICE_REDFLAG", True, 203, _voice("insects_seen", "high"), texts.YES_BN),
    ("R6_VOICE_REDFLAG", True, 203, _voice("hopper_burn", "medium"), None),
    ("R3_HEALTHY", True, 203, FAILED, None), ("R1_BLB", True, 201, FAILED, texts.YES_BN),
    (None, True, None, None, None),            # no photo
    (None, False, 202, None, texts.YES_BN),    # no consent
]


def _fake_predict(img):
    label, conf, margin = CASES_BY_WIDTH[img.size[0]]
    return Prediction(label, conf, {label: conf}, margin, conf < T or margin < MARGIN)


def _read(name: str) -> list[dict]:
    with (ROOT / "data" / name).open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def allowed_segments() -> set[str]:
    """Built straight from the CSVs and texts.py, independently of kombish.rules."""
    allowed = set()
    for row in _read("rules.csv"):
        allowed.add(f"## {row['headline_bn']}")
        if row["sources"]:
            allowed.add(f"*{texts.SOURCE_LABEL_BN}: {row['sources']}*")
    for disease in texts.DISEASE_NAME_BN.values():
        allowed.add(texts.CONFIRM_TEMPLATE_BN.format(disease=disease))
    allowed.update(row["text_bn"] for row in _read("clips.csv"))
    return {nfc(s) for s in allowed}


def run_offscript() -> dict:
    allowed = allowed_segments()
    banned_tokens = {nfc(t) for t in FORBIDDEN_TOKENS}
    logged: list[dict] = []
    state = {"voice": None}

    def log(record):
        logged.append(record)
        return f"id{len(logged)}"

    advise = app_module.make_advise(_fake_predict, lambda: {"threshold": T, "margin": MARGIN},
                                    lambda path: state["voice"], log, True)
    offscript, doses, wrong_rule, details = 0, 0, 0, []
    for expected_rule, consent, width, voice, planning in CONSULTATIONS:
        state["voice"] = None if voice in (None, FAILED) else voice
        before = len(logged)
        image = Image.new("RGB", (width, 60), "green") if width else None
        answer = advise(consent, image, "note.wav" if voice is not None else None, planning)[0]
        segments = [nfc(s) for s in re.split(r"\n\s*\n", answer) if s.strip()]
        bad_segments = [s for s in segments if s not in allowed]
        low = nfc(answer).lower()
        bad_terms = [t for t in FORBIDDEN if nfc(t).lower() in low]
        bad_terms += sorted(set(TOKEN_SPLIT.split(low)) & banned_tokens)
        rule = logged[-1]["rule_id"] if len(logged) > before else None
        offscript += bool(bad_segments)
        doses += bool(bad_terms)
        wrong_rule += rule != expected_rule
        if bad_segments or bad_terms or rule != expected_rule:
            details.append({"expected_rule": expected_rule, "rule": rule, "bad_segments": bad_segments,
                            "bad_terms": bad_terms})
    return {"n": len(CONSULTATIONS), "offscript_failures": offscript, "invented_doses": doses,
            "wrong_rule": wrong_rule, "details": details}


def test_twenty_consultations_stay_on_script():
    result = run_offscript()
    assert result["n"] == 20
    assert result["wrong_rule"] == 0, result["details"]
    assert result["offscript_failures"] == 0, result["details"]
    assert result["invented_doses"] == 0, result["details"]


def test_allowed_set_catches_an_invented_sentence():
    assert nfc("## Spray 5 ml per litre") not in allowed_segments()

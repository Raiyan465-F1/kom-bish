"""One definition of the outcome of a photo, shared by every evaluation script that uses the app's code path.

classifier confident: the prediction passes the thresholds and margin (a confident "other" is included).
advice given:         a confident healthy answer: the only answer the farmer gets from the photo alone.
BLB question asked:   a confident BLB prediction. The app asks the BLB question and gives the BLB answer only
                      on "yes", so with the question unanswered this is NOT advice.
blast question asked: a confident blast prediction. The app asks the lesion-shape question and gives the
                      spray answer only on "yes", so with the question unanswered this is NOT advice.
referred:             everything else (not confident, or a confident "other").

Until 12 Oct 2026 the BLB answer was given without a question, so older result files count confident BLB
predictions under "advice given".
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from kombish import classifier, rules  # noqa: E402

CLASSES = ["bacterial_leaf_blight", "blast", "healthy", "other"]
ADVICE_RULES = {"R3_HEALTHY": "healthy"}
QUESTION_RULES = {"R0_CONFIRM_BLB": "blb_question", "R0_CONFIRM_BLAST": "blast_question"}
QUESTION_CLASS = {"blb_question": "bacterial_leaf_blight", "blast_question": "blast"}


def photo_outcome(img: Image.Image, m: dict) -> dict:
    """The photo-only decision of the app: kombish.classifier.predict, then kombish.rules.decide."""
    pred = classifier.predict(img)
    adv = rules.decide(pred.label, pred.conf, pred.margin >= m["margin"], None, None, threshold=m["threshold"],
                       blast_threshold=m.get("blast_threshold"), blb_threshold=m.get("blb_threshold"),
                       blast_confirmed=None, blb_confirmed=None)   # both confirmation questions are unanswered
    outcome = QUESTION_RULES.get(adv.rule_id) or ("advice" if adv.rule_id in ADVICE_RULES else "referred")
    return {"predicted": pred.label, "confidence": round(pred.conf, 4), "margin": round(pred.margin, 4),
            "classifier_confident": not pred.abstained, "rule_id": adv.rule_id, "outcome": outcome,
            "advice": ADVICE_RULES.get(adv.rule_id)}


def tally(rows: list[dict]) -> dict:
    """rows: photo_outcome() dicts with a "true" key (one of CLASSES)."""
    def count(sel) -> int:
        return sum(1 for r in rows if sel(r))

    def asked(question: str, on_true: bool | None = None) -> int:
        cls = QUESTION_CLASS[question]
        return count(lambda r: r["outcome"] == question and (on_true is None or (r["true"] == cls) == on_true))

    by_true = {}
    for c in CLASSES:
        mine = [r for r in rows if r["true"] == c]
        by_true[c] = {"n": len(mine),
                      "right_advice": sum(r["advice"] == c for r in mine),
                      "wrong_advice": sum(r["outcome"] == "advice" and r["advice"] != c for r in mine),
                      "blb_question_asked": sum(r["outcome"] == "blb_question" for r in mine),
                      "blast_question_asked": sum(r["outcome"] == "blast_question" for r in mine),
                      "referred": sum(r["outcome"] == "referred" for r in mine)}
    return {"n": len(rows),
            "classifier_confident": count(lambda r: r["classifier_confident"]),
            "advice_given": count(lambda r: r["outcome"] == "advice"),
            "right_advice": count(lambda r: r["outcome"] == "advice" and r["advice"] == r["true"]),
            "wrong_advice": count(lambda r: r["outcome"] == "advice" and r["advice"] != r["true"]),
            "blb_question_asked": asked("blb_question"),
            "blb_question_on_true_blb": asked("blb_question", True),
            # a wrong "no insecticide needed, fix the fertiliser" if the farmer answers yes:
            "blb_question_on_other_classes": asked("blb_question", False),
            "blast_question_asked": asked("blast_question"),
            "blast_question_on_true_blast": asked("blast_question", True),
            # a wrong "spray correctly" if the farmer answers yes:
            "blast_question_on_other_classes": asked("blast_question", False),
            "referred": count(lambda r: r["outcome"] == "referred"),
            "top_guess_right": count(lambda r: r["predicted"] == r["true"]),
            "by_true_class": by_true}


def use_model(folder: Path) -> dict:
    """Point kombish.classifier at a local model folder and return its labels.json."""
    import os

    os.environ["MODEL_REPO"] = ""
    classifier.LOCAL_MODEL_DIR = Path(folder).resolve()
    classifier.load.cache_clear()
    return classifier.meta()

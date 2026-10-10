import itertools
import re
import unicodedata
from pathlib import Path

import pytest

from kombish import rules, texts
from kombish.rules import decide, load_clips, load_rules
from kombish.voice import VoiceQuery

ROOT = Path(__file__).resolve().parent.parent
T = 0.70
ORDER = ["R0_NO_CONSENT", "R0_NO_PHOTO", "R5_ABSTAIN", "R6_VOICE_REDFLAG",
         "R1_BLB", "R2_BLAST", "R3_HEALTHY", "R4_OTHER"]
SYMPTOMS = ["brown_spots", "spindle_lesions", "yellowing", "leaf_tip_drying",
            "insects_seen", "hopper_burn", "wilting", "none", "unclear"]


def nfc(s): return unicodedata.normalize("NFC", s)


def all_voices():
    for k in (1, 2):
        for combo in itertools.combinations(SYMPTOMS, k):
            for conf in ("low", "medium", "high"):
                for stage in ("seedling", "booting", "unknown"):
                    for wants in (True, False):
                        yield VoiceQuery(transcript_bn="x", symptoms=list(combo), growth_stage=stage,
                                         farmer_wants_to_spray=wants, confidence=conf)


def wired_clip_ids():
    ids = {r["clip"] for r in load_rules().values()} | {r["extra_clip"] for r in load_rules().values()}
    return sorted((ids - {""}) | {"consent", "voice_failed"})


def test_rules_csv_order_matches_code():
    assert list(load_rules()) == ORDER
    assert [int(r["priority"]) for r in load_rules().values()] == list(range(len(ORDER)))


@pytest.mark.parametrize("label", rules.CLASSES)
@pytest.mark.parametrize("conf,margin_ok", [(0.95, True), (0.50, True), (0.95, False)])
def test_voice_only_makes_answers_more_cautious(label, conf, margin_ok):
    base = decide(label, conf, margin_ok, None, None, threshold=T).decision
    for v in all_voices():
        d = decide(label, conf, margin_ok, v, None, threshold=T).decision
        assert d in {base, "consult_officer"}, (label, v)
        if base != "spray_correctly":
            assert d != "spray_correctly", (label, v)


@pytest.mark.parametrize("label", list(rules.CLASSES) + ["not_a_class"])
def test_low_confidence_always_refers(label):
    assert decide(label, T - 0.01, True, None, None, threshold=T).rule_id == "R5_ABSTAIN"
    assert decide(label, 0.99, False, None, None, threshold=T).rule_id == "R5_ABSTAIN"


def test_label_mapping_when_confident():
    got = {lab: decide(lab, 0.99, True, None, None, threshold=T).decision for lab in rules.CLASSES}
    assert got == {"bacterial_leaf_blight": "no_insecticide_fix_fertiliser", "blast": "spray_correctly",
                   "healthy": "no_spray_monitor", "other": "consult_officer"}


def test_prompts_have_no_clips():
    assert decide("blast", 0.99, True, None, None, threshold=T, consent=False).rule_id == "R0_NO_CONSENT"
    a = decide(None, 0.0, False, None, None, threshold=T)
    assert a.rule_id == "R0_NO_PHOTO" and a.clips == ()


def test_red_flag_needs_medium_or_high_confidence():
    v = lambda c: VoiceQuery(transcript_bn="x", symptoms=["insects_seen"], growth_stage="unknown",
                             farmer_wants_to_spray=True, confidence=c)
    assert decide("healthy", 0.99, True, v("high"), None, threshold=T).rule_id == "R6_VOICE_REDFLAG"
    assert decide("healthy", 0.99, True, v("low"), None, threshold=T).rule_id == "R3_HEALTHY"


@pytest.mark.parametrize("label", rules.CLASSES)
def test_planning_to_spray_never_changes_decision(label):
    ds = {decide(label, 0.99, True, None, p, threshold=T).decision for p in (True, False, None)}
    assert len(ds) == 1


def test_every_decision_rule_has_text_and_declared_clip():
    clips = load_clips()
    for rid, row in load_rules().items():
        assert row["headline_bn"].strip(), rid
        if row["decision"] == "none":
            continue
        for cid in [c for c in (row["clip"], row["extra_clip"]) if c]:
            assert cid in clips, (rid, cid)
            assert clips[cid]["text_bn"].strip(), cid
            assert clips[cid]["file"] == f"audio/{cid}.mp3"


def test_blast_includes_safety_and_neck_blast_line():
    a = decide("blast", 0.99, True, None, None, threshold=T)
    assert a.clips == ("audio/blast.mp3", "audio/safety.mp3")
    assert nfc("শীষ") in nfc(load_clips()["blast"]["text_bn"])   # update deliberately if reviewers reword


def test_consent_clip_matches_screen_text():
    assert nfc(load_clips()["consent"]["text_bn"]) == nfc(texts.CONSENT_BN)


def test_voice_failed_line_is_appended():
    a = decide("healthy", 0.99, True, None, None, threshold=T, voice_failed=True)
    assert load_clips()["voice_failed"]["text_bn"] in a.text_md


# ---- no doses, no brands, no hazardous actives ----
FORBIDDEN = ["trooper", "nativo", "thiovit", "cumulus", "edifenphos", "carbendazim", "propiconazole",
             "থিওভিট", "কমুলাস"]                      # substring match (brands, hazardous actives)
FORBIDDEN_TOKENS = {"মিলি", "মিলিলিটার", "লিটার", "গ্রাম"}   # whole-token match (dose units).
# Whole tokens only: "প্রোগ্রাম" (program, in the consent text) contains "গ্রাম" as a substring.
# "গ্রাম" also means "village"; if a reviewer needs that word, discuss before removing it here.
# "নয়" (nine) is left out on purpose: it also means "is not" (used in the consent text).
BN_NUMBER_WORDS = {nfc(w) for w in ["এক", "দুই", "তিন", "চার", "পাঁচ", "ছয়", "সাত", "আট", "দশ", "বিশ",
                                    "ত্রিশ", "চল্লিশ", "পঞ্চাশ", "একশো", "সাড়ে", "দেড়", "আড়াই"]}
NUMBER_ALLOWLIST = {   # every number a reviewed script may say; change only with reviewer approval
    "blb": {"পাঁচ", "সাড়ে", "তিন"}, "blast": {"সাত", "দশ"}, "healthy": {"ত্রিশ", "চল্লিশ"},
    "not_sure": {"এক", "ছয়", "দুই", "তিন"}, "safety": set(), "consent": set(), "voice_failed": set(),
}
TOKEN_SPLIT = re.compile(r"[\s,।;:!?\-–—()\"'“”‘’]+")


def all_user_facing_texts():
    for row in load_rules().values():
        yield row["rule_id"], row["headline_bn"]
    for cid in wired_clip_ids():
        yield cid, load_clips()[cid]["text_bn"]


def test_no_forbidden_terms():
    for key, text in all_user_facing_texts():
        low = nfc(text).lower()
        for term in FORBIDDEN:
            assert nfc(term).lower() not in low, (key, term)
        tokens = set(TOKEN_SPLIT.split(low))
        assert not (tokens & {nfc(t) for t in FORBIDDEN_TOKENS}), (key, tokens & FORBIDDEN_TOKENS)


def test_numbers_only_from_allowlist():
    for cid in wired_clip_ids():
        text = nfc(load_clips()[cid]["text_bn"])
        assert not re.search(r"[0-9০-৯]", text), (cid, "digits in a spoken script")
        nums = {t for t in TOKEN_SPLIT.split(text) if t in BN_NUMBER_WORDS}
        assert nums <= {nfc(w) for w in NUMBER_ALLOWLIST[cid]}, (cid, nums)


def test_headline_digits_only_16123():
    for rid, row in load_rules().items():
        assert set(re.findall(r"[0-9]+", row["headline_bn"])) <= {"16123"}, rid


# ---- release checks (pytest -m final) ----
@pytest.mark.final
def test_clip_files_exist():
    for cid in wired_clip_ids():
        p = ROOT / load_clips()[cid]["file"]
        assert p.exists() and p.stat().st_size > 0, p


@pytest.mark.final
def test_wired_text_is_reviewed():
    for cid in wired_clip_ids():
        row = load_clips()[cid]
        assert row["review_status"] == "reviewed", cid
        assert row["reviewer_1"] and row["reviewer_2"] not in ("", "PENDING"), cid
    for rid, row in load_rules().items():
        assert row["review_status"] == "reviewed", rid


@pytest.mark.final
def test_no_placeholders_left():
    blob = (ROOT / "data" / "rules.csv").read_text("utf-8") + (ROOT / "data" / "clips.csv").read_text("utf-8")
    blob += (ROOT / "kombish" / "texts.py").read_text("utf-8")
    assert "TODO-C" not in blob and "TODO-HUMAN" not in blob

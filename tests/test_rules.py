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
         "R1_BLB", "R0_CONFIRM_BLAST", "R7_BLAST_UNCONFIRMED", "R2_BLAST", "R3_HEALTHY", "R4_OTHER"]
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
    got = {lab: decide(lab, 0.99, True, None, None, threshold=T, blast_confirmed=True).decision
           for lab in rules.CLASSES}
    assert got == {"bacterial_leaf_blight": "no_insecticide_fix_fertiliser", "blast": "spray_correctly",
                   "healthy": "no_spray_monitor", "other": "consult_officer"}


# ---- spray advice is stricter than no-spray advice ----
BLAST_T = 0.95


def blast(conf, confirmed, voice=None, margin_ok=True):
    return decide("blast", conf, margin_ok, voice, None, threshold=T, blast_threshold=BLAST_T,
                  blast_confirmed=confirmed)


def test_blast_needs_the_farmers_yes():
    asked = blast(0.99, None)
    assert asked.rule_id == "R0_CONFIRM_BLAST" and asked.decision == "none" and asked.clips == ()
    assert asked.text_md == f"## {load_rules()['R0_CONFIRM_BLAST']['headline_bn']}"   # the question, nothing else
    yes = blast(0.99, True)
    assert yes.rule_id == "R2_BLAST" and yes.decision == "spray_correctly"
    no = blast(0.99, False)
    assert no.rule_id == "R7_BLAST_UNCONFIRMED" and no.decision == "consult_officer"
    assert no.clips == ("audio/not_sure.mp3",)


@pytest.mark.parametrize("confirmed", [None, False, True])
def test_blast_below_its_own_threshold_always_refers(confirmed):
    # Confident enough for a no-spray answer (>= T), not confident enough for spray advice (< BLAST_T).
    for conf in (T, 0.83, 0.90, BLAST_T - 0.001):
        assert blast(conf, confirmed).rule_id == "R5_ABSTAIN"
    assert blast(BLAST_T, True).rule_id == "R2_BLAST"   # the threshold itself is enough


@pytest.mark.parametrize("label", ["bacterial_leaf_blight", "healthy", "other"])
def test_blast_threshold_and_question_do_not_touch_other_classes(label):
    plain = decide(label, 0.80, True, None, None, threshold=T)
    for confirmed in (None, False, True):
        gated = decide(label, 0.80, True, None, None, threshold=T, blast_threshold=BLAST_T,
                       blast_confirmed=confirmed)
        assert gated == plain


def test_spray_is_only_reachable_through_a_confirmed_confident_blast():
    for label in list(rules.CLASSES) + [None, "not_a_class"]:
        for conf in (0.0, 0.5, T, 0.9, BLAST_T, 0.999):
            for margin_ok in (True, False):
                for confirmed in (None, False, True):
                    for consent in (True, False):
                        d = decide(label, conf, margin_ok, None, True, threshold=T, consent=consent,
                                   blast_threshold=BLAST_T, blast_confirmed=confirmed).decision
                        allowed = (label == "blast" and conf >= BLAST_T and margin_ok and confirmed is True
                                   and consent)
                        assert (d == "spray_correctly") == allowed, (label, conf, margin_ok, confirmed, consent)


@pytest.mark.parametrize("confirmed", [None, False, True])
def test_voice_never_changes_a_blast_outcome_except_towards_referral(confirmed):
    base = blast(0.99, confirmed).decision
    for v in all_voices():
        assert blast(0.99, confirmed, voice=v).decision in {base, "consult_officer"}
        assert blast(0.80, confirmed, voice=v).decision == "consult_officer"   # below the blast threshold


def test_classifier_abstain_flag_uses_the_blast_threshold():
    from kombish.classifier import should_abstain

    m = {"threshold": 0.83, "margin": 0.2, "blast_threshold": 0.95}
    assert should_abstain("blast", 0.90, 0.8, m) is True            # fine for no-spray advice, not for spray
    assert should_abstain("blast", 0.95, 0.8, m) is False
    assert should_abstain("bacterial_leaf_blight", 0.90, 0.8, m) is False
    assert should_abstain("healthy", 0.82, 0.8, m) is True          # general threshold
    assert should_abstain("blast", 0.99, 0.1, m) is True            # margin
    old = {"threshold": 0.83, "margin": 0.2}                         # a labels.json without the new key
    assert should_abstain("blast", 0.90, 0.8, old) is False


def test_prompt_and_referral_sets_cover_the_new_rules():
    assert "R0_CONFIRM_BLAST" in rules.PROMPT_RULES and "R7_BLAST_UNCONFIRMED" in rules.REFERRAL_RULES
    rows = load_rules()
    assert rows["R0_CONFIRM_BLAST"]["decision"] == "none" and not rows["R0_CONFIRM_BLAST"]["clip"]
    assert rows["R7_BLAST_UNCONFIRMED"]["headline_bn"] == rows["R5_ABSTAIN"]["headline_bn"]


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
    a = decide("blast", 0.99, True, None, None, threshold=T, blast_confirmed=True)
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

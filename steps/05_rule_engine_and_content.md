# 05 — Rule engine, rule table, Bangla texts and safety tests

**Goal:** Build the pure-Python rule engine, the six-row rule table, the Bangla answer texts (drafts), the consent text and the pytest invariants that prove the safety claims.
**Who:** Claude Code.
**When:** Saturday 10 October, night. Before step 06 (Bangla review) and step 13 (app).
**Covers master-plan step:** S06 (instruction file CC-03).

Context: Code decides; the language model only parses voice. Every sentence a farmer can read or hear lives in `data/rules.csv` or `data/clips.csv`. The app never invents pesticide names, brands, doses or pre-harvest days. Voice can only move an answer towards a referral. Low confidence always gives a referral. **Every Bangla string below is a DRAFT — needs native speaker review before recording.** None has been checked by a native speaker or an agronomist.

## Prerequisites

```bash
test -f kombish/rules.py && test -f pytest.ini     # [Run step 03 first.]
source .venv/bin/activate && python -c "import pydantic, gradio"   # [Create .venv and install requirements (step 03).]
```

## Instructions for Claude Code

### 1. `kombish/voice.py` — define the schema now (step 15 adds the Gemini call)

```python
"""Voice parsing. Step 05 defines the schema; step 15 adds the Gemini call."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

Symptom = Literal["brown_spots", "spindle_lesions", "yellowing", "leaf_tip_drying",
                  "insects_seen", "hopper_burn", "wilting", "none", "unclear"]
GrowthStage = Literal["seedling", "tillering", "booting", "flowering", "ripening", "unknown"]


class VoiceQuery(BaseModel):
    transcript_bn: str
    symptoms: list[Symptom]
    growth_stage: GrowthStage
    farmer_wants_to_spray: bool
    confidence: Literal["low", "medium", "high"]


def voice_enabled() -> bool:
    return False  # step 15


def parse_voice(path: str | None) -> VoiceQuery | None:
    return None  # step 15
```

### 2. Write `data/rules.csv` and `data/clips.csv`

Create them with Python's `csv` module (run the snippet once from a scratch file; do not commit the snippet), UTF-8, header row first, so commas inside fields are quoted correctly. Rows must stay in this order (file order = priority order).

`data/rules.csv` columns: `rule_id, priority, conditions, decision, headline_bn, clip, extra_clip, sources, review_status, reviewer, notes`

```python
REFER_HEADLINE = "ছবিটা দেখে আমি নিশ্চিত হতে পারছি না। কৃষি কল সেন্টার: 16123"   # DRAFT — needs native speaker review
REFER_SRC = "Krishi Call Centre 16123, DAE (BSS, 2 Jul 2026)"
RULES = [
  dict(rule_id="R0_NO_CONSENT", priority=0, conditions="Consent box not ticked", decision="none",
       headline_bn="রাজি থাকলে টিক দিন।", clip="", extra_clip="", sources="",
       review_status="draft", reviewer="", notes="Text prompt only; no clip. Sentence taken from the consent draft."),
  dict(rule_id="R0_NO_PHOTO", priority=1, conditions="No image given", decision="none",
       headline_bn="অনুগ্রহ করে ধানের পাতার ছবি দিন।", clip="", extra_clip="", sources="",
       review_status="draft", reviewer="", notes="Text prompt only; no clip."),
  dict(rule_id="R5_ABSTAIN", priority=2, conditions="conf < threshold OR top1 - top2 < margin", decision="consult_officer",
       headline_bn=REFER_HEADLINE, clip="not_sure", extra_clip="", sources=REFER_SRC,
       review_status="draft", reviewer="", notes="Cost and hours of 16123 are not confirmed for 2025-26, so the app states neither."),
  dict(rule_id="R6_VOICE_REDFLAG", priority=3,
       conditions="label = healthy AND voice confidence in {medium, high} AND symptoms include hopper_burn or insects_seen",
       decision="consult_officer", headline_bn=REFER_HEADLINE, clip="not_sure", extra_clip="",
       sources=REFER_SRC + "; planthopper advice is unsafe to automate (Kom Bish claim check)",
       review_status="draft", reviewer="", notes="Voice can only make an answer more cautious."),
  dict(rule_id="R1_BLB", priority=4, conditions="label = bacterial_leaf_blight", decision="no_insecticide_fix_fertiliser",
       headline_bn="কীটনাশক লাগবে না, সার ঠিক করুন", clip="blb", extra_clip="",
       sources="BRRI Plant Pathology Division notice, 19 Mar 2023; DAE/BAMIS agromet bulletin, 17-22 Mar 2023",
       review_status="draft", reviewer="",
       notes="The official notice also lists a sulphur-based foliar mix (potash, a sulphur product, zinc). Kom Bish deliberately omits it and refers the farmer instead. The 'drain standing water' line (DAE official, 2017) stays out unless a reviewer approves it [CHECK]."),
  dict(rule_id="R2_BLAST", priority=5, conditions="label = blast", decision="spray_correctly",
       headline_bn="স্প্রে লাগবে, তবে ঠিকভাবে", clip="blast", extra_clip="safety",
       sources="BRRI Plant Pathology Division notice, 19 Mar 2023; DAE/BAMIS agromet bulletin, 17-22 Mar 2023; FAO PPE guidelines (safety script)",
       review_status="draft", reviewer="",
       notes="Names only the active-ingredient group, never a brand or dose. The neck-blast urgency line is always included, not gated on a spoken growth stage."),
  dict(rule_id="R3_HEALTHY", priority=6, conditions="label = healthy", decision="no_spray_monitor",
       headline_bn="এখন কোনো স্প্রে লাগবে না", clip="healthy", extra_clip="",
       sources="Ali et al. 2017, Frontiers in Environmental Science",
       review_status="draft", reviewer="", notes="'তবে' before the exception stops the 30-40 day rule being heard as 'never spray'."),
  dict(rule_id="R4_OTHER", priority=7, conditions="label = other", decision="consult_officer",
       headline_bn=REFER_HEADLINE, clip="not_sure", extra_clip="", sources=REFER_SRC,
       review_status="draft", reviewer="", notes=""),
]
```

`data/clips.csv` columns: `clip_id, file, text_bn, gloss_en, review_status, reviewer_1, reviewer_2, review_date, duration_s, notes`.
All `text_bn` values are **DRAFT — needs native speaker review before recording**. `review_status="draft"` for all except `brinjal` (`stretch`).

| clip_id | file | text_bn (DRAFT — needs native speaker review before recording) | gloss_en |
|---|---|---|---|
| blb | audio/blb.mp3 | আপনার ধানে পাতাপোড়া রোগ মনে হচ্ছে। এটা কীটনাশক দিয়ে সারে না, তাই কীটনাশক কিনবেন না। এখন ইউরিয়া সার দেওয়া বন্ধ রাখুন। বৃষ্টি থামলে বিঘাপ্রতি পাঁচ কেজি পটাশ আর সাড়ে তিন কেজি জিপসাম দিন। অন্য কিছু ছিটানোর আগে আপনার উপসহকারী কৃষি কর্মকর্তার সাথে কথা বলুন। | It looks like bacterial leaf blight. Insecticide does not cure it, so don't buy any. Stop urea for now. When the rain stops, apply five kg potash and three and a half kg gypsum per bigha. Before spraying anything else, talk to your Sub-Assistant Agriculture Officer. |
| blast | audio/blast.mp3 | আপনার ধানে ব্লাস্ট রোগ মনে হচ্ছে। এই রোগে স্প্রে লাগে, তবে ঠিকভাবে দিতে হবে। ট্রাইসাইক্লাজোল গ্রুপের ছত্রাকনাশক বিকেলে ছিটান, সাত থেকে দশ দিন পর আরেকবার দিন। কতটুকু দেবেন আর ধান কাটার কত দিন আগে থামবেন, বোতলের গায়ে বাংলায় লেখা আছে, ঠিক সেটাই মানুন। ধানে থোড় এলে বা শীষ বের হতে থাকলে দেরি করবেন না, শীষে ব্লাস্ট একবার লাগলে আর সারানো যায় না। | It looks like blast. This disease does need a spray, but done correctly. Spray a tricyclazole-group fungicide in the afternoon and again after seven to ten days. How much to use and how many days before harvest to stop is written in Bangla on the bottle; follow exactly that. If the crop is at booting or heads are coming out, don't delay; neck blast cannot be cured once it sets in. |
| safety | audio/safety.mp3 | স্প্রে করার আগে বোতলের গায়ের লেখা আর রঙের দাগ দেখে নিন। লম্বা হাতার জামা, লম্বা প্যান্ট আর পায়ে জুতা বা বুট পরুন; ওষুধ মেশানোর সময় হাতে গ্লাভস দিন, মুখ ঢেকে রাখুন। বাতাস পিঠের দিকে রেখে ছিটান, যেন ওষুধ আপনার গায়ে না আসে। স্প্রের সময় কিছু খাবেন না, পান করবেন না, বিড়ি-সিগারেট খাবেন না। কাজ শেষে সাবান দিয়ে হাত-মুখ ধুয়ে কাপড় বদলান, সেই কাপড় আলাদা করে ধুয়ে নিন। বোতলে যত দিন অপেক্ষা করতে বলা আছে, তার আগে ফসল কাটবেন না। | Before spraying, read the label and check the colour band. Wear long sleeves, long trousers and shoes or boots; wear gloves while mixing and keep your face covered. Spray with the wind at your back. Don't eat, drink or smoke while spraying. Afterwards wash hands and face with soap, change clothes and wash them separately. Don't harvest before the waiting period written on the bottle. |
| healthy | audio/healthy.mp3 | আপনার ধানের পাতা সুস্থ দেখাচ্ছে, এখন কোনো স্প্রে লাগবে না। রোপণের পর প্রথম ত্রিশ থেকে চল্লিশ দিন কীটনাশক না দিলে উপকারী পোকা বাড়ে, তারাই ক্ষতিকর পোকা খায়। জমিতে ডাল পুঁতে পাখি বসার জায়গা করে দিন, আর সপ্তাহে একবার জমি ঘুরে দেখুন। তবে অনেক পাতা কাটা, মরা ডিগ বা সাদা শীষ দেখলে আবার ছবি পাঠান বা কৃষি কল সেন্টারে ফোন করুন। | Your rice leaves look healthy; no spray is needed now. If you don't use insecticide for the first thirty to forty days after transplanting, helpful insects build up and eat the harmful ones. Put branches in the field for birds to perch, and walk the field once a week. But if you see many cut leaves, dead hearts or white heads, send a photo again or call the Krishi Call Centre. |
| not_sure | audio/not_sure.mp3 | ছবিটা দেখে আমি নিশ্চিত হতে পারছি না। ভুল পরামর্শ দেওয়ার চেয়ে না বলাই ভালো। কৃষি কল সেন্টারে ফোন করুন, নম্বর এক-ছয়-এক-দুই-তিন। অথবা আপনার এলাকার উপসহকারী কৃষি কর্মকর্তাকে ফসলটা দেখান। কোনো ওষুধ কেনার আগে তাঁদের সাথে কথা বলে নিন। | I can't be sure from this photo. Better not to answer than to give wrong advice. Call the Krishi Call Centre on one-six-one-two-three, or show the crop to your local Sub-Assistant Agriculture Officer. Talk to them before buying any medicine. |
| consent | audio/consent.mp3 | (same string as `texts.CONSENT_BN` below) | (same as `texts.CONSENT_GLOSS_EN`) |
| voice_failed | audio/voice_failed.mp3 | TODO-C: one line saying the voice note could not be understood and the advice is from the photo alone. | TODO-C (C writes this line in step 06) |
| brinjal | audio/brinjal.mp3 | মনে হচ্ছে বেগুনের ডগা ও ফল ছিদ্রকারী পোকা। পোকাটা ডগা আর ফলের ভেতরে থাকে, তাই স্প্রে করলে গায়ে লাগে না। সপ্তাহে একবার নেতিয়ে পড়া ডগা আর ছিদ্র করা বেগুন কেটে নষ্ট করে ফেলুন। জমিতে সেক্স ফেরোমন ফাঁদ বসান, কয়টা লাগবে কৃষি কর্মকর্তার কাছে জেনে নিন। স্প্রে কম করলে উপকারী পোকাও বাঁচবে। | Stretch only, not wired: brinjal shoot and fruit borer, non-chemical first. |

Notes column hints: blb → "Fertiliser amounts are attributable to BRRI; reviewers may add 'ব্রির পরামর্শ অনুযায়ী' (according to BRRI)." safety → "Follows FAO tropical PPE guidance; 'face covered' goes slightly beyond FAO's minimum; the waiting-period line comes from Bangladeshi label rules." not_sure → "16123 read digit by digit; a native speaker should confirm which form farmers use."

### 3. `kombish/texts.py` — UI strings and consent

Mark the file header: `# Every Bangla string here is a DRAFT — needs native speaker review before recording.`
Strings marked NEW are not from the content research; C must write or approve them in step 06.

```python
CONSENT_VERSION = "2026-10-10-draft1"   # bump whenever CONSENT_BN changes

CONSENT_BN = (
    "কম বিষ একটা কম্পিউটার প্রোগ্রাম, সরকারি কর্মকর্তা নয়। আপনার ছবি শুধু পরামর্শ দেওয়ার জন্য দেখা হয়, আমরা ছবি রাখি না। "
    "ভয়েস নোট দিলে সেটা দেশের বাইরে Google-এর সার্ভারে প্রক্রিয়া হয়, আর Google তার সেবা উন্নত করতে এটা ব্যবহার করতে পারে; "
    "আমরা রেকর্ডিং রাখি না। আমরা শুধু ফলাফল রাখি, কোন রোগ মনে হয়েছে আর কী পরামর্শ দেওয়া হয়েছে, নাম বা ফোন নম্বর ছাড়া। "
    "আপনার বয়স আঠারোর কম হলে মা-বাবার অনুমতি লাগবে। রাজি থাকলে টিক দিন।"
)
CONSENT_GLOSS_EN = (
    "Kom Bish is a computer program, not a government officer. Your photo is only looked at to give advice; we do not keep it. "
    "If you add a voice note, it is processed on Google's servers outside the country, and Google may use it to improve its "
    "services; we do not keep the recording. We keep only the result, what disease it looked like and what advice was given, "
    "without name or phone number. Under eighteen needs a parent's permission. Tick if you agree."
)
CONSENT_CHECKBOX_BN = "রাজি থাকলে টিক দিন।"
VOICE_PRIVACY_NOTE_BN = "ভয়েস নোট Google-এর সার্ভারে প্রক্রিয়া হয়"
LABEL_PHOTO_BN = "ধানের পাতার ছবি"
LABEL_VOICE_BN = "ভয়েস নোট (ঐচ্ছিক)"
BUTTON_ADVISE_BN = "পরামর্শ নিন"
LABEL_LISTEN_BN = "শুনুন"
TAB_ADVICE_BN = "পরামর্শ"
TAB_DASHBOARD_BN = "ড্যাশবোর্ড"
SPRAY_INTENT_Q_BN = "আপনি কি স্প্রে করার কথা ভাবছিলেন?"
YES_BN, NO_BN = "হ্যাঁ", "না"
CONFIRM_TEMPLATE_BN = "ছবি দেখে মনে হচ্ছে আপনার ধানে {disease}।"
DISEASE_NAME_BN = {"bacterial_leaf_blight": "পাতাপোড়া রোগ", "blast": "ব্লাস্ট রোগ"}
VOICE_ECHO_BN = "আপনি বলছেন: “{transcript}”"     # from the draft "আপনি বলছেন, ..."
SOURCE_LABEL_BN = "সূত্র"                           # NEW
LABEL_SAFETY_BN = "স্প্রের নিরাপত্তা"                  # NEW
FEEDBACK_BN = "ভুল মনে হচ্ছে"                        # NEW ("this looks wrong")
FEEDBACK_THANKS_BN = "ধন্যবাদ"                       # NEW
```

The `consent` row's `text_bn` in `clips.csv` must equal `CONSENT_BN` exactly.

### 4. `kombish/rules.py` — the rule engine

```python
"""Kom Bish rule engine. Pure Python: no network, no model calls.

Code decides. All farmer-facing text comes from data/rules.csv and data/clips.csv.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING

from kombish import texts

if TYPE_CHECKING:
    from kombish.voice import VoiceQuery

ROOT = Path(__file__).resolve().parent.parent
RULES_CSV = ROOT / "data" / "rules.csv"
CLIPS_CSV = ROOT / "data" / "clips.csv"

CLASSES = ("bacterial_leaf_blight", "blast", "healthy", "other")
LABEL_TO_RULE = {"bacterial_leaf_blight": "R1_BLB", "blast": "R2_BLAST",
                 "healthy": "R3_HEALTHY", "other": "R4_OTHER"}
RED_FLAG_SYMPTOMS = frozenset({"hopper_burn", "insects_seen"})
NO_SPRAY_RULES = frozenset({"R1_BLB", "R3_HEALTHY"})
CORRECT_USE_RULES = frozenset({"R2_BLAST"})
REFERRAL_RULES = frozenset({"R4_OTHER", "R5_ABSTAIN", "R6_VOICE_REDFLAG"})
PROMPT_RULES = frozenset({"R0_NO_CONSENT", "R0_NO_PHOTO"})


@dataclass(frozen=True)
class Advice:
    rule_id: str
    decision: str
    headline_bn: str
    text_md: str
    clips: tuple[str, ...]
    sources: tuple[str, ...]


@lru_cache(maxsize=1)
def load_rules() -> dict[str, dict]:
    with RULES_CSV.open(encoding="utf-8", newline="") as f:
        return {row["rule_id"]: row for row in csv.DictReader(f)}


@lru_cache(maxsize=1)
def load_clips() -> dict[str, dict]:
    with CLIPS_CSV.open(encoding="utf-8", newline="") as f:
        return {row["clip_id"]: row for row in csv.DictReader(f)}


def select_rule(label: str | None, conf: float, margin_ok: bool, voice: "VoiceQuery | None",
                *, threshold: float, consent: bool = True) -> str:
    """Return the rule_id. Priority order is fixed here and mirrored in rules.csv."""
    if not consent:
        return "R0_NO_CONSENT"
    if label is None:
        return "R0_NO_PHOTO"
    if label not in LABEL_TO_RULE or conf < threshold or not margin_ok:
        return "R5_ABSTAIN"
    if (label == "healthy" and voice is not None
            and voice.confidence in ("medium", "high")
            and RED_FLAG_SYMPTOMS & set(voice.symptoms)):
        return "R6_VOICE_REDFLAG"
    return LABEL_TO_RULE[label]


def decide(label: str | None, conf: float, margin_ok: bool, voice: "VoiceQuery | None",
           planning_to_spray: bool | None, *, threshold: float, consent: bool = True,
           voice_failed: bool = False) -> Advice:
    """planning_to_spray is logged and counted only; it never changes the decision (tested)."""
    rule_id = select_rule(label, conf, margin_ok, voice, threshold=threshold, consent=consent)
    row = load_rules()[rule_id]
    clip_rows = load_clips()
    clip_ids = [c for c in (row["clip"], row["extra_clip"]) if c]
    parts = [f"## {row['headline_bn']}"]
    if rule_id in ("R1_BLB", "R2_BLAST"):
        parts.append(texts.CONFIRM_TEMPLATE_BN.format(disease=texts.DISEASE_NAME_BN[label]))
    parts += [clip_rows[c]["text_bn"] for c in clip_ids]
    if voice_failed and rule_id not in PROMPT_RULES:
        parts.append(clip_rows["voice_failed"]["text_bn"])
    if row["sources"]:
        parts.append(f"*{texts.SOURCE_LABEL_BN}: {row['sources']}*")
    return Advice(
        rule_id=rule_id,
        decision=row["decision"],
        headline_bn=row["headline_bn"],
        text_md="\n\n".join(parts),
        clips=tuple(clip_rows[c]["file"] for c in clip_ids),
        sources=tuple(s.strip() for s in row["sources"].split(";") if s.strip()),
    )
```

### 5. `tests/test_rules.py` — the invariants

Write these tests (adapt names, keep the assertions):

```python
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
```

### 6. Run

```bash
source .venv/bin/activate
pytest -q
pytest -q -m final    # expected to FAIL now (no clips, nothing reviewed). Print which tests fail; that is the to-do list for steps 06 and 16.
```

### 7. Print a review pack for the human

Print a short table: clip_id, current `text_bn`, `gloss_en`. Tell the human to start step 06 and that the `voice_failed` line and all NEW strings in `texts.py` need C's wording.

## Human actions

- **HUMAN:** read the printed review pack. Start step 06 (native-speaker review) tonight if possible.
- **HUMAN:** commit and push: `git add -A && git commit -m "step 05: rule engine and content" && git push`.

## Done when

- `pytest -q` passes: voice never yields spray; abstain always refers; every decision rule has text and a declared clip; no script contains a dose, a brand, a hazardous active or an unapproved number.
- `pytest -q -m final` fails only on: missing clip files, review status, `TODO-C` (these close in steps 06 and 16).
- `data/rules.csv` has 8 rows in priority order; `data/clips.csv` has 8 rows.

## If it fails

- **CSV parse errors:** rewrite the files with `csv.writer` (never hand-edit quoting), UTF-8 without BOM.
- **Bangla string comparisons fail although the text looks identical:** NFC-normalise both sides (য়/ড় have two Unicode encodings).
- **A reviewer later adds a number:** the allowlist test fails on purpose. Update `NUMBER_ALLOWLIST` only after the reviewer confirms the number is sourced and is not a pesticide dose or waiting period.

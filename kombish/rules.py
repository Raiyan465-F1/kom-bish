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
REFERRAL_RULES = frozenset({"R4_OTHER", "R5_ABSTAIN", "R6_VOICE_REDFLAG", "R7_BLAST_UNCONFIRMED"})
PROMPT_RULES = frozenset({"R0_NO_CONSENT", "R0_NO_PHOTO", "R0_CONFIRM_BLAST"})


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
                *, threshold: float, consent: bool = True, blast_threshold: float | None = None,
                blast_confirmed: bool | None = None, blb_threshold: float | None = None) -> str:
    """Return the rule_id. Priority order is fixed here and mirrored in rules.csv.

    Spray advice is held to a stricter standard than no-spray advice. A blast answer needs (1) confidence
    at or above the blast-only threshold and (2) the farmer's own "yes" to the lesion-shape question.
    Unanswered -> ask the question first (R0_CONFIRM_BLAST). "No" or "not sure" -> referral.
    """
    if not consent:
        return "R0_NO_CONSENT"
    if label is None:
        return "R0_NO_PHOTO"
    if label not in LABEL_TO_RULE or conf < threshold or not margin_ok:
        return "R5_ABSTAIN"
    if label == "blast" and blast_threshold is not None and conf < blast_threshold:
        return "R5_ABSTAIN"
    if label == "bacterial_leaf_blight" and blb_threshold is not None and conf < blb_threshold:
        return "R5_ABSTAIN"   # "no insecticide needed" also has its own threshold when labels.json gives one
    if (label == "healthy" and voice is not None
            and voice.confidence in ("medium", "high")
            and RED_FLAG_SYMPTOMS & set(voice.symptoms)):
        return "R6_VOICE_REDFLAG"
    if label == "blast":
        if blast_confirmed is None:
            return "R0_CONFIRM_BLAST"
        if blast_confirmed is not True:
            return "R7_BLAST_UNCONFIRMED"
    return LABEL_TO_RULE[label]


def decide(label: str | None, conf: float, margin_ok: bool, voice: "VoiceQuery | None",
           planning_to_spray: bool | None, *, threshold: float, consent: bool = True,
           voice_failed: bool = False, blast_threshold: float | None = None,
           blast_confirmed: bool | None = None, blb_threshold: float | None = None) -> Advice:
    """planning_to_spray is logged and counted only; it never changes the decision (tested)."""
    rule_id = select_rule(label, conf, margin_ok, voice, threshold=threshold, consent=consent,
                          blast_threshold=blast_threshold, blast_confirmed=blast_confirmed,
                          blb_threshold=blb_threshold)
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

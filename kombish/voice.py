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

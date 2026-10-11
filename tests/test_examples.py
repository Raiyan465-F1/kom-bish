"""Every example photo must still trigger the rule path it is meant to demonstrate, with no EXIF data."""
import os
from pathlib import Path

import pytest
from PIL import Image

from kombish import classifier, rules

ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = sorted((ROOT / "examples").glob("*.jpg"))
EXPECTED = {"blb_": "R1_BLB", "blast_": "R0_CONFIRM_BLAST", "healthy_": "R3_HEALTHY", "other_": "R4_OTHER",
            "not_sure_": "R5_ABSTAIN"}

if not EXAMPLES:
    pytest.skip("No example photos yet (step 19).", allow_module_level=True)


def expected_rule(name: str) -> str:
    return next(rule for prefix, rule in EXPECTED.items() if name.startswith(prefix))


def test_every_photo_rule_path_has_an_example_and_a_credit():
    assert {expected_rule(p.name) for p in EXAMPLES} == set(EXPECTED.values())
    assert 4 <= len(EXAMPLES) <= 6
    credits = (ROOT / "examples" / "CREDITS.md").read_text("utf-8")
    for p in EXAMPLES:
        assert f"`{p.name}`" in credits, f"{p.name} is not credited in examples/CREDITS.md"


@pytest.mark.parametrize("path", EXAMPLES, ids=lambda p: p.name)
def test_example_has_no_exif(path):
    with Image.open(path) as im:
        assert len(im.getexif()) == 0


needs_model = pytest.mark.skipif(
    not os.getenv("MODEL_REPO", "").strip() and not (classifier.LOCAL_MODEL_DIR / "model.onnx").exists(),
    reason="No model: set MODEL_REPO or put model.onnx and labels.json in models/.")


def decide(path: Path, blast_confirmed):
    m = classifier.meta()
    with Image.open(path) as im:
        pred = classifier.predict(im)
    return rules.decide(pred.label, pred.conf, pred.margin >= m["margin"], None, None, threshold=m["threshold"],
                        blast_threshold=m.get("blast_threshold"), blb_threshold=m.get("blb_threshold"),
                        blast_confirmed=blast_confirmed)


@needs_model
@pytest.mark.parametrize("path", EXAMPLES, ids=lambda p: p.name)
def test_example_triggers_its_rule(path):
    assert decide(path, None).rule_id == expected_rule(path.name)


@needs_model
def test_blast_example_reaches_spray_only_on_yes():
    blast = next(p for p in EXAMPLES if p.name.startswith("blast_"))
    assert decide(blast, True).rule_id == "R2_BLAST"
    assert decide(blast, False).rule_id == "R7_BLAST_UNCONFIRMED"

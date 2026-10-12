import socket
import wave

import pytest
from PIL import Image

import app as app_module
from kombish import logging_store, rules, texts
from kombish.classifier import Prediction
from kombish.voice import VoiceQuery

FAKE = {  # image width -> (label, conf, margin)
    101: ("bacterial_leaf_blight", 0.95, 0.9), 102: ("blast", 0.95, 0.9),
    103: ("healthy", 0.95, 0.9), 104: ("other", 0.95, 0.9), 105: ("blast", 0.40, 0.1),
    106: ("blast", 0.85, 0.8),   # above the general threshold, below the blast-only threshold
}
EXPECTED_RULE = {101: "R1_BLB", 102: "R2_BLAST", 103: "R3_HEALTHY", 104: "R4_OTHER", 105: "R5_ABSTAIN",
                 106: "R5_ABSTAIN"}
T, MARGIN, BLAST_T = 0.7, 0.2, 0.9
YES = {102: texts.YES_BN}   # a blast answer needs the farmer's "yes" to the lesion-shape question
BLB_YES = {101: texts.YES_BN}   # the BLB answer needs the farmer's "yes" to the BLB question
RED_FLAG = VoiceQuery(transcript_bn="x", symptoms=["insects_seen"], growth_stage="unknown",
                      farmer_wants_to_spray=False, confidence="high")


def fake_predict(img):
    label, conf, margin = FAKE[img.size[0]]
    return Prediction(label, conf, {label: conf}, margin, conf < T or margin < MARGIN)


def fake_meta():
    return {"threshold": T, "margin": MARGIN, "blast_threshold": BLAST_T}


class Harness:
    """Fakes shared by the server and the direct tests. No model, no network, no disk log."""

    def __init__(self):
        self.records: list[dict] = []
        self.feedback: list[tuple] = []
        self.voice_result: VoiceQuery | None = None

    def reset(self):
        self.records.clear()
        self.feedback.clear()
        self.voice_result = None

    def voice(self, path):
        return self.voice_result

    def log(self, record):
        self.records.append(record)
        return f"id{len(self.records)}"

    def log_feedback(self, ref_id, feedback):
        self.feedback.append((ref_id, feedback))

    def counts(self):
        return {"total": len(self.records), "no_spray": 0, "correct_use": 0, "referrals": 0, "sprays_avoided": 0}


def expected_text(width, voice=None, voice_failed=False, planning=None, confirmed=True) -> str:
    """confirmed: the farmer's answer to whichever confirmation question the photo triggers."""
    label, conf, margin = FAKE[width]
    return rules.decide(label, conf, margin >= MARGIN, voice, planning, threshold=T, voice_failed=voice_failed,
                        blast_threshold=BLAST_T, blast_confirmed=confirmed, blb_confirmed=confirmed).text_md


def assert_only_allowed_keys(record: dict) -> None:
    assert set(record) == logging_store.CONSULT_KEYS
    for banned in ("photo", "image", "audio", "transcript", "transcript_bn", "ip", "name", "phone"):
        assert banned not in record


@pytest.fixture
def harness():
    return Harness()


@pytest.fixture
def advise(harness):
    return app_module.make_advise(fake_predict, fake_meta, harness.voice, harness.log, True)


def img(width: int) -> Image.Image:
    return Image.new("RGB", (width, 60), "green")


# ---------------------------------------------------------------- direct (no server)

@pytest.mark.parametrize("width", sorted(FAKE))
def test_each_label_path(advise, harness, width):
    out = advise(True, img(width), None, None, YES.get(width), False, BLB_YES.get(width))
    assert out[0] == expected_text(width)
    (rec,) = harness.records
    assert rec["rule_id"] == EXPECTED_RULE[width]
    assert rec["voice_used"] is False and rec["planning_to_spray"] is None
    assert rec["abstained"] is (width == 105)
    assert_only_allowed_keys(rec)
    assert out[4] == "id1"            # consult id kept in gr.State for the feedback button
    assert out[5].visible is True     # feedback button
    for question in (out[7], out[8]):   # both confirmation questions are cleared after an answer
        assert question.visible is False and question.value is None


def test_blast_asks_the_lesion_question_first_and_logs_nothing(advise, harness):
    out = advise(True, img(102), None, texts.YES_BN)   # no answer to the question yet
    assert out[0] == f"## {rules.load_rules()['R0_CONFIRM_BLAST']['headline_bn']}"
    assert harness.records == []                        # no advice was given, so nothing is logged
    assert out[7].visible is True and out[7].value is None
    assert out[8].visible is False                      # the BLB question stays hidden for a blast photo
    assert out[2] is None and out[4] is None and out[5].visible is False


def test_blb_asks_its_question_first_and_logs_nothing(advise, harness):
    out = advise(True, img(101), None, texts.YES_BN)   # no answer to the question yet
    assert out[0] == f"## {rules.load_rules()['R0_CONFIRM_BLB']['headline_bn']}"
    assert harness.records == []                        # no advice was given, so nothing is logged
    assert out[8].visible is True and out[8].value is None
    assert out[7].visible is False                      # the lesion question stays hidden for a BLB photo
    assert out[2] is None and out[4] is None and out[5].visible is False


@pytest.mark.parametrize("answer", [texts.NO_BN, texts.NOT_SURE_BN, "anything else"])
def test_blb_without_a_yes_refers(advise, harness, answer):
    out = advise(True, img(101), None, None, None, False, answer)
    if answer == "anything else":                       # an unknown value is treated as unanswered
        assert harness.records == [] and out[8].visible is True
        return
    assert out[0] == expected_text(101, confirmed=False)
    rec = harness.records[0]
    assert rec["rule_id"] == "R8_BLB_UNCONFIRMED" and rec["decision"] == "consult_officer"
    assert_only_allowed_keys(rec)


def test_a_yes_to_the_other_question_confirms_nothing(advise, harness):
    out = advise(True, img(101), None, None, texts.YES_BN)                  # "yes" to the lesion question, BLB photo
    assert out[0] == f"## {rules.load_rules()['R0_CONFIRM_BLB']['headline_bn']}"
    out = advise(True, img(102), None, None, None, False, texts.YES_BN)     # "yes" to the BLB question, blast photo
    assert out[0] == f"## {rules.load_rules()['R0_CONFIRM_BLAST']['headline_bn']}"
    assert harness.records == []


@pytest.mark.parametrize("answer", [texts.NO_BN, texts.NOT_SURE_BN, "anything else"])
def test_blast_without_a_yes_refers(advise, harness, answer):
    out = advise(True, img(102), None, None, answer)
    if answer == "anything else":                       # an unknown value is treated as unanswered
        assert harness.records == [] and out[7].visible is True
        return
    assert out[0] == expected_text(102, confirmed=False)
    rec = harness.records[0]
    assert rec["rule_id"] == "R7_BLAST_UNCONFIRMED" and rec["decision"] == "consult_officer"
    assert_only_allowed_keys(rec)


@pytest.mark.parametrize("answer", [None, texts.YES_BN, texts.NO_BN])
def test_blast_below_the_blast_threshold_refers_whatever_the_farmer_says(advise, harness, answer):
    out = advise(True, img(106), None, None, answer)
    assert out[0] == expected_text(106)
    assert harness.records[0]["rule_id"] == "R5_ABSTAIN"
    assert out[7].visible is False                      # the question is never asked


@pytest.mark.parametrize("width", [103, 104])
def test_a_stray_yes_does_nothing_for_other_classes(advise, harness, width):
    assert advise(True, img(width), None, None, texts.YES_BN, False, texts.YES_BN)[0] == expected_text(width)
    assert harness.records[0]["rule_id"] == EXPECTED_RULE[width]


def test_only_yes_confirms():
    assert app_module.CONFIRM_ANSWERS == {texts.YES_BN: True, texts.NO_BN: False, texts.NOT_SURE_BN: False}


def test_blast_shows_second_audio_when_clips_exist(harness, monkeypatch):
    monkeypatch.setattr(app_module, "_clip", lambda rel: f"/clips/{rel}" if rel else None)
    advise = app_module.make_advise(fake_predict, fake_meta, harness.voice, harness.log, True)
    out = advise(True, img(102), None, None, texts.YES_BN)
    assert out[2] == "/clips/audio/blast.mp3"
    assert out[3].visible is True and "safety.mp3" in str(out[3].value)
    out = advise(True, img(103), None, None)
    assert out[2] == "/clips/audio/healthy.mp3" and out[3].visible is False


def test_voice_red_flag_refers(advise, harness):
    harness.voice_result = RED_FLAG
    out = advise(True, img(103), "note.wav", None)
    assert out[0] == expected_text(103, voice=RED_FLAG)
    rec = harness.records[0]
    assert rec["rule_id"] == "R6_VOICE_REDFLAG" and rec["decision"] == "consult_officer"
    assert rec["voice_used"] is True and rec["voice_symptoms"] == ["insects_seen"]
    assert rec["voice_confidence"] == "high" and rec["growth_stage"] == "unknown"
    assert out[1].visible is True and "x" in out[1].value   # transcript echoed in its own box, not logged
    assert_only_allowed_keys(rec)


def test_voice_failure_appends_line_and_keeps_photo_answer(advise, harness):
    out = advise(True, img(103), "note.wav", None)   # voice returns None
    assert out[0] == expected_text(103, voice_failed=True)
    assert rules.load_clips()["voice_failed"]["text_bn"] in out[0]
    rec = harness.records[0]
    assert rec["rule_id"] == "R3_HEALTHY" and rec["voice_used"] is True and rec["voice_symptoms"] is None
    assert out[1].visible is False


def test_voice_is_ignored_when_switched_off(harness):
    harness.voice_result = RED_FLAG
    advise = app_module.make_advise(fake_predict, fake_meta, harness.voice, harness.log, False)
    out = advise(True, img(103), "note.wav", None)
    assert out[0] == expected_text(103)
    assert harness.records[0]["rule_id"] == "R3_HEALTHY" and harness.records[0]["voice_used"] is False


def test_no_photo_prompts_and_logs_nothing(advise, harness):
    out = advise(True, None, None, None)
    assert out[0].startswith(f"## {rules.load_rules()['R0_NO_PHOTO']['headline_bn']}")
    assert harness.records == [] and out[4] is None and out[5].visible is False


def test_no_consent_prompts_and_logs_nothing(advise, harness):
    out = advise(False, img(102), "note.wav", texts.YES_BN)
    assert out[0].startswith(f"## {rules.load_rules()['R0_NO_CONSENT']['headline_bn']}")
    assert harness.records == [] and out[2] is None


@pytest.mark.parametrize("answer,expected", [(texts.YES_BN, True), (texts.NO_BN, False), (None, None)])
def test_planning_to_spray_mapping(advise, harness, answer, expected):
    out = advise(True, img(101), None, answer, None, False, texts.YES_BN)
    assert harness.records[0]["planning_to_spray"] is expected
    assert out[0] == expected_text(101)   # never changes the answer


@pytest.mark.parametrize("width,answer", [(101, None), (101, texts.YES_BN), (102, None), (102, texts.YES_BN),
                                          (103, None), (105, None)])
def test_show_english_keeps_bangla_first_and_audio_bangla(advise, harness, width, answer):
    plain = advise(True, img(width), None, None, answer, False, answer)
    english = advise(True, img(width), None, None, answer, True, answer)
    assert english[0].startswith(plain[0]) and english[0] != plain[0]      # Bangla first, English underneath
    assert english[0].count(texts.ENGLISH_NOTE) == 1
    label, conf, margin = FAKE[width]
    adv = rules.decide(label, conf, margin >= MARGIN, None, None, threshold=T, blast_threshold=BLAST_T,
                       blast_confirmed=app_module.CONFIRM_ANSWERS.get(answer),
                       blb_confirmed=app_module.CONFIRM_ANSWERS.get(answer))
    assert english[0] == f"{adv.text_md}\n\n---\n\n{texts.ENGLISH_NOTE}\n\n{adv.text_en_md}"
    assert english[2] == plain[2]                                          # the same (Bangla) clip either way
    assert [r["rule_id"] for r in harness.records[:1]] == [r["rule_id"] for r in harness.records[1:2]]


def test_show_english_also_translates_the_prompts_when_nothing_is_given(advise):
    out = advise(False, None, None, None, None, True)
    assert rules.load_rules()["R0_NO_CONSENT"]["headline_en"] in out[0]


def test_english_toggle_labels():
    off, on = app_module._english_labels(False), app_module._english_labels(True)
    assert off[0].visible is False and on[0].visible is True               # English consent text
    question = rules.load_rules()["R0_CONFIRM_BLAST"]
    assert off[4].label == question["headline_bn"]
    assert on[4].label == f"{question['headline_bn']} / {question['headline_en']}"
    assert off[3].label == texts.SPRAY_INTENT_Q_BN and on[3].label.endswith(texts.SPRAY_INTENT_Q_EN)
    assert off[1].label == texts.CONSENT_CHECKBOX_BN and off[2].label == texts.LABEL_PHOTO_BN
    assert off[5].value == texts.PHOTO_INSTRUCTION_BN                      # the photo instruction, Bangla only
    blb_question = rules.load_rules()["R0_CONFIRM_BLB"]
    assert off[6].label == blb_question["headline_bn"]
    assert on[6].label == f"{blb_question['headline_bn']} / {blb_question['headline_en']}"
    assert on[5].value.startswith(texts.PHOTO_INSTRUCTION_BN) and texts.PHOTO_INSTRUCTION_EN in on[5].value


def test_photo_instruction_is_shown_above_the_photo_box(harness):
    demo = app_module.build_demo(predict_fn=fake_predict, meta_fn=fake_meta, voice_fn=harness.voice,
                                 log_fn=harness.log, feedback_fn=harness.log_feedback, counts_fn=harness.counts,
                                 voice_on=False)
    ids = list(demo.blocks)
    help_id = next(i for i in ids if type(demo.blocks[i]).__name__ == "Markdown"
                   and demo.blocks[i].value == texts.PHOTO_INSTRUCTION_BN)
    image_id = next(i for i in ids if type(demo.blocks[i]).__name__ == "Image")
    assert ids.index(help_id) < ids.index(image_id)


def markdown_values(demo) -> list[str]:
    return [str(getattr(b, "value", "")) for b in demo.blocks.values() if type(b).__name__ == "Markdown"]


def test_computer_generated_voice_is_labelled(harness, monkeypatch):
    clips = {"consent": {"file": "audio/consent.mp3", "voice": "computer-generated"}}
    monkeypatch.setattr(app_module.rules, "load_clips", lambda: clips)
    monkeypatch.setattr(app_module, "_clip", lambda rel: f"/clips/{rel}" if rel else None)
    demo = app_module.build_demo(predict_fn=fake_predict, meta_fn=fake_meta, voice_fn=harness.voice,
                                 log_fn=harness.log, feedback_fn=harness.log_feedback, counts_fn=harness.counts,
                                 voice_on=False)
    notes = [v for v in markdown_values(demo) if texts.AUDIO_SYNTHETIC_NOTE_BN in v]
    assert notes and all("computer-generated voice" in v for v in notes)


def test_no_voice_label_and_no_crash_without_audio(harness, monkeypatch):
    monkeypatch.setattr(app_module, "_clip", lambda rel: None)   # no clip files at all: text only
    demo = app_module.build_demo(predict_fn=fake_predict, meta_fn=fake_meta, voice_fn=harness.voice,
                                 log_fn=harness.log, feedback_fn=harness.log_feedback, counts_fn=harness.counts,
                                 voice_on=False)
    visible = [b for b in demo.blocks.values() if type(b).__name__ == "Markdown"
               and texts.AUDIO_SYNTHETIC_NOTE_BN in str(b.value) and b.visible]
    assert visible == []
    advise = app_module.make_advise(fake_predict, fake_meta, harness.voice, harness.log, False)
    out = advise(True, img(101), None, None, None, False, texts.YES_BN)
    assert out[0] == expected_text(101) and out[2] is None and out[3].visible is False


def test_feedback_handler(harness):
    on_feedback = app_module.make_feedback(harness.log_feedback)
    md, button = on_feedback("id1")
    assert harness.feedback == [("id1", "looks_wrong")]
    assert md.value == texts.FEEDBACK_THANKS_BN and button.visible is False
    on_feedback(None)
    assert len(harness.feedback) == 1


def test_echo_escapes_markdown():
    echoed = app_module._echo("# hi  [x](y) *z*\n\nmore")
    assert "\\#" in echoed and "\\[" in echoed and "\\*" in echoed and "\n" not in echoed


# ---------------------------------------------------------------- through gradio_client

@pytest.fixture(scope="module")
def server(tmp_path_factory):
    from gradio_client import Client, handle_file

    h = Harness()
    demo = app_module.build_demo(predict_fn=fake_predict, meta_fn=fake_meta, voice_fn=h.voice, log_fn=h.log,
                                 feedback_fn=h.log_feedback, counts_fn=h.counts, voice_on=True)
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    _, local_url, _ = demo.launch(prevent_thread_lock=True, server_name="127.0.0.1", server_port=port)
    tmp = tmp_path_factory.mktemp("inputs")
    images = {}
    for width in FAKE:
        path = tmp / f"leaf_{width}.png"
        img(width).save(path)
        images[width] = handle_file(str(path))
    wav = tmp / "silent.wav"
    with wave.open(str(wav), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000)
        w.writeframes(b"\x00\x00" * 16000)   # 1 second of silence
    try:
        yield h, Client(local_url, verbose=False), images, handle_file(str(wav))
    finally:
        demo.close()


@pytest.fixture
def api(server):
    h, client, images, wav = server
    h.reset()

    def call(consent=True, width=None, audio=False, planning=None, blast=None, english=False, blb=None):
        return client.predict(consent, images[width] if width else None, wav if audio else None, planning,
                              blast, english, blb, api_name="/advise")
    return h, call


def test_api_show_english_adds_the_translation_under_the_bangla(api):
    h, call = api
    bangla = call(width=101, blb=texts.YES_BN)[0]
    both = call(width=101, english=True, blb=texts.YES_BN)[0]
    assert bangla == expected_text(101)                       # default: Bangla only
    assert both.startswith(bangla) and texts.ENGLISH_NOTE in both
    assert "No insecticide needed" in both and "No insecticide needed" not in bangla
    assert [r["rule_id"] for r in h.records] == ["R1_BLB", "R1_BLB"]   # the toggle never changes the decision


@pytest.mark.parametrize("width", sorted(FAKE))
def test_api_each_label_path(api, width):
    h, call = api
    out = call(width=width, blast=YES.get(width), blb=BLB_YES.get(width))
    assert out[0] == expected_text(width)
    (rec,) = h.records
    assert rec["rule_id"] == EXPECTED_RULE[width]
    assert_only_allowed_keys(rec)


def test_api_blast_question_then_answer(api):
    h, call = api
    out = call(width=102)                                  # first press: the question, no advice, no log
    assert out[0] == f"## {rules.load_rules()['R0_CONFIRM_BLAST']['headline_bn']}"
    assert h.records == []
    out = call(width=102, blast=texts.NOT_SURE_BN)         # "not sure" refers
    assert out[0] == expected_text(102, confirmed=False)
    assert h.records[-1]["rule_id"] == "R7_BLAST_UNCONFIRMED"
    out = call(width=102, blast=texts.NO_BN)               # "no" refers
    assert h.records[-1]["rule_id"] == "R7_BLAST_UNCONFIRMED"
    out = call(width=102, blast=texts.YES_BN)              # only "yes" gives the spray answer
    assert out[0] == expected_text(102, confirmed=True)
    assert h.records[-1]["rule_id"] == "R2_BLAST" and h.records[-1]["decision"] == "spray_correctly"


def test_api_blb_question_then_answer(api):
    h, call = api
    out = call(width=101)                                  # first press: the question, no advice, no log
    assert out[0] == f"## {rules.load_rules()['R0_CONFIRM_BLB']['headline_bn']}"
    out = call(width=101, blast=texts.YES_BN)              # a "yes" to the lesion question confirms nothing
    assert out[0] == f"## {rules.load_rules()['R0_CONFIRM_BLB']['headline_bn']}"
    assert h.records == []
    out = call(width=101, blb=texts.NOT_SURE_BN)           # "not sure" refers
    assert out[0] == expected_text(101, confirmed=False)
    assert h.records[-1]["rule_id"] == "R8_BLB_UNCONFIRMED"
    out = call(width=101, blb=texts.NO_BN)                 # "no" refers
    assert h.records[-1]["rule_id"] == "R8_BLB_UNCONFIRMED" and h.records[-1]["decision"] == "consult_officer"
    out = call(width=101, blb=texts.YES_BN)                # only "yes" gives the BLB answer
    assert out[0] == expected_text(101, confirmed=True)
    assert h.records[-1]["rule_id"] == "R1_BLB"


def test_api_voice_red_flag(api):
    h, call = api
    h.voice_result = RED_FLAG
    out = call(width=103, audio=True)
    assert out[0] == expected_text(103, voice=RED_FLAG)
    assert h.records[0]["rule_id"] == "R6_VOICE_REDFLAG"


def test_api_voice_failure(api):
    h, call = api
    out = call(width=103, audio=True)
    assert out[0] == expected_text(103, voice_failed=True)
    assert h.records[0]["rule_id"] == "R3_HEALTHY"


def test_api_no_photo(api):
    h, call = api
    out = call(width=None)
    assert out[0].startswith(f"## {rules.load_rules()['R0_NO_PHOTO']['headline_bn']}")
    assert h.records == []


def test_api_no_consent(api):
    h, call = api
    out = call(consent=False, width=102)
    assert out[0].startswith(f"## {rules.load_rules()['R0_NO_CONSENT']['headline_bn']}")
    assert h.records == []


@pytest.mark.parametrize("answer,expected", [(texts.YES_BN, True), (texts.NO_BN, False), (None, None)])
def test_api_planning_to_spray(api, answer, expected):
    h, call = api
    call(width=103, planning=answer)
    assert h.records[0]["planning_to_spray"] is expected

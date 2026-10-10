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
}
EXPECTED_RULE = {101: "R1_BLB", 102: "R2_BLAST", 103: "R3_HEALTHY", 104: "R4_OTHER", 105: "R5_ABSTAIN"}
T, MARGIN = 0.7, 0.2
RED_FLAG = VoiceQuery(transcript_bn="x", symptoms=["insects_seen"], growth_stage="unknown",
                      farmer_wants_to_spray=False, confidence="high")


def fake_predict(img):
    label, conf, margin = FAKE[img.size[0]]
    return Prediction(label, conf, {label: conf}, margin, conf < T or margin < MARGIN)


def fake_meta():
    return {"threshold": T, "margin": MARGIN}


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


def expected_text(width, voice=None, voice_failed=False, planning=None) -> str:
    label, conf, margin = FAKE[width]
    return rules.decide(label, conf, margin >= MARGIN, voice, planning, threshold=T,
                        voice_failed=voice_failed).text_md


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
    out = advise(True, img(width), None, None)
    assert out[0] == expected_text(width)
    (rec,) = harness.records
    assert rec["rule_id"] == EXPECTED_RULE[width]
    assert rec["voice_used"] is False and rec["planning_to_spray"] is None
    assert rec["abstained"] is (width == 105)
    assert_only_allowed_keys(rec)
    assert out[4] == "id1"            # consult id kept in gr.State for the feedback button
    assert out[5].visible is True     # feedback button


def test_blast_shows_second_audio_when_clips_exist(harness, monkeypatch):
    monkeypatch.setattr(app_module, "_clip", lambda rel: f"/clips/{rel}" if rel else None)
    advise = app_module.make_advise(fake_predict, fake_meta, harness.voice, harness.log, True)
    out = advise(True, img(102), None, None)
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
    out = advise(True, img(101), None, answer)
    assert harness.records[0]["planning_to_spray"] is expected
    assert out[0] == expected_text(101)   # never changes the answer


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

    def call(consent=True, width=None, audio=False, planning=None):
        return client.predict(consent, images[width] if width else None, wav if audio else None, planning,
                              api_name="/advise")
    return h, call


@pytest.mark.parametrize("width", sorted(FAKE))
def test_api_each_label_path(api, width):
    h, call = api
    out = call(width=width)
    assert out[0] == expected_text(width)
    (rec,) = h.records
    assert rec["rule_id"] == EXPECTED_RULE[width]
    assert_only_allowed_keys(rec)


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
    call(width=101, planning=answer)
    assert h.records[0]["planning_to_spray"] is expected

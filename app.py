"""Kom Bish Gradio app. Thin UI: every decision is made in kombish/rules.py."""
from __future__ import annotations

import os
import re
import sys
import time
from pathlib import Path

import gradio as gr

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from kombish import classifier, logging_store, rules, texts, voice, zerogpu

ROOT = Path(__file__).resolve().parent
APP_VERSION = os.getenv("APP_VERSION", "0.1.0")
FONT_HEAD = ('<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+Bengali:wght@400;700&display=swap" '
             'rel="stylesheet">')
EXAMPLES = sorted(str(p) for p in (ROOT / "examples").glob("*.jpg"))
MD_SPECIAL = re.compile(r"([\\`*_{}\[\]()#+\-.!|>])")


def _clip(rel: str | None) -> str | None:
    if not rel:
        return None
    p = ROOT / rel
    return str(p) if p.exists() else None


def _echo(transcript: str) -> str:
    t = " ".join(transcript.split())[:300]
    return texts.VOICE_ECHO_BN.format(transcript=MD_SPECIAL.sub(r"\\\1", t))


# Both confirmation questions (blast lesion shape, BLB patches) take the same three answers.
CONFIRM_ANSWERS = {texts.YES_BN: True, texts.NO_BN: False, texts.NOT_SURE_BN: False}   # only "yes" confirms


def _question(visible: bool):
    """A confirmation question. It is cleared after every use so an old answer never reaches a new photo."""
    return gr.Radio(value=None, visible=visible)


def _answer_text(adv: rules.Advice, show_english: bool) -> str:
    """The Bangla answer; with the toggle on, its English translation follows underneath (for reviewers)."""
    if not show_english:
        return adv.text_md
    return f"{adv.text_md}\n\n---\n\n{texts.ENGLISH_NOTE}\n\n{adv.text_en_md}"


def _english_labels(show_english):
    """Toggle handler: show or hide the English under the consent text and beside each prompt."""
    on = bool(show_english)
    question, blb_question = rules.load_rules()["R0_CONFIRM_BLAST"], rules.load_rules()["R0_CONFIRM_BLB"]
    return (gr.Markdown(visible=on),
            gr.Checkbox(label=texts.both(texts.CONSENT_CHECKBOX_BN, texts.CONSENT_CHECKBOX_EN, on)),
            gr.Image(label=texts.both(texts.LABEL_PHOTO_BN, texts.LABEL_PHOTO_EN, on)),
            gr.Radio(label=texts.both(texts.SPRAY_INTENT_Q_BN, texts.SPRAY_INTENT_Q_EN, on)),
            gr.Radio(label=texts.both(question["headline_bn"], question["headline_en"], on)),
            gr.Markdown(value=_photo_instruction(on)),
            gr.Radio(label=texts.both(blb_question["headline_bn"], blb_question["headline_en"], on)))


def _photo_instruction(show_english: bool) -> str:
    """How to take the photo: shown above the photo box."""
    if not show_english:
        return texts.PHOTO_INSTRUCTION_BN
    return f"{texts.PHOTO_INSTRUCTION_BN}\n\n*{texts.PHOTO_INSTRUCTION_EN}*"


def make_advise(predict_fn, meta_fn, voice_fn, log_fn, voice_on: bool):
    def advise(consent, img, audio_path, planning, blast_answer=None, show_english=False, blb_answer=None):
        t0 = time.perf_counter()
        planning_to_spray = {texts.YES_BN: True, texts.NO_BN: False}.get(planning)
        no_answer = (gr.Markdown(value="", visible=False), None, gr.Audio(value=None, visible=False), None,
                     gr.Button(visible=False), gr.Markdown(visible=False))
        if not consent or img is None:
            adv = rules.decide(None, 0.0, False, None, planning_to_spray, threshold=1.0, consent=bool(consent))
            return (_answer_text(adv, show_english), *no_answer, _question(False), _question(False))
        m = meta_fn()
        pred = predict_fn(img)
        voice_used = bool(voice_on and audio_path)
        vq = voice_fn(audio_path) if voice_used else None
        adv = rules.decide(pred.label, pred.conf, pred.margin >= m["margin"], vq, planning_to_spray,
                           threshold=m["threshold"], consent=True, voice_failed=voice_used and vq is None,
                           blast_threshold=m.get("blast_threshold"), blb_threshold=m.get("blb_threshold"),
                           blast_confirmed=CONFIRM_ANSWERS.get(blast_answer),
                           blb_confirmed=CONFIRM_ANSWERS.get(blb_answer))
        if adv.rule_id in rules.PROMPT_RULES:   # ask the confirmation question first; no advice, no log yet
            return (_answer_text(adv, show_english), *no_answer, _question(adv.rule_id == "R0_CONFIRM_BLAST"),
                    _question(adv.rule_id == "R0_CONFIRM_BLB"))
        consult_id = log_fn({
            "app_version": APP_VERSION, "predicted_class": pred.label, "confidence": round(pred.conf, 4),
            "probs": pred.probs, "abstained": pred.abstained, "voice_used": voice_used,
            "voice_symptoms": list(vq.symptoms) if vq else None,
            "voice_confidence": vq.confidence if vq else None,
            "growth_stage": vq.growth_stage if vq else None,
            "planning_to_spray": planning_to_spray, "rule_id": adv.rule_id, "decision": adv.decision,
            "latency_ms": int((time.perf_counter() - t0) * 1000),
            "consent_version": texts.CONSENT_VERSION, "feedback": None,
        })
        main = _clip(adv.clips[0]) if adv.clips else None
        extra = _clip(adv.clips[1]) if len(adv.clips) > 1 else None
        echo = _echo(vq.transcript_bn) if vq else ""
        return (_answer_text(adv, show_english), gr.Markdown(value=echo, visible=bool(echo)), main,
                gr.Audio(value=extra, visible=extra is not None), consult_id,
                gr.Button(visible=True), gr.Markdown(visible=False), _question(False), _question(False))
    return advise


def make_feedback(feedback_fn):
    def on_feedback(consult_id):
        if consult_id:
            feedback_fn(consult_id, "looks_wrong")
        return gr.Markdown(value=texts.FEEDBACK_THANKS_BN, visible=True), gr.Button(visible=False)
    return on_feedback


def build_demo(predict_fn=None, meta_fn=None, voice_fn=None, log_fn=None,
               feedback_fn=None, counts_fn=None, voice_on: bool | None = None) -> gr.Blocks:
    predict_fn = predict_fn or zerogpu.maybe_gpu(classifier.predict)
    meta_fn = meta_fn or classifier.meta
    voice_fn = voice_fn or voice.parse_voice
    log_fn = log_fn or logging_store.log_consult
    feedback_fn = feedback_fn or logging_store.log_feedback
    counts_fn = counts_fn or logging_store.counts
    voice_on = voice.voice_enabled() if voice_on is None else voice_on

    # Clips made with text-to-speech are labelled on screen. A missing clip is fine: the answer is shown as text.
    synthetic_voice = any(row.get("voice") == "computer-generated" and _clip(row["file"])
                          for row in rules.load_clips().values())
    voice_note = f"*{texts.AUDIO_SYNTHETIC_NOTE_BN} (computer-generated voice)*"

    def stats():
        c = counts_fn()
        return c["total"], c["no_spray"], c["correct_use"], c["referrals"], c["sprays_avoided"]

    with gr.Blocks(title="Kom Bish") as demo:
        consult_id = gr.State(None)
        with gr.Tab(texts.TAB_ADVICE_BN):
            gr.Markdown(f"# কম বিষ (Kom Bish)\n\n{texts.CONSENT_BN}")
            # For reviewers and judges: off by default. The app and the audio stay in Bangla either way.
            show_english = gr.Checkbox(label=texts.SHOW_ENGLISH_LABEL, value=False)
            consent_en = gr.Markdown(f"{texts.ENGLISH_NOTE}\n\n{texts.CONSENT_GLOSS_EN}", visible=False)
            if _clip("audio/consent.mp3"):
                gr.Audio(value=_clip("audio/consent.mp3"), label=texts.LABEL_LISTEN_BN,
                         interactive=False, autoplay=False)
                if synthetic_voice:
                    gr.Markdown(voice_note)
            consent = gr.Checkbox(label=texts.CONSENT_CHECKBOX_BN, value=False)
            with gr.Row():
                with gr.Column():
                    photo_help = gr.Markdown(_photo_instruction(False))
                    img = gr.Image(type="pil", sources=["upload", "webcam"], label=texts.LABEL_PHOTO_BN)
                    aud = gr.Audio(sources=["microphone", "upload"], type="filepath",
                                   label=texts.LABEL_VOICE_BN, visible=voice_on)
                    gr.Markdown(texts.VOICE_PRIVACY_NOTE_BN, visible=voice_on)
                    planning = gr.Radio(choices=[texts.YES_BN, texts.NO_BN], value=None,
                                        label=texts.SPRAY_INTENT_Q_BN)
                    # Shown only when the photo looks like blast: spray advice needs the farmer's own "yes".
                    blast_q = gr.Radio(choices=[texts.YES_BN, texts.NO_BN, texts.NOT_SURE_BN], value=None,
                                       label=rules.load_rules()["R0_CONFIRM_BLAST"]["headline_bn"], visible=False)
                    # Shown only when the photo looks like BLB: the BLB answer also needs the farmer's "yes".
                    # A separate box, so a "yes" to one question can never confirm the other.
                    blb_q = gr.Radio(choices=[texts.YES_BN, texts.NO_BN, texts.NOT_SURE_BN], value=None,
                                     label=rules.load_rules()["R0_CONFIRM_BLB"]["headline_bn"], visible=False)
                    btn = gr.Button(texts.BUTTON_ADVISE_BN, variant="primary", interactive=False)
                with gr.Column():
                    answer = gr.Markdown()
                    echo = gr.Markdown(visible=False)
                    out_audio = gr.Audio(type="filepath", label=texts.LABEL_LISTEN_BN,
                                         interactive=False, autoplay=False)
                    out_audio2 = gr.Audio(type="filepath", label=texts.LABEL_SAFETY_BN,
                                          interactive=False, autoplay=False, visible=False)
                    gr.Markdown(voice_note, visible=synthetic_voice)
                    fb_btn = gr.Button(texts.FEEDBACK_BN, variant="secondary", visible=False)
                    fb_md = gr.Markdown(visible=False)
            if EXAMPLES:
                gr.Examples(examples=[[p] for p in EXAMPLES], inputs=[img])
            consent.change(lambda c: gr.Button(interactive=bool(c)), inputs=consent, outputs=btn)
            # A new photo starts with no answer to either question.
            img.change(lambda: (_question(False), _question(False)), outputs=[blast_q, blb_q])
            show_english.change(_english_labels, inputs=show_english,
                                outputs=[consent_en, consent, img, planning, blast_q, photo_help, blb_q])
            btn.click(make_advise(predict_fn, meta_fn, voice_fn, log_fn, voice_on),
                      inputs=[consent, img, aud, planning, blast_q, show_english, blb_q],
                      outputs=[answer, echo, out_audio, out_audio2, consult_id, fb_btn, fb_md, blast_q, blb_q],
                      api_name="advise")
            fb_btn.click(make_feedback(feedback_fn), inputs=consult_id, outputs=[fb_md, fb_btn],
                         api_name="feedback")
        with gr.Tab(texts.TAB_DASHBOARD_BN):
            gr.Markdown("Anonymous counts from the consultation log. **Estimated sprays avoided "
                        "(advice-based, unverified)** = a no-spray answer (R1 or R3) given to a farmer "
                        "who said they were planning to spray. Nobody checked what the farmer did next.")
            nums = [gr.Number(label=lab, precision=0, interactive=False) for lab in (
                "Consultations", "No-spray answers (R1 + R3)", "Correct-use answers (R2)",
                "Referrals (R4-R8)", "Estimated sprays avoided (advice-based, unverified)")]
            gr.Timer(5).tick(stats, outputs=nums)
            demo.load(stats, outputs=nums)
    return demo


demo = build_demo()


def main():
    classifier.load()                 # download the model once at startup; fail loudly if missing
    logging_store.bootstrap_counts()  # seed counters from the persistent log (step 14)
    demo.launch(
        server_name="0.0.0.0",
        server_port=int(os.environ.get("PORT", 7860)),
        share="--share" in sys.argv,
        theme=gr.themes.Soft(font=[gr.themes.GoogleFont("Noto Sans Bengali"), "sans-serif"]),
        head=FONT_HEAD,
        allowed_paths=[str(ROOT / "audio"), str(ROOT / "examples")],
    )


if __name__ == "__main__":
    main()

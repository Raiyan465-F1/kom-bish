# 13 — Gradio app UI

**Goal:** Replace the placeholder with the real app: consent gate, photo, optional microphone, spray-intent question, Bangla answer text plus audio, examples, feedback button and a counters tab, all tested through `gradio_client`.
**Who:** Claude Code.
**When:** Sunday 11 October, evening.
**Covers master-plan step:** S14 (instruction file CC-08).

Context: `app.py` stays thin. The classifier (`kombish/classifier.py`) gives a label and confidence; `kombish/rules.py::decide()` picks the reviewed text and clips; the app only wires them. No model output is shown as advice: only the classifier label (inside the confirm-back line) and, if voice is used, the transcript in a separate box. Gradio is pinned at **6.29.1**: `theme`, `css`, `head` go in `demo.launch()`, not `gr.Blocks()`; microphone recordings arrive as a `.wav` file path; give the main event an explicit `api_name` (Bangla labels otherwise become garbled API parameter names). Phones block autoplay, so `autoplay=False`. Every Bangla string comes from `kombish/texts.py` or `data/*.csv` and is **DRAFT — needs native speaker review before recording** until step 06 marks it reviewed; never type new Bangla into `app.py`.

## Prerequisites

```bash
source .venv/bin/activate
test -f kombish/rules.py && test -f data/rules.csv && python -c "from kombish.rules import decide"   # [Run step 05.]
python -c "from kombish.classifier import predict, meta, Prediction"                                # [Run step 12.]
python -c "from kombish.voice import VoiceQuery, parse_voice, voice_enabled"                        # [Run step 05.]
```

## Instructions for Claude Code

### 1. Minimal `kombish/logging_store.py` (step 14 replaces the storage part; keep these function names)

Write a local-only version now: `log_consult(record) -> str` adds `id` (uuid4 hex), `type="consultation"`, `ts_utc` (UTC ISO 8601), appends one JSON line (`ensure_ascii=False`) to `logs/consults_<uuid>.jsonl`, updates in-memory counters and returns the id. `log_feedback(ref_id, feedback="looks_wrong")` appends `{"id", "type": "feedback", "ts_utc", "ref_id", "feedback"}`. `counts()` returns `{"total", "no_spray", "correct_use", "referrals", "sprays_avoided"}` using `rules.NO_SPRAY_RULES` (R1 + R3), `rules.CORRECT_USE_RULES` (R2), `rules.REFERRAL_RULES` (R4–R6); `sprays_avoided` counts R1 or R3 records with `planning_to_spray is True`. `bootstrap_counts()` is a no-op for now. Protect counters with a `threading.Lock`.

### 2. `app.py`

Write the full file following this structure (adapt details only if a Gradio 6.29.1 signature differs; check with `inspect.signature` when unsure):

```python
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


def make_advise(predict_fn, meta_fn, voice_fn, log_fn, voice_on: bool):
    def advise(consent, img, audio_path, planning):
        t0 = time.perf_counter()
        planning_to_spray = {texts.YES_BN: True, texts.NO_BN: False}.get(planning)
        if not consent or img is None:
            adv = rules.decide(None, 0.0, False, None, planning_to_spray, threshold=1.0, consent=bool(consent))
            return (adv.text_md, gr.Markdown(value="", visible=False), None,
                    gr.Audio(value=None, visible=False), None, gr.Button(visible=False), gr.Markdown(visible=False))
        m = meta_fn()
        pred = predict_fn(img)
        voice_used = bool(voice_on and audio_path)
        vq = voice_fn(audio_path) if voice_used else None
        adv = rules.decide(pred.label, pred.conf, pred.margin >= m["margin"], vq, planning_to_spray,
                           threshold=m["threshold"], consent=True, voice_failed=voice_used and vq is None)
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
        return (adv.text_md, gr.Markdown(value=echo, visible=bool(echo)), main,
                gr.Audio(value=extra, visible=extra is not None), consult_id,
                gr.Button(visible=True), gr.Markdown(visible=False))
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

    def stats():
        c = counts_fn()
        return c["total"], c["no_spray"], c["correct_use"], c["referrals"], c["sprays_avoided"]

    with gr.Blocks(title="Kom Bish") as demo:
        consult_id = gr.State(None)
        with gr.Tab(texts.TAB_ADVICE_BN):
            gr.Markdown(f"# কম বিষ (Kom Bish)\n\n{texts.CONSENT_BN}")
            if _clip("audio/consent.mp3"):
                gr.Audio(value=_clip("audio/consent.mp3"), label=texts.LABEL_LISTEN_BN,
                         interactive=False, autoplay=False)
            consent = gr.Checkbox(label=texts.CONSENT_CHECKBOX_BN, value=False)
            with gr.Row():
                with gr.Column():
                    img = gr.Image(type="pil", sources=["upload", "webcam"], label=texts.LABEL_PHOTO_BN)
                    aud = gr.Audio(sources=["microphone", "upload"], type="filepath",
                                   label=texts.LABEL_VOICE_BN, visible=voice_on)
                    gr.Markdown(texts.VOICE_PRIVACY_NOTE_BN, visible=voice_on)
                    planning = gr.Radio(choices=[texts.YES_BN, texts.NO_BN], value=None,
                                        label=texts.SPRAY_INTENT_Q_BN)
                    btn = gr.Button(texts.BUTTON_ADVISE_BN, variant="primary", interactive=False)
                with gr.Column():
                    answer = gr.Markdown()
                    echo = gr.Markdown(visible=False)
                    out_audio = gr.Audio(type="filepath", label=texts.LABEL_LISTEN_BN,
                                         interactive=False, autoplay=False)
                    out_audio2 = gr.Audio(type="filepath", label=texts.LABEL_SAFETY_BN,
                                          interactive=False, autoplay=False, visible=False)
                    fb_btn = gr.Button(texts.FEEDBACK_BN, variant="secondary", visible=False)
                    fb_md = gr.Markdown(visible=False)
            if EXAMPLES:
                gr.Examples(examples=[[p] for p in EXAMPLES], inputs=[img])
            consent.change(lambda c: gr.Button(interactive=bool(c)), inputs=consent, outputs=btn)
            btn.click(make_advise(predict_fn, meta_fn, voice_fn, log_fn, voice_on),
                      inputs=[consent, img, aud, planning],
                      outputs=[answer, echo, out_audio, out_audio2, consult_id, fb_btn, fb_md],
                      api_name="advise")
            fb_btn.click(make_feedback(feedback_fn), inputs=consult_id, outputs=[fb_md, fb_btn],
                         api_name="feedback")
        with gr.Tab(texts.TAB_DASHBOARD_BN):
            gr.Markdown("Anonymous counts from the consultation log. **Estimated sprays avoided "
                        "(advice-based, unverified)** = a no-spray answer (R1 or R3) given to a farmer "
                        "who said they were planning to spray. Nobody checked what the farmer did next.")
            nums = [gr.Number(label=lab, precision=0, interactive=False) for lab in (
                "Consultations", "No-spray answers (R1 + R3)", "Correct-use answers (R2)",
                "Referrals (R4-R6)", "Estimated sprays avoided (advice-based, unverified)")]
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
    )


if __name__ == "__main__":
    main()
```

Gotchas to handle:
- `gr.themes.GoogleFont(...)` inside `font=[...]` is **unverified until run**. If it raises, drop the `font=` argument; the `head=` link alone loads the font.
- If Gradio refuses to serve the MP3s (file-access error), add `allowed_paths=[str(ROOT / "audio")]` to `launch()`.
- The auto-generated API view lists the optional audio input as "required"; passing `None` still works.
- Remove the step-04 `_probe_fn` and probe button; the ZeroGPU shim now wraps `classifier.predict`.
- Update `tests/test_smoke.py` so it still passes (it must not need network: `build_demo()` must not load the model; `classifier.load()` runs only in `main()`).

### 3. `tests/test_app.py` — every rule path through `gradio_client`

Use fakes so tests need no model and no network:

```python
FAKE = {  # image width -> (label, conf, margin)
    101: ("bacterial_leaf_blight", 0.95, 0.9), 102: ("blast", 0.95, 0.9),
    103: ("healthy", 0.95, 0.9), 104: ("other", 0.95, 0.9), 105: ("blast", 0.40, 0.1),
}
def fake_predict(img):
    label, conf, margin = FAKE[img.size[0]]
    return Prediction(label, conf, {label: conf}, margin, conf < 0.7 or margin < 0.2)
fake_meta = lambda: {"threshold": 0.7, "margin": 0.2}
```
- Build with `build_demo(predict_fn=fake_predict, meta_fn=fake_meta, voice_fn=fake_voice, log_fn=records.append-and-return-id, feedback_fn=..., counts_fn=..., voice_on=True)` where `fake_voice` returns a high-confidence `VoiceQuery` with `symptoms=["insects_seen"]` for one test and `None` (failure) for another.
- Launch with `demo.launch(prevent_thread_lock=True, server_port=<free port>)`, connect with `gradio_client.Client(<local url>)` and call `client.predict(..., api_name="/advise")`. Use `gradio_client.handle_file(path)` for the image and a 1-second silent WAV made with the `wave` module. (Check the exact `launch` return value and `local_url` attribute in 6.29.1.) Close the demo at teardown.
- Cases and expected `rule_id` (check the logged record) and answer text (equals `rules.decide(...).text_md` for the same inputs):
  - width 101 → R1_BLB; 102 → R2_BLAST (second audio visible); 103 → R3_HEALTHY; 104 → R4_OTHER; 105 → R5_ABSTAIN
  - width 103 + voice red flag → R6_VOICE_REDFLAG; width 103 + voice failure → R3_HEALTHY and the `voice_failed` line appended
  - no photo → answer starts with `## অনুগ্রহ করে ধানের পাতার ছবি দিন।`, nothing logged
  - consent False → R0_NO_CONSENT prompt, nothing logged
- Assert every logged record has exactly the keys from `CLAUDE.md` section 6 (no photo, audio, transcript, IP, name or phone keys) and that `planning_to_spray` maps "হ্যাঁ" → True, "না" → False, unanswered → None.
- Also unit-test `make_advise` directly (fast, no server) for the same cases.

### 4. Run

```bash
source .venv/bin/activate
pytest -q
python app.py      # with MODEL_REPO set in .env; open http://localhost:7860
```
Manually: tick consent (button enables), upload a test image from `data/synthetic/prepared/test/` or any rice photo, check the answer, audio players (empty until step 16 clips exist), feedback button, dashboard counters.

## Human actions

- **HUMAN:** open http://localhost:7860, run one consultation with consent on and one with consent off. Check Bangla renders.
- **HUMAN:** commit: `git add -A && git commit -m "step 13: Gradio app" && git push`.

## Done when

- `pytest -q` passes, including `tests/test_app.py` covering R0_NO_CONSENT, R0_NO_PHOTO, R1–R6 and the voice-failure line through `gradio_client`.
- `python app.py` serves the app locally with the real model; the button stays disabled until consent is ticked.
- Logged records contain only the allowed keys.

## If it fails

- **`consent.change` does not re-enable the button:** check how Gradio 6.29.1 updates props (returning `gr.Button(interactive=True)` or `gr.update(interactive=True)`). `decide()` refuses without consent anyway, so the server-side gate still holds.
- **`gradio_client` cannot find `/advise`:** print `client.view_api()` and use the listed endpoint name.
- **Answer text shows raw HTML or broken Bangla shaping:** keep Bangla in Markdown, never in images; the font loads via `head=`.

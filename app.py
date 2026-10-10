"""Kom Bish Gradio app (placeholder until step 13)."""
import os
import sys

import gradio as gr

try:  # local only; hosts set env vars directly
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from kombish.zerogpu import maybe_gpu

APP_VERSION = os.getenv("APP_VERSION", "0.1.0")


@maybe_gpu
def _probe_fn(x):
    return "ok"


def build_demo() -> gr.Blocks:
    with gr.Blocks(title="Kom Bish") as demo:
        gr.Markdown(f"# Kom Bish (কম বিষ)\nPlaceholder build {APP_VERSION}. Hosting probe only.")
        gr.Image(type="pil", sources=["upload", "webcam"], label="ধানের পাতার ছবি")
        gr.Audio(sources=["microphone", "upload"], type="filepath", label="ভয়েস নোট (ঐচ্ছিক)")
        # Hosting probe for ZeroGPU variant B (step 04). Collapsed, so it stays out of the
        # way but can still be pressed on the Space. Step 13 replaces it with the classifier.
        with gr.Accordion("Hosting probe", open=False):
            probe_btn = gr.Button("probe")
            probe_out = gr.Textbox(label="probe result")
        probe_btn.click(_probe_fn, inputs=probe_out, outputs=probe_out, api_name="probe")
    return demo


demo = build_demo()

if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",
        server_port=int(os.environ.get("PORT", 7860)),
        share="--share" in sys.argv,
    )

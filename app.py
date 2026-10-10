"""Kom Bish Gradio app (placeholder until step 13)."""
import os
import sys

import gradio as gr

try:  # local only; hosts set env vars directly
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from kombish import zerogpu  # noqa: F401  (registers the ZeroGPU probe from step 04)

APP_VERSION = os.getenv("APP_VERSION", "0.1.0")


def build_demo() -> gr.Blocks:
    with gr.Blocks(title="Kom Bish") as demo:
        gr.Markdown(f"# Kom Bish (কম বিষ)\nPlaceholder build {APP_VERSION}. Hosting probe only.")
        gr.Image(type="pil", sources=["upload", "webcam"], label="ধানের পাতার ছবি")
        gr.Audio(sources=["microphone", "upload"], type="filepath", label="ভয়েস নোট (ঐচ্ছিক)")
    return demo


demo = build_demo()

if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",
        server_port=int(os.environ.get("PORT", 7860)),
        share="--share" in sys.argv,
    )

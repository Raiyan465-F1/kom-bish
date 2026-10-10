# 03 — Repo scaffold

**Goal:** Create the repo skeleton, pinned requirements, a placeholder Gradio app that runs, a smoke test and CI.
**Who:** Claude Code (the human only runs the done checks and commits).
**When:** Saturday 10 October, evening. Before step 04 (hosting probe, gate G1 at 10 PM).
**Covers master-plan step:** S04 (instruction file CC-01).

Context: Kom Bish is a Gradio 6 app (Python 3.12, `gradio==6.29.1`, ONNX Runtime, no torch) that gives a pre-written Bangla answer for a rice-leaf photo. All config comes from environment variables. The same code must run on a ZeroGPU HF Space, on Render free and on a laptop. Read `CLAUDE.md` first; its names and versions are binding. The Bangla UI labels in this file are **DRAFT — needs native speaker review before recording**.

## Prerequisites

Verify first. If any check fails, stop and print the message in brackets.

```bash
git rev-parse --show-toplevel          # [Run this inside the cloned kom-bish repo. Clone it first (step 01).]
test -f CLAUDE.md && test -d steps     # [Copy CLAUDE.md to the repo root and the step files into steps/ (step 01).]
python3.12 --version                   # [Install Python 3.12. Windows: py -3.12 --version]
git remote -v                          # [The repo needs a GitHub remote named origin.]
```

Do not overwrite `CLAUDE.md` or anything in `steps/`.

## Instructions for Claude Code

1. Create this layout (empty packages get a docstring only):

```
app.py  README.md  LICENSE  CHANGELOG.md  pytest.ini
requirements.txt  requirements-render.txt  requirements-dev.txt  .env.example  .gitignore
kombish/__init__.py classifier.py rules.py voice.py logging_store.py texts.py zerogpu.py
data/.gitkeep  audio/.gitkeep  examples/.gitkeep  training/.gitkeep  scripts/.gitkeep
deck/screens/.gitkeep  video/.gitkeep  submission/.gitkeep  docs/gates.md
tests/__init__.py  tests/test_smoke.py
.github/workflows/tests.yml
```

2. `requirements.txt` (HF Space build; `spaces` only matters on ZeroGPU, the decorator "has no effect in non-ZeroGPU environments"):

```
gradio==6.29.1
onnxruntime==1.31.0
numpy<3
pillow==12.3.0
huggingface_hub==2.2.0
google-genai==2.29.0
pydantic>=2.11
spaces
```

3. `requirements-render.txt`: identical **minus** the `spaces` line (its install footprint was not checked).

4. `requirements-dev.txt`:

```
pytest
ruff
python-dotenv
```

After installing, run `pip freeze | grep -iE "^(pytest|ruff|python-dotenv)=="` and pin those exact versions in the file.

5. `.gitignore`:

```
.env
__pycache__/
*.pyc
.venv/
.venv-train/
venv/
logs/
flagged/
.gradio/
*.onnx
*.pt
*.pth
.ipynb_checkpoints/
.DS_Store
data/raw/
data/train/
data/val/
data/test/
data/dhs_field_blast/
data/synthetic/
models/
raw_audio/
voice_tests/
own_photos/
junk_photos/
submission/private/
video/*.mp4
```

6. `.env.example` (no real values):

```
MODEL_REPO=<hf-user>/kom-bish-rice-leaf
LOG_REPO=<hf-user>/kom-bish-logs
HF_TOKEN=
GEMINI_API_KEY=
GEMINI_MODEL=gemini-3.5-flash-lite
VOICE_ENABLED=false
APP_VERSION=0.1.0
ZEROGPU_MODE=noop
# PORT is set by Render. Leave it unset locally (the app defaults to 7860).
```

Then `cp .env.example .env` (the human fills secrets later; `.env` stays git-ignored).

7. `LICENSE`: standard MIT text, copyright line `Copyright (c) 2026 Team Unsick`.

8. `README.md`: the HF YAML front matter must be the very first lines (HF defaults `python_version` to 3.10, so set it):

```yaml
---
title: Kom Bish
emoji: 🌾
colorFrom: green
colorTo: yellow
sdk: gradio
sdk_version: 6.29.1
python_version: "3.12"
app_file: app.py
short_description: Bangla rice adviser that says whether to spray at all
license: mit
---
```

Below it, add `# Kom Bish (কম বিষ)` and one line: "Work in progress. The judge-facing README is written in step 23."

9. `pytest.ini`:

```ini
[pytest]
addopts = -m "not final"
markers =
    final: release checks (real clips present, reviewed text, no TODO-C placeholders); run with pytest -m final
testpaths = tests
```

10. `kombish/zerogpu.py` (stub; step 04 replaces it):

```python
"""ZeroGPU shim. Step 04 fills this in. Until then it is a no-op."""


def maybe_gpu(fn):
    return fn
```

11. Other `kombish/*.py` files: a one-line module docstring each, stating what later step fills them (classifier → 12, rules/texts → 05, voice → 15, logging_store → 14).

12. `app.py` placeholder. It must expose `build_demo()` and a module-level `demo`, read `PORT`, bind `0.0.0.0`, and include an image input and a microphone input so step 04 can test the phone's permission prompt:

```python
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
```

Gradio 6 note: `theme`, `css` and `head` go in `demo.launch()`, never in `gr.Blocks()` (deprecated there).

13. `tests/test_smoke.py`:

```python
import gradio as gr


def test_app_builds_without_network():
    import app
    assert isinstance(app.build_demo(), gr.Blocks)


def test_no_torch_in_app():
    import sys
    import app  # noqa: F401
    assert "torch" not in sys.modules
```

14. `.github/workflows/tests.yml`. Use `actions/checkout@v6` (from the HF GitHub Actions guide). For `actions/setup-python`, check the current major version at run time (it is not in our sources) and pin that tag:

```yaml
name: tests
on:
  push:
  pull_request:
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
      - uses: actions/setup-python@<current-major>   # check at run time
        with:
          python-version: "3.12"
      - run: pip install -r requirements-render.txt -r requirements-dev.txt
      - run: pytest -q
        env:
          MODEL_REPO: ${{ vars.MODEL_REPO }}
```

15. `docs/gates.md`: a table with rows G1–G7 (name, deadline, decision, date, who). Deadlines: G1 Sat 10 PM hosting route; G2 Sun 6 PM trained ONNX; G3 Sun 10 PM voice on/off; G4 Mon noon hosted app works on phones; G5 Mon 9 PM feature freeze `v1.0`; G6 Tue 8 PM all files final; G7 Wed 10:00 PM email hard stop.

16. `CHANGELOG.md`: heading and an "Unreleased" section with "Scaffold (step 03)".

17. Create the app venv and run the checks:

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements-render.txt -r requirements-dev.txt
pytest -q
python app.py    # open http://localhost:7860, then Ctrl+C
```

18. Show `git status`. Confirm `.env` is **not** listed. Ask the human to commit and push.

## Human actions

- **HUMAN:** open http://localhost:7860 in a browser and confirm the page loads.
- **HUMAN:** commit and push: `git add -A && git commit -m "step 03: repo scaffold" && git push`.
- **HUMAN:** open the repo's **Actions** tab on GitHub and confirm the `tests` workflow is green.

## Done when

```bash
pip install -r requirements-render.txt -r requirements-dev.txt && pytest -q && python app.py
```
- `pytest -q` passes (2 tests).
- `python app.py` serves a page at http://localhost:7860 with an image box and a microphone box.
- `git status` never shows `.env`, `data/raw/` or `models/`.
- The GitHub Actions `tests` run is green.

## If it fails

- **`onnxruntime==1.31.0` will not install:** the Python version is below 3.11. Recreate `.venv` with Python 3.12.
- **`pip` resolves a different gradio:** make sure `gradio==6.29.1` is pinned in both requirements files and in the README `sdk_version`.
- **CI fails on setup-python:** fix the action tag to the current major version and push again.
- **Port 7860 busy:** `PORT=7861 python app.py`.

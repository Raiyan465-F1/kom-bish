# 04 — Hosting probe (gate G1)

**Goal:** Get the placeholder app live over HTTPS on a phone, test the ZeroGPU shim, and fix the hosting route by 10 PM.
**Who:** Both. Claude Code writes the shim and host settings; the human (B) creates the Space and the Render service and tests on a phone.
**When:** Saturday 10 October. **Gate G1 at 10 PM:** hosting route = ZeroGPU / Render / both.
**Covers master-plan step:** S05 (first half of instruction file CC-02; step 17 does the rest).

Context: HF docs now say creating a Gradio Space needs a paid plan, except ZeroGPU Spaces, which free accounts can create if older than 30 days with a verified email (up to 2 Spaces). ZeroGPU works only with the Gradio SDK, supports Python 3.12.12 and 3.10.13, and needs at least one function decorated with `@spaces.GPU`. A Space with none has thrown "No @spaces.GPU function detected during startup". Whether a never-called decorated no-op passes that check is **unverified**, so test two variants. Never import torch (avoids ZeroGPU's CUDA emulation). Deploy to **Render free** regardless (512 MB RAM, 750 instance hours a month, sleeps after 15 min idle, about a minute to wake). The laptop `share=True` link is the live-pitch backup. Phones need HTTPS for the mic and camera; never use a LAN IP or the embedded Space page.

## Prerequisites

Verify first. Stop with the bracketed message if a check fails.

```bash
test -f app.py && test -f kombish/zerogpu.py     # [Run step 03 first.]
grep -q "^spaces" requirements.txt               # [requirements.txt must list spaces (step 03).]
! grep -q "^spaces" requirements-render.txt      # [requirements-render.txt must NOT list spaces.]
git log --oneline -1                             # [Commit and push step 03 first.]
```

Ask the human: "Which HF account (if any) is older than 30 days with a verified email?" Record the answer in `docs/gates.md` under G1. If none, skip the ZeroGPU parts and do Render plus the laptop backup.

## Instructions for Claude Code

1. Replace `kombish/zerogpu.py` with the two-variant shim. Variant is chosen by the env var `ZEROGPU_MODE` (`noop` default, or `wrap`), so the human can switch it in Space settings without a commit:

```python
"""ZeroGPU shim.

ZeroGPU Spaces need at least one @spaces.GPU function at startup. The decorator has no
effect outside ZeroGPU. Kom Bish runs ONNX on CPU and never imports torch.

ZEROGPU_MODE=noop (default): define a decorated function that is never called (variant A).
ZEROGPU_MODE=wrap: also wrap the classifier call in @spaces.GPU(duration=10) (variant B).
Variant B spends each visitor's daily ZeroGPU quota (2 min anonymous, 5 min free account).
"""
import os

try:
    import spaces  # installed from requirements.txt on the HF Space only
except ImportError:  # Render, laptop, CI
    spaces = None


def _mode() -> str:
    return os.getenv("ZEROGPU_MODE", "noop").strip().lower()


if spaces is not None:
    @spaces.GPU(duration=10)
    def _zerogpu_startup_probe():  # variant A: never called
        return None


def maybe_gpu(fn):
    """Return fn unchanged, or wrapped in spaces.GPU(duration=10) when ZEROGPU_MODE=wrap."""
    if spaces is not None and _mode() == "wrap":
        return spaces.GPU(duration=10)(fn)
    return fn
```

2. In the placeholder `app.py`, add a tiny function routed through the shim so variant B has something to wrap before the real classifier exists (step 13 replaces it with the classifier):

```python
from kombish.zerogpu import maybe_gpu

@maybe_gpu
def _probe_fn(x):
    return "ok"
```

Add a hidden `gr.Button("probe")` → `gr.Textbox` wired to `_probe_fn` so variant B can be exercised on the Space.

3. Add `tests/test_zerogpu.py`: with `spaces` not installed, `maybe_gpu(f) is f` for both `ZEROGPU_MODE` values (use `monkeypatch.setenv`).

4. Write a Render settings block into `docs/gates.md` (under G1) for the human to copy:
   - Service type: Web Service, from the GitHub repo `kom-bish`, branch `main`.
   - Runtime: Python. Build command: `pip install -r requirements-render.txt`. Start command: `python app.py`.
   - Instance type: Free.
   - Python 3.12: Render's mechanism for choosing the Python version is **not in our sources**. Open Render's docs at run time, find how to pin Python 3.12, and write the exact setting here. If unclear, stop and ask the human to check in the Render dashboard.
   - Environment variables for now: `APP_VERSION=0.1.0`. (`PORT` is set by Render; the app already reads it.)

5. Write the HF Space checklist into `docs/gates.md` (for the human):
   - New Space → name `kom-bish` → SDK **Gradio** → hardware **ZeroGPU** → public.
   - Upload the repo files (web "Add file > Upload file", or clone the Space repo and push). Step 17 automates this with the official sync action.
   - Space Settings → Variables: `ZEROGPU_MODE=noop`, `APP_VERSION=0.1.0`.
   - Direct phone URL: `https://<hf-user>-kom-bish.hf.space` (not the huggingface.co/spaces page, which embeds the app in an iframe).

6. Run `pytest -q` and `python app.py` locally. Then run `python app.py --share`, print the `*.gradio.live` URL, and ask the human to open it on a phone (this proves the laptop backup works).

7. After the human reports results, fill G1 in `docs/gates.md`: route chosen (ZeroGPU / Render / both), which ZeroGPU variant works, URLs, date, who.

## Human actions

- **HUMAN (B), ZeroGPU route if eligible:** create the Space as in item 5. Wait for the build. Check the Space logs.
  - First test `ZEROGPU_MODE=noop`. If the logs show "No @spaces.GPU function detected during startup" or the Space fails, set `ZEROGPU_MODE=wrap` in Settings → Variables, restart, and test again (press the probe button once).
  - Report to Claude Code: which variant started, and any log errors (paste them).
- **HUMAN (B), Render (do this regardless):** create the web service with the settings Claude Code wrote. Wait for the deploy. Open the `https://…onrender.com` URL.
- **HUMAN (B), phone test:** on a phone over mobile data, open each HTTPS URL directly. Tap the microphone box. The browser must ask for microphone permission. Tap the image box; the phone should offer the camera or gallery.
- **HUMAN:** commit and push: `git add -A && git commit -m "step 04: hosting probe" && git push`.

## Done when

- `pytest -q` passes, including `tests/test_zerogpu.py`.
- At least one hosted HTTPS URL opens on a phone and the browser asks for microphone permission.
- The laptop `python app.py --share` link opens on a phone.
- `docs/gates.md` G1 row says: ZeroGPU / Render / both, the working ZeroGPU variant (if any), the URLs, date and owner.
- Team chat shows the G1 decision before 10 PM.

## If it fails

- **ZeroGPU rejects both variants, or no eligible account:** primary = Render with the keep-awake ping (step 17); live pitch = laptop `share=True`. Optional: a free Static Space landing page later (step 25). PRO (USD 9) only by team choice.
- **Render deploy fails on Python version:** pin Python 3.12 using Render's documented method, then redeploy. onnxruntime 1.31.0 needs Python ≥ 3.11.
- **Render asks for a card:** do not add one without a team decision. Use ZeroGPU if it works, else the laptop share link.
- **Phone does not ask for mic permission:** make sure the URL starts with `https://` and is the direct app URL, not an iframe. Try Chrome on Android and Safari on iPhone.
- **Space stuck on "Paused" after a push:** reported by forum users on free accounts in 2026. Restart from Settings (owner only). If it persists, switch the primary link to Render.

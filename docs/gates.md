# Gates G1–G7

Fill in **Decision**, **Date** and **Who** when each gate is decided.

| Gate | Name | Deadline | Decision | Date | Who |
|---|---|---|---|---|---|
| G1 | Hosting route | Sat 10 Oct, 10 PM | TODO-HUMAN: ZeroGPU / Render / both? Which ZeroGPU variant works? URLs? (see "G1 — hosting route" below) | | |
| G2 | Trained ONNX | Sun 11 Oct, 6 PM | TODO-HUMAN: not trained yet. Needs the raw datasets (step 02), the folder mapping (step 07 Part B) and the Kaggle run (step 10). | | |
| G3 | Voice on/off | Sun 11 Oct, 10 PM | TODO-HUMAN: not scored yet. Needs `GEMINI_API_KEY` and 10 test notes (step 15). Until then `VOICE_ENABLED=false` (photo-only). | | |
| G4 | Hosted app works on phones | Mon 12 Oct, noon | | | |
| G5 | Feature freeze `v1.0` | Mon 12 Oct, 9 PM | | | |
| G6 | All files final | Tue 13 Oct, 8 PM | | | |
| G7 | Email hard stop | Wed 14 Oct, 10:00 PM | | | |

## Data counts

- RiceLeafBD and BD5: TODO-HUMAN. Counts are checked against the published figures when
  `training/prepare_data.py` runs on the real folders (step 07 Part B). Write one line here per mismatch.
- Dhan-Shomadhan (HF mirror `Project-AgML/Dhan-Shomadhan_rice_leaf_disease_classification`), loaded locally
  with `datasets==5.1.0` on 11 Oct 2026: 1,106 rows in total; **74 field-background "Rice Blast" images**
  (198 more on a white background, which are not used). These 74 are the held-out cross-source blast test.

## Code checks done without the real model (11 Oct 2026)

These prove the code runs. They are not results and must never be reported as accuracy.

- Full pipeline on synthetic random-noise images (`training/make_synthetic_data.py`): prepare → train →
  temperature → threshold → ONNX export. ONNX parity max |ORT − torch| = 1.57e-05; `model.onnx` is one
  17.1 MB file; batch 1 and 4 run.
- `training/check_parity.py` on that synthetic export: app preprocessing vs timm eval transform,
  max difference 0.0 over 5 image sizes.
- Local torch for these checks: 2.14.1+cpu. Kaggle's torch version is still unknown (the notebook prints it).

## G1 — hosting route

Status on Sun 11 Oct: code side done (ZeroGPU shim, probe button, tests). Hosted deploys and the phone
test are still open, so G1 is undecided and already past its Sat 10 PM deadline.

**TODO-HUMAN:** Which HF account (if any) is older than 30 days with a verified email? Write the account
name here. If none, skip the ZeroGPU Space and use Render plus the laptop backup.

- HF account for ZeroGPU: TODO-HUMAN
- ZeroGPU variant that started (`noop` / `wrap` / neither): TODO-HUMAN
- HF Space URL: TODO-HUMAN
- Render URL: TODO-HUMAN
- Phone test (mic permission prompt seen, camera/gallery offered): TODO-HUMAN

### Render settings (copy into the Render dashboard)

| Setting | Value |
|---|---|
| Service type | Web Service, from the GitHub repo `kom-bish`, branch `main` |
| Runtime | Python |
| Build command | `pip install -r requirements-render.txt` |
| Start command | `python app.py` |
| Instance type | Free |
| Environment variables | `APP_VERSION=0.1.0` (`PORT` is set by Render; the app already reads it) |

Python 3.12 (checked on 11 Oct 2026 at https://render.com/docs/python-version):

- The repo root has a `.python-version` file containing `3.12`. Render reads it and uses the latest 3.12 patch.
  Nothing to set in the dashboard.
- Render's default for new services is Python 3.14.3, so the pin is needed.
- A `PYTHON_VERSION` environment variable takes precedence over the file and must be a fully qualified
  version (major.minor.patch). Do not set it unless the file is ignored; if you must, use a full 3.12.x
  version such as `3.12.10` (the version in the local `.venv`).

The GitHub repo is private right now. Render can deploy it once you connect your GitHub account, but
judges cannot open a private repo: make it public before submission (step 26 audit).

### HF Space checklist (ZeroGPU route, only if an eligible account exists)

1. New Space → name `kom-bish` → SDK **Gradio** → hardware **ZeroGPU** → public.
2. Upload the repo files (web "Add file > Upload file", or clone the Space repo and push).
   Step 17 automates this with the official sync action.
3. Space Settings → Variables: `ZEROGPU_MODE=noop`, `APP_VERSION=0.1.0`.
4. Wait for the build and read the Space logs.
   - If the logs show "No @spaces.GPU function detected during startup" or the Space fails, set
     `ZEROGPU_MODE=wrap`, restart, open the "Hosting probe" section at the bottom of the page and press
     **probe** once. It should show `ok`.
5. Direct phone URL: `https://<hf-user>-kom-bish.hf.space` (not the huggingface.co/spaces page, which
   embeds the app in an iframe).

### Phone test (HTTPS only, over mobile data)

Open each HTTPS URL directly. Tap the microphone box: the browser must ask for microphone permission.
Tap the image box: the phone should offer the camera or gallery. Never use a LAN IP.

### Laptop backup

`python app.py --share` prints a `*.gradio.live` HTTPS link (best effort, lasts up to 1 week while the
process runs). Verified on 11 Oct 2026 that the link is created and serves the page; a phone test of
that link is still TODO-HUMAN.

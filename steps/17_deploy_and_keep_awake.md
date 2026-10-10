# 17 — Deploy the full app (ZeroGPU Space, Render, laptop backup) and keep it awake

**Goal:** Ship the full app to the host(s) chosen at gate G1, with secrets set, GitHub-to-Space sync, a keep-awake ping for Render, and a tested laptop backup.
**Who:** Both. Claude Code writes the workflows and a hosted smoke test; the human (B) sets secrets and variables and checks the hosts.
**When:** Monday 12 October, morning. Before gate G4 (noon).
**Covers master-plan step:** S18 (second half of instruction file CC-02).

Context: The same code runs on a ZeroGPU Space (`requirements.txt`, includes `spaces`), on Render free (`requirements-render.txt`, no `spaces`; `python app.py`; `PORT` from Render) and on a laptop (`python app.py --share`, a `*.gradio.live` HTTPS link lasting up to one week, best effort). If both hosts work, the HF Space is the primary judge link (free hardware sleeps only after 48 h without visits) and Render is the mirror (sleeps after 15 min idle, about a minute to wake). GitHub-to-Space sync uses the official `huggingface/hub-sync@v0.1.0` action on pushes to `main`: it mirrors files with the `hf` CLI (not git), skips `.github/`, deletes on the Hub any file deleted on GitHub, and avoids the >10 MB Git LFS rule. Every push to `main` rebuilds the Space.

## Prerequisites

```bash
grep -A3 "G1" docs/gates.md                         # [Gate G1 must record the hosting route (step 04).]
source .venv/bin/activate && pytest -q              # [All tests must pass before deploying.]
test -f models/labels.json && grep -q "^MODEL_REPO=" .env && grep -q "^LOG_REPO=" .env   # [Steps 11 and 14.]
ls audio/*.mp3 | wc -l                              # expect 7 (step 16); deploying earlier is allowed, text still works
```
Read the G1 route. Do only the parts for the chosen host(s), plus the laptop backup.

## Instructions for Claude Code

### 1. `.github/workflows/sync-to-hub.yml` (only if the route includes ZeroGPU)

```yaml
name: Sync to Hugging Face Space
on:
  push:
    branches: [main]
  workflow_dispatch:
jobs:
  sync:
    if: ${{ vars.HF_SPACE_ID != '' }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
      - uses: huggingface/hub-sync@v0.1.0
        with:
          github_repo_id: ${{ github.repository }}
          huggingface_repo_id: ${{ vars.HF_SPACE_ID }}
          hf_token: ${{ secrets.HF_SYNC_TOKEN }}
```
Open the action's README at run time and confirm the input names and whether a repo-type/Space input is needed (the official guide's example uses the three inputs above and defaults `space_sdk` to gradio). The secret is named `HF_SYNC_TOKEN` on purpose: it is a different token from the app's log-only `HF_TOKEN`.

Optionally make it depend on tests (`needs:` a test job, or `workflow_run` after `tests`), so a red build never reaches the Space.

### 2. `.github/workflows/keep-awake.yml` (only if the route includes Render)

```yaml
name: Keep Render awake
on:
  schedule:
    - cron: "*/10 * * * *"
  workflow_dispatch:
jobs:
  ping:
    if: ${{ vars.RENDER_URL != '' }}
    runs-on: ubuntu-latest
    steps:
      - run: curl -sS -m 90 -o /dev/null -w "%{http_code}\n" "${{ vars.RENDER_URL }}" || true
```
Arithmetic for the README/gates: one service running all month uses 744 hours (31 × 24) against Render's 750 free instance hours, so pinging every 10–14 minutes stays inside the free hours. Scheduled runs can start late; check the Actions tab.

### 3. `scripts/smoke_hosted.py`

`python scripts/smoke_hosted.py <base_url> --images <dir>`: uses `gradio_client.Client(base_url)` to call `/advise` with: consent off; consent on and no photo; and each image in `<dir>` (consent on, no audio, planning "না"). Prints the first line of each answer (the headline) and the latency. Allow up to 90 s for the first call (Render wake-up). Exit non-zero if any call errors.

### 4. Requirements check

Confirm `requirements.txt` and `requirements-render.txt` differ only by the `spaces` line, and the README front matter still says `sdk_version: 6.29.1` and `python_version: "3.12"`. If the route is Render-only, leave `requirements.txt` as is (it is harmless) but do not create the sync workflow.

### 5. Write the host settings into `docs/gates.md` (no secret values)

Per host: URL, variables set (`MODEL_REPO`, `LOG_REPO`, `GEMINI_MODEL`, `VOICE_ENABLED`, `APP_VERSION`, `ZEROGPU_MODE` on the Space), secrets set (names only: `HF_TOKEN`, `GEMINI_API_KEY`), date, who.

## Human actions

### HF ZeroGPU Space (if G1 includes it) — HUMAN (B)
- [ ] Space **Settings → Variables**: `MODEL_REPO`, `LOG_REPO`, `GEMINI_MODEL` (from G3), `VOICE_ENABLED` (from G3), `APP_VERSION=1.0.0-rc`, `ZEROGPU_MODE` (the variant that worked in G1).
- [ ] Space **Settings → Secrets**: `HF_TOKEN` (the log-only token from step 14), `GEMINI_API_KEY`. (Both reach the app as environment variables.)
- [ ] Create a HF token with write access to the Space only. In GitHub: **Settings → Secrets and variables → Actions** → secret `HF_SYNC_TOKEN`; variable `HF_SPACE_ID=<hf-user>/kom-bish`.
- [ ] Push to `main` (or run the workflow manually). Watch the Space build logs. Open `https://<hf-user>-kom-bish.hf.space`.

### Render (if G1 includes it) — HUMAN (B)
- [ ] Service **Environment**: the same variables and secrets (no `ZEROGPU_MODE` needed). `PORT` is set by Render.
- [ ] Redeploy. Open the `https://…onrender.com` URL (first load can take about a minute).
- [ ] GitHub Actions variable `RENDER_URL=<that URL>`. Run "Keep Render awake" once manually; check it prints 200.

### Laptop backup — HUMAN (B)
- [ ] With `.env` filled, run `python app.py --share`, open the `*.gradio.live` link on a phone, complete one consultation. Note: fine for a live pitch, not for judges browsing later.

### Smoke test and logs — HUMAN
- [ ] Put 4–6 test images (one per class if possible, plus one non-leaf photo) in a local folder and run `python scripts/smoke_hosted.py <url> --images <folder>` against each hosted URL. Paste the output to Claude Code.
- [ ] After about 10 minutes, confirm new lines from the hosted app appear in the `kom-bish-logs` dataset (`app_version` shows the hosted value).
- [ ] Commit: `git add -A && git commit -m "step 17: deployment workflows" && git push`.

## Done when

- Each chosen hosted URL completes consultations through every reachable path: no consent, no photo, and real photos giving BLB, blast, healthy, other or abstain answers (exact classes depend on the images; at least one spray-path and one referral-path answer shown).
- Logs from the hosted app arrive in the private dataset.
- Sync workflow (Space route) and keep-awake workflow (Render route) run green.
- The laptop share link works on a phone.
- `docs/gates.md` lists URLs and the names of variables and secrets per host.

## If it fails

- **Space build fails with "No @spaces.GPU function detected":** set `ZEROGPU_MODE=wrap` and restart; if both variants fail, make Render primary.
- **Space stuck "Paused" or 403 quota errors:** restart from Settings (owner only); if it persists, Render becomes the primary link.
- **Render out of memory:** confirm no torch slipped into `requirements-render.txt` (the onnxruntime stack measured about 166 MB before loading the model).
- **Render sleeps during judging:** keep-awake must be running; also open the link 2 minutes before any live check.
- **Paying USD 9 for one month of HF PRO** (CPU Basic Space) is the most reliable route but breaks the no-budget rule: team decision only.
- **Secret accidentally committed:** rotate it immediately on HF/Google, then remove it from the repo. HF's Secrets Scanner or GitHub push protection may warn first.

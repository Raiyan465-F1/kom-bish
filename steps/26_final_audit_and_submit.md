# 26 — Final pre-submission audit, submission, email reply and hands off (gate G7)

**Goal:** Prove every link works for a stranger, submit on Worker Studio, reply to the selection email, then change nothing.
**Who:** Both. Claude Code runs an automated preflight; humans do the link audit (someone other than B), the Worker Studio submission (C) and the email (lead).
**When:** Wednesday 14 October. Link audit **by noon**; Worker Studio submitted **by 3 PM**; email **by about 6 PM**; **hard stop 10:00 PM** for the email (gate G7). Worker Studio itself closes at 11:59 PM GMT+6, but the email's 10:00 PM governs.
**Covers master-plan steps:** S30, S31, S32, S33.

Context: Judges see the work with no presenter, from their own devices. Every link must open from a phone on mobile data and from a private laptop window. Submitting on Worker Studio locks the entry. After the email is sent, nothing in the Drive folder or on `main` changes (a push to `main` rebuilds the Space).

## Prerequisites

- Gate G6 passed (step 25): Drive folder shared, Worker Studio draft saved, email draft ready.
- Claude Code check:
  ```bash
  git status --short                      # [Working tree must be clean; commit or discard changes.]
  git tag | grep -q "^v1.0"               # [Tag v1.0 must exist (step 21).]
  test -f submission/private/email_reply.md && test -f submission/private/links.txt   # [Finish step 25.]
  ```

## Instructions for Claude Code

### 1. `scripts/preflight.py` — run it and print a PASS/FAIL table

Checks:
1. Git: on `main`, clean tree, `v1.0` (or later) tag exists, local `main` equals `origin/main`.
2. Tests: `pytest -q` and `pytest -q -m final` pass (report any PENDING-reviewer exception recorded in `docs/gates.md`).
3. Secrets: `.env` is not tracked (`git ls-files .env` is empty); no tracked file matches `hf_[A-Za-z0-9]{20,}` or `AIza[0-9A-Za-z_\-]{20,}`; `submission/private/` is not tracked.
4. Placeholders: no `TODO-C`, `TODO-HUMAN`, `VIDEO_URL_TODO`, `<gh-user>`, `<hf-user>` in tracked files outside `steps/`, `CLAUDE.md`, `.env.example` and `*_template*`/`*_draft*` files.
5. README: starts with the YAML front matter; contains `sdk_version: 6.29.1` and `python_version: "3.12"`; contains a ```` ```mermaid ```` block, "Real vs mocked", all three DOIs (`10.17632/kx9rx8p2mz.1`, `10.17632/sjkptpgv79.2`, `10.17632/znsxdctwtt.1`), "CC BY 4.0", the demo URL and a YouTube URL; is under 500 KiB.
6. Numbers: every number from `training/eval_summary.json` quoted in the README appears with the same value.
7. Requirements: `gradio==6.29.1`, `onnxruntime==1.31.0`, `pillow==12.3.0`, `huggingface_hub==2.2.0`, `google-genai==2.29.0` in both requirement files; `spaces` only in `requirements.txt`; no `torch` in either.
8. Files: `audio/<clip>.mp3` for all 7 wired clips; `examples/` has 4–6 JPEGs with empty EXIF; `deck/Kom_Bish_deck.pptx` exists with ≤ 8 slides.
9. Links (network): GitHub repo URL returns 200 without login (public); each demo URL returns 200 within 90 s (Render wake-up); `hf_hub_download(MODEL_REPO, "labels.json")` works with no token and a temporary cache; each URL in `submission/private/links.txt` starting with `https://` returns a non-error status (YouTube and Drive may block scripts; mark them "check by hand" instead of failing).

Print the table, then the list of manual checks below. Do not fix anything silently: report each FAIL with the exact file and line.

### 2. Fix loop

For each FAIL, propose the smallest fix. Code fixes need tests and the human's go-ahead (feature freeze is on). Documents can be fixed directly. Re-run preflight until all automated checks pass.

### 3. After the email is sent

Print this reminder and stop: "Hands off. No pushes to main. Do not edit or move files in the Drive folder. Visit the demo once a day. Keep the Render keep-awake workflow running."

## Human actions

### Link audit by noon — HUMAN (someone other than B), signed in `docs/gates.md`
From a **phone on mobile data** and from a **private laptop window**:
- [ ] GitHub repo opens without login; README renders with the diagram; README links work.
- [ ] Demo wakes and completes one consultation (consent → photo → answer → audio plays).
- [ ] YouTube video plays (Unlisted link) with subtitles.
- [ ] Drive folder opens; the deck downloads; the video plays or shows processing.
- [ ] Model repo page opens.
- [ ] Write "Link audit passed — <name> — <time>" in `docs/gates.md` and commit (this is the last commit before the email).

### Worker Studio submission by 3 PM — HUMAN (C)
- [ ] Open the draft; check the preview; links in order (GitHub, YouTube, demo).
- [ ] Re-open the hosted demo in a new tab (required before submit).
- [ ] Choose track **Inclusive Rural Development & Agriculture** if offered.
- [ ] Submit. Confirm the status shows **Submitted**. Screenshot it. (The entry is now locked.)

### Email reply by about 6 PM (hard limit 10:00 PM) — HUMAN (lead)
- [ ] Open the **original selection email** and press **Reply** (stay on the thread).
- [ ] Paste `submission/private/email_reply.md`: team name, project name, Drive folder link, GitHub, live demo and YouTube links inline.
- [ ] Send. Screenshot the sent message. Post the screenshot in the team chat. Record the time in `docs/gates.md` locally (do not push).

### Hands off — HUMAN (all), until results
- [ ] No pushes to `main`. No edits, renames or moves in the Drive folder.
- [ ] Visit the demo once a day; keep the Render keep-awake workflow running.
- [ ] For the 24 October finale: the live demo runs from a laptop (`python app.py --share`) with the hosted copies as backup.

## Done when (gate G7)

- Preflight shows PASS for every automated check; the manual link audit is signed by noon.
- Worker Studio shows "Submitted" (screenshot kept), done by 3 PM.
- The email reply is sent on the original thread by about 6 PM and never later than 10:00 PM (screenshot kept).
- Nothing in the Drive folder or on `main` changes after the reply.

## If it fails

- **Demo down at audit time:** switch the primary link in `links.txt`, README and the email to the host that works (Render mirror or Space), re-upload `links.txt` to Drive **before** sending the email. Keep the laptop share link for live checks only.
- **Repo shows 404 to strangers:** it is private; make it public (Settings → General → Danger Zone → Change visibility).
- **Worker Studio blocks submission:** check unsaved changes, the hosted-demo check and the track; if still blocked, contact Organizer support, and send the email anyway (the email deadline governs).
- **Running late:** send the email with what exists before 10:00 PM. A late perfect submission scores nothing.

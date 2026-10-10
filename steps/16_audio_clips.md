# 16 — Record and process the Bangla audio clips

**Goal:** Turn the reviewed Bangla scripts into one human-recorded MP3 per answer, named by clip ID, matching the on-screen text word for word.
**Who:** Both. The human (C) records; Claude Code normalises, converts and checks.
**When:** Sunday 11 October, after step 06 is signed off.
**Covers master-plan step:** S17 (instruction file CC-11).

Context: Spoken output is pre-recorded human audio, one clip per answer. No free Bangladeshi synthetic voice exists without a card, and a teammate's voice is also a pitch asset. MP3 mono at 64–96 kbps plays on Android Chrome and iPhone Safari. Clips must say exactly the reviewed `text_bn` in `data/clips.csv`. Offline fallback for a clip C cannot record in time: Gemini 3.8 Flash TTS (lists Bangla, free tier), generated offline, **never called live**, and labelled as synthetic.

Clip IDs and files (from `data/clips.csv`): `blb`, `blast`, `safety`, `healthy`, `not_sure`, `consent`, `voice_failed` → `audio/<clip_id>.mp3`. `brinjal` is a stretch clip and is not wired.

## Prerequisites

```bash
python - <<'EOF'
import csv
rows = {r["clip_id"]: r for r in csv.DictReader(open("data/clips.csv", encoding="utf-8"))}
wired = ["blb", "blast", "safety", "healthy", "not_sure", "consent", "voice_failed"]
bad = [c for c in wired if rows[c]["review_status"] != "reviewed"]
assert not bad, f"Not reviewed yet: {bad}. Finish step 06 before recording."
print("all wired clips reviewed")
EOF
ffmpeg -version | head -1      # [Install ffmpeg (HUMAN): it is needed to convert the recordings.]
```
If any clip is not reviewed, stop. Recording unreviewed text wastes the recording.

## Instructions for Claude Code

### 1. Print the recording script

Print, for each wired clip: the file name to use (`raw_audio/<clip_id>.<any extension>`), the exact `text_bn`, and the reviewed duration. Remind the human of the recording checklist below.

### 2. `scripts/process_clips.py`

`python scripts/process_clips.py --raw raw_audio --out audio`
- For each wired clip, find `raw_audio/<clip_id>.*` (m4a, mp3, wav, ogg, aac). Missing → report it, continue.
- Convert with ffmpeg: trim leading and trailing silence, loudness-normalise, mono, 44.1 kHz, MP3 at 80 kbps:
  ```bash
  ffmpeg -y -i raw_audio/blb.m4a \
    -af "silenceremove=start_periods=1:start_threshold=-50dB,areverse,silenceremove=start_periods=1:start_threshold=-50dB,areverse,loudnorm" \
    -ac 1 -ar 44100 -codec:a libmp3lame -b:a 80k audio/blb.mp3
  ```
- Read the duration with `ffprobe -v error -show_entries format=duration -of csv=p=0 audio/blb.mp3` and write it (1 decimal) into `duration_s` in `data/clips.csv` (via the `csv` module).
- Warn if a clip is longer than 25 s or shorter than 2 s, or larger than 1 MB.
- Print a summary table: clip_id, duration, size, status.

### 3. Optional fallback: `scripts/tts_fallback.py` (only with the human's explicit approval per clip)

- Generates one clip offline with `gemini-3.8-flash-tts` from the reviewed `text_bn`, saves WAV (the API returns 16-bit PCM mono, 24 kHz by default, with a RIFF header), then converts with the same ffmpeg command.
- The exact google-genai call for speech generation is **not in our sources**. Read the Gemini speech-generation docs at run time and use the documented call. If unclear, stop and ask.
- Writes `notes="synthetic voice (Gemini 3.8 Flash TTS), not human-recorded"` into that clip's row in `clips.csv`.
- Never import this script from `app.py` or `kombish/`.

### 4. Check and test

```bash
python scripts/process_clips.py --raw raw_audio --out audio
source .venv/bin/activate
pytest -q
pytest -q -m final        # now expected to pass, unless a reviewer is PENDING
python app.py             # play each answer in the browser
```
Also check `.gitignore` keeps `raw_audio/` out of git, and that `audio/*.mp3` **is** committed (the app needs it).

## Human actions

### Recording checklist — HUMAN (C)

- [ ] Quiet room, phone voice-recorder app, phone 20–30 cm from the mouth, no fan.
- [ ] Read **exactly** the printed reviewed text, slowly and clearly. Numbers as words; 16123 as reviewed (digit by digit unless step 06 decided otherwise).
- [ ] One file per clip, named `<clip_id>` (e.g. `blb.m4a`, `blast.m4a`, `safety.m4a`, `healthy.m4a`, `not_sure.m4a`, `consent.m4a`, `voice_failed.m4a`). Record twice if unsure; keep the better take.
- [ ] Optional: trim obvious mistakes in Audacity before handing over.
- [ ] Copy the files into `raw_audio/` in the repo (git-ignored).
- [ ] After processing, **listen to every MP3 while reading the on-screen text** in the app. Confirm word-for-word match. Tell Claude Code which clips (if any) must be re-recorded.
- [ ] Decide on any synthetic fallback clip explicitly; the README must then say which clip is synthetic.
- [ ] Commit: `git add audio data/clips.csv scripts && git commit -m "step 16: audio clips" && git push`.

## Done when

- Every wired clip exists as `audio/<clip_id>.mp3`, mono, about 80 kbps, under about 25 s.
- `pytest -q -m final` passes `test_clip_files_exist` (and the other final checks, unless a reviewer is still PENDING).
- C confirms each clip matches its on-screen text word for word.
- `raw_audio/` is not in git.

## If it fails

- **ffmpeg missing:** install it (Windows: a static build on PATH; macOS: Homebrew; Linux: the package manager), or ask a teammate to run the script.
- **Loudnorm makes a clip sound odd:** drop `loudnorm` for that clip and normalise in Audacity instead.
- **C cannot record a clip in time:** use the Gemini TTS fallback for that clip only, with approval, and label it synthetic in `clips.csv` and the README. The app still works without a clip (text only), so a missing clip never blocks the demo.

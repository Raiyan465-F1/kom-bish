# 24 — Demo video: script, subtitles and recording checklist (110 s)

**Goal:** Produce a 1:40–1:55 demo video that shows the working product (not slides), with Bangla narration, burned-in English subtitles, uploaded as an MP4 file and as an Unlisted YouTube video.
**Who:** Both. Claude Code writes the shot list, narration draft and SRT; the humans record (B), narrate and edit (C).
**When:** Tuesday 13 October. Gate G6 at 8 PM.
**Covers master-plan step:** S26 (part of instruction file CC-16).

Context: The organisers ask for a 1–2 minute demo video. A demo video "should be a demo of their hack, not a presentation" (MLH); production quality does not affect judging, but test audio first and record landscape (AI Tinkerers guide). BLB and blast demo photos will almost certainly be dataset test images: caption them "sample image from the RiceLeafBD test split" (or BD5). Bengali auto-captioning in Clipchamp is unconfirmed, so write English subtitles by hand and burn them in. **All Bangla narration is DRAFT — needs native speaker review before recording.**

## Prerequisites

```bash
git tag | grep -q "^v1.0"                    # [Feature freeze first (step 21).]
test -f training/eval_summary.json           # [Run step 20 (end-card numbers).]
grep -q "R1_BLB" data/rules.csv              # [Rules exist (step 05).]
```
Ask the human for the primary demo URL and the GitHub repo URL (for the end card).

## Instructions for Claude Code

### 1. `video/shot_list.md` — 110-second plan

| Time | Picture | Audio |
|---|---|---|
| 0–10 s | Title card "Kom Bish (কম বিষ)", then a team photo of a sprayer or a field (own photo) | Bangla line 1 |
| 10–75 s | One unbroken phone screen recording: open the app → read/tick consent → upload the BLB leaf photo (caption: "sample image from the RiceLeafBD test split") → confirm-back line → answer "কীটনাশক লাগবে না, সার ঠিক করুন" with the Bangla text on screen → tap play, the clip is heard | App audio plus a short narration overlay (line 2) |
| 75–98 s | Quick cuts: blast photo (caption with its dataset) → "spray correctly" answer with the safety player; then a junk photo → "not sure, call 16123" | Line 3: "রোগ চিনতে না পারলে কম বিষ আন্দাজ করে না।" |
| 98–110 s | End card: one evaluation number with n from `eval_summary.json` (e.g. junk refusal k of n, or cross-source blast recall), "0 off-script answers in 20" (only if `offscript_failures == 0`), repo URL, demo URL, Team Unsick | Thank-you line (C writes) |

If voice is on (gate G3), optionally show the voice path in the 10–75 s segment by **uploading the cached demo clip file** (step 15), not recording live, so it works even if the Gemini quota is gone. Keep the total at or under 1:55.

### 2. `video/narration_bn.md` — DRAFT — needs native speaker review before recording

- Line 1 (0–10 s): বাংলাদেশে বেশিরভাগ কৃষক দোকানদারের কথায় স্প্রে করেন। কম বিষ বলে দেয়, আদৌ স্প্রে লাগবে কিনা। (Most farmers spray on the dealer's word. Kom Bish says whether to spray at all.) Note for C: the evidence is a 2014–15 survey of brinjal farmers (73.23% followed dealer advice); consider narrowing the wording so it does not overclaim.
- Line 2 (10–75 s): `TODO-C` — one or two short sentences over the consultation (e.g. what the farmer does and that the answer is a reviewed, recorded clip).
- Line 3 (75–98 s): রোগ চিনতে না পারলে কম বিষ আন্দাজ করে না। (When it can't recognise the problem, Kom Bish doesn't guess.)
- Line 4 (98–110 s): `TODO-C` — thank-you line.

### 3. `video/subtitles_en.srt` — hand-written English subtitles

About 12–15 cues, timed to the shot list, each ≤ 2 lines and ≤ 42 characters per line. Translate lines 1 and 3 from the glosses above; for app screens, subtitle the on-screen Bangla headline in English (e.g. "No insecticide needed — fix the fertiliser"; "Spray correctly, and stay safe"; "Not sure — call 16123 or your agriculture officer"). Leave `TODO-C` cues for lines 2 and 4 and fill them when C supplies the Bangla. Validate the SRT format (index, `HH:MM:SS,mmm --> HH:MM:SS,mmm`, text, blank line).

### 4. Print the recording checklist below for the humans.

## Human actions

### Before recording — HUMAN (B)
- [ ] Phone on Do Not Disturb (no notifications, no personal info on screen). Battery charged.
- [ ] Open the hosted app 2 minutes early (Render may need about a minute to wake). Use the direct HTTPS URL.
- [ ] Have the photos ready in the phone gallery: BLB test image, blast test image, junk photo (and the cached demo voice file if used).
- [ ] Turn on the phone's screen recorder **with device audio** so the answer clip is captured. Do a 10-second test recording and listen to it.

### Recording — HUMAN (B records, C narrates)
- [ ] Record the 10–75 s consultation in **one unbroken take**. Record the blast and junk cuts separately.
- [ ] C records the Bangla narration lines (after native review) in a quiet room, phone 20–30 cm away.

### Editing — HUMAN (C)
- [ ] Edit in Clipchamp or CapCut. Place a vertical phone recording on a 16:9 canvas if needed.
- [ ] Add the dataset captions on the BLB and blast photos.
- [ ] Import `video/subtitles_en.srt` and **burn in** the English subtitles.
- [ ] Export: MP4, H.264, the recorded frame rate (25 or 30 fps), 1920×1080, about 8 Mbps (5 Mbps if the file is too big), AAC 48 kHz. Name it `Kom_Bish_demo.mp4`. Target 1:40–1:55 and under about 130 MB.
- [ ] Upload to YouTube as **Unlisted** with a descriptive title; upload the SRT as captions. Copy the URL.
- [ ] Keep the MP4 out of git (`video/*.mp4` is ignored); it goes to Drive in step 25.
- [ ] Give the YouTube URL to Claude Code to add to the README (replace `VIDEO_URL_TODO`) and the deck title slide.
- [ ] Commit: `git add video README.md && git commit -m "step 24: video script and subtitles" && git push`.

## Done when

- The video runs 1:40–1:55, shows one unbroken consultation, the blast and referral cuts, and an end card with a real number and n.
- It plays in a private browser window on YouTube (Unlisted) with English subtitles.
- `Kom_Bish_demo.mp4` exists locally, under about 130 MB.
- `video/shot_list.md`, `video/narration_bn.md` (with C's lines, no `TODO-C`), `video/subtitles_en.srt` are committed.

## If it fails

- **App audio not captured:** record device audio, or add the MP3 clip from `audio/` in the editor at the right moment.
- **Over 2 minutes:** shorten the quick cuts first; never cut the referral example (it shows the app refusing to guess).
- **Hosted app down while recording:** record from the laptop `python app.py --share` link on the phone; say nothing different in the video.

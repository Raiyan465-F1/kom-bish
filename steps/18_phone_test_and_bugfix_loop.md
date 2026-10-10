# 18 — Real-phone test and bug-fix loop (gate G4)

**Goal:** Prove the hosted app works on two real phones over mobile data and on a Windows laptop, and fix what breaks.
**Who:** Both. Humans (B and C) run the checklist; Claude Code reproduces and fixes each failure in a loop.
**When:** Monday 12 October, morning. **Gate G4 at noon:** hosted app works on phones, or switch the primary link to the host that passes (Render plus laptop backup).
**Covers master-plan step:** S21 (instruction file CC-13).

Context: Gradio 6's microphone has not been tested on real phones. `getUserMedia` (mic and camera) needs HTTPS, and an iframe needs `allow="camera; microphone"`, so phones must open the direct `https://<hf-user>-kom-bish.hf.space` or Render URL, never a LAN IP or the embedded huggingface.co Space page. Mobile browsers often block autoplay; the app uses `autoplay=False` with tap-to-play. Bangla is loaded with Noto Sans Bengali through `launch(head=...)`.

## Prerequisites

- Step 17 done: at least one hosted HTTPS URL completes a consultation.
- Two phones (one Android with Chrome, one iPhone with Safari) on **mobile data**, and one Windows laptop with Chrome.
- 3–4 rice-leaf test photos saved on each phone, plus one non-leaf photo.

Claude Code check: `grep -iE "https://.*(hf\.space|onrender\.com)" docs/gates.md` [Record the hosted URLs in docs/gates.md (step 17).]

## Instructions for Claude Code

1. Write `docs/phone_test.md`: a checklist table with one column per device (Android Chrome, iPhone Safari, Windows Chrome) and these rows. Print it for the humans.
   1. Direct HTTPS URL opens over mobile data (note load time; Render may take about a minute to wake).
   2. Consent text is readable; the consent audio plays (if present); the button is disabled until the box is ticked.
   3. Photo upload from the gallery works.
   4. Photo from the camera works (via the file picker's camera option, or the in-page webcam).
   5. Microphone record works and the browser asks permission (only if `VOICE_ENABLED=true`).
   6. Answer appears; Bangla conjuncts are shaped correctly (no broken glyphs or boxes).
   7. Answer audio plays on tap; the second (safety) player appears for a blast answer.
   8. "This looks wrong" button logs and shows thanks.
   9. Slow network: switch to a weak signal; the app waits and finishes (no silent failure).
   10. Non-leaf photo gives a referral or an answer; note which (feeds step 20's junk test).
   11. Dashboard tab shows counts.
2. Loop: for every failed row the humans report, (a) reproduce locally if possible (`python app.py`, Chrome device emulation), (b) fix the smallest thing in `app.py` or `kombish/`, (c) add or update a test if the bug is testable, (d) run `pytest -q`, (e) ask the human to push and recheck that row. Do not change Bangla text or rules here.
3. Record gate G4 in `docs/gates.md`: devices, pass/fail per row, primary judge link chosen, fixes made (commit hashes).

## Human actions

- **HUMAN (B, C):** run the checklist on each device over mobile data. Report failures to Claude Code with: device, browser, row number, what you saw, a screenshot if possible.
- **HUMAN:** after each fix, push (the Space rebuilds; Render redeploys) and recheck the failed rows.
- **HUMAN:** commit: `git add -A && git commit -m "step 18: phone test fixes" && git push`.

## Done when (gate G4, noon)

- All checklist rows pass on two phones (Android Chrome and iPhone Safari) and on Windows Chrome, **or** the primary judge link has been switched to the host that passes, with the laptop share link as live backup.
- `docs/gates.md` G4 row records the result and the primary link.

## If it fails

- **Mic does not work on a phone:** confirm the direct HTTPS URL (not the embedded Space page). If it still fails, keep voice optional; the upload path must work without the in-page widgets.
- **Camera widget fails:** the file picker's camera option via `sources=["upload", ...]` is the fallback; it is usually better on phones anyway.
- **Audio will not play on iPhone:** confirm the files are MP3 and tap-to-play; never rely on autoplay.
- **Bangla looks broken on Windows:** check the Noto Sans Bengali `head=` link loads; Windows otherwise falls back to Vrinda/Nirmala UI.
- **Nothing passes by noon:** primary link = Render (or whichever host passes); live pitch from the laptop `share=True` link. Record it in G4.

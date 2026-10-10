# Phone test checklist (gate G4)

Open the **direct HTTPS URL** over **mobile data**: `https://<hf-user>-kom-bish.hf.space` or the
`https://…onrender.com` URL. Never a LAN IP, and never the embedded huggingface.co/spaces page
(the microphone and camera need HTTPS and are blocked inside that iframe).

Have 3–4 rice-leaf photos and one non-leaf photo saved on each phone. Write **pass**, **fail** or **n/a**
in each cell. For a fail, tell Claude Code: device, browser, row number, what you saw, and a screenshot.

| # | Check | Android Chrome | iPhone Safari | Windows Chrome |
|---|---|---|---|---|
| 1 | Direct HTTPS URL opens over mobile data (note the load time; Render may take about a minute to wake) | | | |
| 2 | Consent text is readable; the consent audio plays (if present); the button is disabled until the box is ticked | | | |
| 3 | Photo upload from the gallery works | | | |
| 4 | Photo from the camera works (the file picker's camera option, or the in-page webcam) | | | |
| 5 | Microphone record works and the browser asks permission (only if `VOICE_ENABLED=true`) | | | |
| 6 | Answer appears; Bangla conjuncts are shaped correctly (no broken glyphs or boxes) | | | |
| 7 | Answer audio plays on tap; the second (safety) player appears for a blast answer | | | |
| 8 | "This looks wrong" button logs and shows thanks | | | |
| 9 | Slow network: switch to a weak signal; the app waits and finishes (no silent failure) | | | |
| 10 | Non-leaf photo gives a referral or an answer; note which (feeds the junk test in step 20) | | | |
| 11 | Dashboard tab shows counts | | | |

Tested URL(s):

Date, testers:

Notes:

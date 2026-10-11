# Demo video shot list (about 110 seconds)

A demo of the working product, not a presentation. Record landscape; test the audio first. English
narration (`video/narration_en.md`), English subtitles burned in (`video/subtitles_en.srt`). The app on
screen stays in Bangla with the "Show English" toggle **off**, exactly as a farmer sees it.

| Time | Picture | Sound |
|---|---|---|
| 0:00–0:08 | Title card "Kom Bish (কম বিষ)", then a photo of a rice field or a sprayer (own photo) | Narration 1 |
| 0:08–0:23 | Phone screen recording: the app opens, the consent text is visible, the consent box is ticked | Narration 2; subtitles translate the consent text |
| 0:23–0:55 | Same recording, unbroken: tap the example `blb_riceleafbd_test.jpg` (caption: "sample image from the RiceLeafBD test split") → press the button → the answer appears → tap play | Narration 3 over the start, then the Bangla clip; subtitles translate the headline and the clip |
| 0:55–1:23 | Tap the example `blast_paddy_doctor_heldout.jpg` (caption: "sample image from the Paddy Doctor held-out set") → the lesion-shape question appears → choose "yes" → press the button → the blast answer with the second (safety) player | Narration 4; subtitles translate the question, the headline and the key lines of both clips |
| 1:23–1:38 | Tap the example `not_sure_field_blast_dhanshomadhan_heldout.jpg` → "not sure, call 16123" | Narration 5; subtitles translate the referral |
| 1:38–1:50 | End card: the test line from narration 6, the repo URL, the demo URL, Team Unsick | Narration 6 |

Checks before recording:

- The clips are a **computer-generated voice**. The app shows that label; keep it in frame at least once.
- Optional: one short cut with the "Show English" toggle on, to show judges that every answer has a
  checked English translation. Keep the main take in Bangla only.
- The end-card numbers come from `training/eval_summary.json` on the day (`wrong_spray_if_yes_total`,
  `external_n`, `external_dataset`). Do not type a number from memory.
- End card URLs: demo https://raiyan465-kom-bish.hf.space ; repo https://github.com/Raiyan465-F1/kom-bish
  (the repo must be public before the video is published).
- The subtitles follow the Bangla text as it is today. If a reviewer changes any Bangla line, update the
  matching cue in `video/subtitles_en.srt` and the English in `data/clips.csv` / `data/rules.csv`.

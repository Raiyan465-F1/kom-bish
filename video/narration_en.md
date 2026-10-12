# Video narration (English)

Language decision (11 Oct 2026): the app, its answers and its audio are Bangla; the video is narrated in
English, with English subtitles for everything the app shows or says in Bangla
(`video/subtitles_en.srt`). Lines are timed to `video/shot_list.md`. Target length: about 1:45.

| # | Time | Narration |
|---|---|---|
| 1 | 0:00–0:08 | In Bangladesh, the shop that sells the spray often gives the advice too. Kom Bish tells a rice farmer whether to spray at all. |
| 2 | 0:08–0:19 | It answers in Bangla, as text and as audio. First it says plainly what happens to the photo, and the farmer agrees. |
| 3 | 0:19–0:52 | The farmer uploads a photo of one leaf. The app asks one question about the patches, and the farmer says yes. The answer: no insecticide needed, fix the fertiliser. Every sentence is pre-written. |
| 4 | 0:52–1:18 | Spray advice is the hardest answer to reach. Again the app first asks the farmer, this time about the shape of the spots, and only a "yes" gives it, always with the safety steps. |
| 5 | 1:18–1:33 | And when the photo is unclear, Kom Bish does not guess. It sends the farmer to the call centre or the local officer. |
| 6 | 1:33–1:45 | We tested it on photos from Bangladesh, India and the Philippines. It recognises healthy leaves and refers unfamiliar diseases. Recognising diseases in a new place needs local data: that is our pilot plan. |

Notes for the speaker:

- Line 3 is spoken in the first 12 seconds of its slot, before the Bangla clip starts; stay silent while the
  clip plays.

- Line 6 must match `training/eval_summary.json` on the day. Say "no wrong spray advice in our tests" only if
  `wrong_spray_if_yes_total` is 0, and do not say the model diagnoses diseases.
- The voice in the app is a computer-generated Bangla voice; the app says so on screen. Do not describe it as
  a human recording.
- Do not name a pesticide brand or a dose. The app never does.
- In line 3, add "and reviewed by a native speaker" only after the Bangla review is done (`docs/bangla_review.md`).

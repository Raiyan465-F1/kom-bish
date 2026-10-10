# Demo video shot list (110 seconds)

A demo of the working product, not a presentation. Record landscape; test the audio first. Target
1:40–1:55. Bangla on this page is DRAFT — needs native speaker review before recording.

| Time | Picture | Audio |
|---|---|---|
| 0–10 s | Title card "Kom Bish (কম বিষ)", then a team photo of a sprayer or a field (own photo) | Bangla line 1 |
| 10–75 s | One unbroken phone screen recording: open the app → read/tick consent → upload the BLB leaf photo (caption: "sample image from the RiceLeafBD test split") → confirm-back line → answer "কীটনাশক লাগবে না, সার ঠিক করুন" with the Bangla text on screen → tap play, the clip is heard | App audio plus a short narration overlay (line 2) |
| 75–98 s | Quick cuts: blast photo (caption with its dataset) → "spray correctly" answer with the safety player; then a junk photo → "not sure, call 16123" | Line 3: "রোগ চিনতে না পারলে কম বিষ আন্দাজ করে না।" |
| 98–110 s | End card: one evaluation number with n from `eval_summary.json` (e.g. junk refusal k of n, or cross-source blast recall), "0 off-script answers in 20" (only if `offscript_failures == 0`), repo URL, demo URL, Team Unsick | Thank-you line (C writes) |

If voice is on (gate G3), optionally show the voice path in the 10–75 s segment by **uploading the cached demo clip file** (step 15), not recording live, so it works even if the Gemini quota is gone. Keep the total at or under 1:55.

Captions: the BLB and blast photos are dataset test images, so caption them on screen
("sample image from the RiceLeafBD test split" / "sample image from the BD5 test split").

TODO-HUMAN: choose the end-card number and its n from `training/eval_summary.json` once it exists
(step 20). Show "0 off-script answers in 20" only if `offscript_failures` is 0.

TODO-HUMAN: repo URL and demo URL for the end card.

# Worker Studio entry text

**Project name:** Kom Bish (কম বিষ)

**Summary** (paste into the form; trim if the form has a limit):

Kom Bish is a Bangla rice adviser that says whether to spray at all. A farmer ticks a consent box, uploads a rice-leaf photo and may add a Bangla voice note. A small image classifier recognises bacterial leaf blight, blast, a healthy leaf or "other". Plain code then picks one of four pre-written, reviewed Bangla answers, shown as text and played as a recorded human voice: no insecticide needed, spray correctly, no spray now, or not sure. Low confidence always refers the farmer to 16123. Nothing is generated live. TODO-HUMAN: one evaluation number with n from `training/eval_summary.json`. Limitation: each disease's training images come from a single dataset, and there is no field trial yet.

TODO-HUMAN before pasting:

- Replace the evaluation sentence with one real number and its n (for example the junk refusal count or the
  cross-source blast recall) from `training/eval_summary.json`.
- State what is real and what is not built, as it stands on the day: voice parsing on or off (gate G3);
  Telegram, WhatsApp and phone calls are not built.
- Recount the words after editing (target: about 100).

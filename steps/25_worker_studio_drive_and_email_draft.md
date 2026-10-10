# 25 — Worker Studio draft, Drive folder, links.txt and email draft (gate G6)

**Goal:** Prepare every submission artefact: the Worker Studio draft (not submitted), the shared Drive folder with `links.txt`, the deck and the video, and a ready-to-send email reply.
**Who:** Both. Claude Code drafts the texts; the human (C) does the platform and Drive work.
**When:** Tuesday 13 October. **Gate G6 at 8 PM:** all files final; the Drive folder opens in a private window.
**Covers master-plan steps:** S27 (optional), S28, S29, S32 draft (instruction file CC-16).

Context: The organisers' selection email asks for a GitHub repo, a 5–8 slide PowerPoint, a 1–2 minute video, and a Google Drive folder holding a links file, the deck and the video; the reply goes **on the selection-email thread by 10:00 PM, Wednesday 14 October** (aim for 6 PM). Worker Studio (h4hbd.ezassist.me) is a showcase and submission page that does not host the project; it needs a name, a summary and at least one public HTTPS link ("Private files alone don't meet this requirement"); submission is blocked until the hosted demo has been opened in a new tab and a track chosen; **submitting locks the entry**; it closes at 11:59 PM GMT+6. Only C has the workspace (invite codes no longer exist). The form's exact field names and character limits sit behind login and were not seen. Bangla in these texts (project name, button name) is **DRAFT — needs native speaker review before recording**; use the reviewed strings from `kombish/texts.py`.

## Prerequisites

- Deck final (step 22), README final (step 23), video exported and on YouTube (step 24).
- Claude Code check:
  ```bash
  test -f deck/Kom_Bish_deck.pptx                           # [Finish step 22.]
  ! grep -q "VIDEO_URL_TODO" README.md                      # [Add the YouTube URL (step 24).]
  grep -q "^submission/private/" .gitignore                 # [submission/private/ must be git-ignored.]
  ```
Ask the human for: team member names, lead email and phone (these go only into `submission/private/`), the GitHub URL, primary demo URL and mirror, YouTube URL, and the Worker Studio entry URL if one exists after saving.

## Instructions for Claude Code

1. `submission/worker_studio_summary.md` (committed): a summary of about 100 words, plain English, no hype. Include: what it does (photo + optional Bangla voice → reviewed Bangla answer, text and recorded audio, says whether to spray at all); the four answers; that code decides and low confidence refers to 16123; what is real vs not built; one evaluation number with n from `training/eval_summary.json`; the single-source limitation. Also a one-line project name: "Kom Bish (কম বিষ)". Print the word count.
2. `submission/links_template.txt` (committed, placeholders only) and `submission/private/links.txt` (filled, git-ignored), following:
   ```
   Kom Bish (কম বিষ) — Team Unsick — Hack for Humanity BD 2026, Round 2
   Track: Inclusive Rural Development & Agriculture
   Team: <name 1> (lead, <email>, <phone>), <name 2>, <name 3>

   GitHub repository:   https://github.com/<gh-user>/kom-bish
   Live demo:           <primary https URL>  (how to try: tick consent, upload a rice-leaf photo, press পরামর্শ নিন)
   Demo mirror:         <second https URL, if any>
   Demo video (YouTube, unlisted): <https://youtu.be/...>
   Demo video (file in this folder): Kom_Bish_demo.mp4
   Pitch deck (file in this folder): Kom_Bish_deck.pptx
   Worker Studio entry: <URL if available>
   Test photos for judges: https://github.com/<gh-user>/kom-bish/tree/main/examples
   ```
   Contacts appear only in the private copy, never in the public repo.
3. `submission/email_reply_draft.md` (committed, placeholders) and `submission/private/email_reply.md` (filled): a short reply for the **original selection-email thread** (use Reply, keep the subject). Body: greeting; team name (Team Unsick) and project name (Kom Bish); the Drive folder link; inline links to GitHub, live demo and YouTube; one sentence on what to try; thanks; lead's name. No attachments needed (files are in the folder).
4. Optional (only if the team is ahead of schedule; skip otherwise): `landing/index.html`, a single static page with two screenshots, the YouTube embed link, and links to the demo, repo and deck, for a free **Static** HF Space (Static Spaces are still free for everyone). Write it with inline CSS and no external scripts.
5. Print the human checklists below.

## Human actions

### Drive folder — HUMAN (C), from a personal Gmail account (work or school accounts may block outside sharing)
- [ ] Create a folder named **Kom Bish – Team Unsick – H4H Round 2**.
- [ ] Upload `submission/private/links.txt` (as `links.txt`), `deck/Kom_Bish_deck.pptx`, and `Kom_Bish_demo.mp4`.
- [ ] Share the folder: **Share → General access → Anyone with the link → Viewer → Copy link**. Files inherit the folder's access.
- [ ] Open the folder link in a **private window**: the three files are visible, the deck downloads, the video plays or shows "Video is still processing" (Drive can take a while; the YouTube link covers this).
- [ ] Give the folder link to Claude Code to fill into `submission/private/email_reply.md`.

### Worker Studio draft — HUMAN (C)
- [ ] Sign in → team workspace → **Upload a solution** (creates a private draft).
- [ ] Name: `Kom Bish (কম বিষ)`. Summary: paste `submission/worker_studio_summary.md` (trim if the form has a limit).
- [ ] Links, all HTTPS, in this order: GitHub repo, YouTube video, live demo. Add the Drive folder only as an extra.
- [ ] Save (this assembles the showcase page). If assembly fails, check every URL starts with `https://` and at least one link is public.
- [ ] **Verify the hosted demo:** open the saved demo URL in a new tab and confirm it loads.
- [ ] Look at the track list; note whether "Inclusive Rural Development & Agriculture" is offered. **Do not submit yet** (submitting locks the entry; step 26 submits by 3 PM Wednesday).

### Optional landing page — HUMAN (B)
- [ ] Only if done early: create a **Static** Space, upload `landing/index.html`, check it loads over HTTPS. Skip if behind schedule.

### Commit — HUMAN
- [ ] `git add submission && git commit -m "step 25: submission drafts" && git push` (check `git status` shows nothing under `submission/private/`).

## Done when (gate G6, 8 PM)

- The Drive folder opens in a private window and holds `links.txt`, `Kom_Bish_deck.pptx`, `Kom_Bish_demo.mp4`; the video plays or shows processing.
- Worker Studio draft saved, showcase page assembles without error, demo link verified in a new tab; **not yet submitted**.
- `submission/private/email_reply.md` is complete with the real folder link and ready to paste.
- `docs/gates.md` G6 is filled.

## If it fails

- **Drive sharing blocked:** the account is a work/school account; recreate the folder from a personal Gmail.
- **Worker Studio form surprises (fields, limits, track names):** adapt the summary length; pick the closest track; ask Organizer support if something blocks saving. Keep the email deadline as the priority.
- **Video still processing on Drive:** that is why the YouTube link is in `links.txt` and the email; leave the file in place.

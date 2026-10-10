# 01 — Team scope, roles and accounts

**Goal:** Agree scope and owners, then create every account and key the build needs.
**Who:** Human (all three). Claude Code has nothing to build here.
**When:** Saturday 10 October, from about 3 PM. Must finish before step 04's gate G1 (10 PM).
**Covers master-plan steps:** S01, S02.

Context: Kom Bish is a Gradio app that gives a pre-written Bangla answer for a rice-leaf photo. Hosting changed in July 2026: Hugging Face (HF) now requires a paid plan to create Gradio Spaces, except ZeroGPU Spaces, which free accounts can create only if the account is **older than 30 days with a verified email**. So account ages decide the hosting route tonight.

## Prerequisites

- Each member has a personal Gmail account and a phone.
- Everyone has read `00_START_HERE.md`.

## Instructions for Claude Code

None. This is a HUMAN step. If this file is pasted into Claude Code, Claude Code should print the checklist below and stop.

## Human actions

### A. Freeze scope and roles (S01) — HUMAN, all

- [ ] Agree roles. **A = model lead** (data, Kaggle runs, evaluation). **B = app and hosting lead** (accounts, deployment, phone tests, screen recording). **C = content and pitch lead**, a native Bangla speaker (script review, clip recording, deck, video narration, Worker Studio, email).
- [ ] Team of two: merge A and B, drop the static landing page and the brinjal stretch, keep everything else.
- [ ] Agree the cut list. Out for Wednesday: Telegram bot, WhatsApp, phone calls, retrieval over documents, live text-to-speech, Whisper models, vegetable classes, brown planthopper advice, any spoken pesticide dose. Brinjal-borer voice answer stays in reserve only.
- [ ] Pin the step table from `00_START_HERE.md` in the team chat with an owner per step.

### B. Accounts and keys (S02) — HUMAN

- [ ] **GitHub (B):** create a **public** repo named `kom-bish`. Add the other two as collaborators. Clone it to the laptop that will run Claude Code. Copy `CLAUDE.md` to the repo root and all step files into `steps/`.
- [ ] **Hugging Face (all):** each member logs in and checks (1) account creation date, (2) email verified. Post in chat: "ZeroGPU possible: yes/no (whose account)". Older than 30 days + verified email = yes.
- [ ] **Kaggle (A at minimum, ideally all):** create an account and complete **phone verification** (Profile → Settings). Phone verification unlocks GPU and internet in notebooks.
- [ ] **Gemini API key (C or B):** create a key in Google AI Studio with a personal Google account. In AI Studio, read the free-tier rate limits for `gemini-3.5-flash-lite` and `gemini-3.8-flash` and post them in chat. (Limits are published only in AI Studio. Daily quotas reset at midnight Pacific, which is 1:00 PM in Bangladesh in October.)
- [ ] **Render (B):** sign up with GitHub. Do not add a card. (No-card status comes from a September 2026 source and was not rechecked on 10 October; if Render asks for a card, tell the team and stop.)
- [ ] **Worker Studio (C only):** create an account and a team workspace at h4hbd.ezassist.me. Invite-code joining no longer exists, so C does the whole entry later.
- [ ] **Store keys outside the repo** (password manager or a private note). Never paste a key into the repo, a chat that judges can see, or a commit.
- [ ] **HF tokens are created later** (step 14 for logging, step 17 for sync). Do not create broad write tokens now.

### C. Optional: paid route (team decision only)

- [ ] Discuss, but do not default to: HF PRO costs USD 9 for one month and unlocks CPU Basic Gradio Spaces. It is the most reliable judge link but breaks the no-budget rule. Record the decision in chat.

## Done when

- Every step in `00_START_HERE.md` has an owner, and the cut list is agreed.
- The public repo `kom-bish` exists, has three collaborators, and contains `CLAUDE.md` and `steps/`.
- Team chat contains: "ZeroGPU possible: yes/no", Kaggle phone verification done (who), Gemini free-tier limits for both models, Render account ready, Worker Studio workspace ready.
- No key is stored inside the repo folder except in `.env` (created in step 03, git-ignored).

## If it fails

- **No HF account passes the 30-day + verified-email test:** plan for Render free as the primary host and a laptop `share=True` link for the live pitch (step 04). PRO for USD 9 only by team decision.
- **Kaggle phone verification fails:** try another member's phone. Fallback training route is Colab free (step 10).
- **Gemini key cannot be created:** voice is optional. Plan to ship with `VOICE_ENABLED=false` and say so in the README.
- **Render asks for a card:** keep ZeroGPU as primary if possible, and the laptop share link as backup.

# 21 — Mentor session 2 and feature freeze (gate G5)

**Goal:** Use the mentor session for three decisions, then freeze features and tag `v1.0`.
**Who:** Both. Humans run the mentor session; Claude Code writes the changelog and tags after checks.
**When:** Mentor session 12 or 13 October (confirm the slot in the WhatsApp group). **Gate G5 at 9 PM Monday:** feature freeze, tag `v1.0`. After this: only bug fixes and documents.
**Covers master-plan steps:** S22, S23.

Context: Round 2 is "judged technically" and decides who presents at the 24 October finale. The submission must show one working flow with nothing faked, plus honest limits. Only changes that take under two hours are accepted after the mentor session.

## Prerequisites

- Steps 17, 18 and 20 done (hosted app passes the phone test; evaluation report exists).
- Claude Code check:
  ```bash
  source .venv/bin/activate && pytest -q && pytest -q -m final   # [All tests, including final checks, must pass before tagging.]
  git status --short                                             # [Working tree must be clean.]
  ```
  If `pytest -m final` fails only because a reviewer is `PENDING`, ask the human whether to tag anyway and record that in `docs/gates.md`.

## Instructions for Claude Code

1. Print the mentor question list (below) for the humans.
2. After the session, write the human's notes into `docs/gates.md` under "Mentor session 2" (date, mentor name, answers, accepted changes with estimated time). Implement only accepted changes under two hours, each with tests.
3. Update `CHANGELOG.md`: a `## v1.0 — 2026-10-12` section summarising the shipped features (consent-gated photo flow, 4-class ONNX classifier with abstention, 6-rule table, reviewed Bangla text and human-recorded clips, optional Gemini voice parsing (on/off per G3), anonymous logging and counters, hosts per G1/G4), and known limits.
4. Set `APP_VERSION=1.0.0` in `.env.example` comments and remind the human to set the host variable `APP_VERSION=1.0.0`.
5. Tag after the human confirms:
   ```bash
   git tag -a v1.0 -m "Kom Bish v1.0 feature freeze (gate G5)"
   git push origin v1.0
   ```
6. Fill G5 in `docs/gates.md` (date/time, commit hash of `v1.0`).

## Human actions

### Mentor session questions — HUMAN (all)
- [ ] Does a Round 2 entry need breadth beyond one working flow?
- [ ] Is the Worker Studio entry weighed in judging, and which deadline governs (email 10:00 PM vs platform 11:59 PM)? (Plan: treat the email's 10:00 PM as binding.)
- [ ] Can the mentor connect us with an agriculture faculty member or officer to read the six rules and four answer scripts? (If yes, record name/role/date in `docs/gates.md`; README then says who reviewed.)
- [ ] Take notes. Accept only changes under two hours.

### Freeze — HUMAN (B)
- [ ] Set host variable `APP_VERSION=1.0.0` on each host.
- [ ] Confirm the tag to Claude Code; check the tag appears on GitHub.
- [ ] Tell the team: from now on only bug fixes and documents.

## Done when (gate G5, 9 PM)

- `pytest -q` and `pytest -q -m final` pass (or the PENDING exception is recorded).
- Tag `v1.0` exists on GitHub; `CHANGELOG.md` has the v1.0 section.
- Mentor notes and any agronomist contact are recorded in `docs/gates.md`.

## If it fails

- **A mentor request takes more than two hours:** decline it for Round 2 and list it under "Next steps" in the README and deck.
- **A bug appears after the tag:** fix it, test it, push it; tag `v1.0.1` if the fix touches app code. Documents can change freely until step 26.

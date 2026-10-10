# 23 — Judge-facing README (and final model card)

**Goal:** Write a README that lets a judge who has never heard of the team understand, try and verify Kom Bish in a few minutes.
**Who:** Claude Code (the human checks it in a private window).
**When:** Tuesday 13 October. Gate G6 at 8 PM.
**Covers master-plan step:** S25 (instruction file CC-15).

Context: Judges see the work with no presenter. Anything not shown or explained looks like a failure, so "real vs mocked" goes above the fold and every limit is stated plainly. GitHub renders Mermaid in Markdown and truncates READMEs beyond 500 KiB. The HF YAML front matter must stay the very first lines (GitHub shows it as a table; harmless). Numbers come only from `training/eval_summary.json` and `training/eval_report.md`. Bangla in the README is **DRAFT — needs native speaker review before recording**; copy headlines from the reviewed `data/rules.csv`, never retype them.

## Prerequisites

```bash
test -f training/eval_summary.json && test -f training/eval_report.md   # [Run step 20.]
grep -iE "https://" docs/gates.md | head                                # [Hosted URLs recorded (steps 17-18).]
head -1 README.md | grep -q "^---$"                                     # [README must start with the HF YAML front matter (step 03).]
```
Ask the human for: team member names (and whether to list them), the primary demo URL and mirror, the deck file location, and the YouTube URL (or say "add after step 24").

## Instructions for Claude Code

Keep the existing YAML front matter unchanged at the top. Below it, write these sections in this order:

1. **Title and one-line pitch in English and Bangla:** "Kom Bish (কম বিষ) — a Bangla rice adviser that says whether to spray at all." Bangla line: **DRAFT — needs native speaker review**; ask C to supply or approve it.
2. **Try it:** primary demo link (direct `https://<hf-user>-kom-bish.hf.space` or the Render URL), mirror link, "first load can take about a minute" note if Render, demo video link, deck (`deck/Kom_Bish_deck.pptx`), 2–3 screenshots from `deck/screens/`, and "test photos: `examples/`". One-line how-to: "Tick the consent box, upload a rice-leaf photo, press পরামর্শ নিন."
3. **Problem (three cited figures):** 73.23% of brinjal farmers followed dealer advice ([Mannan et al. 2021](https://banglajol.info/index.php/BJAR/article/view/64710), 2014–15); about 21% of pooled vegetable samples over residue limits ([Toxicology Reports via DOAJ](https://doaj.org/article/ebb427563ebb4866a52dd8eb382aea54)); 92,094 calls to Krishi Call Centre 16123 from July 2025 to June 2026 ([BSS](https://www.bssnews.net/special-stories/401845)).
4. **What it does — the four answers:** table with headline (Bangla + English), when it fires (rule IDs), and source:
   - R1 BLB: কীটনাশক লাগবে না, সার ঠিক করুন — No insecticide needed, fix the fertiliser — [BRRI notice, 19 Mar 2023](https://brri.portal.gov.bd/sites/default/files/files/brri.portal.gov.bd/news/245bba32_a089_4da8_9845_d9afcddf455f/2023-04-05-05-24-b9fb45272dcf3a51acb0e89254944725.pdf); [DAE/BAMIS bulletin](https://www.bamis.gov.bd/res/pages/2023/03/19/26691.pdf)
   - R2 blast: স্প্রে লাগবে, তবে ঠিকভাবে — Spray correctly (tricyclazole-group fungicide, label dose, safety script) — BRRI notice; DAE/BAMIS; [FAO PPE guidelines](https://fao.org/fileadmin/templates/agphome/documents/Pests_Pesticides/Code/Old_guidelines/PROTECT.pdf)
   - R3 healthy: এখন কোনো স্প্রে লাগবে না — No spray now, keep watching — [Ali et al. 2017](https://www.frontiersin.org/journals/environmental-science/articles/10.3389/fenvs.2017.00016/pdf)
   - R4/R5/R6: Not sure → call 16123 or the Sub-Assistant Agriculture Officer — [BSS 2026](https://www.bssnews.net/special-stories/401845)
   Link to `data/rules.csv` and `data/clips.csv`.
5. **How it works:** a Mermaid diagram plus five short lines. Quote node labels that contain brackets or parentheses so GitHub renders it:
   ```mermaid
   flowchart LR
     A["Consent ticked"] --> B["Rice-leaf photo"]
     B --> C["Preprocess: EXIF, resize 256, crop 224"]
     C --> D["ONNX MobileNetV3, 4 classes"]
     D --> E{"Calibrated confidence above threshold and margin?"}
     E -- "no" --> R5["Not sure: call 16123 or officer"]
     E -- "yes" --> F["decide() in kombish/rules.py"]
     V["Optional Bangla voice note"] --> G["Gemini: fixed symptom list, or nothing"]
     G -- "can only add caution" --> F
     F --> H["Reviewed Bangla text (data/clips.csv)"]
     F --> I["Human-recorded MP3 clip"]
     F --> L[("Anonymous log: private HF dataset")]
   ```
   Lines: the photo is classified; low confidence → referral; code picks one of six rules; the farmer sees and hears only reviewed text; voice (if on) can only make the answer more cautious.
6. **Real vs mocked (above the fold — place it right after "Try it" if the page is long):**

   | Part | Status |
   |---|---|
   | Photo classifier | Real: ONNX MobileNetV3, trained on 4,100 CC BY 4.0 Bangladeshi leaf images |
   | Voice parsing | Real (Gemini `<GEMINI_MODEL>`), or "switched off" per gate G3 with the reason |
   | Spoken answer | Pre-recorded human clips (name any synthetic clip); no live text-to-speech |
   | "Estimated sprays avoided" | Advice-based count, unverified: nobody checked what the farmer did next |
   | Telegram, WhatsApp, phone call | Not built |
   | Agronomist review | "Not yet reviewed by an agronomist", or the reviewer from `docs/gates.md` |
   | Field trial | None |

7. **Safety design:** closed rule table; code decides, the model only recognises; confidence gate and referral; voice can only add caution (link `tests/test_rules.py`); the BLB note: "The official notice also lists a sulphur-based foliar mix; Kom Bish deliberately omits it and refers the farmer instead."; the sentence "Kom Bish names active-ingredient groups only as they appear in BRRI/DAE advisories, never brands or doses, and takes no money from input sellers."; FAO-based safety script on every spray answer; "follow the label" for dose and harvest wait; "0 off-script answers and 0 invented doses in 20 test consultations" (link `tests/test_offscript.py`) only if `offscript_failures == 0`.
8. **Evaluation (with n):** from `training/eval_summary.json`: test n and macro-F1; threshold, margin, coverage, selective accuracy; precision on BLB and blast answers with n; Dhan-Shomadhan field blast n, recall, abstain rate; own healthy-looking leaves wrongly sent to BLB/blast (k of n); junk refusal (k of n). Add "The model abstains more than we would like." if `target_met` is false. State the single-source confound in one sentence. Link `training/eval_report.md`.
9. **Privacy:** what is logged (list the fields) and what never is (photo, audio, transcript, IP, name, phone); logs go to a private HF dataset; voice notes are processed by Google's Gemini free tier, which "is used to improve our products"; consent shown before any input (Personal Data Protection Ordinance 2025 requires explicit consent; its later legal status is uncertain, so we comply anyway).
10. **Run locally:**
    ```bash
    python3.12 -m venv .venv && source .venv/bin/activate
    pip install -r requirements-render.txt -r requirements-dev.txt
    cp .env.example .env          # set MODEL_REPO; LOG_REPO/HF_TOKEN/GEMINI_API_KEY optional
    python app.py                 # http://localhost:7860
    pytest -q                     # safety invariants and app paths
    ```
11. **Judging-criteria map:** Round 2 is "judged technically"; the finale is judged on social/human impact, feasibility and scalability. One line plus a link each: running code (demo, tests, CI), technical depth (calibration, ONNX, eval report), impact (spray-or-not answers, evidence on slide 7, our pilot will measure), feasibility (USD 0 stack, runs on free hosts and a laptop), scalability (host-agnostic config, rules in a CSV, next: SAAO review and a 30-farmer pilot).
12. **Data credits and licences:** RiceLeafBD (DOI 10.17632/kx9rx8p2mz.1; also cite arXiv 2501.08912), RiceLeafDisease-BD5 (DOI 10.17632/sjkptpgv79.2), Dhan-Shomadhan (DOI 10.17632/znsxdctwtt.1, via the HF mirror `Project-AgML/Dhan-Shomadhan_rice_leaf_disease_classification`), all **CC BY 4.0**; base weights `timm/mobilenetv3_large_100.ra_in1k` (Apache-2.0); BRRI, DAE/BAMIS, FAO, Ali et al. 2017; model repo link. Then **Limitations** (single-source confound, no field test, rules not yet agronomist-signed unless recorded, Bangla reviewed by whom, voice accuracy from a 10-note test only, `other` does not cover non-rice photos), **Team**, **Licence** (MIT for code; data keeps its own licences; dataset images are not committed except credited examples).

Then:
- Regenerate the model card if numbers changed (`python training/make_model_card.py`) and re-upload it (step 11 script).
- Print a table of every number in the README next to its value in `eval_summary.json` so the human can verify they match.
- Check all relative links point to files that exist (`git ls-files`), and print every external URL for the human to click.

## Human actions

- **HUMAN:** open the GitHub repo page in a **private browser window**: the README renders, the Mermaid diagram draws, and the demo link opens the app. Ask someone outside the team to try the app from the README's first screen.
- **HUMAN (C):** supply or approve the Bangla pitch line.
- **HUMAN:** commit: `git add README.md training/model_card.md && git commit -m "step 23: judge README" && git push`.

## Done when

- The README renders on GitHub with the Mermaid diagram; the HF YAML block is still first.
- A stranger can open the app from the first screen; checked in a private window.
- Real-vs-mocked, safety design, evaluation with n, privacy, data credits (three DOIs, CC BY 4.0) and limitations are all present.
- Every README number matches `training/eval_summary.json`.

## If it fails

- **Mermaid does not render:** quote every node label and remove special characters; preview on GitHub.
- **The Space shows the README front matter oddly:** that is expected on GitHub; the Space uses it for config.
- **No YouTube link yet:** leave `VIDEO_URL_TODO` and fill it in step 25; step 26's audit greps for `TODO`.

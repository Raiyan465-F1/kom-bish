# 22 — Pitch deck draft (python-pptx), polished by hand

**Goal:** Generate an 8-slide 16:9 PowerPoint draft with full-sentence headlines, real numbers from the evaluation, citation footers and speaker notes, for C to polish.
**Who:** Both. The human takes screenshots and polishes; Claude Code generates the draft.
**When:** Tuesday 13 October. Gate G6 at 8 PM (all files final).
**Covers master-plan step:** S24 (instruction file CC-14).

Context: The organisers ask for a PowerPoint deck of 5–8 slides. Judges see it with no presenter, so every slide needs a full-sentence headline, under 30 words of body text and a 10–12 pt citation footer (YC rules: legible, simple, obvious, one idea per slide). python-pptx 1.0.2: after setting the slide size to 13.333 × 7.5 in, the default template's placeholders stay at their 4:3 positions (tested), so reposition them with a `fit()` helper or use text boxes. Bangla needs a font on the viewing machine (Nirmala UI on Windows); check in PowerPoint. Never use "75% rice reduction" or "150 sprays" (overstated). The BLB box says "No insecticide needed", never "Do not spray". Bangla on slides is **DRAFT — needs native speaker review before recording**; copy headlines from the reviewed `data/rules.csv`, never retype them.

## Prerequisites

```bash
test -f training/eval_summary.json                        # [Run step 20.]
git tag | grep -q "^v1.0"                                 # [Feature freeze first (step 21).]
ls deck/screens/*.png 2>/dev/null | wc -l                 # expect 4-6 (HUMAN, see below); the script uses placeholders if missing
source .venv-train/bin/activate && python -c "import pptx; print(pptx.__version__)"   # expect 1.0.2
```

## Instructions for Claude Code

### 1. `deck/make_deck.py`

Use this tested pattern as the base:

```python
import json, re
from pathlib import Path
from pptx import Presentation
from pptx.util import Inches, Pt

ROOT = Path(__file__).resolve().parent.parent
S = json.loads((ROOT / "training" / "eval_summary.json").read_text(encoding="utf-8"))
BANGLA = re.compile(r"[ঀ-৿]")

prs = Presentation()
prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)   # 16:9


def fit(ph, left=0.6, top=None, width=12.1, height=None):
    """Default template is 4:3 - stretch a placeholder across the 16:9 slide."""
    ph.left, ph.width = Inches(left), Inches(width)
    if top is not None: ph.top = Inches(top)
    if height is not None: ph.height = Inches(height)


def bangla_font(shape, name="Nirmala UI"):
    for p in shape.text_frame.paragraphs:
        for r in p.runs:
            if BANGLA.search(r.text):
                r.font.name = name


def footer(slide, text):
    tb = slide.shapes.add_textbox(Inches(0.6), Inches(6.85), Inches(12.1), Inches(0.5))
    tb.text_frame.text = text
    for p in tb.text_frame.paragraphs:
        for r in p.runs:
            r.font.size = Pt(11)


def headline_slide(title, layout=5):
    s = prs.slides.add_slide(prs.slide_layouts[layout])      # 5 = title only
    s.shapes.title.text = title
    fit(s.shapes.title, top=0.3, height=1.2)
    bangla_font(s.shapes.title)
    return s
```

Helpers to add: `textbox(slide, lines, left, top, width, height, size=20)` (calls `bangla_font`), `picture_or_placeholder(slide, path, left, top, height)` (adds the PNG if it exists, else a grey rectangle with the text `[screenshot: <name>]`), `notes(slide, text)` (`slide.notes_slide.notes_text_frame.text = text`), and a `pct(x)` formatter. Read every number from `S`; print a warning and show `[n/a]` if a key is missing. Never type a metric.

### 2. Slide content (8 slides)

| # | Headline (full sentence) | Body (≤ 30 words) | Footer citation |
|---|---|---|---|
| 1 | Kom Bish (কম বিষ) tells a farmer whether to spray at all. | Team Unsick · Track: Inclusive Rural Development & Agriculture · repo URL · video URL (placeholders until step 24) · one phone screenshot (`deck/screens/01_answer.png`) | none |
| 2 | The dealer sells the spray and also gives the advice. | 73.23% of brinjal farmers followed dealer advice · ~21% of pooled vegetable samples over residue limits · 92,094 calls to 16123 in one year: farmers do ask for help | Mannan et al. 2021, BJAR (Chattogram, Jashore, Mymensingh, 2014–15); Toxicology Reports 2023 systematic review (via DOAJ); BSS/AIS, 2 Jul 2026 |
| 3 | One photo in, one honest answer out. | Three screenshots: photo → confirm-back → "কীটনাশক লাগবে না, সার ঠিক করুন" (No insecticide needed — fix the fertiliser) | Screens from the hosted app; sample image from the RiceLeafBD test split (if so) |
| 4 | Code decides; the model only recognises. | Diagram (shapes + arrows): Photo → ONNX classifier [working] → confidence gate [working] → 6-row rule table [working] → reviewed Bangla text + recorded clip [working]. Voice → Gemini symptom list [working / off per G3] → can only add caution. | Rule table: `data/rules.csv` in the repo |
| 5 | Four answers, each traced to an official source. | 2×2 grid: No insecticide needed — fix the fertiliser (BLB) · Spray correctly, with safety steps (blast) · No spray now — keep watching (healthy) · Not sure → call 16123 (anything else or uncertain) | BRRI Plant Pathology notice 19 Mar 2023; DAE/BAMIS bulletin Mar 2023; Ali et al. 2017; DAE Krishi Call Centre 16123 |
| 6 | We built it and measured it, including where it fails. | From `S`: test macro-F1 (n), coverage and selective accuracy at threshold, cross-source blast recall (n), own healthy leaves wrongly sent to a spray class (k of n), junk refusal (k of n), "0 off-script answers and 0 invented doses in 20" (only if `offscript_failures == 0`), review status | `training/eval_report.md`; datasets CC BY 4.0 (three DOIs) |
| 7 | Kom Bish adds a spray-or-not rule that others do not show. | Small table: Kom Bish, Rice Solution, Dr. Chashi, Groundnut IPM app, 16123 × column "spray-or-not rule + sprays-avoided count" (Kom Bish: yes; others: `[team to verify]`). Evidence: Bt brinjal −51% applications; rice need-based 0–1 vs 2–4 sprays. "Our pilot will measure how much a voice adviser delivers." | IFPRI Bt brinjal RCT (1,200 farmers); Ali et al. 2017 (about 12 need-based fields) |
| 8 | These are our limits, and this is what we do next. | BLB images come from one dataset · rules not yet agronomist-signed (or name the reviewer from `docs/gates.md`) · no field test · Next: SAAO review, 30-farmer pilot | `training/eval_report.md` |

Speaker notes for each slide: 2–4 plain sentences explaining the slide for a judge reading alone (e.g. slide 5: "The BLB answer omits the sulphur-based foliar mix in the official notice and refers the farmer instead.").

Do not invent competitor features. Every competitor cell except Kom Bish's stays `[team to verify]` until a human fills it from a source.

### 3. Build and check

```bash
source .venv-train/bin/activate
python deck/make_deck.py           # writes deck/Kom_Bish_deck.pptx
python - <<'EOF'
from pptx import Presentation
p = Presentation("deck/Kom_Bish_deck.pptx")
print("slides:", len(p.slides), "size:", p.slide_width.inches, "x", p.slide_height.inches)
assert len(p.slides) == 8 and round(p.slide_width.inches, 2) == 13.33
for i, s in enumerate(p.slides, 1):
    words = sum(len(sh.text_frame.text.split()) for sh in s.shapes if sh.has_text_frame and sh != s.shapes.title)
    print(i, s.shapes.title.text if s.shapes.title else "", "| body words:", words)
EOF
```
Report any slide over about 30 body words (footers excluded) so the human can trim.

## Human actions

- **HUMAN (B):** take 4–6 phone screenshots of one consultation on the hosted app (consent, photo, confirm-back + answer, blast answer with safety player, referral answer). Save as PNG in `deck/screens/` named `01_answer.png`, `02_photo.png`, `03_confirm.png`, `04_blb_answer.png`, `05_blast.png`, `06_not_sure.png`. Run the script again.
- **HUMAN (C):** open `deck/Kom_Bish_deck.pptx` in PowerPoint on Windows. Check Bangla is shaped correctly (set Nirmala UI or an installed Noto Sans Bengali if needed). Fix layout, fill `[team to verify]` cells only from sources, add the video URL after step 24. Keep 8 slides or fewer. Save as `deck/Kom_Bish_deck.pptx`.
- **HUMAN:** commit: `git add deck && git commit -m "step 22: deck" && git push`.

## Done when

- `deck/Kom_Bish_deck.pptx` opens in PowerPoint on Windows with Bangla shaped correctly.
- 8 slides or fewer, 16:9, full-sentence headlines, every figure cited in a footer, speaker notes present.
- No "75%" or "150 sprays" claim; the BLB answer reads "No insecticide needed".

## If it fails

- **Placeholders sit in the left two-thirds of the slide:** call `fit()` on every placeholder, or switch that slide to the blank layout (`slide_layouts[6]`) with text boxes.
- **Bangla shows boxes in PowerPoint:** the viewing machine lacks a Bengali font; set Nirmala UI (Windows) and check again.
- **Out of time:** a clean 6-slide deck (title, problem, demo, how it works, measured, limits) meets the 5–8 slide rule.

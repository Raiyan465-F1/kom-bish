"""Generate the 8-slide 16:9 pitch deck draft (python-pptx). Polish it by hand in PowerPoint afterwards.

  python deck/make_deck.py [--voice on|off] [--video-url URL] [--demo-url URL]      # run in .venv-train

Every number comes from training/eval_summary.json; a missing value is shown as [n/a] with a warning.
Bangla headlines are copied from data/rules.csv, never retyped. Competitor cells stay "[team to verify]".
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.util import Inches, Pt

ROOT = Path(__file__).resolve().parent.parent
SCREENS = ROOT / "deck" / "screens"
SUMMARY = ROOT / "training" / "eval_summary.json"
REPO_URL = "https://github.com/Raiyan465-F1/kom-bish"
BANGLA = re.compile(r"[ঀ-৿]")
NA = "[n/a]"
VERIFY = "[team to verify]"

S: dict = {}
prs = Presentation()
prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)   # 16:9


def num(key: str):
    value = S.get(key)
    if value is None:
        print(f"WARNING: eval_summary.json has no value for {key!r}; the deck shows {NA}.")
    return value


def pct(x) -> str:
    return NA if x is None else f"{100 * x:.1f}%"


def k_of_n(k_key: str, n_key: str) -> str:
    k, n = num(k_key), num(n_key)
    return NA if k is None or n is None else f"{k} of {n}"


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
    for p in s.shapes.title.text_frame.paragraphs:
        for r in p.runs:
            r.font.size = Pt(32)
    bangla_font(s.shapes.title)
    return s


def textbox(slide, lines, left, top, width, height, size=20):
    tb = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    tf = tb.text_frame
    tf.word_wrap = True
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = line
        for r in p.runs:
            r.font.size = Pt(size)
    bangla_font(tb)
    return tb


def box(slide, text, left, top, width, height, size=16, fill=(0xE8, 0xF3, 0xE8)):
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(left), Inches(top), Inches(width), Inches(height))
    shape.fill.solid()
    shape.fill.fore_color.rgb = RGBColor(*fill)
    shape.line.color.rgb = RGBColor(0x2E, 0x7D, 0x32)
    tf = shape.text_frame
    tf.word_wrap = True
    tf.text = text
    for p in tf.paragraphs:
        for r in p.runs:
            r.font.size = Pt(size)
            r.font.color.rgb = RGBColor(0x1B, 0x1B, 0x1B)
    bangla_font(shape)
    return shape


def arrow(slide, left, top, width=0.45, height=0.35):
    shape = slide.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, Inches(left), Inches(top), Inches(width), Inches(height))
    shape.fill.solid()
    shape.fill.fore_color.rgb = RGBColor(0x2E, 0x7D, 0x32)
    shape.line.fill.background()
    return shape


def picture_or_placeholder(slide, path: Path, left, top, height):
    if path.exists():
        return slide.shapes.add_picture(str(path), Inches(left), Inches(top), height=Inches(height))
    return box(slide, f"[screenshot: {path.name}]", left, top, height * 0.5, height, size=12, fill=(0xDD, 0xDD, 0xDD))


def notes(slide, text):
    slide.notes_slide.notes_text_frame.text = text


def headlines() -> dict[str, str]:
    with (ROOT / "data" / "rules.csv").open(encoding="utf-8", newline="") as f:
        return {row["rule_id"]: row["headline_bn"] for row in csv.DictReader(f)}


def agronomy_line() -> str:
    gates = ROOT / "docs" / "gates.md"
    if gates.exists():
        for line in gates.read_text("utf-8").splitlines():
            if line.lower().startswith("- agronomy review:") and "none yet" not in line.lower():
                return "Rules reviewed by: " + line.split(":", 1)[1].strip()
    return "Rules not yet agronomist-signed"


def build(voice: str, video_url: str, demo_url: str) -> None:
    H = headlines()
    voice_status = {"on": "[working]", "off": "[switched off: below our accuracy bar]",
                    "undecided": "[on/off decided at gate G3]"}[voice]

    s = headline_slide("Kom Bish (কম বিষ) tells a farmer whether to spray at all.")
    textbox(s, ["Team Unsick", "Track: Inclusive Rural Development & Agriculture", f"Code: {REPO_URL}",
                f"Demo: {demo_url}", f"Video: {video_url}"], 0.6, 2.0, 7.6, 3.5, size=20)
    picture_or_placeholder(s, SCREENS / "01_answer.png", 9.6, 1.7, 5.0)
    notes(s, "Kom Bish is a Bangla rice adviser. A farmer sends a leaf photo and gets a reviewed, recorded answer "
             "that says whether a spray is needed at all. Hack for Humanity BD 2026, Round 2.")

    s = headline_slide("The dealer sells the spray and also gives the advice.")
    textbox(s, ["73.23% of brinjal farmers followed dealer advice.",
                "About 21% of pooled vegetable samples were over residue limits.",
                "92,094 calls to 16123 in one year: farmers do ask for help."], 0.6, 2.0, 12.1, 3.5, size=24)
    footer(s, "Mannan et al. 2021, BJAR (Chattogram, Jashore, Mymensingh, 2014–15); Toxicology Reports 2023 "
              "systematic review (via DOAJ); BSS/AIS, 2 Jul 2026")
    notes(s, "The person who profits from a sale is often the farmer's main adviser. The dealer figure is from a "
             "2014-15 survey of brinjal farmers, not rice farmers. The call-centre figure shows that farmers "
             "already ask for independent advice.")

    s = headline_slide("One photo in, one honest answer out.")
    for i, name in enumerate(["02_photo.png", "03_confirm.png", "04_blb_answer.png"]):
        picture_or_placeholder(s, SCREENS / name, 1.0 + i * 3.6, 1.7, 4.2)
    textbox(s, [H["R1_BLB"], "No insecticide needed — fix the fertiliser"], 0.6, 6.0, 12.1, 0.8, size=18)
    footer(s, "Screens from the hosted app; the leaf is a sample image from the RiceLeafBD test split")
    notes(s, "The farmer ticks consent, uploads a photo, and sees a confirm-back line and the answer. The same "
             "text is played as a human-recorded clip. This example is bacterial leaf blight, where insecticide "
             "does not help.")

    s = headline_slide("Code decides; the model only recognises.")
    steps = ["Photo", "ONNX classifier [working]", "Confidence gate [working]", "6-row rule table [working]",
             "Reviewed Bangla text + recorded clip [working]"]
    for i, text in enumerate(steps):
        box(s, text, 0.5 + i * 2.55, 2.2, 2.05, 1.3, size=14)
        if i < len(steps) - 1:
            arrow(s, 0.5 + i * 2.55 + 2.08, 2.68)
    box(s, f"Voice → Gemini symptom list {voice_status}", 3.05, 4.3, 4.6, 0.9, size=14, fill=(0xFF, 0xF3, 0xD6))
    textbox(s, ["↑ can only add caution"], 7.8, 4.45, 4.5, 0.6, size=16)
    footer(s, "Rule table: data/rules.csv in the repo")
    notes(s, "The classifier only names one of four classes. Plain Python code then picks one of six rules, and "
             "the farmer sees only pre-written, reviewed text. A voice note can move an answer towards a "
             "referral, never towards a spray.")

    s = headline_slide("Four answers, each traced to an official source.")
    grid = [(H["R1_BLB"], "No insecticide needed — fix the fertiliser (bacterial leaf blight)"),
            (H["R2_BLAST"], "Spray correctly, with safety steps (blast)"),
            (H["R3_HEALTHY"], "No spray now — keep watching (healthy)"),
            (H["R5_ABSTAIN"], "Not sure → call 16123 (anything else, or uncertain)")]
    for i, (bn, en) in enumerate(grid):
        box(s, f"{bn}\n{en}", 0.6 + (i % 2) * 6.15, 1.8 + (i // 2) * 2.4, 5.95, 2.2, size=16)
    footer(s, "BRRI Plant Pathology notice 19 Mar 2023; DAE/BAMIS bulletin Mar 2023; Ali et al. 2017; "
              "DAE Krishi Call Centre 16123")
    notes(s, "The BLB answer omits the sulphur-based foliar mix in the official notice and refers the farmer "
             "instead. The blast answer names only the active-ingredient group, never a brand or a dose, and "
             "always adds the safety script.")

    s = headline_slide("We built it and measured it, including where it fails.")
    f1 = num("test_macro_f1")
    lines = [f"Our test photos (n = {S.get('test_n', NA)}): macro-F1 {NA if f1 is None else f'{f1:.3f}'}; advice given "
             f"{k_of_n('test_advice_given', 'test_n')}, wrong {S.get('test_wrong_advice', NA)}.",
             f"Our field photos: advice given {k_of_n('field_advice_given', 'field_n')}, "
             f"wrong {S.get('field_wrong_advice', NA)}.",
             f"External test ({S.get('external_dataset') or NA}): advice given "
             f"{k_of_n('external_advice_given', 'external_n')}, right {S.get('external_right_advice', NA)}; "
             f"junk referred {k_of_n('external_junk_referred', 'external_junk_n')}.",
             "Diseases from a new source are referred, not recognised.",
             f"Own healthy leaves wrongly sent to a spray class: "
             f"{k_of_n('own_healthy_false_trigger_n', 'own_healthy_n')}."]
    if S.get("offscript_failures") == 0 and S.get("invented_doses") == 0 and S.get("offscript_n"):
        lines.append(f"0 off-script answers and 0 invented doses in {S['offscript_n']}.")
    if S.get("target_met") is False:
        lines.append("The model abstains more than we would like.")
    textbox(s, lines, 0.6, 1.8, 12.1, 4.6, size=20)
    footer(s, "training/eval_report.md; datasets CC BY 4.0 (DOIs 10.17632/kx9rx8p2mz.1, 10.17632/sjkptpgv79.2, "
              "10.17632/znsxdctwtt.1)")
    notes(s, "Every number comes from training/eval_summary.json and has its n. Field photos matter most, "
             "because that is what farmers send. Our first model learned the photo background instead of the "
             "disease, so we added a third dataset and a stricter threshold. Blast in field photos is still "
             "mostly referred, not recognised.")

    s = headline_slide("Kom Bish adds a spray-or-not rule that others do not show.")
    rows = [("", "Spray-or-not rule + sprays-avoided count"), ("Kom Bish", "Yes"), ("Rice Solution", VERIFY),
            ("Dr. Chashi", VERIFY), ("Groundnut IPM app", VERIFY), ("16123 call centre", VERIFY)]
    table = s.shapes.add_table(len(rows), 2, Inches(0.6), Inches(1.7), Inches(7.2), Inches(3.3)).table
    for r, (a, b) in enumerate(rows):
        for c, text in enumerate((a, b)):
            cell = table.cell(r, c)
            cell.text = text
            for p in cell.text_frame.paragraphs:
                for run in p.runs:
                    run.font.size = Pt(14)
    textbox(s, ["Bt brinjal: −51% applications.", "Rice, need-based: 0–1 vs 2–4 sprays.",
                "Our pilot will measure how much a voice adviser delivers."], 8.1, 1.8, 4.7, 3.5, size=18)
    footer(s, "IFPRI Bt brinjal RCT (1,200 farmers); Ali et al. 2017 (about 12 need-based fields)")
    notes(s, "Competitor cells are filled only from sources by the team. The two figures show that fewer "
             "sprays are possible in Bangladesh; they are not results of Kom Bish. Measuring our own effect "
             "needs a pilot.")

    s = headline_slide("These are our limits, and this is what we do next.")
    textbox(s, ["Diseases from a new source are referred, not recognised.", f"{agronomy_line()}.", "No field test.",
                "Next: SAAO review, 30-farmer pilot."], 0.6, 2.0, 12.1, 3.5, size=24)
    footer(s, "training/eval_report.md")
    notes(s, "The model may have learned the source dataset rather than the disease, which is why we report "
             "per-source and cross-source numbers. Nobody has checked what a farmer did after an answer. The "
             "next steps are an officer's review of the rules and a small pilot.")


def main(argv: list[str] | None = None) -> int:
    global S
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--out", type=Path, default=ROOT / "deck" / "Kom_Bish_deck.pptx")
    p.add_argument("--summary", type=Path, default=SUMMARY)
    p.add_argument("--voice", choices=["on", "off", "undecided"], default="undecided", help="gate G3 decision")
    p.add_argument("--video-url", default="VIDEO_URL_TODO")
    p.add_argument("--demo-url", default="DEMO_URL_TODO")
    args = p.parse_args(argv)
    if args.summary.exists():
        S = json.loads(args.summary.read_text(encoding="utf-8"))
    else:
        print(f"WARNING: {args.summary} not found (step 20). Every number will show {NA}.")
    build(args.voice, args.video_url, args.demo_url)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(args.out))
    print(f"Wrote {args.out} ({len(prs.slides)} slides)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

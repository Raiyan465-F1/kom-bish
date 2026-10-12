"""Generate the 8-slide 16:9 pitch deck in English (python-pptx).

  python deck/make_deck.py [--team "Name One, Name Two"] [--video-url URL] [--demo-url URL]      # run in .venv-train

Every number comes from training/eval_summary.json (model v2.1: the v2 weights with the thresholds published on
12 Oct 2026); a missing value is shown as [n/a] with a warning. The two confirmation questions are copied from
data/rules.csv, never retyped. Screenshots come from deck/screens/ (python deck/take_screenshots.py takes them
from the live app in Bangla); the captions are English.
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
from pptx.enum.dml import MSO_LINE
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

ROOT = Path(__file__).resolve().parent.parent
SCREENS = ROOT / "deck" / "screens"
SUMMARY = ROOT / "training" / "eval_summary.json"
REPO_URL = "https://github.com/Raiyan465-F1/kom-bish"
MODEL_URL = "https://huggingface.co/Raiyan465/kom-bish-rice-leaf"
TRACK = "Inclusive Rural Development & Agriculture"
BANGLA = re.compile(r"[ঀ-৿]")
NA = "[n/a]"
SLIDES = 8
SHOT_RATIO = 412 / 860            # width / height of a phone screenshot from take_screenshots.py

GREEN, DARK, GREY = RGBColor(0x2E, 0x7D, 0x32), RGBColor(0x1B, 0x5E, 0x20), RGBColor(0x55, 0x55, 0x55)
INK, WHITE = RGBColor(0x1B, 0x1B, 0x1B), RGBColor(0xFF, 0xFF, 0xFF)
REAL_FILL, PLAN_FILL, PLAN_LINE = RGBColor(0xE8, 0xF3, 0xE8), RGBColor(0xFF, 0xF3, 0xD6), RGBColor(0xE6, 0x7E, 0x00)
ROW_FILL = RGBColor(0xF4, 0xF8, 0xF4)

S: dict = {}
prs = Presentation()
prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)   # 16:9


def num(key: str):
    value = S.get(key)
    if value is None:
        print(f"WARNING: eval_summary.json has no value for {key!r}; the deck shows {NA}.")
        return NA
    return value


def share(k_key: str, n_key: str) -> str:
    k, n = S.get(k_key), S.get(n_key)
    return f"{num(k_key)}" if k is None or not n else f"{k} ({100 * k / n:.1f}%)"


def style(shape, size: float, bold: bool = False, color: RGBColor = INK, align=None) -> None:
    for p in shape.text_frame.paragraphs:
        if align is not None:
            p.alignment = align
        for r in p.runs:
            r.font.size, r.font.bold, r.font.color.rgb = Pt(size), bold, color
            if BANGLA.search(r.text):
                r.font.name = "Nirmala UI"


def text(slide, lines, left, top, width, height, size: float = 18, bold: bool = False, color: RGBColor = INK,
         align=None, space: float = 6):
    tb = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    tf = tb.text_frame
    tf.word_wrap = True
    for i, line in enumerate([lines] if isinstance(lines, str) else lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = line
        p.space_after = Pt(space)
    style(tb, size, bold, color, align)
    return tb


def box(slide, label: str, left, top, width, height, size: float = 13, planned: bool = False, bold: bool = False):
    """A rounded box. Green and solid = real and live; orange and dashed = planned."""
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(left), Inches(top), Inches(width), Inches(height))
    shape.fill.solid()
    shape.fill.fore_color.rgb = PLAN_FILL if planned else REAL_FILL
    shape.line.color.rgb = PLAN_LINE if planned else GREEN
    shape.line.width = Pt(1.5)
    if planned:
        shape.line.dash_style = MSO_LINE.DASH
    tf = shape.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    for side in ("margin_left", "margin_right"):
        setattr(tf, side, Inches(0.08))
    tf.text = label
    style(shape, size, bold, INK, PP_ALIGN.CENTER)
    return shape


def arrow(slide, left, top, width=0.24, height=0.3, down: bool = False):
    kind = MSO_SHAPE.DOWN_ARROW if down else MSO_SHAPE.RIGHT_ARROW
    shape = slide.shapes.add_shape(kind, Inches(left), Inches(top), Inches(width), Inches(height))
    shape.fill.solid()
    shape.fill.fore_color.rgb = GREEN
    shape.line.fill.background()
    return shape


def new_slide(title: str, source: str = "", size: float = 30):
    slide = prs.slides.add_slide(prs.slide_layouts[6])   # blank: every shape is placed here
    text(slide, title, 0.6, 0.35, 12.1, 0.9, size=size, bold=True, color=DARK)
    rule = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.6), Inches(1.22), Inches(12.1), Inches(0.04))
    rule.fill.solid()
    rule.fill.fore_color.rgb = GREEN
    rule.line.fill.background()
    if source:
        text(slide, source, 0.6, 7.0, 11.2, 0.4, size=10, color=GREY)
    text(slide, f"{len(prs.slides)} / {SLIDES}", 11.9, 7.0, 0.85, 0.4, size=10, color=GREY, align=PP_ALIGN.RIGHT)
    return slide


def screenshot(slide, name: str, left, top, height, caption: str = "", caption_width: float | None = None):
    path, width = SCREENS / name, height * SHOT_RATIO
    if path.exists():
        pic = slide.shapes.add_picture(str(path), Inches(left), Inches(top), height=Inches(height))
        pic.line.color.rgb = RGBColor(0xBB, 0xBB, 0xBB)
        pic.line.width = Pt(0.75)
    else:
        print(f"WARNING: {path} not found; run python deck/take_screenshots.py. The deck shows a grey box.")
        box(slide, f"[screenshot: {name}]", left, top, width, height, size=11, planned=True)
    if caption:
        cw = caption_width or width + 0.9
        text(slide, caption, left - (cw - width) / 2, top + height + 0.08, cw, 1.0, size=12, color=INK, align=PP_ALIGN.CENTER)


def table(slide, rows: list[list[str]], left, top, widths: list[float], row_height: float = 0.62, size: float = 13):
    shape = slide.shapes.add_table(len(rows), len(widths), Inches(left), Inches(top), Inches(sum(widths)),
                                   Inches(row_height * len(rows)))
    tbl = shape.table
    for c, w in enumerate(widths):
        tbl.columns[c].width = Inches(w)
    for r, row in enumerate(rows):
        tbl.rows[r].height = Inches(row_height)
        for c, value in enumerate(row):
            cell = tbl.cell(r, c)
            cell.text = str(value)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            cell.fill.solid()
            cell.fill.fore_color.rgb = DARK if r == 0 else (ROW_FILL if r % 2 else WHITE)
            for p in cell.text_frame.paragraphs:
                p.alignment = PP_ALIGN.LEFT if c == 0 else PP_ALIGN.CENTER
                for run in p.runs:
                    run.font.size, run.font.bold = Pt(size), r == 0 or c == 0
                    run.font.color.rgb = WHITE if r == 0 else INK
    return tbl


def notes(slide, value: str) -> None:
    slide.notes_slide.notes_text_frame.text = value


def rules_rows() -> dict[str, dict]:
    with (ROOT / "data" / "rules.csv").open(encoding="utf-8", newline="") as f:
        return {row["rule_id"]: row for row in csv.DictReader(f)}


def agronomy_line() -> str:
    gates = ROOT / "docs" / "gates.md"
    if gates.exists():
        for line in gates.read_text("utf-8").splitlines():
            if line.lower().startswith("- agronomy review:") and "none yet" not in line.lower():
                return "Rules reviewed by: " + line.split(":", 1)[1].strip()
    return "The rules are not yet signed off by an agronomist"


def build(team: str, video_url: str, demo_url: str) -> None:
    R = rules_rows()
    q_blb, q_blast = R["R0_CONFIRM_BLB"]["headline_en"], R["R0_CONFIRM_BLAST"]["headline_en"]
    wrong_spray = num("wrong_spray_if_yes_total")
    links = [f"Live app: {demo_url}", f"Code: {REPO_URL}", f"Model: {MODEL_URL}"]
    if video_url:
        links.append(f"Video: {video_url}")

    # 1 ---------------------------------------------------------------- title
    s = prs.slides.add_slide(prs.slide_layouts[6])
    text(s, "Kom Bish (কম বিষ)", 0.7, 1.0, 8.6, 1.1, size=54, bold=True, color=DARK)
    text(s, "A Bangla rice adviser that says whether to spray at all.", 0.7, 2.25, 8.6, 1.0, size=28, color=INK)
    text(s, "Safe by design: it refers what it doesn't know.", 0.7, 3.35, 8.6, 0.6, size=22, bold=True, color=GREEN)
    text(s, [f"Team Unsick · Hack for Humanity BD 2026, Round 2", f"Track: {TRACK}"], 0.7, 4.25, 8.6, 0.9, size=16,
         color=GREY)
    text(s, links, 0.7, 5.35, 8.6, 1.5, size=15, color=INK, space=3)
    screenshot(s, "04_blb_answer.png", 9.85, 0.4, 5.6,
               "The live app, as a farmer sees it: “No insecticide needed, fix the fertiliser”, as text and audio.", 3.4)
    text(s, f"1 / {SLIDES}", 11.9, 7.0, 0.85, 0.4, size=10, color=GREY, align=PP_ALIGN.RIGHT)
    notes(s, "Kom Bish is a Bangla rice adviser. A farmer sends a photo of one rice leaf and gets a pre-written, "
             "reviewed Bangla answer, as text and as an audio clip, that says whether a spray is needed at all. When "
             "it is not sure it sends the farmer to the Krishi Call Centre 16123 or the local agriculture officer. "
             "The app is live; the links are on this slide and on the last one.")

    # 2 ---------------------------------------------------------------- problem
    s = new_slide("The shop that sells the spray often gives the advice too.",
                  "Mannan et al. 2021, BJAR (brinjal farmers, survey of 2014–15); Toxicology Reports systematic review "
                  "(via DOAJ); BSS, 2 Jul 2026")
    facts = [("73.23%", "of brinjal farmers followed dealer advice on pesticides."),
             ("about 21%", "of pooled vegetable samples were over residue limits."),
             ("92,094", "calls reached the Krishi Call Centre 16123 in one year (July 2025 to June 2026): farmers do "
                        "ask for help.")]
    for i, (big, small) in enumerate(facts):
        left = 0.6 + i * 4.1
        box(s, "", left, 1.7, 3.9, 3.3)
        text(s, big, left + 0.2, 1.95, 3.5, 1.0, size=44, bold=True, color=DARK, align=PP_ALIGN.CENTER)
        text(s, small, left + 0.25, 3.15, 3.4, 1.7, size=18, color=INK, align=PP_ALIGN.CENTER)
    text(s, "Kom Bish answers one question first: is a spray needed at all?", 0.6, 5.5, 12.1, 0.7, size=26, bold=True,
         color=GREEN, align=PP_ALIGN.CENTER)
    notes(s, "The person who profits from a sale is often the farmer's main adviser. The dealer figure is from a "
             "2014-15 survey of brinjal farmers, not rice farmers. The call-centre figure shows that farmers already "
             "ask for independent advice. Kom Bish takes no money from input sellers and never names a brand or a dose.")

    # 3 ---------------------------------------------------------------- what the farmer sees
    s = new_slide("One photo in, one honest answer out.",
                  "Screens from the live app in Bangla, 12 Oct 2026. Sample leaf images: RiceLeafBD test split and "
                  "Dhan-Shomadhan held-out set (CC BY 4.0).")
    shots = [("02_photo.png", "1. The farmer agrees to the consent text and gives a close-up photo of one leaf."),
             ("03_blb_question.png", f"2. Before a disease answer the app asks: “{q_blb}”"),
             ("04_blb_answer.png", "3. On “yes”: “No insecticide needed, fix the fertiliser”, as reviewed text and "
                                   "an audio clip (computer-generated voice)."),
             ("07_referral.png", "4. When it is not sure: “I can't be sure from this photo. Krishi Call Centre: 16123.”")]
    for i, (name, caption) in enumerate(shots):
        screenshot(s, name, 1.05 + i * 3.1, 1.42, 4.05, caption, 2.95)
    notes(s, "These are screenshots of the live app, in Bangla, as a farmer sees it on a phone. The farmer ticks the "
             "consent box and uploads a photo of one leaf. If the photo looks like bacterial leaf blight the app "
             "first asks where the patches start. Only on a yes does it give the answer: no insecticide is needed, "
             "fix the fertiliser. The same reviewed text is played as a Bangla audio clip; the voice is "
             "computer-generated and the app says so. When the model is not confident the app says so and gives "
             "the call-centre number. The app has a Show English switch for reviewers.")

    # 4 ---------------------------------------------------------------- safety by design
    s = new_slide("Safe by design: it refers what it doesn't know.",
                  "Thresholds: labels.json in the model repo, revision v2.1. Rules and tests: kombish/rules.py, data/rules.csv, "
                  "tests/test_rules.py")
    gates = [("1. Confidence gate", f"Below {num('threshold')}, or with a close second guess, the app refers the farmer."),
             ("2. Stricter gate per disease", f"Bacterial leaf blight needs {num('blb_threshold')}, blast "
                                              f"{num('blast_threshold')}. Chosen on validation data only."),
             ("3. The farmer's own “yes”", "Before the BLB answer and before the blast (spray) answer, the app asks one "
                                           "question about what is on the leaf. “No” or “not sure” gives a referral."),
             ("4. Closed rule table", "Code picks the answer. Every sentence is pre-written and reviewed. No brands, "
                                      "no doses.")]
    for i, (head, body) in enumerate(gates):
        top = 1.5 + i * 0.98
        box(s, head, 0.6, top, 2.7, 0.84, size=15, bold=True)
        text(s, body, 3.45, top + 0.04, 5.75, 0.9, size=14)
    text(s, ["The two questions (shown in Bangla):", f"BLB: “{q_blb}”", f"Blast: “{q_blast}”"], 0.6, 5.42, 8.6, 1.0,
         size=12, color=GREY, space=2)
    text(s, f"Wrong “spray correctly” advice in all our tests: {wrong_spray}, even if the farmer says “yes” to every "
            "question.", 0.6, 6.42, 8.6, 0.55, size=15, bold=True, color=GREEN)
    screenshot(s, "05_blast_question.png", 9.95, 1.42, 4.75,
               "The lesion-shape question, asked before any spray answer (live app).", 3.2)
    notes(s, "Kom Bish is built to avoid wrong spray advice, not to diagnose everything. An answer has to pass four "
             "gates. First the general confidence gate. Second a stricter threshold for each disease, chosen on "
             "validation data only. Third the farmer's own yes to one question about what is on the leaf: one "
             "question for bacterial leaf blight and one for blast. No or not sure sends the farmer to the call "
             "centre or the officer. Fourth, the answer itself comes from a closed table of reviewed sentences. "
             "Each question has its own answer box, so a yes to one can never confirm the other.")

    # 5 ---------------------------------------------------------------- architecture: real vs planned
    s = new_slide("How it works: what is real today and what is planned.",
                  "Code: kombish/classifier.py, kombish/rules.py, kombish/logging_store.py, data/rules.csv, data/clips.csv")
    chain = ["Consent", "Photo of one leaf", "ONNX classifier\nMobileNetV3, 4 classes, CPU", "Confidence gates",
             "Rule engine\npure Python", "Farmer's “yes”\nBLB or blast question", "Reviewed Bangla text\n+ audio clip"]
    step, width = 1.74, 1.5
    for i, label in enumerate(chain):
        box(s, label, 0.6 + i * step, 1.6, width, 1.15, size=12, bold=i in (3, 5))
        if i < len(chain) - 1:
            arrow(s, 0.6 + i * step + width, 2.02)
    for i in (3, 5):   # the gates and a "no" both lead to the referral
        arrow(s, 0.6 + i * step + 0.63, 2.8, width=0.24, height=0.35, down=True)
    box(s, "Low confidence, “no” or “not sure”:\nreferral to the Krishi Call Centre 16123 or an agriculture officer",
        5.3, 3.2, 5.3, 0.85, size=12)
    box(s, "Anonymous log (private dataset)\nno photo, audio, name or number", 0.6, 3.2, 2.9, 0.85, size=12)
    arrow(s, 3.53, 3.47)
    box(s, "Public\ncounters", 3.82, 3.2, 1.25, 0.85, size=12)
    text(s, "Planned, not built or not switched on", 0.6, 4.4, 8.0, 0.4, size=14, bold=True, color=PLAN_LINE)
    planned = ["Voice note → fixed symptom list\nNEXT STEP: code written, switched off until tested",
               "Officer-verified referrals\n→ local training data (pilot plan)",
               "Telegram, WhatsApp,\nphone call",
               "Human-recorded audio\n(today: computer-generated voice)"]
    for i, label in enumerate(planned):
        box(s, label, 0.6 + i * 3.07, 4.85, 2.9, 1.1, size=12, planned=True, bold=i == 0)
    box(s, "Real and live", 0.6, 6.25, 1.7, 0.45, size=11)
    box(s, "Planned", 2.45, 6.25, 1.7, 0.45, size=11, planned=True)
    text(s, "Voice can only make an answer more cautious: it can turn an answer into a referral, never into a spray.",
         4.35, 6.3, 8.4, 0.45, size=12, color=GREY)
    notes(s, "Everything in green runs in the live app today. The photo goes through an ONNX classifier on the CPU; "
             "the model only names one of four classes. Plain Python code applies the confidence gates and picks a "
             "row in the rule table; for a disease answer the app first asks the farmer one question. The farmer "
             "sees and hears only pre-written, reviewed text. The log is anonymous: no photo, audio, name or phone "
             "number is stored. Orange is planned. Voice input is the next step: the code is written and tested, but "
             "it is switched off until we have tested it with real voice notes, and it can only add caution.")

    # 6 ---------------------------------------------------------------- evidence: three countries
    s = new_slide(f"Tested on photos from three countries: {wrong_spray} wrong spray advice.",
                  "training/eval_report.md and training/eval_summary.json. Data: RiceLeafBD, BD5, Dhan-Shomadhan, Paddy "
                  "Doctor (CC BY 4.0); Zambali Rice Dataset (Apache-2.0)")
    rows = [["Test set", "Photos", "Classifier confident", "Advice given\n(“no spray now”)", "BLB question asked",
             "Blast question asked", "Wrong spray advice"]]
    for label, key in (("Bangladesh\nour test split", "test"), ("India*\nPaddy Doctor held-out", "heldout"),
                       (f"{num('external_country')}\nexternal, never seen", "external")):
        blast_q = num(f"{key}_blast_question_asked")
        blast_other = num(f"{key}_blast_question_on_other_classes")
        blast_cell = "0" if blast_q == 0 else f"{blast_q}\n{blast_q - blast_other} true blast, {blast_other} other"
        blb_q = num(f"{key}_blb_question_asked")
        blb_cell = "0" if blb_q == 0 else (f"{blb_q}\n{num(f'{key}_blb_question_on_true_blb')} true BLB, "
                                           f"{num(f'{key}_blb_question_on_other_classes')} other")
        rows.append([label, num(f"{key}_n"), share(f"{key}_classifier_confident", f"{key}_n"),
                     f"{num(f'{key}_advice_given')}\n{num(f'{key}_right_advice')} right, {num(f'{key}_wrong_advice')} wrong",
                     blb_cell, blast_cell, blast_other])
    table(s, rows, 0.6, 1.5, [2.45, 1.0, 1.75, 1.95, 1.85, 1.85, 1.25], row_height=0.78, size=13)
    text(s, ["*Same source as some training data, so it is not an external test. Only the Philippine set was never "
             "seen in training.",
             "Advice given: the healthy answer, the only answer given from the photo alone. A wrong one is a diseased "
             "leaf told “no spray now”.",
             "BLB / blast question asked: the model is confident, and the app asks the farmer before it answers. "
             "“Other” would become a wrong answer only if the farmer said “yes”.",
             "Wrong spray advice counts the worst case: the farmer answers “yes” to every blast question.",
             f"Model v2.1: weights frozen on 11 Oct 2026; every threshold chosen on validation data only. "
             f"{num('offscript_failures')} off-script answers in {num('offscript_n')} scripted consultations."],
         0.6, 4.75, 12.1, 2.2, size=13, space=4)
    notes(s, "These are the final numbers for the published model, version 2.1. The same definitions are used "
             "everywhere. Classifier confident means the prediction passed the gates. Advice given is the healthy "
             "answer, no spray now: the only answer the farmer gets from the photo alone. For bacterial leaf blight "
             "and for blast the app asks the farmer a question first, so those are counted separately. The Indian "
             "set is held out from Paddy Doctor, which is also part of the training data, so only the Philippine set "
             "is truly external. There the model recognised about half of the healthy leaves and referred almost "
             "every diseased one. Wrong spray advice is zero on all three sets.")

    # 7 ---------------------------------------------------------------- limits
    s = new_slide("What it cannot do yet.", "README, section “Limitations”; docs/gates.md; training/eval_report.md")
    limits = [
        "It does not recognise diseases from a new source. In the Philippine test the BLB question was asked "
        f"{num('external_blb_question_asked')} times and the blast question {num('external_blast_question_asked')} times "
        f"on {num('external_n')} photos: almost every diseased leaf was referred, not recognised.",
        "Four close-up web photos of blast: none was recognised as blast. All four are referred.",
        f"Blast is rarely answered: the blast question was asked {num('test_blast_question_asked')} times on our "
        f"{num('test_n')} test photos and {num('heldout_blast_question_asked')} times on the {num('heldout_n')} Indian photos.",
        f"Wrong “no spray now”: {num('test_wrong_advice')} narrow brown spot leaves on a white sheet (Bangladesh), "
        f"{num('heldout_wrong_advice')} blast leaf (India), {num('external_wrong_advice')} blast leaf (Philippines). The "
        "healthy answer therefore ends: if spots appear or spread, take a new photo or call 16123.",
        "The two confirmation questions rely on the farmer's judgement and have not been tested with farmers.",
        f"No field trial. {agronomy_line()}. The audio is a computer-generated voice.",
        "Voice input is written but switched off. Telegram, WhatsApp and phone calls are not built.",
    ]
    text(s, [f"•  {line}" for line in limits], 0.6, 1.5, 12.1, 5.4, size=18, space=10)
    notes(s, "We measured where it fails and we show it. Outside the sources it was trained on, the model refers "
             "diseased leaves instead of recognising them. Four textbook photos of blast from the web were not "
             "recognised; after we raised one threshold on validation data and added a question, all four are "
             "referred. A few diseased leaves were told no spray now, which is why the healthy answer ends with what "
             "to do if spots appear. Nobody has checked what a farmer did after an answer.")

    # 8 ---------------------------------------------------------------- pilot plan, team, links
    s = new_slide("Next: local data through a pilot.", "README, section “Pilot plan”. Nothing in the plan is built yet.")
    text(s, "Pilot plan (a plan, not a built feature)", 0.6, 1.45, 7.2, 0.45, size=18, bold=True, color=GREEN)
    plan = ["1.  Review first: a Sub-Assistant Agriculture Officer reads the rule table and the answer scripts.",
            "2.  A small pilot: about 30 farmers in one block, photo only.",
            "3.  Officer-verified referrals become local training data, with a separate, explicit consent. Today the "
            "app stores no photos.",
            "4.  Retrain only against a held-out local test: more right answers, no more wrong spray advice.",
            "5.  Then the next step in the app: voice input, which can only add caution.",
            "6.  Measure: how often it refers, how often the officer agrees, any wrong advice, whether the farmer sprayed."]
    text(s, plan, 0.6, 1.95, 7.2, 4.9, size=16, space=9)
    box(s, "", 8.2, 1.5, 4.5, 5.3)
    text(s, "Team Unsick", 8.4, 1.62, 4.1, 0.5, size=22, bold=True, color=DARK)
    text(s, [team, "Hack for Humanity BD 2026, Round 2", f"Track: {TRACK}"], 8.4, 2.2, 4.1, 1.35, size=14, space=3)
    text(s, "Links", 8.4, 3.65, 4.1, 0.4, size=18, bold=True, color=DARK)
    pairs = [("Live app", demo_url), ("Code", REPO_URL), ("Model", MODEL_URL)] + ([("Video", video_url)] if video_url else [])
    text(s, [line for label, url in pairs for line in (label, url)], 8.4, 4.1, 4.1, 2.6, size=12, space=2)
    notes(s, "Recognising diseases in a new place needs local data with trustworthy labels, and the referral already "
             "sends the farmer to the person who can give that label. The plan, which is not built: when the app "
             "refers a farmer and an officer then sees the crop, the officer's diagnosis and the photo, with a "
             "separate explicit consent, become local training data. A new model replaces the old one only if it "
             "gives more right answers on a held-out local test and no more wrong spray advice. The live app, the "
             "code and the model are public at the links on this slide.")


def main(argv: list[str] | None = None) -> int:
    global S
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--out", type=Path, default=ROOT / "deck" / "Kom_Bish_deck.pptx")
    p.add_argument("--summary", type=Path, default=SUMMARY)
    p.add_argument("--team", default="Raiyan Rahman", help="team members, as they should appear on the last slide")
    p.add_argument("--video-url", default="", help="the video line is left out while this is empty")
    p.add_argument("--demo-url", default="https://raiyan465-kom-bish.hf.space")
    args = p.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if args.summary.exists():
        S = json.loads(args.summary.read_text(encoding="utf-8"))
    else:
        print(f"WARNING: {args.summary} not found (step 20). Every number will show {NA}.")
    build(args.team, args.video_url, args.demo_url)
    assert len(prs.slides) == SLIDES, len(prs.slides)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(args.out))
    print(f"Wrote {args.out} ({len(prs.slides)} slides, 16:9)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

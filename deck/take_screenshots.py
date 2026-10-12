"""Take the deck screenshots from the running app, as a farmer sees it on a phone (Bangla, "Show English" off).

  python deck/take_screenshots.py [--url https://raiyan465-kom-bish.hf.space]      # run in .venv-train

Uses Playwright with the installed Microsoft Edge (pip install playwright; 1.63.0 was used; no browser download). Writes
deck/screens/*.png. Every answer shown here is logged by the app as a consultation: tag those records as test
traffic afterwards (scripts/tag_test_records.py prints how).
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
SCREENS = ROOT / "deck" / "screens"
EXAMPLES = ROOT / "examples"
sys.path.insert(0, str(ROOT))
from kombish import texts  # noqa: E402


def headlines() -> dict[str, str]:
    with (ROOT / "data" / "rules.csv").open(encoding="utf-8", newline="") as f:
        return {row["rule_id"]: row["headline_bn"] for row in csv.DictReader(f)}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--url", default="https://raiyan465-kom-bish.hf.space")
    p.add_argument("--channel", default="msedge", help="installed browser to drive: msedge or chrome")
    args = p.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    H = headlines()
    SCREENS.mkdir(parents=True, exist_ok=True)
    started = dt.datetime.now(dt.timezone.utc)

    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel=args.channel, headless=True)
        page = browser.new_page(viewport={"width": 412, "height": 860}, device_scale_factor=2, locale="bn-BD")
        page.goto(args.url, wait_until="domcontentloaded", timeout=120_000)   # the dashboard timer never goes idle
        button = page.get_by_role("button", name=texts.BUTTON_ADVISE_BN)
        button.wait_for(timeout=120_000)
        page.wait_for_timeout(3000)   # web font and example thumbnails

        def shot(name: str, anchor) -> None:
            """Scroll the anchor to just under the Space's floating title bar and save what the farmer sees."""
            anchor.evaluate("el => window.scrollTo(0, el.getBoundingClientRect().top + window.scrollY - 124)")
            page.wait_for_timeout(600)
            page.screenshot(path=str(SCREENS / name))
            print("wrote", name)

        def upload(file: str) -> None:
            page.locator("input[type=file]").first.set_input_files(str(EXAMPLES / file))
            page.wait_for_timeout(1500)

        def press_and_wait(headline: str):
            button.click()
            heading = page.get_by_role("heading", name=headline).first
            heading.wait_for(timeout=90_000)
            page.wait_for_timeout(1200)
            return heading

        def answer_yes(question: str) -> None:
            page.locator("fieldset", has_text=question).get_by_label(texts.YES_BN, exact=True).check()

        shot("01_home.png", page.get_by_role("heading", name="কম বিষ (Kom Bish)").first)
        page.get_by_label(texts.CONSENT_CHECKBOX_BN).check()

        # Bacterial leaf blight: the question first, then the answer on "yes".
        upload("blb_riceleafbd_test.jpg")
        shot("02_photo.png", page.get_by_text(texts.PHOTO_INSTRUCTION_BN).first)
        press_and_wait(H["R0_CONFIRM_BLB"])
        shot("03_blb_question.png", page.locator("fieldset", has_text=H["R0_CONFIRM_BLB"]).first)
        answer_yes(H["R0_CONFIRM_BLB"])
        shot("04_blb_answer.png", press_and_wait(H["R1_BLB"]))

        # Blast: the lesion-shape question first, then the spray answer with the safety clip on "yes".
        upload("blast_paddy_doctor_heldout.jpg")
        press_and_wait(H["R0_CONFIRM_BLAST"])
        shot("05_blast_question.png", page.locator("fieldset", has_text=H["R0_CONFIRM_BLAST"]).first)
        answer_yes(H["R0_CONFIRM_BLAST"])
        shot("06_blast_answer.png", press_and_wait(H["R2_BLAST"]))

        # A real blast leaf the model is not sure about: the referral.
        upload("not_sure_field_blast_dhanshomadhan_heldout.jpg")
        shot("07_referral.png", press_and_wait(H["R5_ABSTAIN"]))
        browser.close()

    ended = dt.datetime.now(dt.timezone.utc)
    print(f"These answers were logged as consultations between {started:%Y-%m-%dT%H:%M:%S} and "
          f"{ended:%Y-%m-%dT%H:%M:%S} UTC. Tag them:\n  python scripts/tag_test_records.py "
          f"--from {started:%Y-%m-%dT%H:%M:%S} --to {ended:%Y-%m-%dT%H:%M:%S} --reason \"deck screenshots\"")
    return 0


if __name__ == "__main__":
    sys.exit(main())

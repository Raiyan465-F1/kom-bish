"""Cut the raw demo recording into the submission video. Speech is never sped up; only dead time is removed.

  python video/make_demo_cut.py --source "C:/Users/raiya/Videos/NVIDIA/Desktop/kombish.mp4"     # run in .venv-train

Every kept piece is listed in CUTS (times in seconds of the raw recording). Pictures and sound can come from
different places: the narration about the leaf blight example was spoken while the screen still showed the
empty upload box, so it is laid over the moment the example is actually run. Deck slides (rendered from
deck/preview/Kom_Bish_deck.pdf) show during the spoken intro and ending, and short pieces of the app's own
audio clips (audio/*.mp3) play over the answer screens, because the recording has no clip audio there.

Burned in: English subtitles for the Bangla app clips only ("subs", words taken from gloss_en in data/clips.csv)
and one caption over the results slides ("caption"). Dark text on a light box in the bottom third.

Writes video/Kom_Bish_demo.mp4 (1080p, 30 fps, H.264 CRF 23, AAC, loudness-normalised, short audio fades at
every cut), video/subtitles_en.srt (the English narration from video/narration_transcript.json, a local
faster-whisper transcript with its mishearings corrected in FIXES, plus the clip subtitles) and
video/preview/contact_sheet.png (one frame per kept piece, with times). Needs ffmpeg on PATH or in the WinGet
links folder, and PyMuPDF and Pillow.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "video" / "Kom_Bish_demo.mp4"
PREVIEW = ROOT / "video" / "preview"
SLIDES = PREVIEW / "slides"
REFERRAL = ROOT / "deck" / "screens" / "07_referral.png"
NARRATION_GAIN, CLIP_GAIN, CONSENT_GAIN = 14, -2, 0   # dB; the narration was recorded about 15 dB below the clips
FADE = 0.06
SRT = ROOT / "video" / "subtitles_en.srt"
TRANSCRIPT = ROOT / "video" / "narration_transcript.json"
RESULTS_CAPTION = "0 wrong 'spray' advice across all test sets (Bangladesh, India, Philippines)"
# Mishearings in the automatic transcript of the narration.
FIXES = {"Ryan Nohoman": "Raiyan Rahman", "Bangla deshi": "Bangladeshi", "combish": "Kom Bish", "Kombish": "Kom Bish",
         "AIC's": "AI sees", "dry slave": "rice leaf"}

# Each piece: what is shown ("rec" times, a deck slide or the referral screenshot) and what is heard.
# audio: ("rec", start, end, gain) or ("clip", name, seconds, gain). Video pieces must add up to the audio length.
CUTS = [
    {"label": "Intro: name and team", "video": [("slide", 1)], "audio": ("rec", 2.65, 6.25, NARRATION_GAIN)},
    {"label": "Problem: dealer advice; Kom Bish decides whether to spray", "video": [("slide", 2)],
     "audio": ("rec", 7.55, 19.15, NARRATION_GAIN)},
    {"label": "Free Bangla web app, consent, close-up of one leaf", "video": [("rec", 20.6, 31.0)],
     "audio": ("rec", 20.6, 31.0, NARRATION_GAIN)},
    # "subs": (start, end, text) within the piece; the text is the clip's English meaning from data/clips.csv.
    {"label": "Consent clip (first 5 s)", "video": [("rec", 33.4, 38.75)], "audio": ("rec", 33.4, 38.75, CONSENT_GAIN),
     "subs": [(0.0, 5.35, "Kom Bish is a computer program, not a government officer.")]},
    {"label": "Tick, then upload", "video": [("rec", 46.55, 49.35)], "audio": ("rec", 46.55, 49.35, NARRATION_GAIN)},
    # ("hold", t, seconds) holds the frame at t: the question screen stays up while the narration explains it.
    {"label": "Leaf blight: the question, yes, the answer", "video": [("hold", 130.3, 6.5), ("rec", 130.3, 134.2),
                                                                     ("rec", 134.2, 146.6)],
     "audio": ("rec", 50.35, 73.15, NARRATION_GAIN)},
    {"label": "Leaf blight answer clip (first 7 s)", "video": [("rec", 154.0, 160.9)], "audio": ("clip", "blb", 6.9, CLIP_GAIN),
     "subs": [(0.0, 3.6, "It looks like bacterial leaf blight."),
              (3.6, 6.9, "Insecticide does not cure it, so don't buy any.")]},
    {"label": "Blast: the lesion question", "video": [("rec", 94.4, 99.45)], "audio": ("rec", 94.4, 99.45, NARRATION_GAIN)},
    {"label": "Blast answer clip (first 5 s)", "video": [("rec", 101.8, 107.2)], "audio": ("clip", "blast", 5.4, CLIP_GAIN),
     "subs": [(0.0, 2.55, "It looks like blast."), (2.55, 5.4, "This disease does need a spray, but done correctly.")]},
    {"label": "Safety clip (first 4.5 s)", "video": [("rec", 107.2, 111.7)], "audio": ("clip", "safety", 4.5, CLIP_GAIN),
     "subs": [(0.0, 2.25, "Before spraying, read the label on the packet or bottle"),
              (2.25, 4.5, "and check the colour band.")]},
    {"label": "Not sure: referral to 16123 (live-app screenshot)", "video": [("referral",)],
     "audio": ("clip", "not_sure", 5.5, CLIP_GAIN),
     "subs": [(0.0, 2.6, "I can't be sure from this photo."), (2.6, 5.5, "Better not to answer than to give wrong advice.")]},
    {"label": "Results: tested on photos ...", "video": [("slide", 6)], "audio": ("rec", 144.3, 147.5, NARRATION_GAIN),
     "caption": RESULTS_CAPTION},
    {"label": "... of Bangladesh, India and the Philippines", "video": [("slide", 6)],
     "audio": ("rec", 148.36, 150.1, NARRATION_GAIN), "caption": RESULTS_CAPTION},
    {"label": "Limit: not enough data", "video": [("slide", 7)], "audio": ("rec", 150.6, 154.75, NARRATION_GAIN),
     "caption": RESULTS_CAPTION},
    {"label": "Next step: a bigger data set", "video": [("slide", 8)], "audio": ("rec", 161.0, 169.45, NARRATION_GAIN)},
    {"label": "Real-field photos may get wrong answers", "video": [("slide", 7)],
     "audio": ("rec", 176.65, 181.3, NARRATION_GAIN)},
    {"label": "Train on local field photos; thank you", "video": [("slide", 8)], "audio": ("rec", 181.5, 193.3, NARRATION_GAIN)},
]


def tool(name: str) -> str:
    found = shutil.which(name)
    if found:
        return found
    links = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WinGet" / "Links" / f"{name}.exe"
    if links.exists():
        return str(links)
    raise SystemExit(f"{name} not found: install FFmpeg (winget install Gyan.FFmpeg.Essentials)")


def audio_seconds(a) -> float:
    return a[2] - a[1] if a[0] == "rec" else a[2]


def wrap(text: str, width: int = 42) -> list[str]:
    import textwrap
    return textwrap.wrap(text, width) or [""]


def overlay_png(text: str, path: Path, size: int, bold: bool) -> None:
    """A full-frame transparent PNG: dark text on a light box in the bottom third."""
    from PIL import Image, ImageDraw, ImageFont
    img = Image.new("RGBA", (1920, 1080), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype("C:/Windows/Fonts/" + ("calibrib" if bold else "calibri") + ".ttf", size)
    lines = [text] if draw.textlength(text, font=font) <= 1760 else wrap(text, 56)
    widths = [draw.textlength(line, font=font) for line in lines]
    line_h, pad = int(size * 1.25), 22
    box_w, box_h = int(max(widths)) + 2 * 34, line_h * len(lines) + 2 * pad
    x0, y0 = (1920 - box_w) // 2, 1080 - 96 - box_h
    draw.rounded_rectangle([x0, y0, x0 + box_w, y0 + box_h], radius=16, fill=(255, 255, 255, 240),
                           outline=(46, 125, 50, 255), width=3)
    for i, (line, w) in enumerate(zip(lines, widths)):
        draw.text(((1920 - w) / 2, y0 + pad + i * line_h), line, font=font, fill=(27, 27, 27, 255))
    img.save(path)


def render_slides() -> None:
    import fitz   # PyMuPDF
    SLIDES.mkdir(parents=True, exist_ok=True)
    pdf = ROOT / "deck" / "preview" / "Kom_Bish_deck.pdf"
    if not pdf.exists():
        raise SystemExit(f"{pdf} not found: render the deck with LibreOffice first (see docs/gates.md)")
    for i, page in enumerate(fitz.open(str(pdf)), 1):
        page.get_pixmap(dpi=144).save(str(SLIDES / f"slide_{i}.png"))   # 13.333 x 7.5 in -> 1920 x 1080


def render_piece(ff: str, src: str, cut: dict, out: Path) -> float:
    total = audio_seconds(cut["audio"])
    stills = [v for v in cut["video"] if v[0] in ("slide", "referral")]
    rec_total = sum(v[2] - v[1] if v[0] == "rec" else v[2] for v in cut["video"] if v[0] in ("rec", "hold"))
    if not stills and abs(rec_total - total) > 0.05:
        raise SystemExit(f"{cut['label']}: pictures last {rec_total:.2f} s but the sound lasts {total:.2f} s")
    args, chains = [ff, "-hide_banner", "-loglevel", "error", "-y"], []
    for k, v in enumerate(cut["video"]):
        d = v[2] - v[1] if v[0] == "rec" else v[2] if v[0] == "hold" else (total - rec_total) / len(stills)
        hold = ""
        if v[0] == "rec":
            args += ["-ss", f"{v[1]:.3f}", "-t", f"{d:.3f}", "-i", src]
        elif v[0] == "hold":
            args += ["-ss", f"{v[1]:.3f}", "-t", "0.5", "-i", src]
            hold = f"trim=end_frame=1,tpad=stop_mode=clone:stop_duration={d:.3f},"
        else:
            img = SLIDES / f"slide_{v[1]}.png" if v[0] == "slide" else REFERRAL
            args += ["-loop", "1", "-framerate", "30", "-t", f"{d:.3f}", "-i", str(img)]
        chains.append(f"[{k}:v]fps=30,scale=1920:1080:force_original_aspect_ratio=decrease,"
                      f"pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=white,setsar=1,format=yuv420p,{hold}"
                      f"trim=duration={d:.3f},setpts=PTS-STARTPTS[v{k}]")
    a = cut["audio"]
    ai = len(cut["video"])
    if a[0] == "rec":
        args += ["-ss", f"{a[1]:.3f}", "-t", f"{total:.3f}", "-i", src]
    else:
        args += ["-t", f"{total:.3f}", "-i", str(ROOT / "audio" / f"{a[1]}.mp3")]
    overlays = [(0.0, total, cut["caption"], 46, True)] if cut.get("caption") else []
    overlays += [(a0, b0, text, 44, False) for a0, b0, text in cut.get("subs", [])]
    chains.append("".join(f"[v{k}]" for k in range(len(cut["video"])))
                  + f"concat=n={len(cut['video'])}:v=1:a=0" + ("[c0]" if overlays else "[v]"))
    for j, (a0, b0, text, size, bold) in enumerate(overlays):
        png = out.with_name(f"{out.stem}_overlay{j}.png")
        overlay_png(text, png, size, bold)
        args += ["-loop", "1", "-framerate", "30", "-t", f"{total:.3f}", "-i", str(png)]
        target = "[v]" if j == len(overlays) - 1 else f"[c{j + 1}]"
        chains.append(f"[c{j}][{ai + 1 + j}:v]overlay=0:0:enable='between(t,{a0:.3f},{b0 - 0.001:.3f})'{target}")
    chains.append(f"[{ai}:a]aresample=48000,aformat=channel_layouts=stereo,volume={a[3]}dB,"
                  f"atrim=duration={total:.3f},afade=t=in:d={FADE},afade=t=out:st={total - FADE:.3f}:d={FADE}[a]")
    args += ["-filter_complex", ";".join(chains), "-map", "[v]", "-map", "[a]", "-t", f"{total:.3f}",
             "-c:v", "libx264", "-preset", "veryfast", "-crf", "16", "-c:a", "pcm_s16le", str(out)]
    subprocess.run(args, check=True)
    return total


def fmt(t: float) -> str:
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def write_srt(starts: list[tuple[float, float, str]]) -> int:
    """English subtitles for the whole cut: the narration word by word from the transcript, and the clip subtitles."""
    words = [w for seg in json.loads(TRANSCRIPT.read_text("utf-8")) for w in seg["words"]]
    cues: list[tuple[float, float, str]] = []
    for (start, _, _), cut in zip(starts, CUTS):
        if cut.get("subs"):
            cues += [(start + a0, start + b0, "[App] " + text) for a0, b0, text in cut["subs"]]
            continue
        a = cut["audio"]
        if a[0] != "rec":
            continue
        mine = [(start + w0 - a[1], start + w1 - a[1], tok.strip()) for w0, w1, tok in words
                if w0 >= a[1] - 0.05 and w1 <= a[2] + 0.1]
        cur: list = []
        for w in mine:
            text = " ".join(x[2] for x in cur + [w])
            gap = bool(cur) and w[0] - cur[-1][1] > 0.6
            done = bool(cur) and cur[-1][2][-1:] in ".?!" and len(" ".join(x[2] for x in cur)) > 24
            if cur and (len(wrap(text)) > 2 or gap or done or w[1] - cur[0][0] > 6.5):
                cues.append((cur[0][0], cur[-1][1], " ".join(x[2] for x in cur)))
                cur = []
            cur.append(w)
        if cur:
            cues.append((cur[0][0], cur[-1][1], " ".join(x[2] for x in cur)))
    out = []
    for i, (t0, t1, text) in enumerate(cues):
        for wrong, right in FIXES.items():
            text = re.sub(re.escape(wrong), right, text, flags=re.I)
        text = text.replace(" -", "-")   # the transcript splits "close-up" into "close -up"
        t1 = max(t1 + 0.3, t0 + 1.0)
        if i + 1 < len(cues):
            t1 = min(t1, cues[i + 1][0] - 0.02)
        out.append(f"{i + 1}\n{fmt(t0)} --> {fmt(t1)}\n" + "\n".join(wrap(text)))
    SRT.write_text("\n\n".join(out) + "\n", "utf-8", newline="\n")
    return len(out)


def contact_sheet(ff: str, starts: list[tuple[float, float, str]], video: Path) -> None:
    from PIL import Image, ImageDraw, ImageFont
    tmp = Path(tempfile.mkdtemp())
    tiles = []
    for i, (t0, d, label) in enumerate(starts):
        frame = tmp / f"{i:02d}.png"
        subprocess.run([tool("ffmpeg"), "-hide_banner", "-loglevel", "error", "-y", "-ss", f"{t0 + min(d / 2, 2.0):.2f}",
                        "-i", str(video), "-frames:v", "1", "-vf", "scale=480:-2", str(frame)], check=True)
        tiles.append((Image.open(frame).convert("RGB"), f"{i + 1}. {int(t0 // 60)}:{t0 % 60:04.1f}–"
                      f"{int((t0 + d) // 60)}:{(t0 + d) % 60:04.1f}", label))
    cols, w, h, cap = 4, 480, 270, 58
    rows = (len(tiles) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * w, rows * (h + cap)), "white")
    draw = ImageDraw.Draw(sheet)
    bold = ImageFont.truetype("C:/Windows/Fonts/calibrib.ttf", 20)
    small = ImageFont.truetype("C:/Windows/Fonts/calibri.ttf", 17)
    for i, (im, times, label) in enumerate(tiles):
        x, y = (i % cols) * w, (i // cols) * (h + cap)
        draw.text((x + 6, y + 4), times, font=bold, fill="black")
        draw.text((x + 6, y + 30), label[:52], font=small, fill=(60, 60, 60))
        sheet.paste(im, (x, y + cap))
    sheet.save(PREVIEW / "contact_sheet.png")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--source", required=True, help="the raw screen recording (MP4)")
    args = p.parse_args(argv)
    ff = tool("ffmpeg")
    PREVIEW.mkdir(parents=True, exist_ok=True)
    render_slides()
    work = Path(tempfile.mkdtemp(prefix="kombish_cut_"))
    starts, t = [], 0.0
    for i, cut in enumerate(CUTS):
        d = render_piece(ff, args.source, cut, work / f"p{i:02d}.mkv")
        starts.append((t, d, cut["label"]))
        t += d
        print(f"{i + 1:>2}. {starts[-1][0]:6.1f}–{t:6.1f} s  {cut['label']}")
    (work / "list.txt").write_text("".join(f"file '{(work / f'p{i:02d}.mkv').as_posix()}'\n" for i in range(len(CUTS))))
    subprocess.run([ff, "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i",
                    str(work / "list.txt"), "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-ar", "48000",
                    "-c:v", "libx264", "-preset", "medium", "-crf", "23", "-r", "30", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(work / "final.mp4")], check=True)
    final = OUT
    try:
        shutil.move(str(work / "final.mp4"), str(OUT))
    except PermissionError:
        spare = OUT.with_name("Kom_Bish_demo_new.mp4")
        shutil.move(str(work / "final.mp4"), str(spare))
        final = spare
        print(f"{OUT} is open in another program (a video player?), so the new video is {spare}. "
              f"Close the player and rename it to {OUT.name}.")
    (PREVIEW / "cut_list.json").write_text(json.dumps(
        [{"piece": i + 1, "new_start": round(s, 2), "seconds": round(d, 2), "label": lab, **CUTS[i]}
         for i, (s, d, lab) in enumerate(starts)], indent=1, default=list), "utf-8")
    contact_sheet(ff, starts, final)
    print(f"wrote {SRT} ({write_srt(starts)} cues)")
    print(f"wrote {final} ({t:.1f} s planned) and {PREVIEW / 'contact_sheet.png'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

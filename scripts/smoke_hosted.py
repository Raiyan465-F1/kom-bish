"""Smoke-test a running Kom Bish app through its public API.

  python scripts/smoke_hosted.py <base_url> --images <dir>

Calls /advise with: consent off; consent on and no photo; then each image in <dir> (consent on, no audio,
planning "no"). Prints the headline of each answer and the latency. Exits non-zero if any call errors.

Every answer the app gives is logged as a consultation. The script ends by printing the command that tags
those records as test traffic, so the public dashboard counters leave them out.
"""
from __future__ import annotations

import argparse
import datetime as dt
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from kombish import texts  # noqa: E402

IMG_EXT = {".jpg", ".jpeg", ".png", ".webp"}


def headline(answer) -> str:
    text = answer if isinstance(answer, str) else str(answer)
    return next((line.lstrip("# ").strip() for line in text.splitlines() if line.strip()), "(empty answer)")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("base_url")
    p.add_argument("--images", type=Path, help="folder of test photos")
    args = p.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # Bangla headlines on a Windows console

    from gradio_client import Client, handle_file

    images = sorted(q for q in args.images.iterdir() if q.suffix.lower() in IMG_EXT) if args.images else []
    t0 = time.perf_counter()
    client = Client(args.base_url, verbose=False, httpx_kwargs={"timeout": 90})   # Render can take ~1 min to wake
    print(f"connected to {args.base_url} in {time.perf_counter() - t0:.1f}s")

    # Inputs 5 and 7 are the two confirmation questions (blast lesion shape, BLB patches). Left unanswered, a
    # blast or BLB photo shows the question itself. Input 6 is the "Show English" toggle (off: Bangla only).
    cases = [("consent off", (False, handle_file(str(images[0])) if images else None, None, None, None, False, None)),
             ("no photo", (True, None, None, None, None, False, None))]
    cases += [(q.name, (True, handle_file(str(q)), None, texts.NO_BN, None, False, None)) for q in images]

    errors = 0
    started = dt.datetime.now(dt.timezone.utc)
    for name, inputs in cases:
        t0 = time.perf_counter()
        try:
            out = client.predict(*inputs, api_name="/advise")
            print(f"{(time.perf_counter() - t0) * 1000:>8.0f} ms  {name:<32} {headline(out[0])}")
        except Exception as e:
            errors += 1
            print(f"{(time.perf_counter() - t0) * 1000:>8.0f} ms  {name:<32} ERROR {type(e).__name__}: {e}")
    print(f"{len(cases) - errors} / {len(cases)} calls succeeded")
    ended = dt.datetime.now(dt.timezone.utc) + dt.timedelta(seconds=5)
    print("Tag these calls as test traffic (wait 5 minutes for the log to be saved, then restart the Space):\n"
          f"  python scripts/tag_test_records.py --from {started:%Y-%m-%dT%H:%M:%S} --to {ended:%Y-%m-%dT%H:%M:%S} "
          "--reason \"smoke test\"")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())

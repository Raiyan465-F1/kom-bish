"""Smoke-test a running Kom Bish app through its public API.

  python scripts/smoke_hosted.py <base_url> --images <dir>

Calls /advise with: consent off; consent on and no photo; then each image in <dir> (consent on, no audio,
planning "no"). Prints the headline of each answer and the latency. Exits non-zero if any call errors.
"""
from __future__ import annotations

import argparse
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

    from gradio_client import Client, handle_file

    images = sorted(q for q in args.images.iterdir() if q.suffix.lower() in IMG_EXT) if args.images else []
    t0 = time.perf_counter()
    client = Client(args.base_url, verbose=False, httpx_kwargs={"timeout": 90})   # Render can take ~1 min to wake
    print(f"connected to {args.base_url} in {time.perf_counter() - t0:.1f}s")

    cases = [("consent off", (False, handle_file(str(images[0])) if images else None, None, None)),
             ("no photo", (True, None, None, None))]
    cases += [(q.name, (True, handle_file(str(q)), None, texts.NO_BN)) for q in images]

    errors = 0
    for name, inputs in cases:
        t0 = time.perf_counter()
        try:
            out = client.predict(*inputs, api_name="/advise")
            print(f"{(time.perf_counter() - t0) * 1000:>8.0f} ms  {name:<32} {headline(out[0])}")
        except Exception as e:
            errors += 1
            print(f"{(time.perf_counter() - t0) * 1000:>8.0f} ms  {name:<32} ERROR {type(e).__name__}: {e}")
    print(f"{len(cases) - errors} / {len(cases)} calls succeeded")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())

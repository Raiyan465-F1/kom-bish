"""Upload model.onnx, labels.json and the model card to the public Hugging Face model repo.

  python scripts/publish_model.py

Asks for the repo ID and a write token. The token is typed at a hidden prompt: it is never read from a
file, never printed and never stored. best.pt is not uploaded (keep it as a private backup).
"""
from __future__ import annotations

import getpass
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODELS = ROOT / "models"
FILES = ["model.onnx", "labels.json", "README.md"]

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass


def main() -> int:
    missing = [f for f in FILES if not (MODELS / f).exists()]
    if missing:
        raise SystemExit(f"Missing in models/: {missing}. Run step 10, then python training/make_model_card.py.")
    card = (MODELS / "README.md").read_text("utf-8")
    if "SMOKE RUN" in card:
        raise SystemExit("models/README.md is from a smoke run. Regenerate it from the real Kaggle output.")
    labels = json.loads((MODELS / "labels.json").read_text("utf-8"))
    if not labels.get("temperature", 0) > 0:
        raise SystemExit("labels.json has no temperature. Use the file from the Kaggle run.")

    default = os.getenv("MODEL_REPO", "").strip()
    repo_id = input(f"Model repo ID [{default or '<hf-user>/kom-bish-rice-leaf'}]: ").strip() or default
    if not repo_id or "<" in repo_id:
        raise SystemExit("No repo ID given.")
    token = getpass.getpass("Hugging Face token with write access to that repo (hidden): ").strip()
    if not token:
        raise SystemExit("No token given.")

    from huggingface_hub import HfApi

    HfApi(token=token).upload_folder(repo_id=repo_id, repo_type="model", folder_path=str(MODELS),
                                     allow_patterns=FILES)
    print(f"Uploaded {', '.join(FILES)} to https://huggingface.co/{repo_id}")
    print(f"Now set MODEL_REPO={repo_id} in .env and as a GitHub Actions variable.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

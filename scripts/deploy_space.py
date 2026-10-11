"""Deploy Kom Bish to a Hugging Face ZeroGPU Gradio Space (the app itself runs ONNX on the CPU).

  python scripts/deploy_space.py [--space <user>/kom-bish] [--zerogpu-mode noop|wrap]

Reads the token from .env and never prints it. Uploads only the files the app needs (an allow-list, so .env,
models, datasets and training code never leave the machine), then sets the Space variables and the log secret.
GEMINI_API_KEY is not uploaded while VOICE_ENABLED is false: a secret the app does not use should not be there.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ALLOW = ["app.py", "requirements.txt", "README.md", "LICENSE", "kombish/*.py", "data/rules.csv", "data/clips.csv",
         "data/voice_cache.json", "audio/*.mp3", "audio/clips_manifest.json", "examples/*.jpg", "examples/CREDITS.md"]


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--space", help="default: <token owner>/kom-bish")
    p.add_argument("--zerogpu-mode", choices=["noop", "wrap"], default="noop")
    p.add_argument("--app-version", default="1.0.0-rc")
    p.add_argument("--settings-only", action="store_true", help="only set variables and secrets, upload nothing")
    args = p.parse_args(argv)

    from dotenv import dotenv_values
    from huggingface_hub import HfApi

    env = dotenv_values(ROOT / ".env")
    api = HfApi(token=env["HF_TOKEN"])
    space = args.space or f"{api.whoami()['name']}/kom-bish"

    if not args.settings_only:
        try:
            api.create_repo(space, repo_type="space", space_sdk="gradio", space_hardware="zero-a10g", private=False,
                            exist_ok=True)
        except Exception as e:
            print(f"REFUSED: Hugging Face would not create the ZeroGPU Space: {type(e).__name__}: {str(e)[:600]}")
            return 2
        api.upload_folder(repo_id=space, repo_type="space", folder_path=str(ROOT), allow_patterns=ALLOW,
                          commit_message="Deploy Kom Bish")
        print(f"uploaded the app files to {space}")

    voice_on = (env.get("VOICE_ENABLED") or "false").strip().lower() == "true"
    variables = {"MODEL_REPO": env.get("MODEL_REPO"), "LOG_REPO": env.get("LOG_REPO"),
                 "GEMINI_MODEL": env.get("GEMINI_MODEL") or "gemini-3.5-flash-lite",
                 "VOICE_ENABLED": "true" if voice_on else "false", "APP_VERSION": args.app_version,
                 "ZEROGPU_MODE": args.zerogpu_mode}
    for key, value in variables.items():
        if not value:
            raise SystemExit(f"{key} is empty in .env")
        api.add_space_variable(space, key, value)
    secrets = {"HF_TOKEN": env.get("HF_TOKEN")}
    if voice_on:
        secrets["GEMINI_API_KEY"] = env.get("GEMINI_API_KEY")
    for key, value in secrets.items():
        if not value:
            raise SystemExit(f"{key} is empty in .env")
        api.add_space_secret(space, key, value)
    print(f"variables set: {sorted(variables)} | secrets set (values not shown): {sorted(secrets)}")

    for _ in range(90):   # wait for the build, up to 15 minutes
        runtime = api.get_space_runtime(space)
        hardware = getattr(runtime, "hardware", None)
        print(f"stage: {runtime.stage} | hardware: {hardware}")
        if runtime.stage in ("RUNNING", "RUNTIME_ERROR", "BUILD_ERROR", "CONFIG_ERROR", "PAUSED", "NO_APP_FILE"):
            break
        time.sleep(10)
    owner, name = space.split("/")
    print(f"Space page: https://huggingface.co/spaces/{space}")
    print(f"Direct app URL: https://{owner.lower()}-{name.lower().replace('_', '-')}.hf.space")
    return 0 if runtime.stage == "RUNNING" else 1


if __name__ == "__main__":
    sys.exit(main())

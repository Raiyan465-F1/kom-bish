"""Tag the team's own test traffic in the consultation log, so the public dashboard counters leave it out.

  python scripts/tag_test_records.py --list
  python scripts/tag_test_records.py --from 2026-10-12T05:25:00 --to 2026-10-12T05:27:00 --reason "smoke test"
  python scripts/tag_test_records.py --ids <id> <id> --reason "phone test"
  python scripts/tag_test_records.py --restart <user>/kom-bish      # the counters are rebuilt when the app starts

Times are UTC, both ends included. Nothing is deleted or changed in the log: the tags are a separate file,
tags/test_records.json, in the private log dataset ({"<record id>": "<reason>"}). The app reads it at startup
(kombish/logging_store.py), so restart the Space after tagging. Only anonymous log fields are printed.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from kombish.logging_store import TEST_TAGS  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--list", action="store_true", help="print every consultation and whether it is tagged")
    p.add_argument("--from", dest="start", help="UTC time, e.g. 2026-10-12T05:25:00")
    p.add_argument("--to", dest="end", help="UTC time, e.g. 2026-10-12T05:27:00")
    p.add_argument("--ids", nargs="*", default=[], help="record ids (or unique prefixes) to tag")
    p.add_argument("--reason", help="why these records are test traffic (stored with the tag)")
    p.add_argument("--restart", metavar="SPACE_ID", help="restart this Space so its counters are rebuilt")
    args = p.parse_args(argv)

    from dotenv import dotenv_values
    from huggingface_hub import HfApi, snapshot_download

    env = dotenv_values(ROOT / ".env")
    repo, token = env["LOG_REPO"], env["HF_TOKEN"]
    api = HfApi(token=token)
    local = Path(snapshot_download(repo_id=repo, repo_type="dataset", token=token,
                                   allow_patterns=["data/*.jsonl", TEST_TAGS]))
    records = []
    for path in sorted((local / "data").glob("*.jsonl")):
        for line in path.read_text("utf-8").splitlines():
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if rec.get("type") == "consultation":
                records.append(rec)
    records.sort(key=lambda r: r["ts_utc"])
    tags_path = local / TEST_TAGS
    tags: dict[str, str] = json.loads(tags_path.read_text("utf-8")) if tags_path.exists() else {}

    chosen = []
    if args.start or args.end or args.ids:
        if not args.reason:
            raise SystemExit("--reason is required when tagging")
        for rec in records:
            in_window = bool(args.start or args.end) and (args.start or "") <= rec["ts_utc"][:19] <= (args.end or "9999")
            by_id = any(rec["id"].startswith(prefix) for prefix in args.ids)
            if (in_window or by_id) and rec["id"] not in tags:
                chosen.append(rec)
        for rec in chosen:
            tags[rec["id"]] = args.reason
        if chosen:
            api.upload_file(path_or_fileobj=json.dumps(tags, indent=1, ensure_ascii=False).encode("utf-8"),
                            path_in_repo=TEST_TAGS, repo_id=repo, repo_type="dataset",
                            commit_message=f"Tag {len(chosen)} test records: {args.reason}")
        print(f"tagged {len(chosen)} more records as test traffic ({args.reason})")

    def counted(rec: dict) -> bool:
        return rec.get("app_version") != "test" and rec["id"] not in tags

    if args.list:
        for rec in records:
            state = "counted" if counted(rec) else tags.get(rec["id"], "check-script record (app_version test)")
            print(f"{rec['ts_utc'][:19]}  {rec['id'][:8]}  {rec.get('app_version'):<9} {rec.get('rule_id'):<21} {state}")
    print(f"consultations in the log: {len(records)} | tagged as test traffic: {sum(r['id'] in tags for r in records)} | "
          f"check-script records: {sum(r.get('app_version') == 'test' for r in records)} | "
          f"counted on the dashboard after a restart: {sum(counted(r) for r in records)}")
    if args.restart:
        api.restart_space(args.restart)
        print(f"restarted {args.restart}; the counters are rebuilt when it is running again")
    return 0


if __name__ == "__main__":
    sys.exit(main())

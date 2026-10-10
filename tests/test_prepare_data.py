import csv
import json
import sys
from pathlib import Path

import pytest

pytest.importorskip("sklearn")   # training venv only; CI without sklearn skips this file
from PIL import Image  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "training"))
import make_synthetic_data  # noqa: E402
import prepare_data  # noqa: E402

PER_CLASS = 12
N_IMAGES = PER_CLASS * 9


@pytest.fixture(scope="module")
def raw(tmp_path_factory):
    base = tmp_path_factory.mktemp("synthetic")
    mapping = make_synthetic_data.make(base, per_class=PER_CLASS)
    return base / "raw", mapping


@pytest.fixture(scope="module")
def prepared(raw, tmp_path_factory):
    root, mapping = raw
    out = tmp_path_factory.mktemp("prepared")
    code = prepare_data.main(["--root", str(root), "--out", str(out),
                              "--mapping-json", str(mapping), "--accept-count-mismatch"])
    assert code == 0
    return out


def test_all_target_folders_exist_in_each_split(prepared):
    for split in prepare_data.SPLITS:
        folders = sorted(d.name for d in (prepared / split).iterdir() if d.is_dir())
        assert folders == list(prepare_data.TARGETS)


def test_no_file_in_two_splits_and_manifest_is_complete(prepared):
    with (prepared / "manifest.csv").open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == N_IMAGES
    assert len({r["orig_path"] for r in rows}) == N_IMAGES
    names = [Path(r["path"]).name for r in rows]
    assert len(set(names)) == len(names)
    on_disk = [p for split in prepare_data.SPLITS for p in (prepared / split).rglob("*.jpg")]
    assert len(on_disk) == N_IMAGES
    assert {r["split"] for r in rows} == set(prepare_data.SPLITS)
    for r in rows:
        assert (prepared / r["path"]).is_file()
        assert r["target"] == prepare_data.SOURCE_CLASS_TO_TARGET[(r["source"], r["source_class"])]
        assert Path(r["path"]).name.startswith(f"{r['source']}__")


def test_long_side_at_most_512(prepared):
    for p in prepared.rglob("*.jpg"):
        with Image.open(p) as im:
            assert max(im.size) <= prepare_data.LONG_SIDE, p


def test_count_mismatch_exits_without_flag(raw, tmp_path):
    root, mapping = raw
    with pytest.raises(SystemExit) as e:
        prepare_data.main(["--root", str(root), "--out", str(tmp_path / "out"), "--mapping-json", str(mapping)])
    assert "Counts differ" in str(e.value)
    assert not (tmp_path / "out").exists()


def test_empty_mapping_exits(raw, tmp_path):
    root, _ = raw
    empty = tmp_path / "empty.json"
    empty.write_text(json.dumps({}), "utf-8")
    with pytest.raises(SystemExit) as e:
        prepare_data.main(["--root", str(root), "--out", str(tmp_path / "out"), "--mapping-json", str(empty)])
    assert "Mapping is empty" in str(e.value)


def test_split_is_seeded(raw, tmp_path):
    root, mapping = raw
    manifests = []
    for name in ("a", "b"):
        out = tmp_path / name
        prepare_data.main(["--root", str(root), "--out", str(out),
                           "--mapping-json", str(mapping), "--accept-count-mismatch"])
        manifests.append((out / "manifest.csv").read_text("utf-8"))
    assert manifests[0] == manifests[1]

import io
import os
import statistics
import sys
import time

import numpy as np
import pytest
from PIL import Image

from kombish import classifier

if not os.getenv("MODEL_REPO", "").strip() and not (classifier.LOCAL_MODEL_DIR / "model.onnx").exists():
    pytest.skip("No model: set MODEL_REPO or put model.onnx and labels.json in models/ (steps 10-11).",
                allow_module_level=True)

CLASSES = ["bacterial_leaf_blight", "blast", "healthy", "other"]


def noise(w: int, h: int, seed: int = 0) -> Image.Image:
    rng = np.random.default_rng(seed)
    return Image.fromarray(rng.integers(0, 256, size=(h, w, 3), dtype=np.uint8))


def test_no_torch():
    import kombish.classifier  # noqa: F401
    assert "torch" not in sys.modules


@pytest.mark.parametrize("size", [(400, 300), (3000, 4000), (4160, 1952)])
def test_preprocess_shapes(size):
    x = classifier.preprocess(noise(*size), classifier.meta())
    assert x.shape == (1, 3, 224, 224)
    assert x.dtype == np.float32


def test_exif_rotation():
    base = Image.linear_gradient("L").resize((400, 300)).convert("RGB")   # not symmetric under rotation
    exif = Image.Exif()
    exif[0x0112] = 6   # Orientation: rotate 90 degrees clockwise to display
    buf = io.BytesIO()
    base.save(buf, "JPEG", quality=95, exif=exif)
    tagged = Image.open(io.BytesIO(buf.getvalue()))
    assert tagged.getexif()[0x0112] == 6
    pixels = Image.fromarray(np.asarray(Image.open(io.BytesIO(buf.getvalue()))))   # decoded pixels, no EXIF
    rotated = pixels.transpose(Image.Transpose.ROTATE_270)   # the same pixels, rotated by hand
    m = classifier.meta()
    np.testing.assert_array_equal(classifier.preprocess(tagged, m), classifier.preprocess(rotated, m))
    assert not np.array_equal(classifier.preprocess(tagged, m), classifier.preprocess(base, m))


def test_predict_contract():
    m = classifier.meta()
    assert m["classes"] == CLASSES
    p = classifier.predict(noise(640, 480, seed=1))
    assert p.label in CLASSES
    assert set(p.probs) == set(CLASSES)
    assert abs(sum(p.probs.values()) - 1.0) <= 1e-3
    assert 0.0 <= p.margin <= p.conf <= 1.0
    assert p.abstained == (p.conf < m["threshold"] or p.margin < m["margin"])


def test_latency(capsys):
    img = noise(1024, 768, seed=2)
    classifier.predict(img)   # first call loads the session
    times = []
    for _ in range(20):
        t0 = time.perf_counter()
        classifier.predict(img)
        times.append((time.perf_counter() - t0) * 1000)
    with capsys.disabled():
        print(f"\n[latency] median predict() on 1024x768: {statistics.median(times):.1f} ms (n=20)")

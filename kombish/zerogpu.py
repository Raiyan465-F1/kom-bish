"""ZeroGPU shim.

ZeroGPU Spaces need at least one @spaces.GPU function at startup. The decorator has no
effect outside ZeroGPU. Kom Bish runs ONNX on CPU and never imports torch.

ZEROGPU_MODE=noop (default): define a decorated function that is never called (variant A).
ZEROGPU_MODE=wrap: also wrap the classifier call in @spaces.GPU(duration=10) (variant B).
Variant B spends each visitor's daily ZeroGPU quota (2 min anonymous, 5 min free account).
"""
import os

try:
    import spaces  # installed from requirements.txt on the HF Space only
except ImportError:  # Render, laptop, CI
    spaces = None


def _mode() -> str:
    return os.getenv("ZEROGPU_MODE", "noop").strip().lower()


if spaces is not None:
    @spaces.GPU(duration=10)
    def _zerogpu_startup_probe():  # variant A: never called
        return None


def maybe_gpu(fn):
    """Return fn unchanged, or wrapped in spaces.GPU(duration=10) when ZEROGPU_MODE=wrap."""
    if spaces is not None and _mode() == "wrap":
        return spaces.GPU(duration=10)(fn)
    return fn

import pytest

from kombish import zerogpu


@pytest.mark.parametrize("mode", ["noop", "wrap"])
def test_maybe_gpu_is_identity_without_spaces(monkeypatch, mode):
    monkeypatch.setattr(zerogpu, "spaces", None)  # Render, laptop, CI: spaces is not installed
    monkeypatch.setenv("ZEROGPU_MODE", mode)

    def f(x):
        return x

    assert zerogpu.maybe_gpu(f) is f


def test_mode_defaults_to_noop(monkeypatch):
    monkeypatch.delenv("ZEROGPU_MODE", raising=False)
    assert zerogpu._mode() == "noop"

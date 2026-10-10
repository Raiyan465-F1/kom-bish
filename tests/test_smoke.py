import gradio as gr


def test_app_builds_without_network():
    import app
    assert isinstance(app.build_demo(), gr.Blocks)


def test_no_torch_in_app():
    import sys
    import app  # noqa: F401
    assert "torch" not in sys.modules

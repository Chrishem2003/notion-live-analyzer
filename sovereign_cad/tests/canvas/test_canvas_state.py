from sovereign_cad.core.geometry import Point2
from sovereign_cad.ui.canvas import CanvasState


def close(a, b, eps=1e-9):
    return abs(a - b) < eps


def test_canvas_initializes():
    canvas = CanvasState()

    assert canvas.viewport is not None
    assert canvas.is_panning is False


def test_cursor_conversion():
    canvas = CanvasState()

    center = canvas.viewport.screen_center()

    world = canvas.update_cursor(center)

    assert close(world.x, 0.0)
    assert close(world.y, 0.0)


def test_pan_lifecycle():
    canvas = CanvasState()

    canvas.begin_pan(
        Point2(100.0, 100.0)
    )

    assert canvas.is_panning is True

    canvas.update_pan(
        Point2(120.0, 100.0)
    )

    canvas.end_pan()

    assert canvas.is_panning is False
    assert canvas.last_pan_screen is None


def test_reset_view():
    canvas = CanvasState()

    canvas.viewport.set_zoom(4.0)

    canvas.reset_view()

    assert close(
        canvas.viewport.zoom,
        1.0
    )
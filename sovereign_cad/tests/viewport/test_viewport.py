from sovereign_cad.core.geometry import Point2, Vector2
from sovereign_cad.ui.viewport import Viewport, Viewport2D


def close(a, b, eps=1e-9):
    return abs(a - b) < eps


def test_viewport_exports():
    assert Viewport is Viewport2D


def test_default_viewport():
    viewport = Viewport()

    assert viewport.width == 1200.0
    assert viewport.height == 800.0
    assert viewport.zoom == 1.0


def test_world_to_screen_origin():
    viewport = Viewport(
        width=1000.0,
        height=800.0,
    )

    screen = viewport.world_to_screen(
        Point2(0.0, 0.0)
    )

    assert close(screen.x, 500.0)
    assert close(screen.y, 400.0)


def test_screen_to_world_origin():
    viewport = Viewport(
        width=1000.0,
        height=800.0,
    )

    world = viewport.screen_to_world(
        Point2(500.0, 400.0)
    )

    assert close(world.x, 0.0)
    assert close(world.y, 0.0)


def test_round_trip():
    viewport = Viewport()

    original = Point2(
        125.5,
        -72.25,
    )

    screen = viewport.world_to_screen(
        original
    )

    result = viewport.screen_to_world(
        screen
    )

    assert close(result.x, original.x)
    assert close(result.y, original.y)


def test_zoom():
    viewport = Viewport()

    viewport.zoom_by(2.0)

    assert viewport.zoom == 2.0

    viewport.zoom_by(0.5)

    assert viewport.zoom == 1.0


def test_pan_world():
    viewport = Viewport()

    viewport.pan_world(
        Vector2(10.0, 20.0)
    )

    assert close(viewport.center.x, 10.0)
    assert close(viewport.center.y, 20.0)


def test_reset():
    viewport = Viewport()

    viewport.pan_world(
        Vector2(10.0, 20.0)
    )

    viewport.zoom_by(4.0)

    viewport.reset()

    assert close(viewport.center.x, 0.0)
    assert close(viewport.center.y, 0.0)
    assert close(viewport.zoom, 1.0)
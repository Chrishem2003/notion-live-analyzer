from sovereign_cad.core.geometry import Point2
from sovereign_cad.ui.viewport import Viewport
from sovereign_cad.rendering import (
    Renderer,
    Renderer2D,
    RenderCommand,
)


def test_renderer_exports():
    assert Renderer is Renderer2D


def test_renderer_initializes():
    viewport = Viewport()

    renderer = Renderer2D(viewport)

    assert renderer.viewport is viewport


def test_render_command():
    command = RenderCommand(
        operation="test"
    )

    assert command.operation == "test"
    assert isinstance(command.data, dict)


def test_grid_rendering():
    viewport = Viewport()

    renderer = Renderer2D(viewport)

    commands = renderer.render_grid(
        spacing=100.0,
        extent=100.0,
    )

    assert len(commands) > 0

    for command in commands:
        assert command.operation == "grid_line"


def test_coordinate_conversion_for_renderer():
    viewport = Viewport(
        width=1000.0,
        height=800.0,
    )

    renderer = Renderer2D(viewport)

    assert renderer.viewport.world_to_screen(
        Point2(0.0, 0.0)
    ).x == 500.0
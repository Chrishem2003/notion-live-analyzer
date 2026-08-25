from __future__ import annotations

from dataclasses import dataclass, field

from sovereign_cad.core.geometry import (
    Point2,
    Vector2,
)

from sovereign_cad.core.entities import (
    EntityRegistry,
)

from sovereign_cad.ui.viewport import (
    Viewport,
)


@dataclass
class CanvasState:
    """
    Runtime state for a 2D SovereignCAD canvas.
    """

    viewport: Viewport = field(
        default_factory=Viewport
    )

    registry: EntityRegistry | None = None

    cursor_screen: Point2 = field(
        default_factory=lambda: Point2(
            0.0,
            0.0,
        )
    )

    cursor_world: Point2 = field(
        default_factory=lambda: Point2(
            0.0,
            0.0,
        )
    )

    is_panning: bool = False

    last_pan_screen: Point2 | None = None

    def update_cursor(
        self,
        screen_point: Point2,
    ) -> Point2:

        self.cursor_screen = screen_point

        self.cursor_world = (
            self.viewport.screen_to_world(
                screen_point
            )
        )

        return self.cursor_world

    def begin_pan(
        self,
        screen_point: Point2,
    ) -> None:

        self.is_panning = True
        self.last_pan_screen = screen_point

    def update_pan(
        self,
        screen_point: Point2,
    ) -> None:

        if not self.is_panning:
            return

        if self.last_pan_screen is None:
            self.last_pan_screen = screen_point
            return

        delta = Vector2(
            screen_point.x
            - self.last_pan_screen.x,

            screen_point.y
            - self.last_pan_screen.y,
        )

        self.viewport.pan(delta)

        self.last_pan_screen = screen_point

        self.update_cursor(
            screen_point
        )

    def end_pan(self) -> None:
        self.is_panning = False
        self.last_pan_screen = None

    def zoom_in(
        self,
        factor: float = 1.2,
    ) -> None:

        self.viewport.zoom_by(factor)

        self.update_cursor(
            self.cursor_screen
        )

    def zoom_out(
        self,
        factor: float = 1.2,
    ) -> None:

        if factor <= 0:
            raise ValueError(
                "Zoom factor must be positive."
            )

        self.viewport.zoom_by(
            1.0 / factor
        )

        self.update_cursor(
            self.cursor_screen
        )

    def reset_view(self) -> None:

        self.viewport.reset()

        self.update_cursor(
            self.cursor_screen
        )
from __future__ import annotations

from dataclasses import dataclass, field

from sovereign_cad.core.geometry import Point2, Vector2


@dataclass
class Viewport:
    """
    SovereignCAD 2D world/screen viewport.

    World coordinates:
        X increases to the right.
        Y increases upward.

    Screen coordinates:
        X increases to the right.
        Y increases downward.
    """

    width: float = 1200.0
    height: float = 800.0

    center: Point2 = field(
        default_factory=lambda: Point2(0.0, 0.0)
    )

    zoom: float = 1.0

    min_zoom: float = 0.0001
    max_zoom: float = 1000000.0

    def __post_init__(self):
        if self.width <= 0:
            raise ValueError("Viewport width must be positive.")

        if self.height <= 0:
            raise ValueError("Viewport height must be positive.")

        if self.zoom <= 0:
            raise ValueError("Viewport zoom must be positive.")

        self.zoom = self._clamp_zoom(self.zoom)

    def _clamp_zoom(self, value: float) -> float:
        return max(
            self.min_zoom,
            min(self.max_zoom, value),
        )

    def world_to_screen(self, point: Point2) -> Point2:
        return Point2(
            (point.x - self.center.x)
            * self.zoom
            + self.width / 2.0,

            self.height / 2.0
            - (point.y - self.center.y)
            * self.zoom,
        )

    def screen_to_world(self, point: Point2) -> Point2:
        return Point2(
            (point.x - self.width / 2.0)
            / self.zoom
            + self.center.x,

            (self.height / 2.0 - point.y)
            / self.zoom
            + self.center.y,
        )

    def world_vector_to_screen(self, vector: Vector2) -> Vector2:
        return Vector2(
            vector.x * self.zoom,
            -vector.y * self.zoom,
        )

    def screen_vector_to_world(self, vector: Vector2) -> Vector2:
        return Vector2(
            vector.x / self.zoom,
            -vector.y / self.zoom,
        )

    def pan(self, delta_screen: Vector2) -> None:
        delta_world = self.screen_vector_to_world(delta_screen)

        self.center = Point2(
            self.center.x - delta_world.x,
            self.center.y - delta_world.y,
        )

    def pan_world(self, delta_world: Vector2) -> None:
        self.center = Point2(
            self.center.x + delta_world.x,
            self.center.y + delta_world.y,
        )

    def zoom_by(self, factor: float) -> None:
        if factor <= 0:
            raise ValueError("Zoom factor must be positive.")

        self.zoom = self._clamp_zoom(
            self.zoom * factor
        )

    def set_zoom(self, zoom: float) -> None:
        if zoom <= 0:
            raise ValueError("Zoom must be positive.")

        self.zoom = self._clamp_zoom(zoom)

    def reset(self) -> None:
        self.center = Point2(0.0, 0.0)
        self.zoom = 1.0

    def screen_center(self) -> Point2:
        return Point2(
            self.width / 2.0,
            self.height / 2.0,
        )


# Compatibility name used by earlier Stage 5 code.
Viewport2D = Viewport
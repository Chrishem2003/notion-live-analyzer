﻿from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

from ..geometry import Point2, Vector2


@dataclass
class Viewport:
    """
    2D CAD viewport.

    world_to_screen:
        Converts model/world coordinates into screen coordinates.

    screen_to_world:
        Converts screen coordinates back into model/world coordinates.

    The viewport uses:
        origin = screen position of world origin
        scale  = pixels per world unit
    """

    width: float = 1200.0
    height: float = 800.0

    origin_x: float = 600.0
    origin_y: float = 400.0

    scale: float = 1.0

    min_scale: float = 1e-6
    max_scale: float = 1e9

    def __post_init__(self) -> None:
        self._validate()

    def _validate(self) -> None:

        values = (
            self.width,
            self.height,
            self.origin_x,
            self.origin_y,
            self.scale,
        )

        if not all(isfinite(value) for value in values):
            raise ValueError("Viewport values must be finite.")

        if self.width <= 0:
            raise ValueError("Viewport width must be positive.")

        if self.height <= 0:
            raise ValueError("Viewport height must be positive.")

        if self.scale <= 0:
            raise ValueError("Viewport scale must be positive.")

    def resize(
        self,
        width: float,
        height: float,
    ) -> None:

        if width <= 0 or height <= 0:
            raise ValueError(
                "Viewport dimensions must be positive."
            )

        self.width = float(width)
        self.height = float(height)

    def set_scale(
        self,
        scale: float,
    ) -> None:

        if scale <= 0:
            raise ValueError(
                "Viewport scale must be positive."
            )

        self.scale = max(
            self.min_scale,
            min(self.max_scale, float(scale)),
        )

    def zoom(
        self,
        factor: float,
        center: Point2 | None = None,
    ) -> None:

        if factor <= 0:
            raise ValueError(
                "Zoom factor must be positive."
            )

        if center is None:
            center = Point2(
                self.width / 2.0,
                self.height / 2.0,
            )

        world_before = self.screen_to_world(center)

        self.set_scale(
            self.scale * factor
        )

        world_after = self.screen_to_world(center)

        self.origin_x += (
            (world_after.x - world_before.x)
            * self.scale
        )

        self.origin_y += (
            (world_after.y - world_before.y)
            * self.scale
        )

    def pan(
        self,
        delta: Vector2,
    ) -> None:

        self.origin_x += delta.x
        self.origin_y += delta.y

    def world_to_screen(
        self,
        point: Point2,
    ) -> Point2:

        return Point2(
            self.origin_x + point.x * self.scale,
            self.origin_y - point.y * self.scale,
        )

    def screen_to_world(
        self,
        point: Point2,
    ) -> Point2:

        return Point2(
            (point.x - self.origin_x) / self.scale,
            (self.origin_y - point.y) / self.scale,
        )

    def world_vector_to_screen(
        self,
        vector: Vector2,
    ) -> Vector2:

        return Vector2(
            vector.x * self.scale,
            -vector.y * self.scale,
        )

    def screen_vector_to_world(
        self,
        vector: Vector2,
    ) -> Vector2:

        return Vector2(
            vector.x / self.scale,
            -vector.y / self.scale,
        )

    def center_world(self) -> Point2:

        return self.screen_to_world(
            Point2(
                self.width / 2.0,
                self.height / 2.0,
            )
        )

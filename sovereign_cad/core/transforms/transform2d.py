﻿from __future__ import annotations

from dataclasses import dataclass
from math import cos, sin

from ..geometry import Point2, Vector2


@dataclass(frozen=True, slots=True)
class Transform2D:
    """
    2D affine transformation.

    x' = a*x + c*y + tx
    y' = b*x + d*y + ty
    """

    a: float = 1.0
    b: float = 0.0
    c: float = 0.0
    d: float = 1.0
    tx: float = 0.0
    ty: float = 0.0

    @classmethod
    def identity(cls) -> Transform2D:
        return cls()

    @classmethod
    def translation(
        cls,
        x: float,
        y: float,
    ) -> Transform2D:

        return cls(
            tx=x,
            ty=y,
        )

    @classmethod
    def rotation(
        cls,
        angle: float,
    ) -> Transform2D:

        c = cos(angle)
        s = sin(angle)

        return cls(
            a=c,
            b=s,
            c=-s,
            d=c,
        )

    @classmethod
    def scaling(
        cls,
        x: float,
        y: float | None = None,
    ) -> Transform2D:

        if y is None:
            y = x

        return cls(
            a=x,
            d=y,
        )

    def apply_point(
        self,
        point: Point2,
    ) -> Point2:

        return Point2(
            self.a * point.x
            + self.c * point.y
            + self.tx,

            self.b * point.x
            + self.d * point.y
            + self.ty,
        )

    def apply_vector(
        self,
        vector: Vector2,
    ) -> Vector2:

        return Vector2(
            self.a * vector.x
            + self.c * vector.y,

            self.b * vector.x
            + self.d * vector.y,
        )

    def then(
        self,
        other: Transform2D,
    ) -> Transform2D:

        """
        Apply this transform first,
        then the other transform.
        """

        return Transform2D(
            a=other.a * self.a + other.c * self.b,
            b=other.b * self.a + other.d * self.b,
            c=other.a * self.c + other.c * self.d,
            d=other.b * self.c + other.d * self.d,

            tx=(
                other.a * self.tx
                + other.c * self.ty
                + other.tx
            ),

            ty=(
                other.b * self.tx
                + other.d * self.ty
                + other.ty
            ),
        )

    def __matmul__(
        self,
        other: Transform2D,
    ) -> Transform2D:

        return self.then(other)

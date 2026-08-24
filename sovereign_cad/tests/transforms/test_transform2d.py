from math import pi

from sovereign_cad.core.geometry import Point2, Vector2
from sovereign_cad.core.transforms import Transform2D


def test_identity():

    transform = Transform2D.identity()

    result = transform.apply_point(
        Point2(3, 4)
    )

    assert result.almost_equal(
        Point2(3, 4)
    )


def test_translation():

    transform = Transform2D.translation(
        10,
        20,
    )

    result = transform.apply_point(
        Point2(1, 2)
    )

    assert result.almost_equal(
        Point2(11, 22)
    )


def test_rotation():

    transform = Transform2D.rotation(
        pi / 2
    )

    result = transform.apply_point(
        Point2(1, 0)
    )

    assert result.almost_equal(
        Point2(0, 1)
    )


def test_scaling():

    transform = Transform2D.scaling(
        2,
        3,
    )

    result = transform.apply_point(
        Point2(4, 5)
    )

    assert result.almost_equal(
        Point2(8, 15)
    )


def test_vector_ignores_translation():

    transform = Transform2D.translation(
        100,
        100,
    )

    result = transform.apply_vector(
        Vector2(2, 3)
    )

    assert result == Vector2(
        2,
        3,
    )


def test_composition():

    scale = Transform2D.scaling(2)

    move = Transform2D.translation(
        10,
        0,
    )

    combined = scale.then(move)

    result = combined.apply_point(
        Point2(1, 0)
    )

    assert result.almost_equal(
        Point2(12, 0)
    )

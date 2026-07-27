"""Guard against `#RRGGBBAA` colours reaching plotly.

Browsers accept 8-digit hex, plotly does not: it raises at render time, which in
Streamlit means a red traceback instead of a chart. The audit burstiness gauge
shipped with `#e74c3c22` and crashed every "Run Full Audit", so this test keeps
translucent plotly colours in `rgba()` form.
"""
import ast
import re
from pathlib import Path

import plotly.graph_objects as go
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
EIGHT_DIGIT_HEX = re.compile(r"^#[0-9a-fA-F]{8}$")

PLOTLY_MODULES = sorted(
    path
    for path in (REPO_ROOT / "modules").glob("*.py")
    if "plotly" in path.read_text(encoding="utf-8")
)


def _color_literals(path: Path):
    """Every string assigned to a ``color``-ish key in the module."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Dict):
            continue
        for key, value in zip(node.keys, node.values):
            if (
                isinstance(key, ast.Constant)
                and isinstance(key.value, str)
                and key.value in ("color", "bgcolor", "bordercolor", "line_color")
                and isinstance(value, ast.Constant)
                and isinstance(value.value, str)
            ):
                yield node.lineno, key.value, value.value


@pytest.mark.parametrize("path", PLOTLY_MODULES, ids=lambda path: path.name)
def test_no_eight_digit_hex_colors(path):
    offenders = [
        f"{path.name}:{line} {key}={color}"
        for line, key, color in _color_literals(path)
        if EIGHT_DIGIT_HEX.match(color)
    ]
    assert not offenders, "plotly rejects #RRGGBBAA — use rgba(): " + ", ".join(offenders)


def test_plotly_accepts_the_burstiness_gauge_colors():
    """The exact gauge that used to crash now builds."""
    figure = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=3.5,
            gauge={
                "axis": {"range": [0, 10]},
                "bar": {"color": "#1d4ed8"},
                "steps": [
                    {"range": [0, 2], "color": "rgba(231, 76, 60, 0.13)"},
                    {"range": [2, 5], "color": "rgba(46, 204, 113, 0.13)"},
                    {"range": [5, 10], "color": "rgba(243, 156, 18, 0.13)"},
                ],
            },
        )
    )
    assert figure.data[0].gauge.steps[0].color == "rgba(231, 76, 60, 0.13)"


def test_plotly_still_rejects_eight_digit_hex():
    """If plotly ever accepts it, this guard can be retired."""
    with pytest.raises(ValueError):
        go.Figure(
            go.Indicator(
                mode="gauge",
                value=1,
                gauge={"steps": [{"range": [0, 2], "color": "#e74c3c22"}]},
            )
        )

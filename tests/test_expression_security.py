"""Regression tests for the research data transformation expression guard."""
from __future__ import annotations

import importlib
import sys
import types

import pytest

# The validator itself is independent of dataframe execution. Stub heavyweight
# UI/data imports so this security-only test can run in the minimal CI job.
for _name in ("numpy", "pandas", "streamlit"):
    if _name not in sys.modules:
        sys.modules[_name] = types.ModuleType(_name)

if not hasattr(sys.modules["pandas"], "DataFrame"):
    sys.modules["pandas"].DataFrame = object

transformer = importlib.import_module("modules.data_transformer")


@pytest.mark.parametrize(
    "expression",
    [
        "age >= 18",
        "income * 1.1",
        "important_variable + 1",
        "IMPORTANCE_SCORE / 2",
    ],
)
def test_validator_allows_normal_expressions_and_identifiers(expression):
    transformer.validate_expression(expression)


@pytest.mark.parametrize(
    "expression",
    [
        "value.__class__",
        "__import__('os')",
        "lambda x: x",
        "value @ local_object",
    ],
)
def test_validator_rejects_forbidden_expression_constructs(expression):
    with pytest.raises(ValueError):
        transformer.validate_expression(expression)

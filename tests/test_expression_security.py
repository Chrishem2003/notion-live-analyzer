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
        "sqrt(measurement)",
        "round(result, 2)",
        "ifelse(age >= 18, adult, minor)",
    ],
)
def test_validator_allows_normal_expressions_and_approved_functions(expression):
    transformer.validate_expression(expression)


@pytest.mark.parametrize(
    "expression",
    [
        "value.__class__",
        "__import__('os')",
        "lambda x: x",
        "(lambda x: x)(value)",
        "value @ local_object",
        "open('secret.txt')",
        "value[0]",
        "[x for x in values]",
    ],
)
def test_validator_rejects_unsafe_expression_constructs(expression):
    with pytest.raises(ValueError):
        transformer.validate_expression(expression)


def test_validator_rejects_empty_expression():
    with pytest.raises(ValueError):
        transformer.validate_expression("   ")

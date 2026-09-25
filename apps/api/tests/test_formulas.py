from decimal import Decimal

import pytest

from frotad.services.formulas import evaluate, validate


def test_arithmetic_and_null():
    subtract = {"op": "subtract", "left": {"ref": "km_fim"}, "right": {"ref": "km_inicio"}}
    assert evaluate(
        subtract, {"km_fim": Decimal(125), "km_inicio": Decimal(100)}.get, None
    ) == Decimal(25)
    divide = {
        "op": "divide",
        "left": {"const": "1"},
        "right": {"const": "3"},
        "zero_behavior": "null",
    }
    assert evaluate(divide, None, None) == Decimal("0.3333")
    divide["right"] = {"const": "0"}
    assert evaluate(divide, None, None) is None
    assert evaluate(subtract, lambda _: None, None) is None


@pytest.mark.parametrize(
    "expression",
    [
        "__import__('os').system('bad')",
        {"op": "eval", "code": "1+1"},
        {"ref": "x.__class__"},
        {"const": float("inf")},
        {"const": "NaN"},
        {"const": True},
        {"op": "divide", "left": {"const": 1}, "right": {"const": 0}, "zero_behavior": "zero"},
        {"op": "count_children", "form_code": "FORM02", "sql": "DROP TABLE x"},
    ],
)
def test_rejects_executable_or_unknown_syntax(expression):
    with pytest.raises(ValueError):
        validate(expression)


def test_bounded_depth_and_overflow():
    expression = {"const": 1}
    for _ in range(14):
        expression = {"op": "subtract", "left": expression, "right": {"const": 1}}
    with pytest.raises(ValueError):
        validate(expression)
    with pytest.raises(ValueError):
        evaluate(
            {"op": "multiply", "left": {"const": "99999999999999"}, "right": {"const": "2"}},
            None,
            None,
        )

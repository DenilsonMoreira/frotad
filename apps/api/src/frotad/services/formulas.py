"""Bounded numeric expression tree; no executable source is accepted."""

import re
from decimal import ROUND_HALF_UP, Decimal, DecimalException, localcontext

KEY = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,79}$")
BINARY = {"add", "subtract", "multiply", "divide"}
LIMIT = Decimal("100000000000000")


def number(value):
    if type(value) not in (str, int, Decimal) or len(str(value)) > 100:
        raise ValueError("invalid numeric value")
    result = Decimal(value)
    if not result.is_finite() or abs(result) >= LIMIT:
        raise ValueError("numeric value out of range")
    return result


def validate(expression):
    nodes = 0
    refs, aggregates = set(), []

    def visit(node, depth):
        nonlocal nodes
        nodes += 1
        if nodes > 128 or depth > 12 or not isinstance(node, dict):
            raise ValueError("formula too complex")
        if set(node) == {"ref"}:
            if not isinstance(node["ref"], str) or not KEY.fullmatch(node["ref"]):
                raise ValueError("invalid reference")
            refs.add(node["ref"])
            return
        if set(node) == {"const"}:
            try:
                number(node["const"])
            except DecimalException:
                raise ValueError("invalid constant") from None
            return
        op = node.get("op")
        if not isinstance(op, str):
            raise ValueError("invalid operation")
        if op in BINARY:
            expected = {"op", "left", "right"} | ({"zero_behavior"} if op == "divide" else set())
            if set(node) != expected or (op == "divide" and node["zero_behavior"] != "null"):
                raise ValueError("invalid arithmetic configuration")
            visit(node["left"], depth + 1)
            visit(node["right"], depth + 1)
        elif op in ("count_children", "sum_children"):
            expected = {"op", "form_code"} | ({"field_key"} if op == "sum_children" else set())
            if set(node) != expected or any(
                not isinstance(node[k], str) or not KEY.fullmatch(node[k])
                for k in expected - {"op"}
            ):
                raise ValueError("invalid child aggregation")
            aggregates.append(node)
        else:
            raise ValueError("unsupported operation")

    visit(expression, 0)
    return refs, aggregates


def evaluate(expression, resolve, aggregate):
    validate(expression)

    def run(node):
        if "ref" in node:
            return resolve(node["ref"])
        if "const" in node:
            return number(node["const"])
        op = node["op"]
        if op in ("count_children", "sum_children"):
            return aggregate(node)
        left, right = run(node["left"]), run(node["right"])
        if left is None or right is None:
            return None
        if op == "divide" and right == 0:
            return None
        if op == "add":
            result = left + right
        elif op == "subtract":
            result = left - right
        elif op == "multiply":
            result = left * right
        else:
            result = left / right
        return number(result)

    try:
        with localcontext() as context:
            context.prec = 38
            result = run(expression)
            return (
                None
                if result is None
                else number(result.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP))
            )
    except DecimalException:
        raise ValueError("calculation out of range") from None

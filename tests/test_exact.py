from __future__ import annotations

import pytest
import sympy as sp

from geometric_function_atlas.exact import (
    ExactExpressionError,
    parse_exact_expression,
)


def test_parse_positive_integer() -> None:
    assert parse_exact_expression("42") == sp.Integer(42)


def test_parse_negative_integer() -> None:
    assert parse_exact_expression("-7") == sp.Integer(-7)


def test_parse_rational() -> None:
    assert parse_exact_expression("3/4") == sp.Rational(3, 4)


def _equals(got: sp.Expr, want: sp.Basic) -> bool:
    return sp.simplify(got - want) == 0


def test_parse_pi_expression() -> None:
    # parabolic Fekete-Szego value from the certificate corpus
    assert _equals(
        parse_exact_expression("(48 + 8*pi**2)/(3*pi**4)"),
        sp.sympify("(48 + 8*pi**2)/(3*pi**4)"),
    )


def test_parse_sqrt_expression() -> None:
    assert _equals(parse_exact_expression("sqrt(2)/2"), sp.sqrt(2) / 2)


def test_parse_reviewed_radius_expression() -> None:
    assert _equals(
        parse_exact_expression("asin((E-1)/(E+1))"),
        sp.asin((sp.E - 1) / (sp.E + 1)),
    )


def test_parse_compound_rational_kr_value() -> None:
    assert _equals(
        parse_exact_expression("9/2 - 3*sqrt(2)"),
        sp.Rational(9, 2) - 3 * sp.sqrt(2),
    )


def test_parse_nested_parens() -> None:
    assert parse_exact_expression("2*(1/(3+1))") == sp.Rational(1, 2)


def test_rejects_scientific_notation() -> None:
    with pytest.raises(ExactExpressionError):
        parse_exact_expression("1e5")


def test_rejects_decimal_notation() -> None:
    with pytest.raises(ExactExpressionError):
        parse_exact_expression("0.5")


def test_rejects_caller_controlled_symbols() -> None:
    with pytest.raises(ExactExpressionError):
        parse_exact_expression("z + 1")


def test_rejects_unknown_function_calls() -> None:
    with pytest.raises(ExactExpressionError):
        parse_exact_expression("sin(1)")


def test_rejects_function_calls_on_arbitrary_names() -> None:
    with pytest.raises(ExactExpressionError):
        parse_exact_expression("eval('1')")


def test_rejects_empty_string() -> None:
    with pytest.raises(ExactExpressionError):
        parse_exact_expression("")


def test_rejects_oversized_integer() -> None:
    with pytest.raises(ExactExpressionError):
        parse_exact_expression("9" * 300)


def test_rejects_oversized_expression() -> None:
    with pytest.raises(ExactExpressionError):
        parse_exact_expression("1+1" * 5000)


def test_rejects_trailing_garbage() -> None:
    with pytest.raises(ExactExpressionError):
        parse_exact_expression("1/2 z")


def test_rejects_unbalanced_parens() -> None:
    with pytest.raises(ExactExpressionError):
        parse_exact_expression("(1+2")


def test_rejects_division_by_zero() -> None:
    with pytest.raises(ExactExpressionError):
        parse_exact_expression("1/0")

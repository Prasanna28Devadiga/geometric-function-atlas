"""Immutable public models used by the reproducibility API."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import sympy as sp

Z = sp.Symbol("z")
MAX_EXPRESSION_NODES = 10_000
MAX_EXPRESSION_DEPTH = 128
MAX_EXPRESSION_INTEGER_BITS = 426
MAX_EXPRESSION_EXPONENT = 256
MAX_EXPRESSION_OPERATIONS = MAX_EXPRESSION_NODES
_MAX_EXPRESSION_INTEGER = 10**128

_DAG_FUNCTIONS = frozenset(
    {
        "Abs",
        "Max",
        "Pi",
        "acosh",
        "asin",
        "asinh",
        "atan",
        "atanh",
        "cos",
        "cosh",
        "exp",
        "log",
        "pi",
        "sin",
        "sinh",
        "tanh",
    }
)


def _integer_within_bound(value: sp.Integer) -> bool:
    integer = abs(int(value))
    return (
        integer.bit_length() <= MAX_EXPRESSION_INTEGER_BITS
        and integer < _MAX_EXPRESSION_INTEGER
    )


def _power_components_within_bound(base: sp.Integer | sp.Rational, exponent: int) -> bool:
    """Bound deferred exact powers without first constructing their result."""

    if exponent == 0:
        return True
    numerator = abs(int(base.p)) if isinstance(base, sp.Rational) else abs(int(base))
    denominator = int(base.q) if isinstance(base, sp.Rational) else 1
    if exponent < 0 and numerator == 0:
        return False
    numerator_power = numerator**abs(exponent)
    denominator_power = denominator**abs(exponent)
    return (
        numerator_power < _MAX_EXPRESSION_INTEGER
        and denominator_power < _MAX_EXPRESSION_INTEGER
    )


def validate_exact_expression(expression: sp.Expr) -> None:
    """Reject unbounded or inexact SymPy trees before expensive operations."""

    pending: list[tuple[sp.Basic, int]] = [(expression, 0)]
    seen: set[int] = set()
    nodes = 0
    while pending:
        node, depth = pending.pop()
        if id(node) in seen:
            continue
        seen.add(id(node))
        nodes += 1
        if nodes > MAX_EXPRESSION_NODES:
            raise ValueError(
                f"expression exceeds {MAX_EXPRESSION_NODES} nodes"
            )
        if depth > MAX_EXPRESSION_DEPTH:
            raise ValueError(
                f"expression exceeds depth limit {MAX_EXPRESSION_DEPTH}"
            )
        if isinstance(node, sp.Integer):
            if not _integer_within_bound(node):
                raise ValueError(
                    "exact integer coefficients exceed the expression resource bound"
                )
        elif isinstance(node, sp.Rational):
            if not _integer_within_bound(node.p) or not _integer_within_bound(node.q):
                raise ValueError(
                    "exact rational coefficients exceed the expression resource bound"
                )
        elif isinstance(node, sp.Float):
            raise TypeError("expression must contain exact, non-floating SymPy values")
        elif node in (sp.oo, -sp.oo, sp.zoo, sp.nan):
            raise ValueError("expression must contain finite exact values")
        if isinstance(node, sp.Pow) and isinstance(node.exp, sp.Integer) and (
            abs(int(node.exp)) > MAX_EXPRESSION_EXPONENT
        ):
            raise ValueError(
                f"integer exponents must be at most {MAX_EXPRESSION_EXPONENT}"
            )
        if (
            isinstance(node, sp.Pow)
            and isinstance(node.exp, sp.Integer)
            and isinstance(node.base, (sp.Integer, sp.Rational))
            and not _power_components_within_bound(node.base, int(node.exp))
        ):
            raise ValueError("exact power components exceed the expression resource bound")
        pending.extend((child, depth + 1) for child in node.args)


def _dag_key(expression: sp.Basic) -> tuple[Any, ...]:
    """Build a hashable exact identity independent of SymPy's printer."""

    if isinstance(expression, sp.Integer):
        return ("integer", str(int(expression)))
    if isinstance(expression, sp.Rational):
        return ("rational", str(int(expression.p)), str(int(expression.q)))
    if isinstance(expression, sp.Symbol):
        if expression != Z:
            raise ValueError("expression DAG contains an undeclared symbol")
        return ("symbol", "z")
    if isinstance(expression, sp.Float):
        raise TypeError("expression DAG cannot contain floating-point values")
    if isinstance(expression, sp.Add):
        return ("add", tuple(sorted(_dag_key(arg) for arg in expression.args)))
    if isinstance(expression, sp.Mul):
        return ("mul", tuple(sorted(_dag_key(arg) for arg in expression.args)))
    if isinstance(expression, sp.Pow):
        return ("pow", _dag_key(expression.base), _dag_key(expression.exp))
    name = expression.func.__name__
    if name not in _DAG_FUNCTIONS:
        raise TypeError(f"unsupported exact expression node: {name}")
    return ("function", name, tuple(_dag_key(arg) for arg in expression.args))


def _dag_node(key: tuple[Any, ...], identifiers: Mapping[tuple[Any, ...], str]) -> dict[str, Any]:
    op = key[0]
    if op in {"integer", "rational", "symbol"}:
        if op == "rational":
            return {
                "id": identifiers[key],
                "op": op,
                "numerator": key[1],
                "denominator": key[2],
            }
        return {"id": identifiers[key], "op": op, "value": key[1]}
    if op in {"add", "mul"}:
        return {
            "id": identifiers[key],
            "op": op,
            "args": [identifiers[child] for child in key[1]],
        }
    if op == "pow":
        return {
            "id": identifiers[key],
            "op": op,
            "args": [identifiers[key[1]], identifiers[key[2]]],
        }
    return {
        "id": identifiers[key],
        "op": op,
        "name": key[1],
        "args": [identifiers[child] for child in key[2]],
    }


def canonical_expression_dag(
    expressions: Mapping[str, sp.Expr | Sequence[sp.Expr]],
) -> dict[str, Any]:
    """Return a bounded, deterministic exact-expression DAG for result records."""

    if not isinstance(expressions, Mapping) or not expressions:
        raise ValueError("expression DAG requires named expressions")
    keys: dict[str, tuple[Any, ...] | tuple[tuple[Any, ...], ...]] = {}
    sequence_roots: set[str] = set()
    for name, expression in expressions.items():
        if isinstance(expression, Sequence) and not isinstance(expression, (str, bytes)):
            keys[name] = tuple(_dag_key(item) for item in expression)
            sequence_roots.add(name)
        else:
            keys[name] = _dag_key(expression)  # type: ignore[arg-type]
    all_keys: set[tuple[Any, ...]] = set()

    def collect(key: tuple[Any, ...]) -> None:
        if key in all_keys:
            return
        all_keys.add(key)
        if key[0] in {"add", "mul"}:
            for child in key[1]:
                collect(child)
        elif key[0] == "pow":
            collect(key[1])
            collect(key[2])
        elif key[0] == "function":
            for child in key[2]:
                collect(child)

    for name, key in keys.items():
        if name in sequence_roots:
            for item in key:
                collect(item)
        else:
            collect(key)  # type: ignore[arg-type]
    if len(all_keys) > MAX_EXPRESSION_NODES:
        raise ValueError("expression DAG exceeds node resource bound")
    ordered = sorted(all_keys)
    identifiers = {key: f"n{index}" for index, key in enumerate(ordered)}
    return {
        "version": 1,
        "nodes": [_dag_node(key, identifiers) for key in ordered],
        "roots": {
        name: (
            [identifiers[item] for item in key]
            if name in sequence_roots
            else identifiers[key]  # type: ignore[index]
        )
            for name, key in sorted(keys.items())
        },
    }


@dataclass(frozen=True, slots=True)
class Generator:
    """A normalized Ma–Minda generator with bibliographic provenance.

    ``expression`` must be a preconstructed exact SymPy expression in :data:`Z`.
    Strings are deliberately rejected because SymPy string parsing is eval-based.
    A generator definition is data, not a claim that every Ma–Minda
    admissibility hypothesis has been independently certified by this package.
    """

    key: str
    name: str
    expression: sp.Expr
    citation: str
    reference_url: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.expression, sp.Expr):
            raise TypeError("expression must be a preconstructed SymPy expression")
        validate_exact_expression(self.expression)
        undeclared = self.expression.free_symbols - {Z}
        if undeclared:
            names = ", ".join(sorted(map(str, undeclared)))
            raise ValueError(f"generator {self.key!r}: undeclared free symbols: {names}")
        if not isinstance(self.key, str) or not self.key:
            raise TypeError("generator key must be a non-empty string")
        if not isinstance(self.name, str) or not self.name:
            raise TypeError("generator name must be a non-empty string")
        if not isinstance(self.citation, str) or not self.citation:
            raise TypeError("generator citation must be a non-empty string")
        if self.reference_url is not None and not isinstance(self.reference_url, str):
            raise TypeError("generator reference_url must be a string or null")

    @property
    def variable(self) -> sp.Symbol:
        return Z

    @property
    def formula(self) -> str:
        """Canonical, non-executable display form of the exact expression."""

        validate_exact_expression(self.expression)
        return sp.sstr(self.expression)

"""Restricted exact-expression parser for baked scientific artifacts.

The Geometric Function Atlas certificate corpus stores exact constants as
compact strings such as ``(48 + 8*pi**2)/(3*pi**4)`` or ``9/2 - 3*sqrt(2)``.
This module turns those strings into SymPy expressions **without** calling
``sympify``/``parse_expr`` (general SymPy string parsing is eval-based) and
without admitting caller-controlled symbols, decimals, or scientific notation.
Only the closed exact-arithmetic subset used by the baked corpus is accepted:
non-negative integers, ``pi``, ``E``, the explicitly allow-listed ``sqrt`` and
``asin`` calls, and ``+ - * / **`` with parentheses.
"""

from __future__ import annotations

import re

import sympy as sp

MAX_EXPRESSION_LENGTH = 512
MAX_INTEGER_BITS = 426
MAX_POWER_EXPONENT = 64
MAX_PARSE_DEPTH = 32

_TOKEN = re.compile(
    r"""
    \s*(?:
        (?P<int>[0-9]+)
      | (?P<constant>pi|E)
      | (?P<function>sqrt|asin)
      | (?P<op>\*\*|[+*/()\-])
    )""",
    re.VERBOSE,
)


class ExactExpressionError(ValueError):
    """Raised when an exact constant string is not in the closed grammar."""


class _Parser:
    def __init__(self, text: str) -> None:
        self._text = text
        self._tokens: list[tuple[str, str]] = []
        position = 0
        while position < len(text):
            match = _TOKEN.match(text, position)
            if match is None or match.end() == position:
                raise ExactExpressionError(
                    f"unexpected character at offset {position} in {text!r}"
                )
            position = match.end()
            kind = match.lastgroup
            assert kind is not None
            self._tokens.append((kind, match.group(kind)))
        if not self._tokens:
            raise ExactExpressionError("exact expression must not be empty")
        self._index = 0

    def _peek(self) -> tuple[str, str] | None:
        if self._index >= len(self._tokens):
            return None
        return self._tokens[self._index]

    def _take(self, kind: str | None = None) -> tuple[str, str] | None:
        token = self._peek()
        if token is None:
            return None
        if kind is not None and token[0] != kind:
            return None
        self._index += 1
        return token

    def _expect(self, kind: str) -> tuple[str, str]:
        token = self._take(kind)
        if token is None:
            raise ExactExpressionError(
                f"expected {kind!r} in {self._text!r}"
            )
        return token

    def parse(self) -> sp.Expr:
        value = self._expression(0)
        if self._peek() is not None:
            raise ExactExpressionError(
                f"trailing tokens in exact expression {self._text!r}"
            )
        if not isinstance(value, sp.Expr):
            raise ExactExpressionError("exact expression did not produce an expression")
        return value

    def _expression(self, depth: int) -> sp.Expr:
        if depth > MAX_PARSE_DEPTH:
            raise ExactExpressionError("exact expression nesting is too deep")
        value = self._term(depth + 1)
        while True:
            token = self._peek()
            if token is None or token[0] not in ("op",):
                break
            operator = token[1]
            if operator not in ("+", "-"):
                break
            self._take("op")
            right = self._term(depth + 1)
            value = value + right if operator == "+" else value - right
        return value

    def _term(self, depth: int) -> sp.Expr:
        value = self._factor(depth + 1)
        while True:
            token = self._peek()
            if token is None or token[0] != "op":
                break
            operator = token[1]
            if operator not in ("*", "/"):
                break
            self._take("op")
            right = self._factor(depth + 1)
            if operator == "*":
                value = sp.expand(value * right)
            else:
                if right == 0:
                    raise ExactExpressionError("division by zero in exact expression")
                value = sp.expand(value / right)
        return value

    def _factor(self, depth: int) -> sp.Expr:
        if depth > MAX_PARSE_DEPTH:
            raise ExactExpressionError("exact expression nesting is too deep")
        base = self._atom(depth + 1)
        token = self._peek()
        if token is not None and token[0] == "op" and token[1] == "**":
            self._take("op")
            exponent_token = self._take("int")
            if exponent_token is None:
                raise ExactExpressionError(
                    f"power exponent must be an integer in {self._text!r}"
                )
            exponent = int(exponent_token[1])
            if exponent > MAX_POWER_EXPONENT:
                raise ExactExpressionError(
                    f"power exponent {exponent} exceeds the bound "
                    f"{MAX_POWER_EXPONENT}"
                )
            base = base ** exponent
        return base

    def _atom(self, depth: int) -> sp.Expr:
        if depth > MAX_PARSE_DEPTH:
            raise ExactExpressionError("exact expression nesting is too deep")
        token = self._peek()
        if token is None:
            raise ExactExpressionError(
                f"unexpected end of exact expression {self._text!r}"
            )
        kind, text = token
        if kind == "int":
            self._take("int")
            integer = int(text)
            if integer.bit_length() > MAX_INTEGER_BITS:
                raise ExactExpressionError(
                    f"integer in {self._text!r} exceeds the {MAX_INTEGER_BITS}-bit bound"
                )
            return sp.Integer(integer)
        if kind == "constant":
            self._take("constant")
            return sp.pi if text == "pi" else sp.E
        if kind == "function":
            self._take("function")
            opening = self._take("op")
            if opening is None or opening[1] != "(":
                raise ExactExpressionError(
                    f"{text} must be followed by '(' in {self._text!r}"
                )
            inner = self._expression(depth + 1)
            closing = self._take("op")
            if closing is None or closing[1] != ")":
                raise ExactExpressionError(
                    f"missing ')' after {text} in {self._text!r}"
                )
            return sp.sqrt(sp.expand(inner)) if text == "sqrt" else sp.asin(sp.expand(inner))
        if kind == "op":
            if text == "(":
                self._take("op")
                inner = self._expression(depth + 1)
                closing = self._take("op")
                if closing is None or closing[1] != ")":
                    raise ExactExpressionError(
                        f"missing ')' in exact expression {self._text!r}"
                    )
                return inner
            if text == "-":
                self._take("op")
                return -self._factor(depth + 1)
            if text == "+":
                self._take("op")
                return self._factor(depth + 1)
        raise ExactExpressionError(
            f"unexpected token {text!r} in exact expression {self._text!r}"
        )


def parse_exact_expression(text: str) -> sp.Expr:
    """Parse a baked exact constant into a SymPy expression.

    The grammar is closed: non-negative integers, ``pi``, ``E``, the
    allow-listed ``sqrt(expr)`` and ``asin(expr)`` calls, ``+ - * / **`` and
    parentheses. Decimal, scientific, symbolic, and unknown function-call forms
    are rejected. ``text`` must be a plain string with a bounded length.
    """

    if not isinstance(text, str):
        raise TypeError("exact expression must be a string")
    if len(text) > MAX_EXPRESSION_LENGTH:
        raise ExactExpressionError(
            f"exact expression exceeds the {MAX_EXPRESSION_LENGTH}-character bound"
        )
    return _Parser(text).parse()

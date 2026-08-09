"""Immutable public models used by the reproducibility API."""

from __future__ import annotations

from dataclasses import dataclass

import sympy as sp

Z = sp.Symbol("z")
MAX_EXPRESSION_OPERATIONS = 10_000


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
        undeclared = self.expression.free_symbols - {Z}
        if undeclared:
            names = ", ".join(sorted(map(str, undeclared)))
            raise ValueError(f"generator {self.key!r}: undeclared free symbols: {names}")
        if int(sp.count_ops(self.expression)) > MAX_EXPRESSION_OPERATIONS:
            raise ValueError(
                f"generator {self.key!r}: expression exceeds "
                f"{MAX_EXPRESSION_OPERATIONS} operations"
            )

    @property
    def variable(self) -> sp.Symbol:
        return Z

    @property
    def formula(self) -> str:
        """Canonical, non-executable display form of the exact expression."""

        return sp.sstr(self.expression)

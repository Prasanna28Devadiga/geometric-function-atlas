"""Exact coefficient operations for Ma–Minda generators."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import sympy as sp

from .catalog import generator_artifact_version, get_generator
from .models import Generator
from .version import __version__

MAX_TAYLOR_ORDER = 64


@dataclass(frozen=True, slots=True)
class GeneratorSeriesResult:
    """Exact generator coefficients with reproducibility metadata."""

    generator: Generator
    order: int
    coefficients: tuple[sp.Expr, ...]
    method: str = "exact_symbolic_taylor_series"
    evidence_status: str = "proven_exact_algebraic"

    def to_dict(self) -> dict[str, Any]:
        return {
            "generator": self.generator.key,
            "generator_formula": self.generator.formula,
            "generator_citation": self.generator.citation,
            "order": self.order,
            "coefficients": [str(value) for value in self.coefficients],
            "method": self.method,
            "evidence_status": self.evidence_status,
            "assumptions": ["phi(0) = 1", "expression uses only the variable z"],
            "package_version": __version__,
            "artifact_versions": {
                "generator_catalog": generator_artifact_version(self.generator)
            },
            "novelty_claim": False,
        }


def _resolve_generator(generator: str | Generator) -> Generator:
    return get_generator(generator) if isinstance(generator, str) else generator


def taylor_coefficients(
    generator: str | Generator,
    *,
    order: int,
) -> tuple[sp.Expr, ...]:
    """Return exact ``B_1, …, B_order`` for ``phi(z) = 1 + Σ B_n z^n``.

    Custom :class:`Generator` objects are accepted so reproductions are not
    limited to the built-in catalog. The normalization ``phi(0) = 1`` is checked
    exactly before coefficients are returned.
    """

    if order < 1:
        raise ValueError("order must be at least 1")
    if order > MAX_TAYLOR_ORDER:
        raise ValueError(f"order must be at most {MAX_TAYLOR_ORDER}")

    resolved = _resolve_generator(generator)
    expression = resolved.expression
    variable = resolved.variable
    if sp.simplify(expression.subs(variable, 0) - 1) != 0:
        raise ValueError(f"generator {resolved.key!r}: phi(0) must equal 1")

    polynomial = sp.series(expression, variable, 0, order + 1).removeO().expand()
    return tuple(
        sp.simplify(polynomial.coeff(variable, degree))
        for degree in range(1, order + 1)
    )


def generator_series(
    generator: str | Generator,
    *,
    order: int,
) -> GeneratorSeriesResult:
    """Return exact coefficients plus a structured provenance record."""

    resolved = _resolve_generator(generator)
    return GeneratorSeriesResult(
        generator=resolved,
        order=order,
        coefficients=taylor_coefficients(resolved, order=order),
    )

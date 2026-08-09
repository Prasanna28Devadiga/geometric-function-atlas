"""Exact Fekete–Szegő constants under Ma–Minda assumptions."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Any

import sympy as sp

from .catalog import generator_artifact_version
from .coefficients import _resolve_generator, taylor_coefficients
from .models import Generator
from .version import __version__

MAX_DECIMAL_PRECISION = 1_000
MAX_RATIONAL_CHARACTERS = 128
MAX_RATIONAL_COMPONENT_BITS = 426
_RATIONAL_PATTERN = re.compile(r"([+-]?\d+)(?:/([+-]?\d+))?", flags=re.ASCII)

_MA_MINDA_REFERENCE = (
    "W. C. Ma and D. Minda, A unified treatment of some special classes of "
    "univalent functions, Proceedings of the Conference on Complex Analysis, "
    "Tianjin 1992, International Press (1994), 157–169."
)


@dataclass(frozen=True, slots=True)
class FeketeSzegoResult:
    """Exact result plus the assumptions and provenance needed to review it."""

    generator: Generator
    mu: sp.Rational
    b1: sp.Expr
    b2: sp.Expr
    value: sp.Expr
    method: str = "ma_minda_fekete_szego_closed_form"
    evidence_status: str = "proven_exact_under_declared_assumptions"

    def decimal(self, *, precision: int = 16) -> str:
        if precision < 2:
            raise ValueError("precision must be at least 2")
        if precision > MAX_DECIMAL_PRECISION:
            raise ValueError(f"precision must be at most {MAX_DECIMAL_PRECISION}")
        return str(sp.N(self.value, precision))

    def to_dict(self, *, precision: int = 16) -> dict[str, Any]:
        """Return a JSON-serializable, evidence-typed record."""

        return {
            "generator": self.generator.key,
            "generator_formula": self.generator.formula,
            "generator_citation": self.generator.citation,
            "mu": str(self.mu),
            "B1": str(self.b1),
            "B2": str(self.b2),
            "value_exact": str(self.value),
            "value_decimal": self.decimal(precision=precision),
            "method": self.method,
            "evidence_status": self.evidence_status,
            "assumptions": [
                "phi is an admissible Ma-Minda generator",
                "phi has real Taylor coefficients",
                "B1 is positive",
            ],
            "theorem_reference": _MA_MINDA_REFERENCE,
            "package_version": __version__,
            "artifact_versions": {
                "generator_catalog": generator_artifact_version(self.generator)
            },
            "novelty_claim": False,
        }


def _rational(value: float | str | sp.Rational) -> sp.Rational:
    if isinstance(value, str):
        if len(value) > MAX_RATIONAL_CHARACTERS:
            raise ValueError(
                f"mu must be at most {MAX_RATIONAL_CHARACTERS} characters"
            )
        match = _RATIONAL_PATTERN.fullmatch(value)
        if match is None:
            raise ValueError(
                "mu must be a real rational in integer or integer/integer syntax, "
                f"got {value!r}"
            )
        numerator = int(match.group(1))
        denominator = int(match.group(2) or "1")
        if denominator == 0:
            raise ValueError(f"mu must be a real rational number, got {value!r}")
        result = sp.Rational(numerator, denominator)
    elif isinstance(value, bool):
        raise TypeError(f"mu must be a real rational number, got {value!r}")
    elif isinstance(value, int):
        result = sp.Rational(value)
    elif isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"mu must be a real rational number, got {value!r}")
        result = sp.Rational(str(value))
    elif isinstance(value, sp.Rational):
        result = value
    else:
        raise TypeError(f"mu must be a real rational number, got {value!r}")

    if not isinstance(result, sp.Rational):
        raise TypeError(f"mu must be a real rational number, got {value!r}")
    numerator = abs(int(result.p))
    denominator = int(result.q)
    if max(numerator.bit_length(), denominator.bit_length()) > MAX_RATIONAL_COMPONENT_BITS:
        raise ValueError(
            "mu numerator and denominator must each be at most 128 decimal digits"
        )
    if max(len(str(numerator)), len(str(denominator))) > 128:
        raise ValueError(
            "mu numerator and denominator must each be at most 128 decimal digits"
        )
    return result


def fekete_szego(
    generator: str | Generator,
    *,
    mu: float | str | sp.Rational,
) -> FeketeSzegoResult:
    """Compute the exact sharp ``|a3 - mu*a2**2|`` constant.

    For an admissible Ma–Minda generator
    ``phi(z) = 1 + B1*z + B2*z**2 + ...``, the general formula is

    ``B1/2 * max(1, |B2/B1 + (1 - 2*mu)*B1|)``.

    The package checks the exact coefficient preconditions it can decide. Full
    analytic admissibility and literature novelty are deliberately outside this
    function's claim boundary.
    """

    resolved = _resolve_generator(generator)
    b1, b2 = taylor_coefficients(resolved, order=2)
    if b1.is_real is not True or b1.is_positive is not True:
        raise ValueError(f"generator {resolved.key!r}: B1 must be positive and real")
    if b2.is_real is not True:
        raise ValueError(f"generator {resolved.key!r}: B2 must be real")

    exact_mu = _rational(mu)
    multiplier = sp.simplify(b2 / b1 + (1 - 2 * exact_mu) * b1)
    value = sp.simplify(b1 * sp.Max(1, sp.Abs(multiplier)) / 2)
    return FeketeSzegoResult(
        generator=resolved,
        mu=exact_mu,
        b1=b1,
        b2=b2,
        value=value,
    )

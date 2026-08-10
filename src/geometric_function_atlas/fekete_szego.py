"""Exact Fekete–Szegő constants under Ma–Minda assumptions."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import sympy as sp

from .catalog import generator_artifact_version
from .coefficients import _resolve_generator, taylor_coefficients
from .contracts import (
    CheckStatus,
    FailureState,
    InvalidInputError,
    ResourceLimitError,
    VerificationCheck,
    VerificationReport,
    build_result_payload,
)
from .models import Generator, canonical_expression_dag, validate_exact_expression
from .version import FEKETE_FIXTURE_ID, SOURCE_ARTIFACT_COMMIT

MAX_DECIMAL_PRECISION = 1_000
MAX_RATIONAL_CHARACTERS = 128
MAX_RATIONAL_COMPONENT_BITS = 426
_RATIONAL_PATTERN = re.compile(r"([+-]?\d+)(?:/([+-]?\d+))?", flags=re.ASCII)


def _validate_rational_components(result: sp.Rational) -> None:
    numerator = abs(int(result.p))
    denominator = int(result.q)
    if max(numerator.bit_length(), denominator.bit_length()) > MAX_RATIONAL_COMPONENT_BITS:
        raise ResourceLimitError(
            "mu numerator and denominator must each be at most 128 decimal digits"
        )
    if max(len(str(numerator)), len(str(denominator))) > 128:
        raise ResourceLimitError(
            "mu numerator and denominator must each be at most 128 decimal digits"
        )

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

    def __post_init__(self) -> None:
        if not isinstance(self.generator, Generator):
            raise TypeError("generator must be a Generator")
        if not isinstance(self.mu, sp.Rational) or isinstance(self.mu, sp.Float):
            raise TypeError("mu must be a real rational number")
        _validate_rational_components(self.mu)
        if self.method != "ma_minda_fekete_szego_closed_form":
            raise ValueError("method is a closed package-owned value")
        normalized: list[sp.Expr] = []
        for label, value in (("B1", self.b1), ("B2", self.b2), ("value", self.value)):
            if isinstance(value, (bool, float)):
                raise TypeError(f"{label} must be an exact symbolic value")
            exact = sp.Integer(value) if isinstance(value, int) else value
            if not isinstance(exact, sp.Expr):
                raise TypeError(f"{label} must be an exact symbolic value")
            validate_exact_expression(exact)
            normalized.append(exact)
        object.__setattr__(self, "b1", normalized[0])
        object.__setattr__(self, "b2", normalized[1])
        object.__setattr__(self, "value", normalized[2])

    @property
    def evidence_status(self) -> str:
        """Return the package-derived computational evidence state."""

        if not self.verification_report.success:
            return FailureState.UNRESOLVED.value
        return "proven_exact_under_declared_assumptions"

    def decimal(self, *, precision: int = 16) -> str:
        if isinstance(precision, bool) or not isinstance(precision, int):
            raise TypeError("precision must be an integer")
        if precision < 2:
            raise InvalidInputError("precision must be at least 2")
        if precision > MAX_DECIMAL_PRECISION:
            raise ResourceLimitError(
                f"precision must be at most {MAX_DECIMAL_PRECISION}"
            )
        return str(sp.N(self.value, precision))

    @property
    def verification_report(self) -> VerificationReport:
        normalized = sp.simplify(
            self.generator.expression.subs(self.generator.variable, 0)
        )
        normalization_ok = normalized == 1
        expected_b1, expected_b2 = taylor_coefficients(self.generator, order=2)
        coefficients_ok = self.b1 == expected_b1 and self.b2 == expected_b2
        b1_ok = expected_b1.is_real is True and expected_b1.is_positive is True
        b2_ok = expected_b2.is_real is True
        if expected_b1 == 0:
            expected_value: Any = "unavailable (B1 is zero)"
            value_ok = False
        else:
            expected_value = sp.simplify(
                expected_b1
                * sp.Max(
                    1,
                    sp.Abs(
                        expected_b2 / expected_b1
                        + (1 - 2 * self.mu) * expected_b1
                    ),
                )
                / 2
            )
            value_ok = expected_value == self.value

        def check(
            name: str,
            checked: str,
            expected: Any,
            observed: Any,
            ok: bool,
            scope: str,
            reason: str,
        ) -> VerificationCheck:
            return VerificationCheck(
                name=name,
                checked=checked,
                expected=expected,
                observed=observed,
                status=CheckStatus.PASS if ok else CheckStatus.FAIL,
                scope=scope,
                failure_reason=None if ok else reason,
            )

        return VerificationReport(
            checks=(
                check(
                    "generator_normalization",
                    "generator value at z = 0",
                    "1",
                    str(normalized),
                    normalization_ok,
                    "generator definition",
                    "generator is not normalized at the origin",
                ),
                check(
                    "generator_taylor_coefficients",
                    "first and second generator Taylor coefficients",
                    [str(expected_b1), str(expected_b2)],
                    [str(self.b1), str(self.b2)],
                    coefficients_ok,
                    "exact symbolic expansion",
                    "stored B1/B2 do not match the generator expansion",
                ),
                check(
                    "positive_real_first_coefficient",
                    "first generator Taylor coefficient B1",
                    "positive real",
                    str(expected_b1),
                    b1_ok,
                    "Ma-Minda closed-form preconditions",
                    "B1 is not positive and real",
                ),
                check(
                    "real_second_coefficient",
                    "second generator Taylor coefficient B2",
                    "real",
                    str(expected_b2),
                    b2_ok,
                    "Ma-Minda closed-form preconditions",
                    "B2 is not real",
                ),
                check(
                    "exact_functional_value",
                    "closed-form Fekete-Szego value",
                    str(expected_value),
                    str(self.value),
                    value_ok,
                    "exact symbolic arithmetic",
                    "stored value does not match the closed form",
                ),
            )
        )

    def to_dict(self, *, precision: int = 16) -> dict[str, Any]:
        """Return a JSON-serializable, evidence-typed record."""

        return build_result_payload(
            result_type="fekete_szego",
            canonical_inputs={"generator": self.generator.key, "mu": str(self.mu)},
            exact_expressions={
                "generator": self.generator.formula,
                "B1": str(self.b1),
                "B2": str(self.b2),
                "value": str(self.value),
            },
            method=self.method,
            evidence_status=self.evidence_status,
            assumptions=(
                "phi is an admissible Ma-Minda generator",
                "phi has real Taylor coefficients",
                "B1 is positive",
            ),
            source_references=(self.generator.citation, _MA_MINDA_REFERENCE),
            artifact_versions={
                "generator_catalog": generator_artifact_version(self.generator),
                "source_commit": SOURCE_ARTIFACT_COMMIT
                if generator_artifact_version(self.generator) != "user-supplied"
                else "caller-supplied",
                "fixture_or_proof": FEKETE_FIXTURE_ID,
            },
            verification=self.verification_report,
            exact_expression_dag=canonical_expression_dag(
                {
                    "generator": self.generator.expression,
                    "B1": self.b1,
                    "B2": self.b2,
                    "value": self.value,
                }
            ),
            provenance=(
                "caller_supplied"
                if generator_artifact_version(self.generator) == "user-supplied"
                else "built_in"
            ),
            legacy_fields={
                "generator": self.generator.key,
                "generator_formula": self.generator.formula,
                "generator_citation": self.generator.citation,
                "mu": str(self.mu),
                "B1": str(self.b1),
                "B2": str(self.b2),
                "value_exact": str(self.value),
                "value_decimal": self.decimal(precision=precision),
                "theorem_reference": _MA_MINDA_REFERENCE,
            },
        )


def _rational(value: int | str | sp.Rational) -> sp.Rational:
    if isinstance(value, str):
        if len(value) > MAX_RATIONAL_CHARACTERS:
            raise ResourceLimitError(
                f"mu must be at most {MAX_RATIONAL_CHARACTERS} characters"
            )
        match = _RATIONAL_PATTERN.fullmatch(value)
        if match is None:
            raise InvalidInputError(
                "mu must be a real rational in integer or integer/integer syntax, "
                f"got {value!r}"
            )
        numerator = int(match.group(1))
        denominator = int(match.group(2) or "1")
        if denominator == 0:
            raise InvalidInputError(f"mu must be a real rational number, got {value!r}")
        result = sp.Rational(numerator, denominator)
    elif isinstance(value, bool):
        raise TypeError(f"mu must be a real rational number, got {value!r}")
    elif isinstance(value, int):
        if abs(value).bit_length() > MAX_RATIONAL_COMPONENT_BITS:
            raise ResourceLimitError(
                "mu numerator and denominator must each be at most 128 decimal digits"
            )
        result = sp.Rational(value)
    elif isinstance(value, float):
        raise TypeError(f"mu must be a real rational number, got {value!r}")
    elif isinstance(value, sp.Rational):
        result = value
    else:
        raise TypeError(f"mu must be a real rational number, got {value!r}")

    if not isinstance(result, sp.Rational):
        raise TypeError(f"mu must be a real rational number, got {value!r}")
    _validate_rational_components(result)
    return result


def fekete_szego(
    generator: str | Generator,
    *,
    mu: int | str | sp.Rational,
) -> FeketeSzegoResult:
    """Compute the exact sharp ``|a3 - mu*a2**2|`` constant.

    For an admissible Ma–Minda generator
    ``phi(z) = 1 + B1*z + B2*z**2 + ...``, the general formula is

    ``B1/2 * max(1, |B2/B1 + (1 - 2*mu)*B1|)``.

    The package checks the exact coefficient preconditions it can decide. Full
    analytic admissibility and literature novelty are deliberately outside this
    function's claim boundary.
    """

    exact_mu = _rational(mu)
    resolved = _resolve_generator(generator)
    b1, b2 = taylor_coefficients(resolved, order=2)
    if b1.is_real is not True or b1.is_positive is not True:
        raise InvalidInputError(
            f"generator {resolved.key!r}: B1 must be positive and real"
        )
    if b2.is_real is not True:
        raise InvalidInputError(f"generator {resolved.key!r}: B2 must be real")

    multiplier = sp.simplify(b2 / b1 + (1 - 2 * exact_mu) * b1)
    value = sp.simplify(b1 * sp.Max(1, sp.Abs(multiplier)) / 2)
    return FeketeSzegoResult(
        generator=resolved,
        mu=exact_mu,
        b1=b1,
        b2=b2,
        value=value,
    )

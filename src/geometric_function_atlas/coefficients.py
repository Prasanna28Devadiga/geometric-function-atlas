"""Exact coefficient operations for Ma–Minda generators."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import sympy as sp

from .catalog import generator_artifact_version, get_generator
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
from .version import GENERATOR_FIXTURE_ID, SOURCE_ARTIFACT_COMMIT

MAX_TAYLOR_ORDER = 64


@dataclass(frozen=True, slots=True)
class GeneratorSeriesResult:
    """Exact generator coefficients with reproducibility metadata."""

    generator: Generator
    order: int
    coefficients: tuple[sp.Expr, ...]
    method: str = "exact_symbolic_taylor_series"

    def __post_init__(self) -> None:
        if isinstance(self.order, bool) or not isinstance(self.order, int):
            raise TypeError("order must be a positive integer")
        if self.order < 1:
            raise InvalidInputError("order must be at least 1")
        if self.order > MAX_TAYLOR_ORDER:
            raise ResourceLimitError(f"order must be at most {MAX_TAYLOR_ORDER}")
        if not isinstance(self.generator, Generator):
            raise TypeError("generator must be a Generator")
        if self.method != "exact_symbolic_taylor_series":
            raise ValueError("method is a closed package-owned value")
        normalized: list[sp.Expr] = []
        for value in self.coefficients:
            if isinstance(value, (bool, float)):
                raise TypeError("coefficients must be exact symbolic values")
            exact = sp.Integer(value) if isinstance(value, int) else value
            if not isinstance(exact, sp.Expr):
                raise TypeError("coefficients must be exact symbolic values")
            validate_exact_expression(exact)
            normalized.append(exact)
        if len(normalized) != self.order:
            raise ValueError("coefficients length must equal order")
        object.__setattr__(self, "coefficients", tuple(normalized))

    @property
    def evidence_status(self) -> str:
        """Return the package-derived computational evidence state."""

        if not self.verification_report.success:
            return FailureState.UNRESOLVED.value
        return "proven_exact_under_declared_assumptions"

    @property
    def verification_report(self) -> VerificationReport:
        normalized = sp.simplify(
            self.generator.expression.subs(self.generator.variable, 0)
        )
        expected: Any
        try:
            expected_coefficients = taylor_coefficients(
                self.generator, order=self.order
            )
            coefficients_ok = expected_coefficients == self.coefficients
            expected = [str(value) for value in expected_coefficients]
            reason = "stored coefficients do not match the exact expansion"
        except (TypeError, ValueError):
            expected = "unavailable (invalid or over-limit order)"
            coefficients_ok = False
            reason = "exact expansion could not be recomputed"
        return VerificationReport(
            checks=(
                VerificationCheck(
                    name="generator_normalization",
                    checked="generator value at z = 0",
                    expected="1",
                    observed=str(normalized),
                    status=CheckStatus.PASS if normalized == 1 else CheckStatus.FAIL,
                    scope="generator definition",
                    failure_reason=(
                        None
                        if normalized == 1
                        else "generator is not normalized at the origin"
                    ),
                ),
                VerificationCheck(
                    name="exact_taylor_coefficients",
                    checked=f"Taylor coefficients through order {self.order}",
                    expected=expected,
                    observed=[str(value) for value in self.coefficients],
                    status=(
                        CheckStatus.PASS if coefficients_ok else CheckStatus.FAIL
                    ),
                    scope="exact symbolic expansion",
                    failure_reason=None if coefficients_ok else reason,
                ),
            )
        )

    def to_dict(self) -> dict[str, Any]:
        return build_result_payload(
            result_type="generator_series",
            canonical_inputs={"generator": self.generator.key, "order": self.order},
            exact_expressions={
                "generator": self.generator.formula,
                "coefficients": [str(value) for value in self.coefficients],
            },
            method=self.method,
            evidence_status=self.evidence_status,
            assumptions=("phi(0) = 1", "expression uses only the variable z"),
            source_references=(self.generator.citation,),
            artifact_versions={
                "generator_catalog": generator_artifact_version(self.generator),
                "source_commit": SOURCE_ARTIFACT_COMMIT
                if generator_artifact_version(self.generator) != "user-supplied"
                else "caller-supplied",
                "fixture_or_proof": GENERATOR_FIXTURE_ID,
            },
            verification=self.verification_report,
            exact_expression_dag=canonical_expression_dag(
                {
                    "generator": self.generator.expression,
                    "coefficients": self.coefficients,
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
                "order": self.order,
                "coefficients": [str(value) for value in self.coefficients],
            },
        )


def _resolve_generator(generator: str | Generator) -> Generator:
    if isinstance(generator, str):
        return get_generator(generator)
    if not isinstance(generator, Generator):
        raise TypeError("generator must be a built-in key or Generator")
    return generator


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

    if isinstance(order, bool) or not isinstance(order, int):
        raise TypeError("order must be a positive integer")
    if order < 1:
        raise InvalidInputError("order must be at least 1")
    if order > MAX_TAYLOR_ORDER:
        raise ResourceLimitError(f"order must be at most {MAX_TAYLOR_ORDER}")

    resolved = _resolve_generator(generator)
    expression = resolved.expression
    variable = resolved.variable
    if sp.simplify(expression.subs(variable, 0) - 1) != 0:
        raise InvalidInputError(f"generator {resolved.key!r}: phi(0) must equal 1")

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

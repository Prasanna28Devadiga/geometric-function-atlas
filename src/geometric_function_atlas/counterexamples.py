"""Certified re-evaluation of supplied counterexample witnesses."""

from __future__ import annotations

import builtins
import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import sympy as sp
from mpmath import iv

from .contracts import (
    CheckStatus,
    UnresolvedError,
    VerificationCheck,
    VerificationReport,
    build_result_payload,
)
from .models import canonical_expression_dag
from .version import COUNTEREXAMPLE_FIXTURE_ID


@dataclass(frozen=True, slots=True)
class CounterexampleResult:
    """Result of checking one claimed violation point."""

    property: str
    coefficients: tuple[float, ...]
    point: tuple[float, float]
    interval_lower: float
    interval_upper: float
    threshold: float
    certified: bool

    @builtins.property
    def direction(self) -> str:
        if self.property == "starlike":
            return "disproves" if self.certified else "not_disproved"
        return "violates_criterion" if self.certified else "not_violated"

    def to_dict(self) -> dict[str, Any]:
        coefficient_exact = tuple(_exact_float(value) for value in self.coefficients)
        point_exact = tuple(_exact_float(value) for value in self.point)
        interval_exact = (
            _exact_float(self.interval_lower),
            _exact_float(self.interval_upper),
        )
        threshold_exact = _exact_float(self.threshold)
        exact_expressions = {
            "coefficients": [sp.sstr(value) for value in coefficient_exact],
            "point": [sp.sstr(value) for value in point_exact],
            "interval": [sp.sstr(value) for value in interval_exact],
            "threshold": sp.sstr(threshold_exact),
        }
        verification = VerificationReport(
            checks=(
                VerificationCheck(
                    name="interval_is_ordered",
                    checked="the certified interval has lower <= upper",
                    expected=True,
                    observed=self.interval_lower <= self.interval_upper,
                    status=CheckStatus.PASS,
                    scope="returned binary64 endpoint enclosure",
                ),
                VerificationCheck(
                    name="classification_matches_interval",
                    checked="the verdict follows from the threshold-separated interval",
                    expected=self.direction,
                    observed=self.direction,
                    status=CheckStatus.PASS,
                    scope="supplied witness point only",
                ),
            )
        )
        return build_result_payload(
            result_type="counterexample_verification",
            canonical_inputs={
                "property": self.property,
                "coefficients": [float.hex(value) for value in self.coefficients],
                "point": [float.hex(value) for value in self.point],
            },
            exact_expressions=exact_expressions,
            exact_expression_dag=canonical_expression_dag(
                {
                    "coefficients": coefficient_exact,
                    "point": point_exact,
                    "interval": interval_exact,
                    "threshold": threshold_exact,
                }
            ),
            method="certified_point_interval_evaluation",
            evidence_status="certified_enclosure",
            assumptions=(
                "f(z) is the supplied normalized polynomial",
                "the witness point lies in the open unit disk",
                "inputs are interpreted as exact IEEE-754 binary64 values",
            ),
            source_references=(
                "gft.pointwise parity fixture and standard pointwise criteria",
            ),
            artifact_versions={
                "generator_catalog": "user-supplied",
                "source_commit": "caller-supplied",
                "fixture_or_proof": COUNTEREXAMPLE_FIXTURE_ID,
            },
            verification=verification,
            legacy_fields={
                "property": self.property,
                "coefficients": [repr(value) for value in self.coefficients],
                "point": [repr(value) for value in self.point],
                "interval": [
                    repr(self.interval_lower),
                    repr(self.interval_upper),
                ],
                "threshold": repr(self.threshold),
                "certified": self.certified,
                "direction": self.direction,
            },
            provenance="caller_supplied",
        )


def _exact_float(value: float) -> sp.Rational:
    numerator, denominator = value.as_integer_ratio()
    return sp.Rational(numerator, denominator)


def _thin(value: float) -> Any:
    return iv.mpf([value, value])


def _poly_interval(
    coefficients: Sequence[float],
    z: Any,
    *,
    multipliers: Sequence[int] | None = None,
) -> Any:
    if not coefficients:
        return iv.mpc(_thin(0.0), _thin(0.0))
    factors = tuple(multipliers) if multipliers is not None else (1,) * len(coefficients)
    if len(factors) != len(coefficients):
        raise ValueError("polynomial coefficients and multipliers must have equal length")

    def interval_coefficient(index: int) -> Any:
        # Integer derivative scaling stays inside interval arithmetic. Computing
        # n*a_n as a float first can exclude the exact binary-float product.
        return _thin(factors[index]) * _thin(coefficients[index])

    result = iv.mpc(interval_coefficient(-1), _thin(0.0))
    for index in range(len(coefficients) - 2, -1, -1):
        result = result * z + iv.mpc(interval_coefficient(index), _thin(0.0))
    return result


def _complex_interval_contains_zero(value: Any) -> bool:
    return (
        float(value.real.a) <= 0.0 <= float(value.real.b)
        and float(value.imag.a) <= 0.0 <= float(value.imag.b)
    )


def _validated_coefficients(coefficients: Sequence[float]) -> tuple[float, ...]:
    try:
        values = tuple(float(value) for value in coefficients)
    except (TypeError, ValueError) as exc:
        raise ValueError("coefficients must be a sequence of real numbers") from exc
    if any(not math.isfinite(value) for value in values):
        raise ValueError("coefficients must be finite real numbers")
    return values


def _validated_point(point: tuple[float, float]) -> tuple[float, float]:
    if not isinstance(point, (tuple, list)) or len(point) != 2:
        raise ValueError("point must be a pair (real, imaginary)")
    try:
        real, imaginary = float(point[0]), float(point[1])
    except (TypeError, ValueError) as exc:
        raise ValueError("point must contain real numbers") from exc
    if not math.isfinite(real) or not math.isfinite(imaginary):
        raise ValueError("point must contain finite real numbers")
    if math.hypot(real, imaginary) >= 1.0:
        raise ValueError("counterexample point must lie inside the open unit disk")
    return real, imaginary


def _evaluate_counterexample_interval(
    values: tuple[float, ...],
    real: float,
    imaginary: float,
    property_name: str,
) -> tuple[float, float, float, bool]:
    """Return the authoritative interval and classification for validated inputs."""

    if property_name == "starlike" and real == 0.0 and imaginary == 0.0:
        # For every normalized analytic f(z)=z+..., z f'(z)/f(z) has
        # removable value 1 at the origin.
        return 1.0, 1.0, 0.0, False
    z = iv.mpc(_thin(real), _thin(imaginary))

    # Power-basis coefficients for f and f'. The normalized z coefficient is implicit.
    f_coefficients = (0.0, 1.0, *values)
    fp_coefficients = (1.0, *values)
    fp_multipliers = (1, *range(2, len(values) + 2))
    fpp_coefficients = values
    fpp_multipliers = tuple(
        degree * (degree - 1) for degree in range(2, len(values) + 2)
    )
    fppp_coefficients = values[1:]
    fppp_multipliers = tuple(
        degree * (degree - 1) * (degree - 2)
        for degree in range(3, len(values) + 2)
    )
    try:
        fp_value = _poly_interval(fp_coefficients, z, multipliers=fp_multipliers)
        if property_name == "starlike":
            f_value = _poly_interval(f_coefficients, z)
            if _complex_interval_contains_zero(f_value):
                raise UnresolvedError(
                    "criterion denominator f(z) contains zero; the witness is singular or unresolved"
                )
            quantity = z * fp_value / f_value
            lower = float(quantity.real.a)
            upper = float(quantity.real.b)
            threshold = 0.0
            certified = upper <= threshold
        else:
            if _complex_interval_contains_zero(fp_value):
                raise UnresolvedError(
                    "criterion denominator f'(z) contains zero; the witness is singular or unresolved"
                )
            one_minus_radius_squared = _thin(1.0) - (
                z.real**2 + z.imag**2
            )
            fpp_value = _poly_interval(
                fpp_coefficients, z, multipliers=fpp_multipliers
            )
            if property_name == "becker_univalent":
                quantity = one_minus_radius_squared * abs(fpp_value / fp_value)
                threshold = 1.0
            else:
                ratio = fpp_value / fp_value
                schwarzian = (
                    _poly_interval(
                        fppp_coefficients, z, multipliers=fppp_multipliers
                    )
                    / fp_value
                    - iv.mpc(_thin(1.5), _thin(0.0)) * ratio * ratio
                )
                quantity = one_minus_radius_squared**2 * abs(schwarzian)
                threshold = 2.0
            lower = float(quantity.a)
            upper = float(quantity.b)
            certified = lower > threshold
    except ZeroDivisionError as exc:
        raise UnresolvedError(
            "criterion denominator contains zero; the witness is singular or unresolved"
        ) from exc

    if not math.isfinite(lower) or not math.isfinite(upper):
        raise UnresolvedError(
            "criterion evaluation produced an unbounded interval; the witness is unresolved"
        )

    return lower, upper, threshold, certified


def verify_counterexample(
    coefficients: Sequence[float],
    *,
    point: tuple[float, float],
    property: str = "starlike",
) -> CounterexampleResult:
    """Rigorously check a claimed pointwise counterexample.

    ``coefficients`` are ``[a2, a3, ...]`` for
    ``f(z) = z + a2*z**2 + a3*z**3 + ...``. Supported violations are:

    * ``starlike``: ``Re(z*f'(z)/f(z)) <= 0``;
    * ``becker_univalent``: ``(1-|z|^2)|f''(z)/f'(z)| > 1``;
    * ``nehari_univalent``: ``(1-|z|^2)^2|S_f(z)| > 2``.
    """

    supported = {"starlike", "becker_univalent", "nehari_univalent"}
    if property not in supported:
        allowed = ", ".join(sorted(supported))
        raise ValueError(f"property must be one of: {allowed}")

    values = _validated_coefficients(coefficients)
    real, imaginary = _validated_point(point)
    lower, upper, threshold, certified = _evaluate_counterexample_interval(
        values, real, imaginary, property
    )

    return CounterexampleResult(
        property=property,
        coefficients=values,
        point=(real, imaginary),
        interval_lower=lower,
        interval_upper=upper,
        threshold=threshold,
        certified=certified,
    )

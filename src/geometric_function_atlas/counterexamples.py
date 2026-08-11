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
from .records import build_screen_record
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
    if not isinstance(coefficients, Sequence) or isinstance(
        coefficients, (str, bytes, bytearray)
    ):
        raise TypeError("coefficients must be a sequence of real numbers")
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


def _poly_float(coefficients: Sequence[float], z: complex) -> complex:
    """Horner evaluation of a power series whose first entry is the constant term."""

    if not coefficients:
        return 0.0 + 0.0j
    result: complex = coefficients[-1]
    for coefficient in reversed(coefficients[:-1]):
        result = result * z + coefficient
    return result


def _fpolys(coefficients: Sequence[float]) -> tuple[
    list[float], list[float], list[float], list[float]
]:
    """Power-basis coefficient lists for f, f', f'', f''' of
    ``f(z) = z + sum_{n>=2} a_n z^n`` (real coefficients)."""

    values = [float(value) for value in coefficients]
    n_max = len(values) + 1
    f = [0.0, 1.0] + values
    fp = [1.0] + [degree * values[degree - 2] for degree in range(2, n_max + 1)]
    fpp = [
        degree * (degree - 1) * values[degree - 2]
        for degree in range(2, n_max + 1)
    ]
    fppp = [
        degree * (degree - 1) * (degree - 2) * values[degree - 2]
        for degree in range(3, n_max + 1)
    ]
    return f, fp, fpp, fppp


def _float_screen_value(
    property_name: str, coefficients: tuple[float, ...], z: complex
) -> float:
    """Float evaluation of the pointwise criterion at one point."""

    f, fp, fpp, fppp = _fpolys(coefficients)
    fp_value = _poly_float(fp, z)
    if property_name == "starlike":
        f_value = _poly_float(f, z)
        if abs(f_value) < 1e-300:
            return float("nan")
        return (z * fp_value / f_value).real
    if abs(fp_value) < 1e-300:
        return float("nan")
    one_minus = 1.0 - (z.real**2 + z.imag**2)
    if property_name == "becker_univalent":
        return one_minus * abs(_poly_float(fpp, z) / fp_value)
    fpp_value = _poly_float(fpp, z)
    fppp_value = _poly_float(fppp, z)
    schwarzian = fppp_value / fp_value - 1.5 * (fpp_value / fp_value) ** 2
    return one_minus**2 * abs(schwarzian)


def _worst_grid_point(
    property_name: str,
    coefficients: tuple[float, ...],
    *,
    grid_r: int = 120,
    grid_theta: int = 180,
    max_r: float = 0.99,
) -> tuple[complex, float]:
    """Float grid search for the most-violating point of a criterion."""

    worst_value: float | None = None
    worst_z: complex | None = None
    for r_index in range(grid_r):
        radius = 0.05 + (max_r - 0.05) * r_index / max(grid_r - 1, 1)
        for t_index in range(grid_theta):
            theta = 2 * math.pi * t_index / grid_theta
            z = complex(radius * math.cos(theta), radius * math.sin(theta))
            value = _float_screen_value(property_name, coefficients, z)
            if not math.isfinite(value):
                continue
            if worst_value is None or (
                value < worst_value
                if property_name == "starlike"
                else value > worst_value
            ):
                worst_value = value
                worst_z = z
    if worst_z is None or worst_value is None:
        raise UnresolvedError(
            "grid search produced no finite evaluations for the criterion"
        )
    return worst_z, worst_value


_SEARCH_THRESHOLDS = {
    "starlike": 0.0,
    "becker_univalent": 1.0,
    "nehari_univalent": 2.0,
}


@dataclass(frozen=True, slots=True)
class WitnessSearchResult:
    """Outcome of a grid search followed by interval certification."""

    property: str
    coefficients: tuple[float, ...]
    certified: bool
    point: tuple[float, float] | None
    interval_lower: float | None
    interval_upper: float | None
    threshold: float
    margin: float | None
    screen_value: float
    grid_points: int

    def to_dict(self) -> dict[str, Any]:
        exact_coefficients = tuple(
            sp.sstr(_exact_float(value)) for value in self.coefficients
        )
        evidence = "certified_enclosure" if self.certified else "numerical_screen"
        checks = (
            VerificationCheck(
                name="grid_search_screened",
                checked="float grid search for the most-violating point",
                expected="a finite candidate point on the grid",
                observed=(
                    f"screen value {self.screen_value:g} at "
                    f"{self.point[0]:g},{self.point[1]:g}"
                    if self.point is not None
                    else "no finite candidate"
                ),
                status=CheckStatus.PASS,
                scope="float grid search (not a proof)",
            ),
            VerificationCheck(
                name="interval_certified",
                checked="certified interval enclosure at the candidate point",
                expected="threshold-separated enclosure",
                observed=(
                    f"certified={self.certified}, margin={self.margin:g}"
                    if self.margin is not None
                    else "unresolved"
                ),
                status=CheckStatus.PASS,
                scope="mpmath interval arithmetic at the exact binary64 point",
            ),
        )
        return build_screen_record(
            record_type="witness_search",
            canonical_inputs={
                "property": self.property,
                "coefficients": list(exact_coefficients),
            },
            method="grid_search_then_interval_certification",
            evidence_kind=evidence,
            tier="rigorous",
            assumptions=(
                "f(z) is the supplied finite polynomial",
                "the grid locates a candidate; interval arithmetic certifies only the final point",
                "a certified violation for a truncation is about the truncation",
            ),
            source_references=(
                "gft.pointwise find_and_certify parity at source commit acee553",
            ),
            verification=VerificationReport(checks=checks),
            details={
                "certified": self.certified,
                "point": None if self.point is None else list(self.point),
                "interval_lower": self.interval_lower,
                "interval_upper": self.interval_upper,
                "threshold": self.threshold,
                "margin": self.margin,
                "screen_value": self.screen_value,
                "grid_points": self.grid_points,
            },
        )


def find_counterexample(
    coefficients: Sequence[float],
    *,
    property: str = "starlike",
    witness_hint: tuple[float, float] | None = None,
    grid_r: int = 120,
    grid_theta: int = 180,
) -> WitnessSearchResult:
    """Search for a violation point and certify it in interval arithmetic.

    ``coefficients`` are ``[a2, a3, ...]`` for
    ``f(z) = z + a2*z**2 + ...``. A float grid locates the most-violating
    point; the final verdict is certified only when the interval enclosure at
    that exact point clears the threshold. ``witness_hint``, when supplied,
    is tried before the grid candidate.
    """

    supported = {"starlike", "becker_univalent", "nehari_univalent"}
    if property not in supported:
        allowed = ", ".join(sorted(supported))
        raise ValueError(f"property must be one of: {allowed}")

    values = _validated_coefficients(coefficients)
    grid_point, screen_value = _worst_grid_point(
        property, values, grid_r=grid_r, grid_theta=grid_theta
    )
    candidates: list[tuple[float, float]] = []
    if witness_hint is not None:
        real, imaginary = _validated_point(witness_hint)
        candidates.append((real, imaginary))
    candidates.append((grid_point.real, grid_point.imag))

    threshold = _SEARCH_THRESHOLDS[property]
    best: dict[str, Any] | None = None
    for real, imaginary in candidates:
        try:
            lower, upper, evaluated_threshold, certified = (
                _evaluate_counterexample_interval(values, real, imaginary, property)
            )
        except (UnresolvedError, ZeroDivisionError, ValueError, ArithmeticError):
            continue
        margin = (
            threshold - upper if property == "starlike" else lower - threshold
        )
        candidate = {
            "certified": certified,
            "point": (real, imaginary),
            "lower": lower,
            "upper": upper,
            "margin": margin,
            "threshold": evaluated_threshold,
        }
        if certified or best is None:
            best = candidate
        if certified:
            break
    if best is None:
        raise UnresolvedError(
            "no candidate point could be evaluated in interval arithmetic"
        )

    return WitnessSearchResult(
        property=property,
        coefficients=values,
        certified=bool(best["certified"]),
        point=best["point"],
        interval_lower=best["lower"],
        interval_upper=best["upper"],
        threshold=best["threshold"],
        margin=best["margin"],
        screen_value=screen_value,
        grid_points=grid_r * grid_theta,
    )

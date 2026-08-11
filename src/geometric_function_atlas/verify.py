"""Tiered verification of normalized analytic functions.

The website's verification sandbox exposes three cost tiers. The package
mirrors them with explicit epistemic labels so a numerical screen is never
presented as a proof:

* ``screen``    — float grid evaluation of pointwise criteria; the verdict is
                  ``numerical_screen`` evidence about the sampled grid only.
* ``symbolic``  — exact arithmetic: the Schild/Goodman C01 sufficient
                  condition ``sum(n*|a_n|) <= 1`` (starlikeness) and the
                  Alexander-convexity condition ``sum(n^2*|a_n|) <= 1``.
                  For a *finite polynomial* these are complete proofs; for a
                  truncation only a partial sum above 1 is conclusive (it
                  disproves the sufficient condition, never the property).
* ``rigorous``  — the symbolic exact checks plus certified interval
                  evaluation of the criterion at the worst screened point.
                  A threshold-separated enclosure certifies the violation for
                  the supplied finite polynomial.

Closed-form inputs must be preconstructed SymPy expressions; formula strings
are deliberately rejected because SymPy string parsing is eval-based.
"""

from __future__ import annotations

import builtins
import math
from dataclasses import dataclass
from typing import Any

import sympy as sp
from mpmath import iv

from .contracts import (
    CheckStatus,
    InvalidInputError,
    ResourceLimitError,
    VerificationCheck,
    VerificationReport,
)
from .counterexamples import (
    _evaluate_counterexample_interval,
    _poly_interval,
    _thin,
)
from .records import build_screen_record
from .version import SOURCE_ARTIFACT_COMMIT

TIERS: tuple[str, ...] = ("screen", "symbolic", "rigorous")
_PROPERTIES: tuple[str, ...] = (
    "starlike",
    "convex",
    "univalent",
    "becker_univalent",
    "nehari_univalent",
)
_POINTWISE_PROPERTIES = frozenset(
    {"starlike", "convex", "becker_univalent", "nehari_univalent"}
)
_THRESHOLDS = {
    "starlike": 0.0,
    "convex": 0.0,
    "becker_univalent": 1.0,
    "nehari_univalent": 2.0,
}
MAX_VERIFY_COEFFICIENTS = 128
MAX_CLOSED_FORM_ORDER = 40
_REFERENCE = (
    "gft.symbolic C01 (Schild/Goodman) and Alexander-convexity sufficient "
    f"conditions at source commit {SOURCE_ARTIFACT_COMMIT}"
)
_SCREEN_REFERENCE = (
    "gft.verifiers numerical screens at source commit " + SOURCE_ARTIFACT_COMMIT
)
_INTERVAL_REFERENCE = (
    "gft.pointwise certified interval evaluation at source commit "
    + SOURCE_ARTIFACT_COMMIT
)


def _validated_coefficients(coefficients: Any) -> tuple[float, ...]:
    if isinstance(coefficients, (str, bytes, bytearray)) or not isinstance(
        coefficients, (list, tuple)
    ):
        raise TypeError("coefficients must be a sequence of real numbers")
    if len(coefficients) > MAX_VERIFY_COEFFICIENTS:
        raise ResourceLimitError(
            f"coefficients must have at most {MAX_VERIFY_COEFFICIENTS} entries"
        )
    try:
        values = tuple(float(value) for value in coefficients)
    except (TypeError, ValueError) as exc:
        raise ValueError("coefficients must be a sequence of real numbers") from exc
    if any(not math.isfinite(value) for value in values):
        raise ValueError("coefficients must be finite real numbers")
    return values


def _exact_float(value: float) -> sp.Expr:
    numerator, denominator = value.as_integer_ratio()
    return sp.Rational(numerator, denominator)


def _decide_le_one(total: sp.Expr) -> bool | None:
    """Exactly decide ``total <= 1``, with a certified numeric fallback."""

    diff = sp.simplify(total - 1)
    if diff.is_number:
        sign = diff.is_nonpositive
        if sign is not None:
            return bool(sign)
        value = sp.N(diff, 50)
        if value.is_real:
            numeric = float(value)
            if abs(numeric) > 1e-40:
                return numeric <= 0
    return None


def _criterion_sums(
    coefficients: tuple[float, ...],
) -> tuple[sp.Expr, sp.Expr]:
    exact = tuple(_exact_float(value) for value in coefficients)
    c01 = sp.Add(
        *[sp.Integer(degree) * sp.Abs(value) for degree, value in enumerate(exact, start=2)]
    ) if exact else sp.Integer(0)
    convex = sp.Add(
        *[sp.Integer(degree) ** 2 * sp.Abs(value) for degree, value in enumerate(exact, start=2)]
    ) if exact else sp.Integer(0)
    return c01, convex


def _horner(coefficients: tuple[float, ...], z: complex) -> complex:
    """Evaluate ``z + a2*z**2 + ...`` by Horner in the z-basis."""

    if not coefficients:
        return z
    result: complex = coefficients[-1]
    for coefficient in reversed(coefficients[:-1]):
        result = result * z + coefficient
    return (result * z + 1.0) * z


def _derivative_polynomials(
    coefficients: tuple[float, ...],
) -> tuple[tuple[float, ...], tuple[float, ...], tuple[float, ...]]:
    """Power-basis coefficients of f', f'', f''' (constant term included)."""

    n_max = len(coefficients) + 1
    fp = [1.0] + [
        degree * coefficients[degree - 2] for degree in range(2, n_max + 1)
    ]
    fpp = [
        degree * (degree - 1) * coefficients[degree - 2]
        for degree in range(2, n_max + 1)
    ]
    fppp = [
        degree * (degree - 1) * (degree - 2) * coefficients[degree - 2]
        for degree in range(3, n_max + 1)
    ]
    return tuple(fp), tuple(fpp), tuple(fppp)


def _poly_value(coefficients: tuple[float, ...], z: complex) -> complex:
    """Horner evaluation of a plain power series (constant term first)."""

    if not coefficients:
        return 0.0
    result: complex = coefficients[-1]
    for coefficient in reversed(coefficients[:-1]):
        result = result * z + coefficient
    return result


def _screen_value(
    property_name: str,
    coefficients: tuple[float, ...],
    z: complex,
) -> float:
    fp_list, fpp_list, fppp_list = _derivative_polynomials(coefficients)
    fp = _poly_value(fp_list, z)
    if property_name == "starlike":
        f = _horner(coefficients, z)
        if abs(f) < 1e-300:
            return float("nan")
        return (z * fp / f).real
    if property_name == "convex":
        if abs(fp) < 1e-300:
            return float("nan")
        fpp = _poly_value(fpp_list, z)
        return (1.0 + z * fpp / fp).real
    radius_squared = (z.real**2 + z.imag**2) * 1.0
    if abs(fp) < 1e-300:
        return float("nan")
    fpp = _poly_value(fpp_list, z)
    if property_name == "becker_univalent":
        return (1.0 - radius_squared) * abs(fpp / fp)
    fppp = _poly_value(fppp_list, z)
    schwarzian = fppp / fp - 1.5 * (fpp / fp) ** 2
    return (1.0 - radius_squared) ** 2 * abs(schwarzian)


def _grid_scan(
    property_name: str,
    coefficients: tuple[float, ...],
    *,
    grid_r: int,
    grid_theta: int,
    rmax: float,
) -> tuple[float, tuple[float, float] | None, int]:
    """Return (worst margin, worst point, evaluated point count)."""

    threshold = _THRESHOLDS[property_name]
    maximize = property_name in ("becker_univalent", "nehari_univalent")
    worst_margin: float | None = None
    worst_point: tuple[float, float] | None = None
    evaluated = 0
    for r_index in range(grid_r):
        radius = 0.05 + (rmax - 0.05) * r_index / max(grid_r - 1, 1)
        for t_index in range(grid_theta):
            theta = 2 * math.pi * t_index / grid_theta
            z = complex(radius * math.cos(theta), radius * math.sin(theta))
            value = _screen_value(property_name, coefficients, z)
            if not math.isfinite(value):
                continue
            evaluated += 1
            margin = value - threshold
            if worst_margin is None or (
                margin > worst_margin if maximize else margin < worst_margin
            ):
                worst_margin = margin
                worst_point = (z.real, z.imag)
    if worst_margin is None:
        raise InvalidInputError(
            "screen produced no finite evaluations; the criterion is singular on the grid"
        )
    return worst_margin, worst_point, evaluated


def _certified_interval(
    property_name: str,
    coefficients: tuple[float, ...],
    point: tuple[float, float],
) -> tuple[float, float, float, bool]:
    if property_name == "convex":
        return _evaluate_convex_interval(coefficients, point[0], point[1])
    return _evaluate_counterexample_interval(
        coefficients, point[0], point[1], property_name
    )


def _evaluate_convex_interval(
    values: tuple[float, ...],
    real: float,
    imaginary: float,
) -> tuple[float, float, float, bool]:
    if real == 0.0 and imaginary == 0.0:
        return 1.0, 1.0, 0.0, False
    z = iv.mpc(_thin(real), _thin(imaginary))
    fp_coefficients = (1.0, *values)
    fp_multipliers = (1, *range(2, len(values) + 2))
    fpp_coefficients = values
    fpp_multipliers = tuple(
        degree * (degree - 1) for degree in range(2, len(values) + 2)
    )
    fp_value = _poly_interval(fp_coefficients, z, multipliers=fp_multipliers)
    if fp_value.real.a <= 0.0 <= fp_value.real.b and (
        fp_value.imag.a <= 0.0 <= fp_value.imag.b
    ):
        raise RuntimeError("criterion denominator f'(z) contains zero")
    fpp_value = _poly_interval(fpp_coefficients, z, multipliers=fpp_multipliers)
    quantity = iv.mpc(_thin(1.0), _thin(0.0)) + z * fpp_value / fp_value
    lower = float(quantity.real.a)
    upper = float(quantity.real.b)
    if not math.isfinite(lower) or not math.isfinite(upper):
        raise RuntimeError("criterion evaluation produced an unbounded interval")
    return lower, upper, 0.0, upper <= 0.0


def _closed_form_coefficients(
    expression: sp.Expr,
) -> tuple[tuple[float, ...], bool, sp.Basic]:
    if not isinstance(expression, sp.Expr):
        raise TypeError("closed_form must be a preconstructed SymPy expression")
    symbols = expression.free_symbols
    if len(symbols) != 1:
        raise InvalidInputError(
            "closed_form must depend on exactly one variable"
        )
    variable = next(iter(symbols))
    f0 = sp.simplify(expression.subs(variable, 0))
    fp0 = sp.simplify(sp.diff(expression, variable).subs(variable, 0))
    if f0 != 0 or fp0 != 1:
        raise InvalidInputError(
            f"closed_form is not normalized: f(0)={f0}, f'(0)={fp0}"
        )
    polynomial = bool(expression.is_polynomial(variable))
    if polynomial:
        degree = sp.degree(sp.Poly(sp.expand(expression), variable))
        order = max(int(degree), 2)
    else:
        order = MAX_CLOSED_FORM_ORDER
    series = sp.series(expression, variable, 0, order + 1).removeO().expand()
    coefficients: list[float] = []
    for degree in range(2, order + 1):
        coefficient = series.coeff(variable, degree)
        if coefficient == 0:
            coefficients.append(0.0)
            continue
        try:
            coefficients.append(float(sp.N(coefficient, 30)))
        except (TypeError, ValueError) as exc:
            raise InvalidInputError(
                "closed_form Taylor coefficients must be numeric"
            ) from exc
    return tuple(coefficients), polynomial, variable


@dataclass(frozen=True, slots=True)
class FunctionVerificationResult:
    """Structured outcome of one tiered verification run."""

    property: str
    coefficients: tuple[float, ...]
    tier: str
    outcome: str
    evidence_kind: str
    verification_report: VerificationReport
    details: dict[str, Any]
    witness_point: tuple[float, float] | None = None
    certified: bool = False
    min_margin: float | None = None
    exact_coefficients: tuple[str, ...] = ()

    @builtins.property
    def passes(self) -> bool:
        return self.outcome in {"passes_screen", "proven", "certified_violation"}

    def to_dict(self) -> dict[str, Any]:
        return build_screen_record(
            record_type="function_verification",
            canonical_inputs={
                "property": self.property,
                "coefficients": list(self.exact_coefficients),
                "tier": self.tier,
            },
            method="tiered_function_verification",
            evidence_kind=self.evidence_kind,
            tier=self.tier,
            assumptions=(
                "f(z) is the supplied normalized function",
                "coefficients are interpreted as exact binary64 rational values",
                "a finite polynomial is the whole function unless truncation is declared",
            ),
            source_references=(_SCREEN_REFERENCE, _REFERENCE, _INTERVAL_REFERENCE),
            verification=self.verification_report,
            details={
                "outcome": self.outcome,
                "witness_point": (
                    None if self.witness_point is None else list(self.witness_point)
                ),
                "certified": self.certified,
                "min_margin": self.min_margin,
                **self.details,
            },
        )


def verify_function(
    coefficients: Any = None,
    *,
    closed_form: sp.Expr | None = None,
    property: str = "starlike",
    max_cost: str = "screen",
    truncation: bool = False,
    grid_r: int = 40,
    grid_theta: int = 48,
    rmax: float = 0.98,
) -> FunctionVerificationResult:
    """Verify a normalized analytic function at the requested cost tier.

    Exactly one of ``coefficients`` (``[a2, a3, ...]`` for
    ``f(z) = z + a2*z**2 + ...``) or ``closed_form`` (a preconstructed SymPy
    expression) is required.
    """

    if max_cost not in TIERS:
        allowed = ", ".join(TIERS)
        raise InvalidInputError(f"max_cost must be one of: {allowed}")
    if property not in _PROPERTIES:
        allowed = ", ".join(_PROPERTIES)
        raise InvalidInputError(f"property must be one of: {allowed}")
    if (coefficients is None) == (closed_form is None):
        raise InvalidInputError(
            "provide exactly one of coefficients or closed_form"
        )
    if not isinstance(truncation, bool):
        raise TypeError("truncation must be a bool")
    if property == "univalent" and max_cost != "symbolic":
        raise InvalidInputError(
            "univalence has no pointwise screen; use max_cost='symbolic' or "
            "verify the Becker/Nehari criteria"
        )

    if closed_form is not None:
        values, polynomial, _ = _closed_form_coefficients(closed_form)
    else:
        values = _validated_coefficients(coefficients)
        polynomial = not truncation

    exact_coefficients = tuple(
        sp.sstr(_exact_float(value)) for value in values
    )

    if max_cost == "screen":
        return _screen_verdict(property, values, exact_coefficients, grid_r, grid_theta, rmax)
    if max_cost == "symbolic":
        return _symbolic_verdict(property, values, exact_coefficients, polynomial)
    return _rigorous_verdict(
        property, values, exact_coefficients, polynomial, grid_r, grid_theta, rmax
    )


def _finite_check() -> VerificationCheck:
    return VerificationCheck(
        name="input_finite",
        checked="supplied coefficients are finite real numbers",
        expected="finite binary64 values",
        observed="finite",
        status=CheckStatus.PASS,
        scope="input validation",
    )


def _screen_verdict(
    property_name: str,
    values: tuple[float, ...],
    exact_coefficients: tuple[str, ...],
    grid_r: int,
    grid_theta: int,
    rmax: float,
) -> FunctionVerificationResult:
    threshold = _THRESHOLDS[property_name]
    margin, point, evaluated = _grid_scan(
        property_name, values, grid_r=grid_r, grid_theta=grid_theta, rmax=rmax
    )
    maximizes = property_name in ("becker_univalent", "nehari_univalent")
    violation = margin > 0.0 if maximizes else margin < 0.0
    screen_check = VerificationCheck(
        name="criterion_grid_screen",
        checked=f"{property_name} criterion on a sampled disk grid",
        expected="no violation at any sampled point",
        observed=(
            f"violation screened, {'max' if maximizes else 'min'} margin {margin:.6g}"
            if violation
            else f"no violation screened, {'max' if maximizes else 'min'} margin {margin:.6g}"
        ),
        status=CheckStatus.PASS,
        scope="float grid screen (not a proof)",
    )
    return FunctionVerificationResult(
        property=property_name,
        coefficients=values,
        tier="screen",
        outcome="fails_screen" if violation else "passes_screen",
        evidence_kind="numerical_screen",
        verification_report=VerificationReport(
            checks=(_finite_check(), screen_check)
        ),
        details={
            "threshold": threshold,
            "grid_points": evaluated,
            "worst_point": None if point is None else list(point),
        },
        witness_point=point,
        min_margin=margin,
        exact_coefficients=exact_coefficients,
    )


def _symbolic_verdict(
    property_name: str,
    values: tuple[float, ...],
    exact_coefficients: tuple[str, ...],
    polynomial: bool,
) -> FunctionVerificationResult:
    c01, convex = _criterion_sums(values)
    c01_str = sp.sstr(c01)
    convex_str = sp.sstr(convex)
    c01_decided = _decide_le_one(c01)
    convex_decided = _decide_le_one(convex)

    if c01_decided is None:
        c01_check = VerificationCheck(
            name="c01_exact_sum",
            checked="C01: sum(n*|a_n|) <= 1 in exact arithmetic",
            expected="decidable exact comparison",
            observed=f"sum = {c01_str}",
            status=CheckStatus.SKIP,
            required=False,
            scope="exact symbolic arithmetic",
            failure_reason=None,
        )
        outcome = "undecidable"
        evidence_kind = "inconclusive"
    elif polynomial and c01_decided:
        outcome = "proven"
        evidence_kind = "exact_proof"
        c01_check = VerificationCheck(
            name="c01_exact_sum",
            checked="C01: sum(n*|a_n|) <= 1 in exact arithmetic",
            expected=f"sum <= 1 (decided, polynomial: {c01_str})",
            observed=c01_str,
            status=CheckStatus.PASS,
            scope="exact symbolic arithmetic",
        )
    elif not polynomial and c01_decided:
        outcome = "inconclusive_truncation"
        evidence_kind = "inconclusive"
        c01_check = VerificationCheck(
            name="c01_exact_sum",
            checked="C01 partial sum on a truncation",
            expected="partial sum <= 1 (tail unknown)",
            observed=c01_str,
            status=CheckStatus.PASS,
            scope="exact symbolic arithmetic on the truncation",
        )
    else:
        outcome = "c01_fails_sufficient_condition"
        evidence_kind = "inconclusive"
        c01_check = VerificationCheck(
            name="c01_exact_sum",
            checked="C01: sum(n*|a_n|) <= 1 in exact arithmetic",
            expected="sum <= 1",
            observed=c01_str,
            status=CheckStatus.PASS,
            scope="exact symbolic arithmetic",
            failure_reason=None,
        )

    convex_check = VerificationCheck(
        name="alexander_convexity_sum",
        checked="Alexander condition: sum(n^2*|a_n|) <= 1",
        expected="decided comparison",
        observed=f"sum = {convex_str}" + ("" if convex_decided is not None else " (undecidable)"),
        status=CheckStatus.SKIP if convex_decided is None else CheckStatus.PASS,
        required=polynomial and convex_decided is not None,
        scope="exact symbolic arithmetic",
        failure_reason=(
            None
            if convex_decided is not None
            else "comparison undecidable in exact arithmetic"
        ),
    )

    details: dict[str, Any] = {
        "c01_sum": c01_str,
        "convex_sum": convex_str,
        "polynomial": polynomial,
        "c01_le_1": c01_decided,
    }
    if outcome == "proven":
        if property_name == "convex" and convex_decided:
            details["convex_proven"] = True
        if property_name == "univalent":
            details["univalent_proven"] = True
    return FunctionVerificationResult(
        property=property_name,
        coefficients=values,
        tier="symbolic",
        outcome=outcome,
        evidence_kind=evidence_kind,
        verification_report=VerificationReport(checks=(_finite_check(), c01_check, convex_check)),
        details=details,
        min_margin=None,
        exact_coefficients=exact_coefficients,
    )


def _rigorous_verdict(
    property_name: str,
    values: tuple[float, ...],
    exact_coefficients: tuple[str, ...],
    polynomial: bool,
    grid_r: int,
    grid_theta: int,
    rmax: float,
) -> FunctionVerificationResult:
    c01, _ = _criterion_sums(values)
    c01_str = sp.sstr(c01)
    c01_decided = _decide_le_one(c01)
    c01_check = VerificationCheck(
        name="c01_exact_sum",
        checked="C01: sum(n*|a_n|) <= 1 in exact arithmetic",
        expected="decided exact comparison",
        observed=c01_str,
        status=CheckStatus.PASS if c01_decided is not None else CheckStatus.SKIP,
        required=c01_decided is not None,
        scope="exact symbolic arithmetic",
        failure_reason=(
            None if c01_decided is not None else "comparison undecidable in exact arithmetic"
        ),
    )

    margin, point, evaluated = _grid_scan(
        property_name, values, grid_r=grid_r, grid_theta=grid_theta, rmax=rmax
    )
    grid_check = VerificationCheck(
        name="criterion_grid_screen",
        checked=f"{property_name} criterion on a sampled disk grid",
        expected="no violation at any sampled point",
        observed=f"min margin {margin:.6g}",
        status=CheckStatus.PASS,
        scope="float grid screen (not a proof)",
    )

    interval_check: VerificationCheck
    certified = False
    interval_details: dict[str, Any] = {}
    if point is None:
        interval_check = VerificationCheck(
            name="interval_certification",
            checked="certified interval at the worst screened point",
            expected="threshold-separated enclosure",
            observed="no finite grid point",
            status=CheckStatus.SKIP,
            required=False,
            scope="mpmath interval arithmetic",
            failure_reason=None,
        )
    else:
        try:
            lower, upper, threshold, certified = _certified_interval(
                property_name, values, point
            )
        except (ZeroDivisionError, ValueError, ArithmeticError, RuntimeError) as exc:
            interval_check = VerificationCheck(
                name="interval_certification",
                checked="certified interval at the worst screened point",
                expected="threshold-separated enclosure",
                observed=f"unresolved: {exc}",
                status=CheckStatus.SKIP,
                required=False,
                scope="mpmath interval arithmetic",
                failure_reason=None,
            )
            certified = False
        else:
            interval_check = VerificationCheck(
                name="interval_certification",
                checked="certified interval at the worst screened point",
                expected="threshold-separated enclosure",
                observed=(
                    f"certified={certified}, interval=[{lower:.6g}, {upper:.6g}]"
                ),
                status=CheckStatus.PASS,
                scope="mpmath interval arithmetic",
            )
            interval_details = {
                "interval_lower": lower,
                "interval_upper": upper,
                "interval_threshold": threshold,
            }

    if polynomial and c01_decided:
        outcome = "proven"
        evidence_kind = "exact_proof"
    elif certified:
        outcome = "certified_violation"
        evidence_kind = "certified_enclosure"
    else:
        outcome = "no_certified_violation_on_grid"
        evidence_kind = "numerical_screen"

    return FunctionVerificationResult(
        property=property_name,
        coefficients=values,
        tier="rigorous",
        outcome=outcome,
        evidence_kind=evidence_kind,
        verification_report=VerificationReport(
            checks=(_finite_check(), grid_check, c01_check, interval_check)
        ),
        details={
            "c01_sum": c01_str,
            "polynomial": polynomial,
            "grid_points": evaluated,
            "worst_point": None if point is None else list(point),
            **interval_details,
        },
        witness_point=point,
        certified=certified,
        min_margin=margin,
        exact_coefficients=exact_coefficients,
    )

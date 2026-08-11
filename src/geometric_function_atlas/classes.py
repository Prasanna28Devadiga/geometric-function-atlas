"""Ma–Minda class screens and extremal coefficients.

The website source catalog enumerates named and parametric Ma–Minda classes
``S*(phi)`` with ``phi(0) = 1`` and ``phi'(0) > 0``. This module reproduces
the class-level operations as *screens* unless the check is exact:

* admissibility — ``phi(0) = 1`` and ``phi'(0) > 0`` are decided in exact
  arithmetic; the region conditions (``Re phi > 0`` on the disk, real
  coefficients, starlikeness with respect to 1) are float winding-number and
  grid screens with reported margins;
* membership — the subordination screen ``z f'(z)/f(z) in phi(D)`` on a
  sampled disk grid (a true member always passes; a non-member whose
  violation is confined to a thin annulus near ``|z| = 1`` can slip through);
* containment — ``phi_inner(D) subset phi_outer(D)`` by sampled boundary
  winding numbers, which by subordination transitivity is the same as
  ``S*(phi_inner) subset S*(phi_outer)``;
* extremal coefficients — exact Taylor coefficients of the sharp member
  ``f_phi(z) = z exp(int_0^z (phi(t) - 1)/t dt)`` via the standard recurrence.
"""

from __future__ import annotations

import cmath
import math
from dataclasses import dataclass
from typing import Any

import sympy as sp

from .catalog import get_generator, list_generators
from .coefficients import taylor_coefficients
from .contracts import (
    CheckStatus,
    InvalidInputError,
    ResourceLimitError,
    VerificationCheck,
    VerificationReport,
)
from .models import Generator, Z
from .records import build_screen_record
from .version import SOURCE_ARTIFACT_COMMIT
from .verify import _exact_float

MAX_EXTREMAL_ORDER = 24
_REFERENCE = (
    "gft.maminda class screens and extremal recurrence at source commit "
    + SOURCE_ARTIFACT_COMMIT
)


def _phi_function(generator: Generator) -> Any:
    """Return a complex-valued evaluator for the exact generator expression."""

    function = sp.lambdify(Z, generator.expression, modules="cmath")
    return lambda z: complex(function(complex(z)))


def _phi_derivative_function(generator: Generator) -> Any:
    function = sp.lambdify(Z, sp.diff(generator.expression, Z), modules="cmath")
    return lambda z: complex(function(complex(z)))


def _boundary_curve(
    generator: Generator, *, n: int = 720, radius: float = 0.999
) -> tuple[complex, ...]:
    evaluator = _phi_function(generator)
    return tuple(
        evaluator(radius * cmath.exp(complex(0.0, 2 * math.pi * index / n)))
        for index in range(n)
    )


def _winding_number(point: complex, curve: tuple[complex, ...]) -> int:
    """Ray-crossing winding number of a closed curve around a point."""

    winding = 0
    count = len(curve)
    for index in range(count):
        a = curve[index]
        b = curve[(index + 1) % count]
        if (a.imag <= point.imag < b.imag) or (b.imag <= point.imag < a.imag):
            crossing = (point.imag - a.imag) / (b.imag - a.imag)
            x = a.real + crossing * (b.real - a.real)
            if x > point.real:
                winding += 1 if b.imag > a.imag else -1
    return winding


def list_classes() -> tuple[Generator, ...]:
    """Return the Ma–Minda class catalog in stable key order."""

    return list_generators()


def _get_class(key: str) -> Generator:
    return get_generator(key)


def class_admissibility(
    class_key: str,
    *,
    n_theta: int = 120,
    radii: tuple[float, ...] = (0.3, 0.6, 0.9, 0.99),
) -> "ClassAdmissibilityResult":
    """Check the Ma–Minda admissibility conditions for one class.

    Exact: ``phi(0) = 1`` and ``phi'(0)`` real and positive. Screens with
    reported margins: ``Re phi > 0`` on the disk, real-coefficient symmetry,
    and starlikeness with respect to 1.
    """

    generator = _get_class(class_key)
    expression = generator.expression

    phi0 = sp.simplify(expression.subs(Z, 0))
    phi0_ok = phi0 == 1
    derivative0 = sp.simplify(sp.diff(expression, Z).subs(Z, 0))
    derivative_ok = (
        derivative0.is_real is True and derivative0.is_positive is True
    )

    evaluator = _phi_function(generator)
    derivative_evaluator = _phi_derivative_function(generator)
    theta = tuple(2 * math.pi * index / n_theta for index in range(n_theta))
    points: list[complex] = []
    for radius in radii:
        points.extend(
            radius * cmath.exp(complex(0.0, angle)) for angle in theta
        )

    values = [evaluator(point) for point in points]
    finite = [value for value in values if math.isfinite(value.real) and math.isfinite(value.imag)]
    re_min = float(min(value.real for value in finite)) if finite else float("nan")
    re_ok = math.isfinite(re_min) and re_min > 0.0

    upper = [point for point in points if point.imag > 1e-12]
    symmetry_error = 0.0
    if upper:
        errors = [
            abs(evaluator(complex(point.real, -point.imag)) - complex(
                evaluator(point).real, -evaluator(point).imag
            ))
            for point in upper
        ]
        symmetry_error = float(max(errors))
    symmetry_ok = symmetry_error < 1e-9

    starlike_values: list[float] = []
    for point, value in zip(points, values, strict=True):
        denominator = value - 1.0
        if abs(denominator) < 1e-9:
            continue
        derivative = derivative_evaluator(point)
        quantity = point * derivative / denominator
        if math.isfinite(quantity.real):
            starlike_values.append(quantity.real)
    starlike_min = (
        float(min(starlike_values)) if starlike_values else float("nan")
    )
    starlike_ok = math.isfinite(starlike_min) and starlike_min > -1e-9

    checks = (
        _exact_check(
            "phi0_equals_1",
            "generator value at z = 0",
            "1",
            sp.sstr(phi0),
            phi0_ok,
            "generator is not normalized at the origin",
        ),
        _exact_check(
            "phi_prime0_positive",
            "first derivative at z = 0",
            "real and positive",
            sp.sstr(derivative0),
            derivative_ok,
            "phi'(0) is not real and positive",
        ),
        _screen_check(
            "re_phi_positive",
            "Re phi > 0 on a sampled disk grid",
            re_ok,
            f"min Re = {re_min:.6g}" if math.isfinite(re_min) else "no finite evaluations",
            "grid contains points with Re phi <= 0",
        ),
        _screen_check(
            "real_coefficients_symmetry",
            "phi(conj z) == conj phi(z) on sampled points",
            symmetry_ok,
            f"max symmetry error = {symmetry_error:.3g}",
            "symmetry error exceeds 1e-9",
        ),
        _screen_check(
            "starlike_wrt_1",
            "Re(z phi'(z)/(phi(z)-1)) > 0 on sampled points",
            starlike_ok,
            f"min value = {starlike_min:.6g}" if math.isfinite(starlike_min) else "no finite evaluations",
            "grid contains points violating starlikeness with respect to 1",
        ),
    )
    report = VerificationReport(checks=checks)
    return ClassAdmissibilityResult(
        class_key=class_key,
        admissible=report.success,
        verification_report=report,
        exact_values={"phi0": sp.sstr(phi0), "phi_prime0": sp.sstr(derivative0)},
        margins={
            "re_min": re_min,
            "symmetry_max_error": symmetry_error,
            "starlike_wrt_1_min": starlike_min,
        },
    )


def _exact_check(
    name: str,
    checked: str,
    expected: str,
    observed: str,
    ok: bool,
    reason: str,
) -> VerificationCheck:
    return VerificationCheck(
        name=name,
        checked=checked,
        expected=expected,
        observed=observed,
        status=CheckStatus.PASS if ok else CheckStatus.FAIL,
        scope="exact symbolic evaluation",
        failure_reason=None if ok else reason,
    )


def _screen_check(
    name: str,
    checked: str,
    ok: bool,
    observed: str,
    reason: str,
) -> VerificationCheck:
    return VerificationCheck(
        name=name,
        checked=checked,
        expected="condition holds on the sampled grid",
        observed=observed,
        status=CheckStatus.PASS if ok else CheckStatus.FAIL,
        scope="float grid screen (not a proof)",
        failure_reason=None if ok else reason,
    )


@dataclass(frozen=True, slots=True)
class ClassAdmissibilityResult:
    """Admissibility verdict with exact and screen check details."""

    class_key: str
    admissible: bool
    verification_report: VerificationReport
    exact_values: dict[str, str]
    margins: dict[str, float]

    def to_dict(self) -> dict[str, Any]:
        return build_screen_record(
            record_type="class_admissibility",
            canonical_inputs={"class_key": self.class_key},
            method="ma_minda_admissibility_screens",
            evidence_kind="numerical_screen",
            tier="screen",
            assumptions=(
                "phi is the named catalog generator",
                "region conditions are evaluated as float screens with reported margins",
            ),
            source_references=(_REFERENCE,),
            verification=self.verification_report,
            details={
                "admissible": self.admissible,
                "phi0": self.exact_values["phi0"],
                "phi_prime0": self.exact_values["phi_prime0"],
                **self.margins,
            },
        )


def _zfp_over_f(coefficients: tuple[float, ...], z: complex) -> complex:
    """``z f'(z)/f(z)`` for ``f(z) = z + sum a_n z^n``."""

    if not coefficients:
        return 1.0 + 0.0j
    fp = 1.0 + 0.0j
    f = z
    power = z
    for degree, coefficient in enumerate(coefficients, start=2):
        power *= z
        f += coefficient * power
        fp += degree * coefficient * power / z if abs(z) > 1e-300 else 0.0
    if abs(f) < 1e-300:
        return complex(float("nan"), float("nan"))
    return z * fp / f


def class_member_screen(
    class_key: str,
    coefficients: list[float] | tuple[float, ...],
    *,
    grid_r: int = 16,
    grid_theta: int = 24,
    max_r: float = 0.95,
    n_boundary: int = 720,
) -> "ClassMembershipResult":
    """Screen ``f in S*(phi)``: sample ``z f'/f`` on a grid and test whether
    every value lies inside the sampled boundary of ``phi(D)``."""

    generator = _get_class(class_key)
    try:
        values = tuple(float(value) for value in coefficients)
    except (TypeError, ValueError) as exc:
        raise ValueError("coefficients must be a sequence of real numbers") from exc
    if any(not math.isfinite(value) for value in values):
        raise ValueError("coefficients must be finite real numbers")
    if len(values) > 128:
        raise ResourceLimitError("at most 128 coefficients are supported")

    curve = _boundary_curve(generator, n=n_boundary)
    radii = tuple(
        0.05 + (max_r - 0.05) * index / max(grid_r - 1, 1)
        for index in range(grid_r)
    )
    theta = tuple(2 * math.pi * index / grid_theta for index in range(grid_theta))
    inside_count = 0
    total = 0
    min_distance = float("inf")
    witness: complex | None = None
    for radius in radii:
        for angle in theta:
            z = radius * cmath.exp(complex(0.0, angle))
            w = _zfp_over_f(values, z)
            if not (math.isfinite(w.real) and math.isfinite(w.imag)):
                continue
            total += 1
            if _winding_number(w, curve) == 1:
                inside_count += 1
                sampled = curve[::8]
                distance = min(abs(w - point) for point in sampled)
                min_distance = min(min_distance, float(distance))
            elif witness is None:
                witness = w
    if total == 0:
        raise InvalidInputError("membership screen produced no finite evaluations")
    member = inside_count == total
    checks = (
        VerificationCheck(
            name="input_finite",
            checked="supplied coefficients are finite real numbers",
            expected="finite binary64 values",
            observed="finite",
            status=CheckStatus.PASS,
            scope="input validation",
        ),
        VerificationCheck(
            name="subordination_winding_screen",
            checked="z f'/f lies inside the sampled boundary of phi(D)",
            expected=f"{total} sampled values inside",
            observed=f"{inside_count}/{total} inside",
            status=CheckStatus.PASS if member else CheckStatus.FAIL,
            scope="float winding-number screen (not a proof)",
            failure_reason=None if member else "grid value lies outside the sampled boundary",
        ),
    )
    if member:
        witness_pair: tuple[float, float] | None = None
    else:
        witness_pair = (
            None if witness is None else (witness.real, witness.imag)
        )
    return ClassMembershipResult(
        class_key=class_key,
        coefficients=values,
        member=member,
        fraction_inside=inside_count / total,
        min_dist_to_boundary=float(min_distance) if total else float("nan"),
        witness_w=witness_pair,
        verification_report=VerificationReport(checks=checks),
    )


@dataclass(frozen=True, slots=True)
class ClassMembershipResult:
    """Subordination membership screen verdict."""

    class_key: str
    coefficients: tuple[float, ...]
    member: bool
    fraction_inside: float
    min_dist_to_boundary: float
    witness_w: tuple[float, float] | None
    verification_report: VerificationReport

    def to_dict(self) -> dict[str, Any]:
        exact_coefficients = tuple(sp.sstr(_exact_float(v)) for v in self.coefficients)
        return build_screen_record(
            record_type="class_membership",
            canonical_inputs={
                "class_key": self.class_key,
                "coefficients": list(exact_coefficients),
            },
            method="ma_minda_membership_winding_screen",
            evidence_kind="numerical_screen",
            tier="screen",
            assumptions=(
                "f(z) is the supplied finite polynomial",
                "the boundary of phi(D) is sampled at a finite resolution",
                "a violation confined to a thin annulus near |z|=1 can slip through",
            ),
            source_references=(_REFERENCE,),
            verification=self.verification_report,
            details={
                "member": self.member,
                "fraction_inside": self.fraction_inside,
                "min_dist_to_boundary": self.min_dist_to_boundary,
                "witness_w": None if self.witness_w is None else list(self.witness_w),
            },
        )


def class_containment_screen(
    inner: str,
    outer: str,
    *,
    n_inner: int = 180,
    r_inner: float = 0.99,
    n_outer: int = 720,
) -> "ClassContainmentResult":
    """Screen ``phi_inner(D) subset phi_outer(D)`` by winding numbers.

    By subordination transitivity this is the same screen as
    ``S*(phi_inner) subset S*(phi_outer)``. A failed screen returns a boundary
    witness ``w`` attained by the inner extremal function.
    """

    inner_generator = _get_class(inner)
    outer_generator = _get_class(outer)
    inner_points = _boundary_curve(inner_generator, n=n_inner, radius=r_inner)
    outer_curve = _boundary_curve(outer_generator, n=n_outer)
    inside = [_winding_number(point, outer_curve) == 1 for point in inner_points]
    fraction = sum(inside) / len(inside)
    contained = all(inside)
    margin = float("nan")
    witness: complex | None = None
    if contained:
        sampled = outer_curve[::4]
        distances = [
            min(abs(point - other) for other in sampled) for point in inner_points
        ]
        margin = float(min(distances))
    else:
        witness = next(
            point for point, ok in zip(inner_points, inside, strict=True) if not ok
        )
    checks = (
        VerificationCheck(
            name="inner_curve_inside_outer",
            checked="sampled inner boundary points lie inside the outer region",
            expected=f"{len(inner_points)} sampled points inside",
            observed=f"{sum(inside)}/{len(inner_points)} inside",
            status=CheckStatus.PASS if contained else CheckStatus.FAIL,
            scope="float winding-number screen (not a proof)",
            failure_reason=(
                None if contained else "an inner boundary point lies outside the outer region"
            ),
        ),
    )
    return ClassContainmentResult(
        inner=inner,
        outer=outer,
        contained=contained,
        fraction_inside=fraction,
        margin=margin,
        witness_w=None if witness is None else (witness.real, witness.imag),
        verification_report=VerificationReport(checks=checks),
    )


@dataclass(frozen=True, slots=True)
class ClassContainmentResult:
    """Containment screen verdict between two classes."""

    inner: str
    outer: str
    contained: bool
    fraction_inside: float
    margin: float
    witness_w: tuple[float, float] | None
    verification_report: VerificationReport

    def to_dict(self) -> dict[str, Any]:
        return build_screen_record(
            record_type="class_containment",
            canonical_inputs={"inner": self.inner, "outer": self.outer},
            method="ma_minda_containment_winding_screen",
            evidence_kind="numerical_screen",
            tier="screen",
            assumptions=(
                "phi(D) regions are sampled at finite boundary resolution",
                "containment is by sampled winding numbers, not a theorem",
                "a failed screen is a boundary witness, not a proof of non-containment",
            ),
            source_references=(_REFERENCE,),
            verification=self.verification_report,
            details={
                "contained": self.contained,
                "fraction_inside": self.fraction_inside,
                "margin": self.margin,
                "witness_w": None if self.witness_w is None else list(self.witness_w),
                "witness_function": "extremal of the inner class",
            },
        )


def class_extremal_coefficients(
    class_key: str,
    order: int,
) -> tuple[sp.Expr, ...]:
    """Return exact ``[a2, ..., a_{order+1}]`` of the sharp member
    ``f_phi(z) = z exp(int (phi - 1)/t dt)``.

    With ``phi - 1 = sum B_k z^k``, ``f/z = exp(sum (B_k/k) z^k)`` and the
    exponential-of-series recurrence gives the exact rational coefficients.
    """

    if isinstance(order, bool) or not isinstance(order, int):
        raise TypeError("order must be a positive integer")
    if order < 1:
        raise InvalidInputError("order must be at least 1")
    if order > MAX_EXTREMAL_ORDER:
        raise ResourceLimitError(f"order must be at most {MAX_EXTREMAL_ORDER}")

    generator = _get_class(class_key)
    b = taylor_coefficients(generator, order=order)
    e: list[sp.Expr] = [sp.Integer(1)]
    for degree in range(1, order + 1):
        total = sp.Integer(0)
        for k in range(1, degree + 1):
            total += sp.Integer(k) * b[k - 1] / k * e[degree - k]
        e.append(sp.simplify(total / degree))
    return tuple(sp.Rational(e[degree]) for degree in range(1, order + 1))

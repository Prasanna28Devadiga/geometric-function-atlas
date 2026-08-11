"""Bounded exact Schur-parameter coefficient machinery.

The website's certificates express every member's Taylor coefficients through
the classical **factored** Schur parametrisation (``gft/dag.py`` convention):

    c1 = gamma0
    c2 = (1 - gamma0^2) * gamma1
    c3 = (1 - gamma0^2) * ((1 - gamma1^2) * gamma2 - gamma0 * gamma1^2)
    c4 = (1 - gamma0^2) * ((1 - gamma1^2) * (1 - gamma2^2) * gamma3
                           - (1 - gamma1^2) * gamma1 * gamma2^2
                           - 2 (1 - gamma1^2) * gamma0 * gamma1 * gamma2
                           + gamma0^2 * gamma1^3)

where ``w(z) = c1 z + c2 z^2 + ...`` is the Schwarz function and the member is
``f(z) = z * exp(int_0^z (phi(w(t)) - 1)/t dt)`` for the class generator phi.
With phi(z) = 1 + B1 z + B2 z^2 + ..., this yields exact Taylor coefficients
``a2..a_{order+1}`` of ``f``.

All parameters are real exact values (the certificate extremals are real), the
depth is bounded, and unsupported functionals fail closed.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Any

import sympy as sp

from .contracts import InvalidInputError, ResourceLimitError, UnsupportedError
from .exact import ExactExpressionError, parse_exact_expression

MAX_SCHUR_DEPTH = 5
MAX_COEFFICIENT_ORDER = 8

_FEKETE_SZEGO_PATTERN = re.compile(r"^fekete_szego_mu([0-9]+(?:\.[0-9]+)?)$", re.ASCII)
_GAMMA_PATTERN = re.compile(r"^[+-]?[0-9]+(?:/[0-9]+)?$", re.ASCII)

_STATIC_FUNCTIONALS = {
    "hankel2_2": ("Hankel H₂(2)", r"|a_2a_4-a_3^{2}|"),
    "inv_a3": ("Inverse coeff. |A₃|", r"|A_3|=|2a_2^{2}-a_3|"),
    "log_gamma2": ("Logarithmic γ₂", r"|\gamma_2|"),
    "zalcman_a2a3_a4": ("Gen. Zalcman (2,3)", r"|a_2a_3-a_4|"),
}


def _exact_gamma(value: Any, *, label: str) -> sp.Expr:
    """Parse one Schur parameter as an exact real value.

    Accepts ints, ``Fraction``-style exact strings (``0``, ``1``, ``-1/2``),
    and sympy Rational/Integer values. Floats and decimals are rejected so the
    extremal replay never silently coerces a binary64 approximation.
    """
    if isinstance(value, bool):
        raise InvalidInputError(f"{label} must be an exact rational, not a bool")
    if isinstance(value, int):
        parsed: sp.Expr = sp.Integer(value)
    elif isinstance(value, str):
        if _GAMMA_PATTERN.fullmatch(value) is None:
            raise InvalidInputError(
                f"{label} must be an exact integer or integer/integer string"
            )
        parsed = sp.Rational(value)
    elif isinstance(value, sp.Expr) and value.is_Rational:
        parsed = value
    else:
        raise InvalidInputError(
            f"{label} must be an exact rational; floats and decimals are rejected"
        )
    if parsed < -1 or parsed > 1:
        raise InvalidInputError(f"{label} must lie in the closed unit interval")
    return parsed


def schur_omega_coefficients(gammas: Sequence[Any]) -> list[sp.Expr]:
    """Exact Taylor coefficients ``[c1..cm]`` of the Schwarz function w(z).

    Uses the factored convention of the certificate engine. The parameters are
    real, each inside the closed unit interval, and the depth is bounded.
    """

    if len(gammas) > MAX_SCHUR_DEPTH:
        raise ResourceLimitError(
            f"Schur depth {len(gammas)} exceeds the bound {MAX_SCHUR_DEPTH}"
        )
    if len(gammas) < 1:
        raise InvalidInputError("at least one Schur parameter is required")
    gamma = [_exact_gamma(value, label=f"gamma[{index}]") for index, value in enumerate(gammas)]
    weight = [1 - gamma[index] ** 2 for index in range(len(gamma))]
    coefficients: list[sp.Expr] = [gamma[0]]
    if len(gamma) >= 2:
        coefficients.append(weight[0] * gamma[1])
    if len(gamma) >= 3:
        coefficients.append(
            weight[0] * (weight[1] * gamma[2] - gamma[0] * gamma[1] ** 2)
        )
    if len(gamma) >= 4:
        coefficients.append(
            weight[0]
            * (
                weight[1] * weight[2] * gamma[3]
                - weight[1] * gamma[1] * gamma[2] ** 2
                - 2 * weight[1] * gamma[0] * gamma[1] * gamma[2]
                + gamma[0] ** 2 * gamma[1] ** 3
            )
        )
    return [sp.simplify(value) for value in coefficients]


def _exact_phi_coefficient(value: Any, *, index: int) -> sp.Expr:
    """Parse one phi Taylor coefficient ``B_{index+1}`` as an exact value."""
    if isinstance(value, sp.Expr):
        return value
    if isinstance(value, str):
        try:
            return parse_exact_expression(value)
        except ExactExpressionError as exc:
            raise InvalidInputError(
                f"phi coefficient B{index + 1} is not a valid exact expression"
            ) from exc
    raise TypeError(f"phi coefficient B{index + 1} must be an expression or string")


def member_coefficients(
    phi_coefficients: Sequence[Any],
    gammas: Sequence[Any],
    *,
    order: int,
) -> list[sp.Expr]:
    """Exact Taylor coefficients ``[a2..a_{order+1}]`` of the class member.

    ``phi_coefficients`` are ``[B1, B2, ...]`` with
    ``phi(z) = 1 + B1 z + B2 z^2 + ...``. The member is reconstructed as
    ``f(z) = z exp(int (phi(w)-1)/z dz)`` with ``w`` built from the factored
    Schur parameters. Exact and bounded; malformed inputs fail closed.
    """

    if isinstance(order, bool) or not isinstance(order, int) or order < 1:
        raise InvalidInputError("order must be a positive integer")
    if order > MAX_COEFFICIENT_ORDER:
        raise ResourceLimitError(
            f"coefficient order {order} exceeds the bound {MAX_COEFFICIENT_ORDER}"
        )
    if len(gammas) > MAX_SCHUR_DEPTH:
        raise ResourceLimitError(
            f"Schur depth {len(gammas)} exceeds the bound {MAX_SCHUR_DEPTH}"
        )
    B = [
        _exact_phi_coefficient(value, index=index)
        for index, value in enumerate(phi_coefficients)
    ]
    if not B:
        raise InvalidInputError("at least one phi coefficient is required")
    if len(B) < order:
        # Missing higher-order generator coefficients are treated as zero:
        # the member is exact for the truncated polynomial generator.
        B = B + [sp.Integer(0)] * (order - len(B))

    omega = [sp.Integer(0)] + schur_omega_coefficients(gammas)
    omega += [sp.Integer(0)] * (order - len(omega) + 1)

    # q = sum_j B_j w^j truncated at z^order (phi(w) - 1 as a series)
    q: list[sp.Expr] = [sp.Integer(0)] * (order + 1)
    power = omega[:]
    for j in range(order):
        for k in range(order + 1):
            q[k] += power[k] * B[j]
        if j < order - 1:
            power = [
                sp.expand(sum(power[i] * omega[k - i] for i in range(k + 1)))
                for k in range(order + 1)
            ]

    # f/z = exp(sum q_k z^k / k)  ->  e_n = (1/n) sum_{k<=n} q_k e_{n-k}
    e: list[sp.Expr] = [sp.Integer(1)]
    for n in range(1, order + 1):
        e.append(sp.simplify(sum(q[k] * e[n - k] for k in range(1, n + 1)) / n))
    return e[1:]


def _fekete_szego_mu(functional_key: str) -> sp.Rational:
    match = _FEKETE_SZEGO_PATTERN.fullmatch(functional_key)
    if match is None:
        raise UnsupportedError(f"unsupported functional: {functional_key}")
    # sympy parses decimal strings such as "0.25" exactly
    value: sp.Rational = sp.Rational(match.group(1))
    return value


def functional_value(functional_key: str, coefficients: Sequence[sp.Expr]) -> sp.Expr:
    """Exact value of one supported coefficient functional.

    Supported families (the certificate corpus): Fekete–Szegő ``|a3 - mu a2^2|``,
    second Hankel ``|a2 a4 - a3^2|``, inverse ``|A3| = |2 a2^2 - a3|``,
    logarithmic ``|gamma_2| = |(a3 - a2^2/2)/2|``, and generalized Zalcman
    ``|a2 a3 - a4|``. Anything else fails closed as unsupported.
    """

    # Fail closed on the key before touching the coefficients, so an unknown
    # functional is never misreported as an input-shape problem.
    if _FEKETE_SZEGO_PATTERN.fullmatch(functional_key):
        minimum = 2  # a2, a3
    elif functional_key == "hankel2_2":
        minimum = 3  # a2, a3, a4
    elif functional_key == "inv_a3" or functional_key == "log_gamma2":
        minimum = 2  # a2, a3
    elif functional_key == "zalcman_a2a3_a4":
        minimum = 3  # a2, a3, a4
    else:
        raise UnsupportedError(f"unsupported functional: {functional_key}")
    if len(coefficients) < minimum:
        raise InvalidInputError(
            f"functional {functional_key} requires at least {minimum} "
            "coefficients (a2..a{})".format(minimum + 1)
        )
    a2, a3 = coefficients[0], coefficients[1]
    if _FEKETE_SZEGO_PATTERN.fullmatch(functional_key):
        mu = _fekete_szego_mu(functional_key)
        return sp.simplify(sp.Abs(sp.expand(a3 - mu * a2**2)))
    if functional_key == "hankel2_2":
        a4 = coefficients[2]
        return sp.simplify(sp.Abs(sp.expand(a2 * a4 - a3**2)))
    if functional_key == "inv_a3":
        return sp.simplify(sp.Abs(sp.expand(2 * a2**2 - a3)))
    if functional_key == "log_gamma2":
        # log(f(z)/z) = 2 (gamma_1 z + gamma_2 z^2 + ...)
        return sp.simplify(sp.Abs(sp.expand((a3 - a2**2 / 2) / 2)))
    a4 = coefficients[2]
    return sp.simplify(sp.Abs(sp.expand(a2 * a3 - a4)))


def functional_display(functional_key: str) -> tuple[str, str]:
    """Return ``(display_name, latex)`` for a functional key.

    Dynamic Fekete–Szegő keys are derived; the remaining supported families
    use the website's published labels.
    """

    if _FEKETE_SZEGO_PATTERN.fullmatch(functional_key):
        mu = _fekete_szego_mu(functional_key)
        return (f"Fekete–Szegő (μ={mu})", rf"|a_3-{sp.latex(mu)}\,a_2^{{2}}|")
    label = _STATIC_FUNCTIONALS.get(functional_key)
    if label is None:
        raise UnsupportedError(f"unsupported functional: {functional_key}")
    return label


def functional_family(functional_key: str) -> str:
    """Functional family key used by the proofs gallery facet."""
    if _FEKETE_SZEGO_PATTERN.fullmatch(functional_key):
        return "fekete_szego"
    if functional_key.startswith("hankel"):
        return "hankel"
    if functional_key.startswith("zalcman"):
        return "zalcman"
    if functional_key.startswith("log_"):
        return "logarithmic"
    if functional_key.startswith("inv_"):
        return "inverse"
    return "other"

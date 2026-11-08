"""Exact low-level coefficient transforms, without analytic bound promotion.

These functions return bare SymPy tuples, like taylor_coefficients. Real Schur
parameters, depth and order inherit schur.py's bounds. A finite tuple is a jet,
not a declaration that the analytic function or its inverse has zero tail.
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import sympy as sp

from .models import validate_exact_expression
from .schur import member_coefficients


def inverse_logarithmic_coefficients(coefficients: Sequence[Any]) -> tuple[sp.Expr, ...]:
    """Return Gamma1..Gamma4 of log(f^{-1}(w)/w)=2*sum Gamma_n*w^n.

    Input is the complete initial jet [a2,...], of length 1..4. Returns exact
    signed coefficients, not absolute values, global bounds or inverse-disk
    certification. Formal reversion only needs f'(0)=1; analytic inversion
    requires local analyticity, and the radius 1/4 additionally needs univalence
    in the unit disk. No formula strings or binary floats are evaluated.
    """
    values = _exact_jet(coefficients, maximum=4)
    a = values[0]
    result = [-a / 2]
    if len(values) >= 2:
        b = values[1]
        result.append(3*a**2/4-b/2)
    if len(values) >= 3:
        b, c = values[1:3]
        result.append(-5*a**3/3+2*a*b-c/2)
    if len(values) >= 4:
        b, c, d = values[1:4]
        result.append(35*a**4/8-15*a**2*b/2+5*a*c/2+5*b**2/4-d/2)
    return tuple(result)


def logarithmic_coefficients(coefficients: Sequence[Any]) -> tuple[sp.Expr, ...]:
    """Signed gamma1..gamma4 for log(f(z)/z)=2*sum gamma_n*z^n.

    Exact initial jet [a2,...] of length 1..4. Formal near-zero logarithm only;
    no global nonvanishing, bound, univalence or unknown-tail guarantee.
    """
    values = _exact_jet(coefficients, maximum=4)
    a = values[0]
    result = [a/2]
    if len(values) >= 2:
        result.append(values[1]/2-a**2/4)
    if len(values) >= 3:
        result.append(values[2]/2-a*values[1]/2+a**3/6)
    if len(values) >= 4:
        b, c, d = values[1:4]
        result.append(d/2-a*c/2+a**2*b/2-b**2/4-a**4/8)
    return tuple(result)


def inverse_coefficients(coefficients: Sequence[Any]) -> tuple[sp.Expr, ...]:
    """Formal inverse jet [A2,...,A5] from [a2,...,a5], length 1..4.

    Normalization f(0)=0, f'(0)=1 is assumed. The local inverse's unknown tail
    and domain are not certified; global univalence is not tested. These bounded
    reversion identities are independently checked by composition in both orders.
    """
    values = _exact_jet(coefficients, maximum=4)
    a = values[0]
    result = [-a]
    if len(values) >= 2:
        b = values[1]
        result.append(2*a**2-b)
    if len(values) >= 3:
        b, c = values[1:3]
        result.append(-5*a**3+5*a*b-c)
    if len(values) >= 4:
        b, c, d = values[1:4]
        result.append(14*a**4-21*a**2*b+6*a*c+3*b**2-d)
    return tuple(result)


def schippers_origin(coefficients: Sequence[Any]) -> tuple[sp.Expr, ...]:
    """Return sigma3(0), optionally sigma4(0), from a normalized initial jet.

    Supply exactly [a2,a3] or [a2,a3,a4]. Convention: sigma3 is the classical
    Schwarzian, sigma_(n+1)=sigma_n'-(n-1)*(f''/f')*sigma_n. Only origin
    values are returned, not a disk norm, higher operators or a univalence test.
    """
    values = _exact_jet(coefficients)
    if len(values) < 2:
        raise ValueError('supply 2..3 coefficients a2..a4')
    a, b = values[:2]
    result = [6*b-6*a**2]
    if len(values) == 3:
        result.append(24*values[2]-72*a*b+48*a**3)
    return tuple(result)


def _exact_jet(coefficients: Sequence[Any], *, maximum: int = 3) -> list[sp.Expr]:
    if not 1 <= len(coefficients) <= maximum:
        raise ValueError(f'supply 1..{maximum} coefficients a2..a{maximum+1}')
    values = []
    for value in coefficients:
        if isinstance(value, bool) or not isinstance(value, (int, sp.Expr)):
            raise TypeError('coefficients must be preconstructed exact expressions')
        value = sp.Integer(value) if isinstance(value, int) else value
        validate_exact_expression(value)
        values.append(value)
    return values


def linear_subordination_coefficients(
    phi_coefficients: Sequence[Any], gammas: Sequence[Any], *, alpha: Any, order: int,
) -> tuple[sp.Expr, ...]:
    """Jets for (1-alpha)f/z + alpha*f' = phi(omega), 0 <= alpha <= 1.

    alpha is an exact preconstructed rational. alpha=1 is bounded turning;
    alpha=0 is f/z subordination. Reuse the existing starlike recurrence and
    recover q=phi(omega)-1 via z*(f_star/z)' = q*(f_star/z), then divide q_n
    by 1+n*alpha. This avoids a second Schur/composition engine. Same bounds,
    real-rational Schur parameters and missing-B polynomial convention as the
    convex transform. No admissibility, global bounds or tail claims are made.
    """
    if isinstance(alpha, bool) or not isinstance(alpha, (int, sp.Rational)):
        raise TypeError('alpha must be a preconstructed exact rational')
    alpha = sp.Rational(alpha)
    if not 0 <= alpha <= 1:
        raise ValueError('alpha must lie in [0,1]')
    # Alexander scaling recovers the exact starlike jet, already validated.
    convex = convex_member_coefficients(phi_coefficients, gammas, order=order)
    e = [sp.Integer(1)] + [n*v for n, v in enumerate(convex, 2)]
    q = [sp.Integer(0)]
    for n in range(1, order + 1):
        q.append(sp.cancel(n*e[n] - sum(q[k]*e[n-k] for k in range(1, n))))
    return tuple(sp.cancel(q[n]/(1+n*alpha)) for n in range(1, order+1))


def product_subordination_coefficients(
    base_coefficients: Sequence[Any], phi_coefficients: Sequence[Any],
    gammas: Sequence[Any], *, order: int,
) -> tuple[sp.Expr, ...]:
    """Jet of f=g*phi(omega) from a normalized base jet g=z+b2*z²+... .

    Supply exactly order base coefficients b2..b_(order+1); missing base terms
    are unknown, not zero. Composition reuses the existing real Schur engine.
    No starlikeness/univalence of g or f is inferred from finite jets, and no
    unknown tail or global analytic class membership is certified.
    """
    composed = [sp.Integer(1)] + list(linear_subordination_coefficients(
        phi_coefficients, gammas, alpha=0, order=order,
    ))
    if len(base_coefficients) != order:
        raise ValueError('supply exactly order base coefficients')
    base = [sp.Integer(1)] + _exact_jet(base_coefficients, maximum=8)
    return tuple(sp.cancel(sum(base[k]*composed[n-k] for k in range(n+1)))
                 for n in range(1, order+1))


def mixed_derivative_coefficients(
    phi_coefficients: Sequence[Any], gammas: Sequence[Any], *, alpha: Any, order: int,
) -> tuple[sp.Expr, ...]:
    """Jet for (1-alpha)f' + alpha*(1+zf''/f') = phi(omega).

    Exact rational alpha in [0,1]. This nonlinear derivative interpolation is
    NOT linear_subordination_coefficients. Reuses its composed generator and
    solves the triangular formal equation for F=f'. Endpoint alpha=0 is bounded
    turning; alpha=1 is convex. Local formal jets do not establish continuation,
    nonvanishing of f' in the disk, admissibility or global class membership.
    Order/depth and polynomial-generator conventions inherit the Schur engine.
    """
    if isinstance(alpha, bool) or not isinstance(alpha, (int, sp.Rational)):
        raise TypeError('alpha must be a preconstructed exact rational')
    alpha = sp.Rational(alpha)
    if not 0 <= alpha <= 1:
        raise ValueError('alpha must lie in [0,1]')
    q = [sp.Integer(1)] + list(linear_subordination_coefficients(
        phi_coefficients, gammas, alpha=0, order=order,
    ))
    derivative = [sp.Integer(1)]
    for n in range(1, order+1):
        rhs = q[n] + sum(q[k]*derivative[n-k] for k in range(1, n))
        rhs -= (1-alpha)*sum(derivative[k]*derivative[n-k] for k in range(1, n))
        derivative.append(sp.cancel(rhs/(1+alpha*(n-1))))
    return tuple(sp.cancel(derivative[n]/(n+1)) for n in range(1, order+1))


def convex_member_coefficients(
    phi_coefficients: Sequence[Any], gammas: Sequence[Any], *, order: int,
) -> tuple[sp.Expr, ...]:
    """Return [a2,...] for 1+zf''/f'=phi(omega), normalized f(0)=0,f'(0)=1.

    Uses Alexander's identity: coefficients of zf' are n*a_n. This reuses the
    existing exact starlike recurrence, not a second coefficient engine.
    Missing generator coefficients inherit the polynomial-generator convention
    of member_coefficients; supply every B1..B_order for a general generator.
    Analytic admissibility of phi remains a caller assumption, not a proof.
    """
    if len(phi_coefficients) > 8:
        raise ValueError('supply at most eight generator coefficients')
    exact = []
    for value in phi_coefficients:
        if isinstance(value, bool) or not isinstance(value, (int, sp.Expr)):
            raise TypeError('generator coefficients must be preconstructed exact expressions')
        value = sp.Integer(value) if isinstance(value, int) else value
        validate_exact_expression(value)
        exact.append(value)
    star = member_coefficients(exact, gammas, order=order)
    return tuple(sp.cancel(value / n) for n, value in enumerate(star, 2))

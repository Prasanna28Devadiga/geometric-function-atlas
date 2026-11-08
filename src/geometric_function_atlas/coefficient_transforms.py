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
    """Return Gamma1..Gamma3 of log(f^{-1}(w)/w)=2*sum Gamma_n*w^n.

    Input is the complete initial jet [a2,...], of length 1..3. Returns exact
    signed coefficients, not absolute values, global bounds or inverse-disk
    certification. Formal reversion only needs f'(0)=1; analytic inversion
    requires local analyticity, and the radius 1/4 additionally needs univalence
    in the unit disk. No formula strings or binary floats are evaluated.
    """
    values = _exact_jet(coefficients)
    a = values[0]
    result = [-a / 2]
    if len(values) >= 2:
        b = values[1]
        result.append(3*a**2/4-b/2)
    if len(values) >= 3:
        b, c = values[1:3]
        result.append(-5*a**3/3+2*a*b-c/2)
    return tuple(result)


def logarithmic_coefficients(coefficients: Sequence[Any]) -> tuple[sp.Expr, ...]:
    """Signed gamma1..gamma3 for log(f(z)/z)=2*sum gamma_n*z^n.

    Exact initial jet [a2,...] of length 1..3. Formal near-zero logarithm only;
    no global nonvanishing, bound, univalence or unknown-tail guarantee.
    """
    values = _exact_jet(coefficients)
    a = values[0]
    result = [a/2]
    if len(values) >= 2:
        result.append(values[1]/2-a**2/4)
    if len(values) >= 3:
        result.append(values[2]/2-a*values[1]/2+a**3/6)
    return tuple(result)


def _exact_jet(coefficients: Sequence[Any]) -> list[sp.Expr]:
    if not 1 <= len(coefficients) <= 3:
        raise ValueError('supply 1..3 coefficients a2..a4')
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

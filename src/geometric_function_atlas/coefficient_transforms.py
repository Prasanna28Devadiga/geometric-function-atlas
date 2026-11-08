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
    if not 1 <= len(coefficients) <= 3:
        raise ValueError('supply 1..3 coefficients a2..a4')
    values = []
    for value in coefficients:
        if isinstance(value, bool) or not isinstance(value, (int, sp.Expr)):
            raise TypeError('coefficients must be preconstructed exact expressions')
        value = sp.Integer(value) if isinstance(value, int) else value
        validate_exact_expression(value)
        values.append(value)
    a = values[0]
    result = [-a / 2]
    if len(values) >= 2:
        b = values[1]
        result.append(3*a**2/4-b/2)
    if len(values) >= 3:
        b, c = values[1:3]
        result.append(-5*a**3/3+2*a*b-c/2)
    return tuple(result)


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

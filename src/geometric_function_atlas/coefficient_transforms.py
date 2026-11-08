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


def schwarzian_derivative_origin(coefficients: Sequence[Any]) -> sp.Expr:
    """Return S_f'(0) from exactly [a2,a3,a4] for f=z+a2*z²+....

    This is the ordinary derivative of the classical Schwarzian, not sigma4
    in Schippers' recurrence. Exact local algebra only: no disk norm, global
    univalence, tail declaration, or source-theorem certification.
    """
    values = _exact_jet(coefficients)
    if len(values) != 3:
        raise ValueError('supply exactly 3 coefficients a2..a4')
    a, b, c = values
    return 24*(c-2*a*b+a**3)


def ruscheweyh_coefficients(
    coefficients: Sequence[Any], *, degree: int, inverse: bool = False,
) -> tuple[sp.Expr, ...]:
    """Apply or undo D^degree on an exact normalized initial jet a2..a9.

    D^m multiplies a_n by binomial(m+n-1,n-1). Degree is an integer 0..64;
    inverse=True divides by that multiplier, not functional inversion. Input
    length is 1..8; no omitted tail is declared zero. Local coefficient algebra
    only: no univalence, analytic continuation or global class certification.
    """
    if isinstance(degree, bool) or not isinstance(degree, (int, sp.Integer)):
        raise TypeError('degree must be an exact integer')
    if not 0 <= degree <= 64:
        raise ValueError('degree must lie in 0..64')
    if not isinstance(inverse, bool):
        raise TypeError('inverse must be boolean')
    values = _exact_jet(coefficients, maximum=8)
    return tuple(sp.cancel(a/sp.binomial(degree+n-1, n-1) if inverse
                           else a*sp.binomial(degree+n-1, n-1))
                 for n, a in enumerate(values, 2))


def owa_fractional_coefficients(
    coefficients: Sequence[Any], *, rho: Any, inverse: bool = False,
) -> tuple[sp.Expr, ...]:
    """Apply/undo normalized Owa fractional multipliers to a2..a9.

    Omega^rho f=Gamma(2-rho)*z^rho*D^rho f multiplies a_n by
    Gamma(n+1)*Gamma(2-rho)/Gamma(n+1-rho). Exact rational 0<=rho<=1;
    rho=0 is identity and rho=1 is z*f'. The latter is the endpoint extension.
    A finite rational product avoids special-function numerical evaluation.
    Accepts 1..8 exact coefficients. Inverse divides multipliers, not functional
    reversion. No global analyticity, preservation, univalence or bound claim.
    """
    if isinstance(rho, bool) or not isinstance(rho, (int, sp.Rational)):
        raise TypeError('rho must be an exact rational')
    rho = sp.Rational(rho)
    if not 0 <= rho <= 1:
        raise ValueError('rho must lie in [0,1]')
    if not isinstance(inverse, bool):
        raise TypeError('inverse must be boolean')
    values = _exact_jet(coefficients, maximum=8)
    multiplier = sp.Integer(1)
    result = []
    for n, value in enumerate(values, 2):
        multiplier *= sp.Rational(n)/(n-rho)
        result.append(sp.cancel(value/multiplier if inverse else value*multiplier))
    return tuple(result)


def bernardi_coefficients(
    coefficients: Sequence[Any], *, gamma: Any, inverse: bool = False,
) -> tuple[sp.Expr, ...]:
    """Apply/undo I_gamma: a_n -> (gamma+1)*a_n/(gamma+n).

    For exact rational gamma>=0, I_gamma f=(gamma+1)*z**(-gamma)
    integral_0^z t**(gamma-1)*f(t) dt, defined equivalently by its normalized
    power series. Accepts exact jets a2..a9, length1..8. inverse=True solves
    z*F'+gamma*F=(gamma+1)*f coefficientwise; it is not functional inversion.
    No univalence, preservation theorem, unknown tail or global bound claim.
    """
    if isinstance(gamma, bool) or not isinstance(gamma, (int, sp.Rational)):
        raise TypeError('gamma must be an exact rational')
    gamma = sp.Rational(gamma)
    if gamma < 0:
        raise ValueError('gamma must be nonnegative')
    if not isinstance(inverse, bool):
        raise TypeError('inverse must be boolean')
    values = _exact_jet(coefficients, maximum=8)
    return tuple(sp.cancel(a*(gamma+n)/(gamma+1) if inverse
                           else a*(gamma+1)/(gamma+n))
                 for n, a in enumerate(values, 2))


def euler_differential_coefficients(
    coefficients: Sequence[Any], *, second: Any, first: Any, inverse: bool = False,
) -> tuple[sp.Expr, ...]:
    """Apply/undo jets of second*z²*f''+first*z*f'+(1-first)*f.

    Exact rational first and second; accepts a2..a9, length1..8. Normalization
    is preserved. Inverse divides nonzero multipliers, not functional inversion.
    Bare finite algebra, not analytic membership or preservation.
    """
    for parameter in (second, first):
        if isinstance(parameter, bool) or not isinstance(parameter, (int, sp.Rational)):
            raise TypeError('Euler parameters must be exact rationals')
    if not isinstance(inverse, bool):
        raise TypeError('inverse must be boolean')
    values = _exact_jet(coefficients, maximum=8)
    multipliers = [1+first*(n-1)+second*n*(n-1) for n in range(2, len(values)+2)]
    if inverse and any(multiplier == 0 for multiplier in multipliers):
        raise ValueError('cannot invert a zero Euler multiplier')
    return tuple(sp.cancel(value/multiplier if inverse else value*multiplier)
                 for value, multiplier in zip(values, multipliers, strict=True))


def _exact_q(q: Any) -> sp.Rational:
    if isinstance(q, bool) or not isinstance(q, (int, sp.Rational)):
        raise TypeError('q must be a preconstructed exact rational')
    q = sp.Rational(q)
    if not 0 < q <= 1:
        raise ValueError('q must lie in (0,1]; q=1 is the classical limit')
    return q


def q_al_oboudi_coefficients(
    coefficients: Sequence[Any], *, q: Any, lam: int, degree: int,
    inverse: bool = False,
) -> tuple[sp.Expr, ...]:
    """Apply/undo [1+(n-1)*lam]_q**degree on an exact a2..a9 jet.

    This is the multiplier definition of the q-Al-Oboudi operator, not
    (1+lam*([n]_q-1))**degree and not [n*lam]_q**degree. Integer lam1..64
    and degree0..64 only; exact rational0<q<=1 (q1 classical limit).
    lam1 gives the iterated Jackson Euler operator (z*D_q)**degree.
    inverse=True divides multipliers; no functional inverse, disk membership,
    global bound, unknown-tail or noninteger-lam convention is inferred.
    """
    q = _exact_q(q)
    if isinstance(lam, bool) or not isinstance(lam, (int, sp.Integer)):
        raise TypeError('lam must be an exact integer')
    if not 1 <= lam <= 64:
        raise ValueError('lam must lie in 1..64')
    # Share degree, inverse and exact-jet admission with the ordinary multiplier.
    ruscheweyh_coefficients(coefficients, degree=degree, inverse=inverse)
    values = _exact_jet(coefficients, maximum=8)
    result = []
    for n, value in enumerate(values, 2):
        power = 1+(n-1)*lam
        number = sp.Integer(power) if q == 1 else (1-q**power)/(1-q)
        multiplier = number**degree
        result.append(sp.cancel(value/multiplier if inverse else value*multiplier))
    return tuple(result)


def q_starlike_member_coefficients(
    phi_coefficients: Sequence[Any], gammas: Sequence[Any], *, q: Any, order: int,
) -> tuple[sp.Expr, ...]:
    """Formal normalized jet solving z*D_q f/f=phi(omega).

    D_q f=(f(z)-f(q*z))/((1-q)*z), with q=1 the ordinary derivative.
    Exact rational 0<q<=1; composition reuses the bounded real Schur engine
    (order<=8, depth<=5, missing B entries polynomial). This triangular formal
    solution does not prove disk analyticity, nonvanishing or global membership:
    its q-difference equation may introduce poles. No complex-Schur extension,
    arbitrary q-operator convention, global bound or tail certification.
    """
    q = _exact_q(q)
    composed = [sp.Integer(0)] + list(linear_subordination_coefficients(
        phi_coefficients, gammas, alpha=0, order=order,
    ))
    jet = [sp.Integer(1)]
    for n in range(1, order+1):
        denominator = sum(q**k for k in range(1, n+1))  # [n+1]_q - 1
        jet.append(sp.cancel(sum(composed[k]*jet[n-k] for k in range(1, n+1))
                             / denominator))
    return tuple(jet[1:])


def q_ruscheweyh_coefficients(
    coefficients: Sequence[Any], *, q: Any, degree: int, inverse: bool = False,
) -> tuple[sp.Expr, ...]:
    """Apply/undo integer q-Ruscheweyh multipliers [m+n-1]_q!/([m]_q![n-1]_q!).

    Exact rational 0<q<=1, integer degree 0..64 and exact a2..a9 jet (length
    1..8). q=1 is the classical limit. inverse=True undoes multipliers, NOT
    functional inversion. Noninteger q-gamma conventions are intentionally
    unsupported. No analytic continuation, univalence or unknown-tail claim.
    """
    q = _exact_q(q)
    # Reuse the ordinary transform's exact jet/degree/inverse validation.
    ruscheweyh_coefficients(coefficients, degree=degree, inverse=inverse)
    values = _exact_jet(coefficients, maximum=8)
    multiplier = sp.Integer(1)
    result = []
    for j, value in enumerate(values, 1):
        multiplier *= (sum(q**k for k in range(degree+j))
                       / sum(q**k for k in range(j)))
        result.append(sp.cancel(value/multiplier if inverse else value*multiplier))
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

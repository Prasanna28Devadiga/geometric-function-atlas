"""Jackson convex endpoint composition is not the ordinary Alexander identity."""

import sympy as s

from geometric_function_atlas import (
    q_al_oboudi_coefficients,
    q_starlike_member_coefficients,
    z,
)
from geometric_function_atlas.schur import schur_omega_coefficients


def test_jackson_convex_endpoint_rescales_generator():
    # For F=z*D_q h, D_q(zG)=G+q*z*D_q G. Hence the F generator
    # must be 1+q*(phi-1), NOT phi. A nonradial input avoids hidden identities.
    gammas = [0, s.Rational(1, 2), s.Rational(-1, 3)]
    coefficients = [s.Rational(1, 3), s.Rational(1, 5), s.Rational(1, 7)]
    for q in [s.Rational(1, 2), s.Rational(2, 3)]:
        transformed = q_starlike_member_coefficients(
            [q*b for b in coefficients], gammas, q=q, order=3
        )
        jet = q_al_oboudi_coefficients(
            transformed, q=q, lam=1, degree=1, inverse=True
        )
        f = z+sum(c*z**n for n, c in enumerate(jet, 2))
        dqf = s.cancel((f-f.subs(z, q*z))/((1-q)*z))
        d2qf = s.cancel((dqf-dqf.subs(z, q*z))/((1-q)*z))
        omega = sum(c*z**n for n, c in enumerate(
            schur_omega_coefficients(gammas, order=3), 1
        ))
        phi = 1+sum(c*omega**n for n, c in enumerate(coefficients, 1))
        residual = s.series(1+z*d2qf/dqf-phi, z, 0, 4).removeO()
        assert s.expand(residual) == 0
        wrong = q_al_oboudi_coefficients(
            q_starlike_member_coefficients(coefficients, gammas, q=q, order=3),
            q=q, lam=1, degree=1, inverse=True,
        )
        assert wrong != jet


def test_jackson_product_identity_generic_polynomial():
    q = s.Symbol('q')
    a0, a1, a2, a3 = s.symbols('a0 a1 a2 a3')
    polynomial = a0+a1*z+a2*z*z+a3*z**3
    direct = s.cancel((z*polynomial-q*z*polynomial.subs(z, q*z))/((1-q)*z))
    dq = s.cancel((polynomial-polynomial.subs(z, q*z))/((1-q)*z))
    assert s.expand(direct-polynomial-q*z*dq) == 0

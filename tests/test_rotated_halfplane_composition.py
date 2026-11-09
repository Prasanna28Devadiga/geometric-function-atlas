"""The low-level convex jet solver does not assume positive-real generators."""
from itertools import product

import sympy as sp

from geometric_function_atlas import convex_member_coefficients, z


def test_negative_and_complex_generator_against_whole_nonradial_equation():
    """Direct rational Schwarz substitution, not correlated radial coefficients."""
    omega = z*(sp.Rational(1, 2)-z/3)/(1-z/6)
    for C, gammas in product(
        [sp.Integer(1), sp.Integer(2), (1+sp.I)/2, (1-sp.I)/2],
        [[sp.Rational(1, 2), -sp.Rational(1, 3), 0, 0], [0, 1, 0, 0]],
    ):
        w = omega if gammas[0] else z*z
        jet = convex_member_coefficients([-C]*4, gammas, order=4)
        f = z+sum(value*z**n for n, value in enumerate(jet, 2))
        # phi(w)=1-C*w/(1-w), so z*f''*(1-w)+C*w*f'=0.
        # Multiplying the literal rational denominator yields independent
        # polynomial coefficients, without taking another coefficient-engine path.
        numerator = sp.fraction(sp.cancel(
            z*sp.diff(f, z, 2)*(1-w)+C*w*sp.diff(f, z)
        ))[0].expand()
        assert all(numerator.coeff(z, n) == 0 for n in range(5))
        wrong = sp.fraction(sp.cancel(
            z*sp.diff(f, z, 2)*(1-w)-C*w*sp.diff(f, z)
        ))[0].expand()
        assert any(wrong.coeff(z, n) != 0 for n in range(1, 5))

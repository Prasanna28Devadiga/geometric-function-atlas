"""Composition anchors for existing APIs, not new theorem certification."""
import sympy as sp

import geometric_function_atlas as gfa
from geometric_function_atlas.schur import member_coefficients


def test_composed_operator_direct_generic_polynomial():
    z = gfa.z
    coefficients = sp.symbols('a2:6')
    f = z + sum(c*z**n for n, c in enumerate(coefficients, 2))
    for degree in (0, 1, 2):
        direct = f
        for _ in range(degree):
            direct = sp.expand(z*sp.diff(direct, z))
        operated = gfa.q_al_oboudi_coefficients(coefficients, q=1, lam=1, degree=degree)
        for beta in (0, sp.Rational(1, 2), 1):
            expected = sp.expand((1-beta)*direct+beta*z*sp.diff(direct, z))
            got = gfa.euler_differential_coefficients(operated, second=0, first=beta)
            assert tuple(expected.coeff(z, n) for n in range(2, 6)) == got
            undo_euler = gfa.euler_differential_coefficients(got, second=0, first=beta, inverse=True)
            assert gfa.q_al_oboudi_coefficients(undo_euler, q=1, lam=1, degree=degree, inverse=True) == coefficients


def test_composed_subordination_with_nonradial_schwarz_function():
    z = gfa.z
    omega = z*(sp.Rational(1, 2)-z)/(1-z/2)
    target = 1+omega/2
    H = member_coefficients([sp.Rational(1, 2), sp.S.Zero, sp.S.Zero], [sp.Rational(1, 2), -1], order=3)
    for beta in (0, sp.Rational(1, 2), 1):
        F = gfa.euler_differential_coefficients(H, second=0, first=beta, inverse=True)
        for degree in (0, 1, 2):
            jet = gfa.q_al_oboudi_coefficients(F, q=1, lam=1, degree=degree, inverse=True)
            direct = z+sum(c*z**n for n, c in enumerate(jet, 2))
            for _ in range(degree):
                direct = sp.expand(z*sp.diff(direct, z))
            transformed = (1-beta)*direct+beta*z*sp.diff(direct, z)
            residual = z*sp.diff(transformed, z)/transformed-target
            assert sp.series(residual, z, 0, 4).removeO().expand() == 0

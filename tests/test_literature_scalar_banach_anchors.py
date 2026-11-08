"""Scalar controls for arXiv2610.13869/15497/33031, not Banach certification."""
import sympy as s

from geometric_function_atlas import convex_member_coefficients
from geometric_function_atlas.schur import member_coefficients


def test_robertson_order_eight_against_independent_closed_form():
    z = s.Symbol('z')
    for alpha in [s.Integer(0), s.Rational(1, 2), s.Rational(3, 4)]:
        beta = 2 * (1 - alpha)
        closed = z * (1 - z) ** (-beta)
        jet = member_coefficients([beta] * 8, [1], order=8)
        expected = tuple(s.diff(closed, z, n).subs(z, 0) / s.factorial(n)
                         for n in range(2, 10))
        assert tuple(jet) == expected
        convex = convex_member_coefficients([beta] * 8, [1], order=8)
        assert tuple(convex) == tuple(a / n for n, a in enumerate(expected, 2))


def test_rotated_symmetric_toeplitz_is_not_hermitian():
    jet = member_coefficients([s.Integer(2)] * 3, [1], order=3)
    a, b, c = (x * s.I ** n for n, x in enumerate(jet, 1))
    assert s.Abs(s.Matrix([[b, c], [c, b]]).det()) == 25
    assert s.Abs(s.Matrix([[a, b, c], [b, a, b], [c, b, a]]).det()) == 84
    assert s.Abs(s.Matrix([[b, c], [s.conjugate(c), b]]).det()) != 25


def test_nonradial_convex_primitive_hankel_and_zero_control():
    z = s.Symbol('z')
    # omega=z*(1/2-z)/(1-z/2), f'=1/(1-z+z^2); poles only on boundary.
    omega = z * (s.Rational(1, 2) - z) / (1 - z / 2)
    derivative = 1 / (1 - z + z * z)
    assert s.factor(1 + z * s.diff(derivative, z) / derivative
                    - (1 + omega) / (1 - omega)) == 0
    direct = s.integrate(s.series(derivative, z, 0, 8).removeO(), z)
    expected = tuple(direct.expand().coeff(z, n) for n in range(2, 10))
    jet = convex_member_coefficients([2] * 8, [s.Rational(1, 2), -1], order=8)
    assert tuple(jet) == expected
    a, b, c = jet[:3]
    assert (a, b, c) == (s.Rational(1, 2), 0, -s.Rational(1, 4))
    assert a * c - b * b == -s.Rational(1, 8)
    assert tuple(convex_member_coefficients([2, 2, 2], [0], order=3)) == (0, 0, 0)

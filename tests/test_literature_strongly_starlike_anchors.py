"""Independent defining-equation anchors for arXiv:2610.20849v1 scalar slices."""
import sympy as s

from geometric_function_atlas import logarithmic_coefficients
from geometric_function_atlas.schur import member_coefficients


def test_strongly_starlike_nonradial_equation_and_ordinary_log():
    z = s.Symbol('z')
    omega = z * (s.Rational(1, 2) - z) / (1 - z / 2)
    for alpha in [s.Rational(1, 4), s.Rational(2, 5), s.Integer(1)]:
        phi = ((1 + z) / (1 - z)) ** alpha
        B = [s.expand(s.series(phi, z, 0, 5).removeO()).coeff(z, k)
             for k in range(1, 5)]
        jet = member_coefficients(B, [s.Rational(1, 2), -1], order=4)
        # Direct whole rational Schwarz composition, independently of Schur recurrence.
        P = s.series(((1 + omega) / (1 - omega)) ** alpha, z, 0, 5).removeO()
        L = s.integrate(s.cancel((P - 1) / z), z)
        direct = s.series(z * s.exp(L), z, 0, 6).removeO().expand()
        assert tuple(jet) == tuple(direct.coeff(z, k) for k in range(2, 6))
        assert logarithmic_coefficients(jet) == tuple(L.expand().coeff(z, k) / 2
                                                     for k in range(1, 5))


def test_strongly_starlike_symmetric_and_asymmetric_source_witnesses():
    z, alpha = s.symbols('z alpha', positive=True)
    phi = ((1 + z) / (1 - z)) ** alpha
    coeff = s.series(phi, z, 0, 5).removeO().expand()
    for a in [s.Rational(1, 4), s.Rational(1, 2), s.Integer(1)]:
        B = [s.factor(coeff.coeff(z, k).subs(alpha, a)) for k in range(1, 5)]
        asymmetric = member_coefficients(B, [1], order=4)
        assert tuple(asymmetric) == (2*a, 3*a*a, 2*a*(1+17*a*a)/9,
                                     a*a*(7+38*a*a)/9)
        symmetric = member_coefficients(B, [0, 1], order=4)
        assert tuple(symmetric) == (0, a, 0, a*a)
        g1, g2, g3, _ = logarithmic_coefficients(symmetric)
        assert g1*g3-g2*g2 == -a*a/4

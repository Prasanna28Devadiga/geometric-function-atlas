"""Independent whole-function anchors, not literature theorem certifications."""
import sympy as s

from geometric_function_atlas import (
    Generator,
    generator_series,
    inverse_coefficients,
    z,
)
from geometric_function_atlas.schur import member_coefficients


def test_elastic_square_root_and_reciprocal_generators():
    p = (1 + z) / (1 - z)
    for alpha in [s.Integer(0), s.Integer(1), s.Rational(3, 2), s.Integer(2), -s.Integer(1)]:
        beta = alpha if alpha >= 1 else 1 - alpha
        w = (p + s.sqrt(p**2 + 4*beta*(beta-1))) / (2*beta)
        if alpha <= 0:
            w = 1/w
        B = generator_series(Generator(key='elastic-anchor', name='Elastic anchor', expression=w, citation='DOI10.1007/s13324-026-01235-1 Eq17/18'), order=3).coefficients
        jet = member_coefficients(B, [1], order=3)
        f = z + sum(a*z**n for n, a in enumerate(jet, 2))
        W = s.series(z*s.diff(f,z)/f, z, 0, 4).removeO()
        residual = s.series(alpha*W+(1-alpha)/W-p, z, 0, 4).removeO()
        assert s.expand(residual) == 0
        d = 2*alpha-1
        assert jet[0] == 2/d
        assert jet[1] == (3+4*alpha*(alpha-1)/d)/d**2


def test_genuine_biunivalent_mobius_inverse():
    for t in [s.Rational(1,4), s.Rational(1,2), -s.Rational(1,2), s.Integer(1)]:
        jet = member_coefficients([s.Integer(1)]*4, [t], order=4)
        assert tuple(jet) == tuple(t**n for n in range(1,5))
        inv = inverse_coefficients(jet)
        assert inv == tuple((-t)**n for n in range(1,5))
        f = z/(1-t*z)
        g = z/(1+t*z)
        assert s.cancel(f.subs(z,g)-z) == 0
        assert s.cancel(g.subs(z,f)-z) == 0


def test_exponential_characterization_nonradial_primitive():
    """DOI10.3389/fams.2026.1777576, KC sigma1, K=exp(z)."""
    omega = z*(s.Rational(1, 2)-z)/(1-z/2)
    f = z*s.exp(2*z)*(1-z/2)**3
    assert s.cancel(z*s.diff(f, z)/f-1-omega) == 0
    jet = member_coefficients([s.Integer(1)]+[s.Integer(0)]*4,
                              [s.Rational(1, 2), -1], order=5)
    direct = s.series(f, z, 0, 7).removeO().expand()
    assert tuple(jet) == tuple(direct.coeff(z, n) for n in range(2, 7))
    # The characterization uses exp(W-1), not W or exp(z*W).
    W = s.cancel(z*s.diff(f, z)/f)
    assert s.simplify(W-1-omega) == 0
    assert s.cancel(z*W-omega) != 0


def test_q_multiplicative_mobius_defining_expression():
    """DOI10.31926/but.mif.2026.6.68.1.8 Eq8,15,17."""
    t = s.Rational(1, 100)
    f = z/(1-t*z)
    jet = member_coefficients([s.Integer(1)]*3, [t], order=3)
    assert tuple(jet) == (t, t*t, t**3)
    for q in [s.Rational(1, 4), s.Rational(1, 2), s.Rational(3, 4)]:
        Dq = s.cancel((f-f.subs(z, q*z))/((1-q)*z))
        exponent = s.cancel(z*z*Dq/f)
        assert s.cancel(exponent-z/(1-q*t*z)) == 0
        L = (1-t*z)*s.exp(exponent)
        coeffs = generator_series(Generator(key='q-multiplicative-anchor',
            name='Fixed defining expression', expression=L,
            citation='DOI10.31926/but.mif.2026.6.68.1.8 Eq8'), order=2).coefficients
        assert tuple(coeffs) == (1-t, s.Rational(1, 2)+(q-1)*t)
        eta1, eta2 = coeffs
        literal17 = -(eta2-eta1**2)-eta1*(q+1)+q+s.Rational(1, 2)
        assert literal17 == jet[1]

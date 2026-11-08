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

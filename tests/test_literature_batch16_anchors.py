"""Independent defining-equation anchors; no global source theorem certification."""
import sympy as s

import geometric_function_atlas as atlas
from geometric_function_atlas.schur import member_coefficients


def test_scaled_exponential_nonradial_direct_primitive():
    z = atlas.z
    omega = z * (s.Rational(1, 3) + z) / (1 + z / 3)
    for alpha in [s.Rational(2, 5), s.Rational(2, 3), s.Integer(1)]:
        B = atlas.generator_series(atlas.Generator(key='scaled-exp', name='Scaled exponential', expression=s.exp(alpha * z), citation='arXiv:2610.36737v2 Eq3'), order=3).coefficients
        jet = member_coefficients(B, [s.Rational(1, 3), 1, 0], order=3)
        # Integrate the defining logarithmic derivative, independently of recurrence.
        rhs = s.series(s.exp(alpha * omega), z, 0, 4).removeO()
        primitive = sum(rhs.coeff(z, n) * z**n / n for n in range(1, 4))
        direct = s.series(s.exp(primitive), z, 0, 4).removeO()
        assert tuple(jet) == tuple(s.expand(direct).coeff(z, n) for n in range(1, 4))
        inv = atlas.inverse_coefficients(jet)
        f = z + sum(a * z**n for n, a in enumerate(jet, 2))
        g = z + sum(a * z**n for n, a in enumerate(inv, 2))
        assert s.series(f.subs(z, g), z, 0, 5).removeO().expand() == z


def test_completely_convex_mobius_two_point_and_atlas_anchor():
    z, x, t = s.symbols('z x t')
    f = z / (1 - t * z)
    kernel = 2 * z * s.diff(f, z) / (f - f.subs(z, x)) - (z + x) / (z - x)
    assert s.factor(kernel - (1 + t * z) / (1 - t * z)) == 0
    assert s.factor(s.limit(kernel, x, z) - (1 + z * s.diff(f, z, 2) / s.diff(f, z))) == 0
    for tv in [s.Rational(-1, 3), s.Rational(1, 2)]:
        B = atlas.generator_series(atlas.Generator(key='mobius', name='Mobius kernel', expression=(1 + tv * atlas.z) / (1 - tv * atlas.z), citation='arXiv:2607.09925v1 Example2.2'), order=4).coefficients
        jet = atlas.convex_member_coefficients(B, [1, 0, 0, 0], order=4)
        assert jet == tuple(tv**n for n in range(1, 5))

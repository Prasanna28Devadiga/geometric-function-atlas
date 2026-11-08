"""Independent convex primitive and generalized FS normalization anchors."""
import sympy as s

from geometric_function_atlas import convex_member_coefficients
from geometric_function_atlas.schur import member_coefficients


def test_nonradial_convex_primitive_attains_one_eighth():
    z = s.Symbol('z')
    derivative = 1 / (1 - z + z**2)
    omega = z * (s.Rational(1, 2) - z) / (1 - z/2)
    assert s.cancel(1 + z*s.diff(derivative, z)/derivative
                    - (1+omega)/(1-omega)) == 0
    jet = convex_member_coefficients([s.Integer(2)]*5,
                                    [s.Rational(1, 2), -1], order=5)
    direct = s.integrate(s.series(derivative, z, 0, 6).removeO(), z).expand()
    assert tuple(jet) == tuple(direct.coeff(z, k) for k in range(2, 7))
    a, b, c = jet[:3]
    assert (a, b, c) == (s.Rational(1, 2), 0, -s.Rational(1, 4))
    assert a*c-b*b == -s.Rational(1, 8)
    # Exact i-rotation remains symmetric, not Hermitian.
    rotated = [s.expand(v*s.I**k) for k, v in enumerate(jet, 1)]
    assert rotated[0]*rotated[2]-rotated[1]**2 == -s.Rational(1, 8)


def test_generalized_fs_uses_three_lambda_over_two_in_convex_identity():
    z, a, b, lam = s.symbols('z a b lam')
    F = z+a*z**2+b*z**3
    P = s.series(1+z*s.diff(F, z, 2)/s.diff(F, z), z, 0, 3).removeO().expand()
    b1, b2 = P.coeff(z, 1), P.coeff(z, 2)
    assert s.expand(b-lam*a*a-(b2-(3*lam/2-1)*b1*b1)/6) == 0
    assert s.expand(b-lam*a*a-(b2-(2*lam/3-1)*b1*b1)/6) == -5*lam*a*a/9
    for solve, expected in [(convex_member_coefficients, (1, 1)),
                            (member_coefficients, (2, 3))]:
        jet = solve([s.Integer(2)]*2, [1], order=2)
        assert tuple(jet) == expected
    convex = convex_member_coefficients([s.Integer(2)]*2, [1], order=2)
    assert abs(convex[1]-convex[0]**2) == 0
    assert abs(2-(s.Rational(2, 3)-1)*4)/6 == s.Rational(5, 9)

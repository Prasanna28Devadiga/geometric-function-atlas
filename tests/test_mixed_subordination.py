import pytest
import sympy as sp

import geometric_function_atlas as atlas


def test_mixed_derivative_direct_equation():
    z = atlas.z
    omega = z*(sp.Rational(1, 2)+z)/(1+z/2)
    for alpha in (0, sp.Rational(1, 2), 1):
        jet = atlas.mixed_derivative_coefficients([sp.Rational(5, 6), 0, 0, 0, sp.Rational(1, 6)], [sp.Rational(1, 2), 1], alpha=alpha, order=4)
        f = z+sum(v*z**n for n, v in enumerate(jet, 2))
        residual = (1-alpha)*sp.diff(f, z)+alpha*(1+z*sp.diff(f, z, 2)/sp.diff(f, z))-(1+5*omega/6+omega**5/6)
        assert sp.series(residual, z, 0, 5).removeO().expand() == 0
        if alpha == 0:
            assert jet == atlas.linear_subordination_coefficients([sp.Rational(5, 6)], [sp.Rational(1, 2), 1], alpha=1, order=4)
        if alpha == 1:
            assert jet == atlas.convex_member_coefficients([sp.Rational(5, 6)], [sp.Rational(1, 2), 1], order=4)


@pytest.mark.parametrize('alpha', [True, 0.5, '1/2', -1, 2])
def test_mixed_rejects_invalid_alpha(alpha):
    with pytest.raises((TypeError, ValueError)):
        atlas.mixed_derivative_coefficients([1], [1], alpha=alpha, order=3)

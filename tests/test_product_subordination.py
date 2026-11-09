import pytest
import sympy as sp

import geometric_function_atlas as atlas


def test_product_subordination_direct_koebe():
    z = atlas.z
    omega = z*(sp.Rational(1, 2)+z)/(1+z/2)
    jet = atlas.product_subordination_coefficients([2, 3, 4, 5], [1, 0, -sp.Rational(1, 6)], [sp.Rational(1, 2), 1], order=4)
    expected = sp.series((1+sp.sin(omega))/(1-z)**2, z, 0, 5).removeO().expand()
    assert jet == tuple(expected.coeff(z, n) for n in range(1, 5))


@pytest.mark.parametrize('base', [[1], [1, 2.0], [1, '2'], [1, True]])
def test_product_refuses_unknown_or_inexact_base(base):
    with pytest.raises((TypeError, ValueError)):
        atlas.product_subordination_coefficients(base, [1], [1], order=2)

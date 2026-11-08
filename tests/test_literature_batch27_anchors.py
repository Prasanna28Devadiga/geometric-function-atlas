"""Independent whole-function anchors for existing bounded tuple APIs.

No general harmonic-class or Schwarzian-norm optimizer is introduced.
"""
import pytest
import sympy as sp

import geometric_function_atlas as atlas


@pytest.mark.parametrize('alpha', [sp.Rational(1, 2), 1, sp.Rational(4, 3), sp.Rational(3, 2), sp.Rational(7, 4)])
@pytest.mark.parametrize('power', [1, 2])
def test_convex_jets_against_binomial_derivative_and_schwarzian(alpha, power):
    z = atlas.z
    alpha = sp.sympify(alpha)
    derivative = (1 - z**power)**(-alpha / power)
    jet = atlas.convex_member_coefficients([alpha] * 7, [1] if power == 1 else [0, 1], order=7)
    polynomial = z + sum(c * z**n for n, c in enumerate(jet, 2))
    assert sp.series(sp.diff(polynomial, z) - derivative, z, 0, 8).removeO() == 0
    pre = sp.cancel(sp.diff(derivative, z) / derivative)
    schwarzian = sp.cancel(sp.diff(pre, z) - pre**2 / 2)
    actual = atlas.schippers_origin(jet[:2])[0]
    assert actual == schwarzian.subs(z, 0)
    expected = alpha * (2 - alpha) / 2 if power == 1 else alpha
    assert actual == expected
    # Changing omega=z² into omega=z is not a harmless correlated control.
    assert alpha != alpha * (2 - alpha) / 2


@pytest.mark.parametrize('k', [0, sp.Rational(1, 4), sp.Rational(1, 2), sp.Rational(3, 4)])
def test_halfplane_shear_analytic_jets_against_independent_rational_ode(k):
    z = atlas.z
    derivative = 1 / ((1 - z)**2 * (1 - k*z))
    data = atlas.generator_series(atlas.Generator(
        key='shear-derivative-anchor', name='Rational derivative anchor',
        expression=derivative, citation='arXiv:2505.17157v1 Eq2.4'), order=7)
    jet = atlas.linear_subordination_coefficients(data.coefficients, [1], alpha=1, order=7)
    polynomial = z + sum(c*z**n for n, c in enumerate(jet, 2))
    # Clear denominators before comparing arbitrary low coefficients.
    residual = sp.expand(sp.diff(polynomial, z)*(1-z)**2*(1-k*z) - 1)
    assert all(residual.coeff(z, n) == 0 for n in range(8))
    coanalytic_derivative = -k*z*derivative
    assert sp.cancel(derivative + coanalytic_derivative - 1/(1-z)**2) == 0
    lam = (3 + 4*sp.I)/5
    rotated = sp.conjugate(lam)*polynomial.subs(z, lam*z)
    assert sp.simplify(sp.diff(rotated, z).subs(z, 0) - 1) == 0
    assert sp.simplify(sp.diff(rotated, z, 3).subs(z, 0)/6 - lam**2*jet[1]) == 0

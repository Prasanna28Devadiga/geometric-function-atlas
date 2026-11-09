"""Bounded normalized Hadamard jets; no convolution-duality theorem claim."""
import pytest
import sympy as sp

import geometric_function_atlas as atlas


def test_hadamard_is_coefficientwise_not_ordinary_product():
    assert hasattr(atlas, 'hadamard_coefficients'), 'missing normalized Hadamard jet API'
    got = atlas.hadamard_coefficients([2, 3, 4], [2, 3, 4])
    assert got == (4, 9, 16)
    assert got != (4, 10, 20)  # ordinary product of origin-one factors


def test_independent_symbolic_coefficients_and_commutativity():
    a, b, c, d = sp.symbols('a b c d')
    assert atlas.hadamard_coefficients([a, b], [c, d]) == (a*c, b*d)
    assert atlas.hadamard_coefficients([c, d], [a, b]) == (a*c, b*d)


def test_rational_whole_function_anchor_and_identity_kernel():
    t = sp.Rational(1, 3)
    jet = atlas.class_extremal_coefficients('starlike', order=8)
    got = atlas.hadamard_coefficients(jet, [t**n for n in range(1, 9)])
    # k*g_t=k(t*z)/t=z/(1-t*z)^2, globally analytic in the unit disk.
    assert got == tuple((n+1)*t**n for n in range(1, 9))
    assert atlas.hadamard_coefficients(jet, [1]*8) == jet


@pytest.mark.parametrize('left,right', [([], []), ([1], [1, 2]), ([1]*9, [1]*9)])
def test_unknown_or_overlong_jet_rejected(left, right):
    with pytest.raises(ValueError):
        atlas.hadamard_coefficients(left, right)


@pytest.mark.parametrize('bad', [True, 0.5, '1/2', sp.Float('0.5'), sp.oo, sp.nan])
def test_inexact_or_nonfinite_coefficients_rejected(bad):
    with pytest.raises((ValueError, TypeError)):
        atlas.hadamard_coefficients([bad], [1])
    with pytest.raises((ValueError, TypeError)):
        atlas.hadamard_coefficients([1], [bad])

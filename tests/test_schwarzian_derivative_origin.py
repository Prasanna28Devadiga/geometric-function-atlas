"""Independent differential anchors, not disk-norm certification."""
import pytest
import sympy as sp

import geometric_function_atlas as atlas


def test_generic_derivative_not_next_schippers_invariant():
    z = sp.Symbol('z')
    a, b, c = sp.symbols('a b c')
    f = z+a*z**2+b*z**3+c*z**4
    P = sp.diff(f,z,2)/sp.diff(f,z)
    expected = sp.diff(sp.diff(P,z)-P**2/2,z).subs(z,0)
    actual = atlas.schwarzian_derivative_origin([a,b,c])
    assert sp.expand(actual-expected) == 0
    s3,s4 = atlas.schippers_origin([a,b,c])
    assert sp.expand(actual-s4-4*a*s3) == 0
    assert atlas.schwarzian_derivative_origin([2,3,4]) == 0
    assert s4 != actual


@pytest.mark.parametrize('jet', [[], [1], [1,2], [1,2,3,4]])
def test_complete_three_coefficient_jet_required(jet):
    with pytest.raises(ValueError):
        atlas.schwarzian_derivative_origin(jet)


@pytest.mark.parametrize('bad', ['1/2', 0.5, True, sp.oo, sp.nan])
def test_inexact_or_nonfinite_entries_rejected(bad):
    with pytest.raises((TypeError, ValueError)):
        atlas.schwarzian_derivative_origin([0,0,bad])


def test_mobius_and_cubic_anchors():
    assert atlas.schwarzian_derivative_origin([1,1,1]) == 0
    assert atlas.schwarzian_derivative_origin([0,0,sp.Rational(1,2)]) == 12

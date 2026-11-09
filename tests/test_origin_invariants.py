"""Independent formal-composition and differential anchors, not global bounds."""
import pytest
import sympy as sp

import geometric_function_atlas as atlas


def test_inverse_coefficients_composition_both_directions():
    assert hasattr(atlas, 'inverse_coefficients'), 'bounded inverse jet missing'
    a, b, c, d, w = sp.symbols('a b c d w')
    jet = atlas.inverse_coefficients([a, b, c, d])
    f = w + a*w**2 + b*w**3 + c*w**4 + d*w**5
    g = w + sum(v*w**n for n, v in enumerate(jet, 2))
    # Polynomial truncation avoids expensive nested symbolic series.
    for composition in (f.subs(w, g), g.subs(w, f)):
        residual = sp.Poly(composition, w)
        assert [sp.expand(residual.nth(n)) for n in range(6)] == [0, 1, 0, 0, 0, 0]
    assert atlas.inverse_coefficients([2, 3, 4, 5]) == (-2, 5, -14, 42)
    assert atlas.inverse_coefficients([1, 1, 1, 1]) == (-1, 1, -1, 1)
    for n in range(1, 5):
        assert atlas.inverse_coefficients([a,b,c,d][:n]) == jet[:n]


def test_schippers_origin_independent_differential_recurrence():
    assert hasattr(atlas, 'schippers_origin'), 'origin differential invariants missing'
    a, b, c, w = sp.symbols('a b c w')
    f = w+a*w**2+b*w**3+c*w**4
    pre = sp.diff(f,w,2)/sp.diff(f,w)
    s3 = sp.diff(pre,w)-pre**2/2
    s4 = sp.diff(s3,w)-2*pre*s3
    expected = tuple(sp.expand(v.subs(w,0)) for v in (s3,s4))
    assert atlas.schippers_origin([a,b,c]) == expected
    assert atlas.schippers_origin([a,b]) == expected[:1]
    assert atlas.schippers_origin([1,1,1]) == (0,0)
    assert atlas.schippers_origin([2,3,4]) == (-6,48)


@pytest.mark.parametrize('bad', [[], [1]*5, [True], ['1/2'], [0.1], [sp.oo], [sp.nan]])
def test_inverse_rejects_invalid_jets(bad):
    assert hasattr(atlas, 'inverse_coefficients')
    with pytest.raises((TypeError, ValueError)):
        atlas.inverse_coefficients(bad)


@pytest.mark.parametrize('bad', [[], [1], [1]*4, [1,True], [1,'1/2'], [1,sp.Float('0.2')], [1,sp.oo]])
def test_schippers_rejects_invalid_jets(bad):
    assert hasattr(atlas, 'schippers_origin')
    with pytest.raises((TypeError, ValueError)):
        atlas.schippers_origin(bad)

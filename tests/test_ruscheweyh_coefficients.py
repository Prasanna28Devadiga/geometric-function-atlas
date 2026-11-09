"""Independent derivative anchors for bounded Ruscheweyh jets."""
import pytest
import sympy as s

import geometric_function_atlas as atlas


def test_ruscheweyh_derivative_definition_and_inverse():
    z=s.Symbol('z')
    jet=[s.Rational(2,3),-2,s.I,s.sqrt(2)]
    f=z+sum(a*z**n for n,a in enumerate(jet,2))
    for degree in [0,1,2,4]:
        actual=atlas.ruscheweyh_coefficients(jet,degree=degree)
        # D^m f = z/m! * (z^(m-1) f)^(m) for m>=1.
        exact=f if degree==0 else z*s.diff(z**(degree-1)*f,z,degree)/s.factorial(degree)
        expected=tuple(s.expand(exact).coeff(z,n) for n in range(2,6))
        assert actual==expected
        assert atlas.ruscheweyh_coefficients(actual,degree=degree,inverse=True)==tuple(jet)


def test_ruscheweyh_geometric_anchor_and_bounded_edges():
    # D^m(z/(1-z))=z/(1-z)^(m+1).
    for m in [0,s.Integer(1),4,64]:
        expected=tuple(s.rf(m+1,k)/s.factorial(k) for k in range(1,9))
        assert atlas.ruscheweyh_coefficients([1]*8,degree=m)==expected
        assert atlas.ruscheweyh_coefficients(expected,degree=m,inverse=True)==(1,)*8


@pytest.mark.parametrize('degree',[-1,65])
def test_ruscheweyh_degree_bounds(degree):
    with pytest.raises(ValueError):
        atlas.ruscheweyh_coefficients([1],degree=degree)


@pytest.mark.parametrize('degree',[True,'1',1.0,s.Rational(1,2)])
def test_ruscheweyh_degree_exact_integer(degree):
    with pytest.raises(TypeError):
        atlas.ruscheweyh_coefficients([1],degree=degree)


@pytest.mark.parametrize('jet',[[],[1]*9,[True],['1'],[s.Float(1)],[s.oo],[s.nan]])
def test_ruscheweyh_exact_complete_jet(jet):
    with pytest.raises((ValueError,TypeError)):
        atlas.ruscheweyh_coefficients(jet,degree=1)


def test_ruscheweyh_inverse_is_boolean_not_truthiness():
    with pytest.raises(TypeError):
        atlas.ruscheweyh_coefficients([1],degree=1,inverse=1)

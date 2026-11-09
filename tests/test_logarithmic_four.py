"""Fourth logarithms: independent formal-series/composition anchors."""
import pytest
import sympy as sp

import geometric_function_atlas as gfa


def test_fourth_ordinary_log_independent_series():
    a,b,c,d,z = sp.symbols('a b c d z')
    exact = gfa.logarithmic_coefficients([a,b,c,d])
    native = sp.series(sp.log(1+a*z+b*z**2+c*z**3+d*z**4)/2,z,0,5).removeO().expand()
    assert len(exact)==4
    assert all(sp.expand(exact[n-1]-native.coeff(z,n))==0 for n in range(1,5))
    assert gfa.logarithmic_coefficients([2,3,4,5]) == (1,sp.Rational(1,2),sp.Rational(1,3),sp.Rational(1,4))


def test_fourth_inverse_log_independent_composition():
    a,b,c,d,w=sp.symbols('a b c d w')
    # Recover reversion recursively without the package inverse transform.
    f=w+a*w**2+b*w**3+c*w**4+d*w**5
    inverse=w
    for n in range(2,6):
        residual=sp.series(f.subs(w,inverse),w,0,n+1).removeO().expand().coeff(w,n)
        inverse=sp.expand(inverse-residual*w**n)
    assert sp.series(f.subs(w,inverse),w,0,6).removeO().expand()==w
    native=sp.series(sp.log(inverse/w)/2,w,0,5).removeO().expand()
    exact=gfa.inverse_logarithmic_coefficients([a,b,c,d])
    assert len(exact)==4
    assert all(sp.expand(exact[n-1]-native.coeff(w,n))==0 for n in range(1,5))
    assert gfa.inverse_logarithmic_coefficients([1,1,1,1]) == (-sp.Rational(1,2),sp.Rational(1,4),-sp.Rational(1,6),sp.Rational(1,8))
    assert gfa.inverse_logarithmic_coefficients([0,-sp.Rational(1,4),0,sp.Rational(1,24)]) == (0,sp.Rational(1,8),0,sp.Rational(11,192))


@pytest.mark.parametrize('transform',[gfa.logarithmic_coefficients,gfa.inverse_logarithmic_coefficients])
@pytest.mark.parametrize('bad',[True,sp.oo,sp.nan,sp.Float('0.5'),'1/2'])
def test_fourth_entry_exactness_guard(transform,bad):
    with pytest.raises((TypeError,ValueError)):
        transform([1,2,3,bad])


def test_schippers_length_boundary_unchanged():
    with pytest.raises(ValueError):
        gfa.schippers_origin([1,2,3,4])

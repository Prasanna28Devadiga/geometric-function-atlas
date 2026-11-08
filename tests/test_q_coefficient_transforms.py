"""Independent Jackson defining-equation and multiplier controls."""
import pytest
import sympy as s

from geometric_function_atlas import (
    linear_subordination_coefficients,
    q_ruscheweyh_coefficients,
    q_starlike_member_coefficients,
    ruscheweyh_coefficients,
)
from geometric_function_atlas.schur import member_coefficients


def test_jackson_defining_equation_and_classical_limit():
    z=s.Symbol('z')
    B=[s.Rational(3,4),s.Rational(-1,8),s.Rational(1,16),s.Integer(0)]
    for q in [s.Rational(1,2),s.Rational(3,4),1]:
        a=q_starlike_member_coefficients(B,[s.Rational(1,3),s.Rational(-1,2),1],q=q,order=4)
        f=z+sum(v*z**n for n,v in enumerate(a,2))
        derivative=s.diff(f,z) if q==1 else (f-f.subs(z,q*z))/((1-q)*z)
        observed=s.series(z*derivative/f,z,0,5).removeO().expand()
        composed=linear_subordination_coefficients(B,[s.Rational(1,3),s.Rational(-1,2),1],alpha=0,order=4)
        assert s.expand(observed-1-sum(v*z**n for n,v in enumerate(composed,1)))==0
    assert a==tuple(member_coefficients(B,[s.Rational(1,3),s.Rational(-1,2),1],order=4))


def test_q_multipliers_independent_products_and_roundtrip():
    jet=[1,s.sqrt(2),s.I,0,1,2,3,4]
    for q in [s.Rational(1,2),s.Rational(3,4),1]:
        for m in [0,1,4]:
            a=q_ruscheweyh_coefficients(jet,q=q,degree=m)
            for n,(v,c) in enumerate(zip(jet,a),2):
                multiplier=s.prod(sum(q**k for k in range(m+j))/sum(q**k for k in range(j)) for j in range(1,n))
                assert s.cancel(c-v*multiplier)==0
            assert q_ruscheweyh_coefficients(a,q=q,degree=m,inverse=True)==tuple(jet)
            if q==1: assert a==ruscheweyh_coefficients(jet,degree=m)
    assert q_ruscheweyh_coefficients([1],q=s.Rational(1,2),degree=64)==(2-s.Rational(1,2)**64,)
    assert q_ruscheweyh_coefficients([1,1,1],q=s.Rational(1,2),degree=1)==(s.Rational(3,2),s.Rational(7,4),s.Rational(15,8))


@pytest.mark.parametrize('q',[0,-1,2,True,0.5,'1/2',s.Symbol('q'),s.oo])
def test_reject_q(q):
    with pytest.raises((TypeError,ValueError)):
        q_starlike_member_coefficients([1],[1],q=q,order=1)
    with pytest.raises((TypeError,ValueError)):
        q_ruscheweyh_coefficients([1],q=q,degree=0)


def test_validation_and_bounds_inherited():
    for degree in [-1,65,True,s.Rational(1,2),'1']:
        with pytest.raises((TypeError,ValueError)):
            q_ruscheweyh_coefficients([1],q=1,degree=degree)
    for jet in [[],[1]*9,[0.1],['1'],[True],[s.oo]]:
        with pytest.raises((TypeError,ValueError)):
            q_ruscheweyh_coefficients(jet,q=1,degree=0)
    with pytest.raises(TypeError): q_ruscheweyh_coefficients([1],q=1,degree=0,inverse=1)
    for kwargs in [{'order':0},{'order':9},{'order':True}]:
        with pytest.raises((TypeError,ValueError)):
            q_starlike_member_coefficients([1],[1],q=1,**kwargs)
    with pytest.raises((TypeError,ValueError)):
        q_starlike_member_coefficients([1],[s.I],q=1,order=1)

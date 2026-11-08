"""Normalized fractional Owa multiplier, not fractional function inversion."""
import pytest
import sympy as s

import geometric_function_atlas as a


def test_public_fractional_owa_and_independent_half_order_integral():
    assert hasattr(a, 'owa_fractional_coefficients')
    u=s.Symbol('u')
    for n in range(2,10):
        # t=z-v² removes the half-order Abel kernel before differentiating.
        expected=(s.Rational(2*n+1,2)*s.integrate((1-u*u)**n,(u,0,1)))
        jet=[s.Integer(0)]*(n-2)+[s.Integer(1)]
        assert a.owa_fractional_coefficients(jet,rho=s.Rational(1,2))[-1]==expected
    assert a.owa_fractional_coefficients([1,1,1],rho=s.Rational(1,2))==(s.Rational(4,3),s.Rational(8,5),s.Rational(64,35))


def test_endpoints_independent_euler_and_roundtrip():
    x=s.Symbol('x');jet=[x,s.sqrt(2),s.I,0,1,2,3,4]
    for rho in [0,s.Rational(1,7),s.Rational(1,2),s.Rational(9,10),1]:
        image=a.owa_fractional_coefficients(jet,rho=rho)
        assert a.owa_fractional_coefficients(image,rho=rho,inverse=True)==tuple(jet)
    assert a.owa_fractional_coefficients(jet,rho=0)==tuple(jet)
    assert a.owa_fractional_coefficients(jet,rho=1)==a.euler_differential_coefficients(jet,first=1,second=0)


@pytest.mark.parametrize('rho',[True,0.5,'1/2',s.sqrt(2),s.oo,-1,s.Rational(11,10)])
def test_reject_fractional_order(rho):
    with pytest.raises((TypeError,ValueError)):
        a.owa_fractional_coefficients([1],rho=rho)


@pytest.mark.parametrize('jet',[[],[1]*9,[True],[0.5],['1/2'],[s.oo]])
def test_reject_jet(jet):
    with pytest.raises((TypeError,ValueError)):
        a.owa_fractional_coefficients(jet,rho=0)


def test_reject_nonboolean_inverse():
    with pytest.raises(TypeError):
        a.owa_fractional_coefficients([0],rho=0,inverse=1)

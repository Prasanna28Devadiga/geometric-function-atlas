"""Independent whole-polynomial anchors, not source theorem certifications."""
import sympy as s

from geometric_function_atlas import (
    linear_subordination_coefficients,
    q_al_oboudi_coefficients,
    z,
)


def test_derivative_endpoint_against_independent_polynomial_integral():
    u=s.Symbol('u')
    cs=s.symbols('c1:9')
    whole=s.integrate(1+sum(c*u**n for n,c in enumerate(cs,1)),(u,0,z))
    jet=linear_subordination_coefficients(cs,[1],alpha=1,order=8)
    assert s.expand(whole-z-sum(c*z**n for n,c in enumerate(jet,2)))==0
    for k in range(1,5):
        d=s.Rational(k-1,k+1)
        radial=s.hyperexpand(s.hyper([-1,k-1],[k+1],z*z))
        actual=linear_subordination_coefficients([0,-3*d],[1],alpha=1,order=2)
        assert s.expand(z*radial-z-actual[0]*z*z-actual[1]*z**3)==0


def test_jackson_laurent_normalization_requires_pole_product_factor():
    cs=s.symbols('c2:7')
    H=z+sum(c*z**n for n,c in enumerate(cs,2))
    f=H/z**2
    for q in [s.Rational(1,2),s.Rational(2,3),s.Rational(3,4)]:
        jet=q_al_oboudi_coefficients(cs,q=q,lam=1,degree=1)
        zDH=z+sum(c*z**n for n,c in enumerate(jet,2))
        reconstructed=(zDH/z)/z**2+H.subs(z,q*z)*(z**-2-(q*z)**-2)/((1-q)*z)
        direct=(f-f.subs(z,q*z))/((1-q)*z)
        assert s.cancel(reconstructed-direct)==0
        naive=zDH/z**3
        assert s.cancel(naive-direct)!=0

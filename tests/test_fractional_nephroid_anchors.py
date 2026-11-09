"""Independent bounded fractional and nephroid anchors, not source bounds."""
import sympy as s

import geometric_function_atlas as a
from geometric_function_atlas.schur import member_coefficients


def test_third_order_abel_kernel_and_generic_owa_jet():
    u=s.Symbol('u')
    values=s.symbols('a2:10')
    image=a.owa_fractional_coefficients(values,rho=s.Rational(2,3))
    for n,value in enumerate(values,2):
        # t=z*(1-u³) cancels the u^-2 kernel before differentiating.
        expected=(n+s.Rational(1,3))*s.integrate((1-u**3)**n,(u,0,1))
        assert s.cancel(image[n-2]-expected*value)==0
    assert a.owa_fractional_coefficients(image,rho=s.Rational(2,3),inverse=True)==values


def test_nephroid_nonradial_whole_equations_and_complex_rotations():
    z=a.z
    for t in [s.Rational(1,2),s.Integer(1),s.I,-s.I]:
        B=[s.Integer(0),t,s.Integer(0),s.Integer(0),s.Integer(0),-t**3/3]
        jets=member_coefficients(B,[1],order=6)
        whole=z*s.exp(t*z*z/2-t**3*z**6/18)
        assert s.cancel(z*s.diff(whole,z)/whole-1-t*z*z+t**3*z**6/3)==0
        direct=s.series(whole,z,0,8).removeO().expand()
        assert jets==[direct.coeff(z,n) for n in range(2,8)]
        bounded=a.linear_subordination_coefficients(B,[1],alpha=1,order=6)
        primitive=z+t*z**3/3-t**3*z**7/21
        assert s.expand(s.diff(primitive,z)-1-t*z*z+t**3*z**6/3)==0
        assert bounded==tuple(primitive.coeff(z,n) for n in range(2,8))

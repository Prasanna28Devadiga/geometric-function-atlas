"""Independent whole-function anchors; no source theorem certification."""
import sympy as sp

import geometric_function_atlas as atlas


def test_bessel_factor_from_independent_circle_moments():
    z=atlas.z
    x=sp.Symbol('x', real=True)
    factor=atlas.Generator(key='bessel-v0-anchor',name='Bessel v0 factor',
        expression=sp.hyper([],[1],-z/4),citation='10.24193/subbmath.2026.3.3 Eq1.14,delta0')
    actual=atlas.generator_series(factor,order=8).coefficients
    # J0(sqrt(z))=(1/pi)*integral_0^pi cos(sqrt(z)*cos(x))dx.
    expected=tuple(sp.simplify((-1)**n*sp.integrate(sp.cos(x)**(2*n),(x,0,sp.pi))
        /(sp.pi*sp.factorial(2*n))) for n in range(1,9))
    assert actual==expected


def test_repeated_product_and_raducanu_orhan_direct_differentiation():
    z=atlas.z
    c=sp.symbols('c2:10')
    polynomial=z+sum(v*z**n for n,v in enumerate(c,2))
    for delta,mu in [(sp.Rational(1,2),sp.Rational(1,3)),(1,0),(0,1)]:
        current=polynomial
        jet=c
        for _ in range(3):
            current=sp.expand((1-delta+mu)*current+(delta-mu)*z*sp.diff(current,z)
                +delta*mu*z*z*sp.diff(current,z,2))
            jet=atlas.euler_differential_coefficients(jet,first=delta-mu,second=delta*mu)
            assert jet==tuple(current.coeff(z,n) for n in range(2,10))
    t=sp.Rational(-1,2)
    factor=atlas.Generator(key='mobius-power-anchor',name='Mobius factor',
        expression=1/(1-t*z),citation='10.12688/f1000research.172490.2 Eq5')
    phi=atlas.generator_series(factor,order=8).coefficients
    jet=(sp.Integer(0),)*8
    for beta in range(1,4):
        jet=atlas.product_subordination_coefficients(jet,phi,[1],order=8)
        direct=sp.series(z/(1-t*z)**beta,z,0,10).removeO().expand()
        assert jet==tuple(direct.coeff(z,n) for n in range(2,10))

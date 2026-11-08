"""Low-level exact transforms: Alexander and inverse logarithms, not bounds."""
import pytest
import sympy as sp

import geometric_function_atlas as gfa


def test_logarithms_independent_series():
    assert hasattr(gfa, 'logarithmic_coefficients'), 'ordinary log transform missing'
    a,b,c,z = sp.symbols('a b c z')
    expected = sp.series(sp.log(1+a*z+b*z**2+c*z**3)/2,z,0,4).removeO().expand()
    assert gfa.logarithmic_coefficients([a,b,c]) == tuple(expected.coeff(z,n) for n in range(1,4))
    assert gfa.logarithmic_coefficients([2,3,4]) == (1,sp.Rational(1,2),sp.Rational(1,3))
    for bad in ([], [1]*4, [True], [sp.Float('0.1')], ['1/2'], [sp.oo]):
        with pytest.raises((TypeError,ValueError)):
            gfa.logarithmic_coefficients(bad)


def test_linear_subordination_anchors():
    assert hasattr(gfa, 'linear_subordination_coefficients'), 'linear transform missing'
    # f'=1+tanh(z), a different differential equation than convex/starlike.
    B = [sp.Integer(1), sp.Integer(0), -sp.Rational(1,3)]
    assert gfa.linear_subordination_coefficients(B, [1], alpha=1, order=3) == (
        sp.Rational(1,2), 0, -sp.Rational(1,12))
    assert gfa.linear_subordination_coefficients(B, [0,1], alpha=0, order=3) == (0,1,0)
    assert gfa.linear_subordination_coefficients(B, [0,0,1], alpha=sp.Rational(1,2), order=3) == (0,0,sp.Rational(2,5))
    for bad in (True, 0.5, '1/2', -1, 2, sp.oo):
        with pytest.raises((TypeError, ValueError)):
            gfa.linear_subordination_coefficients(B, [1], alpha=bad, order=3)


def test_linear_subordination_independent_differential_equation():
    # Independently compose a rational Schwarz function, retaining its tail.
    z = gfa.z
    omega = z*(sp.Rational(1,2)-z)/(1-z/2)
    phi = 1+sp.Rational(4,5)*omega+omega**4/5
    for alpha in (0, sp.Rational(1,2), 1):
        jet = gfa.linear_subordination_coefficients(
            [sp.Rational(4,5),0,0,sp.Rational(1,5)],
            [sp.Rational(1,2),-1], alpha=alpha, order=4)
        f = z+sum(v*z**n for n,v in enumerate(jet,2))
        residual = (1-alpha)*f/z+alpha*sp.diff(f,z)-phi
        assert sp.series(residual,z,0,5).removeO().expand() == 0
    for bad in ([sp.Float('0.1')], [sp.oo], [True], ['1/2'], []):
        with pytest.raises((TypeError,ValueError)):
            gfa.linear_subordination_coefficients(bad,[1],alpha=1,order=3)
    for order, gammas in ((9,[1]), (True,[1]), (1,[]), (1,[0]*6)):
        with pytest.raises(ValueError):
            gfa.linear_subordination_coefficients([1],gammas,alpha=1,order=order)


def test_convex_alexander_anchors_and_normalization():
    assert hasattr(gfa, 'convex_member_coefficients'), 'public convex transform missing'
    # phi=(1+z)/(1-z), omega=z -> f=z/(1-z).
    assert gfa.convex_member_coefficients([sp.Integer(2)]*3, [1], order=3) == (1,1,1)
    # omega=z^2 -> f=atanh(z), not z/(1-z).
    assert gfa.convex_member_coefficients([sp.Integer(2)]*3, [0,1], order=3) == (0,sp.Rational(1,3),0)
    # apple phi=exp(z)*sqrt(1+z).
    for bad in ([sp.Float('0.5')],[sp.oo],[True],[0.5]):
        with pytest.raises((TypeError,ValueError)):
            gfa.convex_member_coefficients(bad,[1],order=1)
    phi = gfa.generator_series(gfa.Generator(key='apple',name='apple',expression=sp.exp(gfa.z)*sp.sqrt(1+gfa.z),citation='arXiv:2606.15780v1 (3.1)'), order=3)
    assert gfa.convex_member_coefficients(phi.coefficients,[1],order=3) == (sp.Rational(3,4),sp.Rational(25,48),sp.Rational(385,1152))


def test_inverse_logarithms_composition_and_rejections():
    assert hasattr(gfa, 'inverse_logarithmic_coefficients'), 'inverse log transform missing'
    a,b,c = sp.symbols('a b c')
    values = gfa.inverse_logarithmic_coefficients([a,b,c])
    assert values == (-a/2, 3*a**2/4-b/2, -5*a**3/3+2*a*b-c/2)
    # Independent compositional inverse through degree 4.
    w = sp.Symbol('w')
    inverse = w-a*w**2+(2*a**2-b)*w**3+(-5*a**3+5*a*b-c)*w**4
    composition = inverse+a*inverse**2+b*inverse**3+c*inverse**4
    assert sp.series(composition,w,0,5).removeO().expand() == w
    log = sp.series(sp.log(inverse/w)/2,w,0,4).removeO().expand()
    assert tuple(log.coeff(w,n) for n in range(1,4)) == values
    assert gfa.inverse_logarithmic_coefficients([1,1,1]) == (-sp.Rational(1,2),sp.Rational(1,4),-sp.Rational(1,6))
    for invalid in ([0.1],['__import__("os").system("false")'],[sp.oo],[True],[]):
        with pytest.raises((TypeError,ValueError)):
            gfa.inverse_logarithmic_coefficients(invalid)
    with pytest.raises(ValueError):
        gfa.inverse_logarithmic_coefficients([1]*4)

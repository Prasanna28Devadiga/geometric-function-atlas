"""Direct derivative and dilation-conjugacy controls, independent of multipliers."""
import pytest
import sympy as sp

import geometric_function_atlas as atlas


def test_normalized_second_order_euler_definition():
    assert hasattr(atlas, 'euler_differential_coefficients'), 'missing normalized Euler differential transform'
    z = sp.Symbol('z')
    jet = [sp.Rational(2, 3), -1, sp.I, sp.sqrt(2)]
    f = z + sum(c*z**n for n, c in enumerate(jet, 2))
    for a, b in [(0, 0), (0, 1), (sp.Rational(1, 4), sp.Rational(3, 4)), (-1, 2)]:
        expected = sp.expand(a*z**2*sp.diff(f,z,2)+b*z*sp.diff(f,z)+(1-b)*f)
        got = atlas.euler_differential_coefficients(jet, second=a, first=b)
        assert got == tuple(expected.coeff(z,n) for n in range(2,6))


def test_euler_inverse_and_singular_refusal():
    jet = (sp.Rational(1,3), sp.I, 4)
    got = atlas.euler_differential_coefficients(jet, second=1, first=0)
    assert atlas.euler_differential_coefficients(got, second=1, first=0, inverse=True)==jet
    # The second coefficient is annihilated at first=-1, second=0.
    assert atlas.euler_differential_coefficients([7], second=0, first=-1)==(0,)
    with pytest.raises(ValueError, match='zero'):
        atlas.euler_differential_coefficients([0], second=0, first=-1, inverse=True)


def test_euler_input_guards():
    for bad in [True, 0.5, '1', sp.oo, sp.Symbol('a')]:
        for keyword in ['first', 'second']:
            args = {'first': 0, 'second': 0}
            args[keyword] = bad
            with pytest.raises((TypeError, ValueError)):
                atlas.euler_differential_coefficients([1], **args)
    for jet in [[], [1]*9, [True], [0.1], ['1'], [sp.oo]]:
        with pytest.raises((TypeError, ValueError)):
            atlas.euler_differential_coefficients(jet, first=0, second=0)
    with pytest.raises(TypeError):
        atlas.euler_differential_coefficients([1], first=0, second=0, inverse=1)


def test_q_al_oboudi_nonunit_lambda_dilation_conjugacy():
    z = sp.Symbol('z')
    jet = [sp.Rational(2,3), -1, sp.I, 5]
    for lam in [1,2,3]:
        for q in [sp.Rational(1,2), sp.Rational(3,4), sp.Integer(1)]:
            for degree in [0,1,3]:
                # P_lam f = z^(1-lam)*f(z^lam); P_lam T = (z D_q) P_lam.
                expected = z + sum(c*z**(1+lam*(n-1)) for n,c in enumerate(jet,2))
                for _ in range(degree):
                    expected = sp.expand(z*sp.diff(expected,z) if q==1 else (expected-expected.subs(z,q*z))/(1-q))
                got = atlas.q_al_oboudi_coefficients(jet,q=q,lam=lam,degree=degree)
                actual = z + sum(c*z**(1+lam*(n-1)) for n,c in enumerate(got,2))
                assert sp.expand(expected-actual)==0

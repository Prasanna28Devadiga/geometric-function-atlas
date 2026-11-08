"""Independent defining-equation anchors for bounded integral multipliers."""
import pytest
import sympy as sp

import geometric_function_atlas as atlas


def test_bernardi_direct_integral():
    assert hasattr(atlas, 'bernardi_coefficients'), 'missing public Bernardi transform'
    z = sp.Symbol('z')
    jet = [sp.Rational(2,3), -1, 4, 2]
    f = z + sum(a*z**n for n,a in enumerate(jet,2))
    for gamma in [0,1,3,sp.Rational(1,2)]:
        gamma = sp.Rational(gamma)
        got = atlas.bernardi_coefficients(jet, gamma=gamma)
        assert got == tuple(sp.cancel((gamma+1)*a/(gamma+n)) for n,a in enumerate(jet,2))
        F = z + sum(a*z**n for n,a in enumerate(got,2))
        assert sp.expand(z*sp.diff(F,z)+gamma*F-(gamma+1)*f) == 0
        if gamma.is_Integer:
            expected = (gamma+1)*sp.integrate(z**(gamma-1)*f,z)/z**gamma
            assert sp.expand(F-expected) == 0
        assert atlas.bernardi_coefficients(got,gamma=gamma,inverse=True) == tuple(jet)


def test_q_al_oboudi_defining_iteration():
    assert hasattr(atlas, 'q_al_oboudi_coefficients'), 'missing q-Al-Oboudi transform'
    z = sp.Symbol('z')
    jet = [sp.Rational(2,3), -1, 4]
    f = z + sum(a*z**n for n,a in enumerate(jet,2))
    for q in [sp.Rational(1,2), sp.Rational(2,3),sp.Integer(1)]:
        for lam in [1,2,3]:
            for degree in [0,1,3]:
                # Direct D_q powers of monomials independently define the source multiplier.
                expected = []
                for n,a in enumerate(jet,2):
                    power = 1+(n-1)*lam
                    monomial = z**power
                    dq = sp.diff(monomial,z) if q==1 else sp.cancel((monomial-monomial.subs(z,q*z))/((1-q)*z))
                    expected.append(sp.cancel(a*(dq/z**(power-1))**degree))
                got = atlas.q_al_oboudi_coefficients(jet,q=q,lam=lam,degree=degree)
                assert got == tuple(expected)
                assert atlas.q_al_oboudi_coefficients(got,q=q,lam=lam,degree=degree,inverse=True) == tuple(jet)
                if lam==1:
                    repeated = f
                    for _ in range(degree):
                        repeated = z*sp.diff(repeated,z) if q==1 else sp.cancel((repeated-repeated.subs(z,q*z))/(1-q))
                    assert sp.expand(repeated-z-sum(a*z**n for n,a in enumerate(got,2)))==0



def test_multiplier_guard_contracts():
    for gamma in [-1, True, 0.5, "1", sp.Symbol("g"), sp.oo]:
        with pytest.raises((TypeError,ValueError)):
            atlas.bernardi_coefficients([1],gamma=gamma)
    for lam in [0,65,True,sp.Rational(1,2),"1"]:
        with pytest.raises((TypeError,ValueError)):
            atlas.q_al_oboudi_coefficients([1],q=1,lam=lam,degree=1)
    for q in [0,-1,2,True,0.5,"1/2"]:
        with pytest.raises((TypeError,ValueError)):
            atlas.q_al_oboudi_coefficients([1],q=q,lam=1,degree=1)
    for degree in [-1,65,True,sp.Rational(1,2)]:
        with pytest.raises((TypeError,ValueError)):
            atlas.q_al_oboudi_coefficients([1],q=1,lam=1,degree=degree)
    for jet in [[],[1]*9,[0.1],[True],[sp.oo],["1"]]:
        for inverse in [False,True]:
            with pytest.raises((TypeError,ValueError)):
                atlas.bernardi_coefficients(jet,gamma=0,inverse=inverse)
            with pytest.raises((TypeError,ValueError)):
                atlas.q_al_oboudi_coefficients(jet,q=1,lam=1,degree=1,inverse=inverse)
    with pytest.raises(TypeError):
        atlas.bernardi_coefficients([1],gamma=0,inverse=1)
    with pytest.raises(TypeError):
        atlas.q_al_oboudi_coefficients([1],q=1,lam=1,degree=1,inverse=1)
    jet=[sp.sqrt(2),sp.I,0,1,2,3,4,5]
    assert len(atlas.bernardi_coefficients(jet,gamma=10**4))==8
    assert atlas.q_al_oboudi_coefficients([1],q=1,lam=64,degree=64)==(sp.Integer(65)**64,)

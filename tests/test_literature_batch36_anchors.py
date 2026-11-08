"""Independent defining-equation anchors; no source theorem certification."""
import sympy as s

from geometric_function_atlas import bernardi_coefficients, q_al_oboudi_coefficients, z


def test_bernardi_normalized_quadratics_against_integral():
    u=s.symbols('u')
    for gamma in [0,s.Rational(1,2),1]:
        for c in [s.Rational(1,16),s.Rational(1,8),s.Rational(1,4)]:
            f=u-c*u**2
            # Integral substitution t=z*u avoids a complex-power origin branch.
            whole=(gamma+1)*z*s.integrate(u**gamma*(1-c*z*u),(u,0,1))
            jet=bernardi_coefficients([-c],gamma=gamma)
            assert s.expand(whole-z-jet[0]*z**2)==0
            assert s.expand(z*s.diff(whole,z)+gamma*whole-(gamma+1)*f.subs(u,z))==0


def test_jackson_two_image_combination_independent_symbols():
    cs=s.symbols('c2:10')
    f=z+sum(c*z**n for n,c in enumerate(cs,2))
    for q in [s.Rational(1,2),s.Rational(2,3),s.Rational(3,4)]:
        image=q_al_oboudi_coefficients(cs,q=q,lam=1,degree=1)
        for v in [1,s.Rational(3,2)]:
            actual=z+sum(((1-v)*d+v*c)*z**n for n,(c,d) in enumerate(zip(cs,image),2))
            independent=(1-v)*(f-f.subs(z,q*z))/(1-q)+v*f
            assert s.expand(actual-independent)==0


def test_rational_q_image_mobius_control():
    # beta0/1 coefficient combination, not a general Salagean operator API.
    t=s.Rational(1,16);q=s.Rational(1,2);v=s.Rational(3,2)
    f=z/(1-t*z)
    direct=s.cancel((1-v)*(f-f.subs(z,q*z))/(1-q)+v*f)
    jet=[t**n for n in range(1,9)]
    dj=q_al_oboudi_coefficients(jet,q=q,lam=1,degree=1)
    expected=s.series(direct,z,0,10).removeO().expand()
    assert all(s.cancel(expected.coeff(z,n)-((1-v)*d+v*c))==0
               for n,(c,d) in enumerate(zip(jet,dj),2))

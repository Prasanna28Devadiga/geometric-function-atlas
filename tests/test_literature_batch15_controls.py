"""Independent defining-equation controls for compositions of existing APIs."""
import sympy as sp

from geometric_function_atlas import (
    convex_member_coefficients,
    generator_series,
    product_subordination_coefficients,
    q_al_oboudi_coefficients,
    z,
)
from geometric_function_atlas.schur import member_coefficients


def test_exponential_negative_rotation_matches_entire_primitive():
    phi=generator_series('exponential',order=4).coefficients
    star=member_coefficients(phi,[-1,0,0,0],order=4)
    convex=convex_member_coefficients(phi,[-1,0,0,0],order=4)
    primitive=sum((-z)**n/(n*sp.factorial(n)) for n in range(1,5))
    derivative=sp.series(sp.exp(primitive),z,0,5).removeO()
    for n in range(1,5):
        assert sp.expand(derivative).coeff(z,n)==star[n-1]
        assert convex[n-1]==star[n-1]/(n+1)
    assert star[0]==-1  # rotation orientation guard


def test_product_then_inverse_jackson_matches_direct_whole_rational_function():
    t=sp.Rational(2,5)
    f=z/(1-t*z)
    psi=member_coefficients([t**n for n in range(1,4)],[1,0,0],order=3)
    for q in [sp.Rational(1,2),sp.Rational(2,3),sp.Rational(3,4)]:
        h=1/(1-q*t*z)
        jackson=sp.cancel((f-f.subs(z,q*z))/((1-q)*z))
        assert sp.cancel(z*jackson/f-h)==0
        product=product_subordination_coefficients(psi,[(q*t)**n for n in range(1,4)],[1,0,0],order=3)
        recovered=q_al_oboudi_coefficients(product,q=q,lam=1,degree=1,inverse=True)
        assert tuple(recovered)==tuple(t**n for n in range(1,4))
        # Ordinary Alexander division is a different operator for q<1.
        assert product[0]/2 != recovered[0]
        for tau in [1,2,3]:
            assert sp.cancel(z*jackson*f**(tau-1)/f**tau-h)==0

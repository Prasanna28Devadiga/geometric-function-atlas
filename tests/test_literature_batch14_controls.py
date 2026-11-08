"""Independent exact anchors for existing APIs, not literature endorsement."""
import sympy as sp

from geometric_function_atlas import linear_subordination_coefficients, z
from geometric_function_atlas.schur import member_coefficients


def test_rotated_spirallike_member_matches_direct_binomial_primitive():
    # Re(exp(i*alpha)*zf'/f)>0; alpha=pi/4 has D=1-i.
    # Complex generator coefficients are exact; real-Schur support is unchanged.
    D=1-sp.I
    jet=member_coefficients([D]*4,[1,0,0,0],order=4)
    direct=sp.series(z*(1-z)**(-D),z,0,6).removeO()
    assert sp.expand(direct-z-sum(v*z**n for n,v in enumerate(jet,2)))==0
    W=1+D*z/(1-z)
    p=sp.cancel((1+sp.I)*W-sp.I)
    assert sp.cancel(p-(1+z)/(1-z))==0
    assert sp.simplify(jet[0]-(1+sp.I))!=0  # orientation mutation


def test_linear_derivative_whole_quadratic_has_no_invented_tail():
    b=sp.Rational(41,100)
    jet=linear_subordination_coefficients([2*b,0,0],[1,0,0],alpha=1,order=3)
    assert list(jet)==[b,0,0]
    f=z+b*z*z
    assert sp.diff(f,z)==1+2*b*z
    point=(-sp.Integer(141)+100*sp.I)/173
    W=sp.cancel(z*sp.diff(f,z)/f).subs(z,point)
    defect=sp.cancel((W**2-1)*sp.conjugate(W**2-1)-1)
    assert defect==sp.Rational(208515620637768,22349460945964321)>0
    # A positive-real derivative proves global univalence, not lemniscate membership.
    assert 1-2*b>0

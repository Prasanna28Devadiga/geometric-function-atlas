"""Independent whole-function anchors, not literature theorem certifications."""
import sympy as s

from geometric_function_atlas import (
    Generator,
    bernardi_coefficients,
    convex_member_coefficients,
    euler_differential_coefficients,
    generator_series,
    inverse_coefficients,
    product_subordination_coefficients,
    z,
)
from geometric_function_atlas.schur import member_coefficients


def test_elastic_square_root_and_reciprocal_generators():
    p = (1 + z) / (1 - z)
    for alpha in [s.Integer(0), s.Integer(1), s.Rational(3, 2), s.Integer(2), -s.Integer(1)]:
        beta = alpha if alpha >= 1 else 1 - alpha
        w = (p + s.sqrt(p**2 + 4*beta*(beta-1))) / (2*beta)
        if alpha <= 0:
            w = 1/w
        B = generator_series(Generator(key='elastic-anchor', name='Elastic anchor', expression=w, citation='DOI10.1007/s13324-026-01235-1 Eq17/18'), order=3).coefficients
        jet = member_coefficients(B, [1], order=3)
        f = z + sum(a*z**n for n, a in enumerate(jet, 2))
        W = s.series(z*s.diff(f,z)/f, z, 0, 4).removeO()
        residual = s.series(alpha*W+(1-alpha)/W-p, z, 0, 4).removeO()
        assert s.expand(residual) == 0
        d = 2*alpha-1
        assert jet[0] == 2/d
        assert jet[1] == (3+4*alpha*(alpha-1)/d)/d**2


def test_genuine_biunivalent_mobius_inverse():
    for t in [s.Rational(1,4), s.Rational(1,2), -s.Rational(1,2), s.Integer(1)]:
        jet = member_coefficients([s.Integer(1)]*4, [t], order=4)
        assert tuple(jet) == tuple(t**n for n in range(1,5))
        inv = inverse_coefficients(jet)
        assert inv == tuple((-t)**n for n in range(1,5))
        f = z/(1-t*z)
        g = z/(1+t*z)
        assert s.cancel(f.subs(z,g)-z) == 0
        assert s.cancel(g.subs(z,f)-z) == 0


def test_exponential_characterization_nonradial_primitive():
    """DOI10.3389/fams.2026.1777576, KC sigma1, K=exp(z)."""
    omega = z*(s.Rational(1, 2)-z)/(1-z/2)
    f = z*s.exp(2*z)*(1-z/2)**3
    assert s.cancel(z*s.diff(f, z)/f-1-omega) == 0
    jet = member_coefficients([s.Integer(1)]+[s.Integer(0)]*4,
                              [s.Rational(1, 2), -1], order=5)
    direct = s.series(f, z, 0, 7).removeO().expand()
    assert tuple(jet) == tuple(direct.coeff(z, n) for n in range(2, 7))
    # The characterization uses exp(W-1), not W or exp(z*W).
    W = s.cancel(z*s.diff(f, z)/f)
    assert s.simplify(W-1-omega) == 0
    assert s.cancel(z*W-omega) != 0


def test_q_multiplicative_mobius_defining_expression():
    """DOI10.31926/but.mif.2026.6.68.1.8 Eq8,15,17."""
    t = s.Rational(1, 100)
    f = z/(1-t*z)
    jet = member_coefficients([s.Integer(1)]*3, [t], order=3)
    assert tuple(jet) == (t, t*t, t**3)
    for q in [s.Rational(1, 4), s.Rational(1, 2), s.Rational(3, 4)]:
        Dq = s.cancel((f-f.subs(z, q*z))/((1-q)*z))
        exponent = s.cancel(z*z*Dq/f)
        assert s.cancel(exponent-z/(1-q*t*z)) == 0
        L = (1-t*z)*s.exp(exponent)
        coeffs = generator_series(Generator(key='q-multiplicative-anchor',
            name='Fixed defining expression', expression=L,
            citation='DOI10.31926/but.mif.2026.6.68.1.8 Eq8'), order=2).coefficients
        assert tuple(coeffs) == (1-t, s.Rational(1, 2)+(q-1)*t)
        eta1, eta2 = coeffs
        literal17 = -(eta2-eta1**2)-eta1*(q+1)+q+s.Rational(1, 2)
        assert literal17 == jet[1]


def test_gregory_removable_generator_integral_anchor():
    """G(z)=integral_0^1 (1+z)^x dx; no polynomial replacement."""
    x = s.Symbol('x')
    G = s.Piecewise((s.Integer(1), s.Eq(z, 0)),
                    (z/s.log(1+z), True))
    got = generator_series(Generator(key='gregory-anchor', name='Gregory',
        expression=G, citation='DOI10.19139/soic-2310-5070-3241 Eq1.1'),
        order=5).coefficients
    independent = []
    for n in range(1, 6):
        polynomial = s.prod(x-j for j in range(n))/s.factorial(n)
        independent.append(s.integrate(polynomial, (x, 0, 1)))
    assert tuple(got) == tuple(independent)
    # A nonradial Schwarz map guards against correlated coefficient slices.
    omega = z*(s.Rational(1, 2)-z)/(1-z/2)
    jet = member_coefficients(got, [s.Rational(1, 2), -1], order=4)
    f = z + sum(a*z**n for n, a in enumerate(jet, 2))
    wjet = s.series(omega, z, 0, 5).removeO()
    rhs = 1 + sum(b*wjet**n for n, b in enumerate(got[:4], 1))
    assert s.series(z*s.diff(f,z)/f-rhs, z, 0, 5).removeO().expand() == 0


def test_fourfold_range_target_is_not_auxiliary_equality():
    """Same half-plane image does not give equal coefficient sequences."""
    target = (1+z**4)/(1-z**4)
    coeffs = generator_series(Generator(key='fourfold-halfplane-anchor',
        name='Fourfold half-plane', expression=target,
        citation='Literal fixed-target control, DOI10.31801/cfsuasmas.1637685'),
        order=4).coefficients
    assert tuple(coeffs) == (0, 0, 0, 2)
    for t in [s.Rational(1, 2), s.I/2]:
        f = z/(1-t*z)
        g = z/(1+t*z)
        assert s.cancel(f.subs(z,g)-z) == 0
        assert s.cancel(g.subs(z,f)-z) == 0
        h = s.cancel(z*s.diff(f,z)/f)
        p = s.cancel(z*s.diff(g,z)/g)
        assert s.cancel(h-1/(1-t*z)) == 0
        assert s.cancel(p-1/(1+t*z)) == 0
        # Their Cayley maps have |omega| <= |t|/(2-|t|) < 1;
        # composing target with a fourth root is not an analytic disk lift.
        assert abs(t)/(2-abs(t)) < 1
        assert s.series(h-target,z,0,2).removeO().expand().coeff(z,1) == t


def test_wright_hypergeometric_ode_and_integral_anchor():
    """Whole 0F1 generator, independent ODE and integral coefficient controls."""
    for L in [1, 2]:
        n = s.Rational(1, 16)
        K = s.hyper([], [L], n)
        phi = 1+(s.hyper([], [L], n*z)-1)/K
        B = generator_series(Generator(key='wright-anchor', name='Wright factor',
            expression=phi, citation='DOI10.28924/2291-8639-24-2026-75 Eq1.5 tau1'),
            order=4).coefficients
        # 0F1 solves z*Y''+L*Y'=n*Y, independently of the source moment proof.
        Y = 1+sum(K*b*z**k for k, b in enumerate(B, 1))
        ode = s.expand(z*s.diff(Y, z, 2)+L*s.diff(Y, z)-n*Y)
        assert all(s.simplify(ode.coeff(z, k)) == 0 for k in range(4))
        jet = product_subordination_coefficients([0]*4, B, [1], order=4)
        assert all(s.simplify(a-b) == 0 for a, b in zip(jet, B))
        integral = bernardi_coefficients(jet, gamma=0)
        f = z+sum(a*z**k for k, a in enumerate(jet, 2))
        F = z+sum(a*z**k for k, a in enumerate(integral, 2))
        assert s.simplify(z*s.diff(F, z)-f) == 0


def test_shifted_primitive_composition_preserves_nonnormalized_origin():
    """Euler+Bernardi handles z^k*h' without inventing a harmonic solver."""
    a2, a3, a4, a5 = s.symbols('a2 a3 a4 a5')
    generic = (a2, a3, a4, a5)
    nonradial = convex_member_coefficients([2]*4, [s.Rational(1, 2), -1], order=4)
    for jet in [generic, nonradial]:
        h = z + sum(c*z**n for n, c in enumerate(jet, 2))
        E = euler_differential_coefficients(jet, second=0, first=1)
        for degree, scale in [(1, s.Integer(1)), (2, s.Rational(1, 3))]:
            transformed = bernardi_coefficients(E, gamma=degree)
            G = scale*z**(degree+1)/(degree+1) * (
                1 + sum(c*z**n for n, c in enumerate(transformed, 1)))
            assert s.expand(s.diff(G, z)-scale*z**degree*s.diff(h, z)) == 0
            assert G.subs(z, 0) == 0
            assert s.diff(G, z).subs(z, 0) == 0
            independent = s.integrate(scale*z**degree*s.diff(h, z), z)
            assert s.expand(G-independent) == 0

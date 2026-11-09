"""Independent native Poisson and fixedpoint anchors (no new theorem API)."""

import sympy as s

import geometric_function_atlas as a


def test_poisson_whole_function_product_and_bernardi_ode():
    z = a.z
    for k in [s.Rational(1, 5), s.Rational(1, 4)]:
        factor = 1 + s.exp(-k) * (s.exp(k * z) - 1)
        B = a.generator_series(
            a.Generator(
                key="poisson-anchor",
                name="Poisson factor",
                expression=factor,
                citation="10.37193/CMI.2026.01.12 PDFp4",
            ),
            order=8,
        ).coefficients
        jet = a.product_subordination_coefficients((0,) * 8, B, [1], order=8)
        assert all(
            s.simplify(c - s.exp(-k) * k ** (n - 1) / s.factorial(n - 1)) == 0
            for n, c in enumerate(jet, 2)
        )
        image = a.bernardi_coefficients(jet, gamma=0)
        F = z + sum(c * z**n for n, c in enumerate(image, 2))
        psi = z * factor
        assert s.series(z * s.diff(F, z) - psi, z, 0, 10).removeO().expand() == 0


def test_independent_fixedpoint_polynomial_and_degreezero_identity():
    z = a.z
    c = s.Rational(1, 32)
    # Negative fixedpoint -1/3, genuine whole normalized polynomial.
    jet = a.linear_subordination_coefficients([-2 * c, -9 * c], [1], alpha=1, order=2)
    jet = a.ruscheweyh_coefficients(jet, degree=0)
    F = z + sum(v * z**n for n, v in enumerate(jet, 2))
    assert s.expand(F - (z - c * z * z - 3 * c * z**3)) == 0
    assert F.subs(z, -s.Rational(1, 3)) == -s.Rational(1, 3)
    assert 2 * c + 9 * c < 1

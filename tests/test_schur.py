from __future__ import annotations

import pytest
import sympy as sp

from geometric_function_atlas.contracts import (
    InvalidInputError,
    ResourceLimitError,
    UnsupportedError,
)
from geometric_function_atlas.schur import (
    MAX_SCHUR_DEPTH,
    functional_value,
    member_coefficients,
    schur_omega_coefficients,
)


def _bell_phi() -> list[sp.Expr]:
    # phi(z) = exp(exp(z) - 1) = 1 + z + z^2 + 5z^3/6 + 5z^4/8 + ...
    # (Bell numbers; matches the site's published B1..B4)
    return [sp.Integer(1), sp.Integer(1), sp.Rational(5, 6), sp.Rational(5, 8)]


def _starlike_phi() -> list[sp.Expr]:
    # phi(z) = (1+z)/(1-z) = 1 + 2z + 2z^2 + 2z^3 + ...
    return [sp.Integer(2), sp.Integer(2), sp.Integer(2), sp.Integer(2)]


def _parabolic_phi() -> list[sp.Expr]:
    # phi(z) = 1 + 8z/pi^2 + 16z^2/(3 pi^2) + 184z^3/(45 pi^2) + 352z^4/(105 pi^2) + ...
    return [
        8 / sp.pi**2,
        16 / (3 * sp.pi**2),
        184 / (45 * sp.pi**2),
        352 / (105 * sp.pi**2),
    ]


def test_factored_schur_omega_matches_dag_convention() -> None:
    # gft/dag.py schur_omega: c1 = g0, c2 = (1-g0^2) g1, c3 = (1-g0^2)((1-g1^2) g2 - g0 g1^2)
    assert schur_omega_coefficients(["0", "1"]) == [sp.Integer(0), sp.Integer(1)]
    assert schur_omega_coefficients(["1", "0"]) == [sp.Integer(1), sp.Integer(0)]
    assert schur_omega_coefficients(["1/2", "1/2"]) == [
        sp.Rational(1, 2),
        sp.Rational(3, 8),
    ]


def test_member_coefficients_bell_extremal_z_squared() -> None:
    # bell with gamma = (0, 1): w(z) = z^2, f(z) = z exp(z^2/2 + z^4/4 + ...)
    # so a2 = 0, a3 = 1/2, a4 = 0, a5 = 3/8.
    coefficients = member_coefficients(_bell_phi(), ["0", "1"], order=4)
    assert coefficients[0] == 0
    assert coefficients[1] == sp.Rational(1, 2)
    assert coefficients[2] == 0
    assert coefficients[3] == sp.Rational(3, 8)


def test_member_coefficients_starlike_factored_site_formula() -> None:
    # starlike with gamma = (1/2, 1/2): a3 = 9/8 in the factored convention
    coefficients = member_coefficients(_starlike_phi(), ["1/2", "1/2"], order=4)
    assert sp.simplify(coefficients[1] - sp.Rational(9, 8)) == 0


def test_member_coefficients_parabolic_fs_value() -> None:
    # parabolic FS mu=1/4 at gamma = (1, 0): (48 + 8 pi^2)/(3 pi^4)
    coefficients = member_coefficients(_parabolic_phi(), ["1", "0"], order=4)
    value = functional_value("fekete_szego_mu0.25", coefficients)
    assert sp.simplify(value - (48 + 8 * sp.pi**2) / (3 * sp.pi**4)) == 0


def test_functional_value_fekete_szego() -> None:
    coefficients = [sp.Rational(1, 2), sp.Rational(3, 4)]
    assert functional_value("fekete_szego_mu0", coefficients) == sp.Rational(3, 4)
    # |a3 - mu a2^2|
    assert functional_value("fekete_szego_mu2", coefficients) == sp.Rational(1, 4)


def test_functional_value_hankel2_2() -> None:
    coefficients = [sp.Integer(1), sp.Integer(1), sp.Integer(1)]
    assert functional_value("hankel2_2", coefficients) == 0


def test_functional_value_inv_a3() -> None:
    coefficients = [sp.Integer(1), sp.Rational(5, 4)]
    assert functional_value("inv_a3", coefficients) == sp.Rational(3, 4)


def test_functional_value_log_gamma2() -> None:
    # log(f/z) = 2(gamma_1 z + gamma_2 z^2 + ...), gamma_2 = (a3 - a2^2/2)/2
    coefficients = [sp.Integer(1), sp.Rational(3, 2)]
    assert functional_value("log_gamma2", coefficients) == sp.Rational(1, 2)


def test_functional_value_zalcman() -> None:
    coefficients = [sp.Integer(1), sp.Integer(2), sp.Integer(3)]
    value = functional_value("zalcman_a2a3_a4", coefficients)
    assert sp.simplify(value - 1) == 0


def test_unsupported_functional_raises() -> None:
    with pytest.raises(UnsupportedError):
        functional_value("hankel3_1", [sp.Integer(1)])


def test_gamma_beyond_unit_disk_rejected() -> None:
    with pytest.raises(InvalidInputError):
        member_coefficients(_bell_phi(), ["2", "0"], order=4)


def test_gamma_negative_one_is_valid() -> None:
    coefficients = member_coefficients(_bell_phi(), ["-1", "0"], order=3)
    assert sp.simplify(coefficients[0] + 1) == 0


def test_schur_depth_bounded() -> None:
    with pytest.raises(ResourceLimitError):
        member_coefficients(
            _bell_phi(), ["0"] * (MAX_SCHUR_DEPTH + 1), order=6
        )


def test_decimal_gamma_rejected() -> None:
    with pytest.raises(InvalidInputError):
        member_coefficients(_bell_phi(), ["0.5", "0"], order=4)

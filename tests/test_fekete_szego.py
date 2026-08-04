from __future__ import annotations

import json

import pytest
import sympy as sp

from gft_registry import FeketeSzegoResult, fekete_szego


def test_classical_starlike_anchor_matches_known_constants() -> None:
    a3 = fekete_szego("starlike", mu=0)
    zalcman_face = fekete_szego("starlike", mu=1)

    assert a3.value == sp.Integer(3)
    assert zalcman_face.value == sp.Integer(1)
    assert a3.evidence_status == "proven_exact_under_declared_assumptions"


def test_exponential_generator_keeps_exact_arithmetic() -> None:
    result = fekete_szego("exponential", mu="0")

    assert isinstance(result, FeketeSzegoResult)
    assert result.b1 == 1
    assert result.b2 == sp.Rational(1, 2)
    assert result.value == sp.Rational(3, 4)
    assert result.decimal(precision=20) == "0.75000000000000000000"


def test_result_serializes_without_losing_exact_values() -> None:
    result = fekete_szego("sine", mu=sp.Rational(1, 2))
    payload = result.to_dict(precision=16)

    assert payload["generator"] == "sine"
    assert payload["mu"] == "1/2"
    assert payload["value_exact"] == "1/2"
    assert payload["value_decimal"] == "0.5000000000000000"
    assert payload["method"] == "ma_minda_fekete_szego_closed_form"
    assert payload["novelty_claim"] is False
    assert payload["package_version"] == "0.1.0"
    assert payload["artifact_versions"]["generator_catalog"]
    json.dumps(payload)


def test_fekete_szego_rejects_generator_without_positive_b1() -> None:
    from gft_registry import Generator, z

    generator = Generator(
        key="bad",
        name="Bad first coefficient",
        expression=1 - z,
        citation="User supplied",
    )
    with pytest.raises(ValueError, match="B1 must be positive"):
        fekete_szego(generator, mu=0)


def test_fekete_szego_rejects_non_real_b2() -> None:
    from gft_registry import Generator, z

    generator = Generator(
        key="complex-b2",
        name="Complex second coefficient",
        expression=1 + z + sp.I * z**2,
        citation="User supplied",
    )
    with pytest.raises(ValueError, match="B2 must be real"):
        fekete_szego(generator, mu=0)


def test_fekete_szego_rejects_invalid_or_excessive_inputs() -> None:
    with pytest.raises(ValueError, match="real rational"):
        fekete_szego("sine", mu="sqrt(2)")
    with pytest.raises(ValueError, match="at most 128 characters"):
        fekete_szego("sine", mu="1" * 129)
    with pytest.raises(ValueError, match="precision must be at most 1000"):
        fekete_szego("sine", mu=0).decimal(precision=1001)


def test_fekete_szego_rejects_scientific_notation_before_sympy_parsing() -> None:
    with pytest.raises(ValueError, match="integer or integer/integer"):
        fekete_szego("sine", mu="1e1000")


@pytest.mark.parametrize(
    "mu",
    [sp.Integer(10) ** 128, sp.Rational(1, sp.Integer(10) ** 128)],
)
def test_fekete_szego_bounds_preconstructed_rational_components(mu: sp.Rational) -> None:
    with pytest.raises(ValueError, match="at most 128 decimal digits"):
        fekete_szego("sine", mu=mu)

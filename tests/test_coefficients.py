from __future__ import annotations

import pytest
import sympy as sp

from geometric_function_atlas import Generator, generator_series, taylor_coefficients, z


def test_exact_taylor_coefficients_for_sine_generator() -> None:
    assert taylor_coefficients("sine", order=4) == (
        sp.Integer(1),
        sp.Integer(0),
        -sp.Rational(1, 6),
        sp.Integer(0),
    )


def test_exact_taylor_coefficients_preserve_square_root_series() -> None:
    assert taylor_coefficients("cosh_sqrt", order=4) == (
        sp.Rational(1, 2),
        sp.Rational(1, 24),
        sp.Rational(1, 720),
        sp.Rational(1, 40320),
    )


def test_custom_normalized_generator_is_supported() -> None:
    generator = Generator(
        key="custom",
        name="Custom generator",
        expression=1 + 2 * z + 3 * z**2,
        citation="User supplied",
    )
    assert taylor_coefficients(generator, order=3) == (
        sp.Integer(2),
        sp.Integer(3),
        sp.Integer(0),
    )


def test_taylor_coefficients_reject_invalid_order() -> None:
    with pytest.raises(ValueError, match="order must be at least 1"):
        taylor_coefficients("sine", order=0)


def test_taylor_coefficients_reject_non_normalized_generator() -> None:
    generator = Generator(
        key="bad",
        name="Not normalized",
        expression=2 + z,
        citation="User supplied",
    )
    with pytest.raises(ValueError, match=r"phi\(0\) must equal 1"):
        taylor_coefficients(generator, order=2)


def test_generator_series_carries_reproducibility_metadata() -> None:
    result = generator_series("sine", order=4)
    payload = result.to_dict()

    assert result.coefficients == (1, 0, -sp.Rational(1, 6), 0)
    assert payload["method"] == "exact_symbolic_taylor_series"
    assert payload["evidence_status"] == "proven_exact_under_declared_assumptions"
    assert payload["package_version"] == "0.2.0"
    assert payload["artifact_versions"]["generator_catalog"]
    assert payload["novelty_claim"] is False


def test_verification_report_detects_mutated_coefficients() -> None:
    generator = Generator(
        key="mutated",
        name="Mutated",
        expression=1 + z + z**2,
        citation="Test",
    )
    result = generator_series(generator, order=2)
    mutated = result.__class__(
        generator=result.generator,
        order=result.order,
        coefficients=(sp.Integer(99), sp.Integer(99)),
    )

    assert mutated.verification_report.success is False


def test_taylor_coefficients_reject_excessive_order() -> None:
    with pytest.raises(ValueError, match="order must be at most 64"):
        taylor_coefficients("sine", order=65)

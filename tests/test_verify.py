"""Tiered function verification: numerical screen, symbolic proof, rigorous enclosure."""

from __future__ import annotations

import pytest
import sympy as sp

from geometric_function_atlas.contracts import (
    InvalidInputError,
    ResourceLimitError,
)
from geometric_function_atlas.records import validate_screen_record
from geometric_function_atlas.verify import (
    TIERS,
    verify_function,
)


def test_screen_tier_detects_non_starlike_polynomial() -> None:
    result = verify_function(coefficients=[1.0], property="starlike", max_cost="screen")
    assert result.tier == "screen"
    assert result.evidence_kind == "numerical_screen"
    assert result.outcome == "fails_screen"
    assert result.min_margin < 0
    # The screen executed consistently; the verdict lives in `outcome`.
    assert result.verification_report.success


def test_screen_tier_passes_for_c01_safe_polynomial() -> None:
    result = verify_function(coefficients=[0.25], property="starlike", max_cost="screen")
    assert result.outcome == "passes_screen"
    assert result.min_margin > 0
    assert result.verification_report.success


def test_symbolic_tier_proves_starlike_for_polynomial() -> None:
    result = verify_function(coefficients=[0.25], property="starlike", max_cost="symbolic")
    assert result.tier == "symbolic"
    assert result.evidence_kind == "exact_proof"
    assert result.outcome == "proven"
    names = {check.name for check in result.verification_report.checks}
    assert {"c01_exact_sum", "alexander_convexity_sum"} <= names


def test_symbolic_tier_proves_convex_and_univalent_by_implication() -> None:
    result = verify_function(coefficients=[0.25], property="convex", max_cost="symbolic")
    assert result.outcome == "proven"
    assert result.details["convex_sum"] == "1"


def test_symbolic_tier_record_serializes_without_nan() -> None:
    # The symbolic tier has no grid margin; its record must serialize as a
    # closed JSON payload with min_margin null (NaN breaks the JSON contract).
    result = verify_function(coefficients=[0.25], property="starlike", max_cost="symbolic")
    assert result.min_margin is None
    record = result.to_dict()
    assert record["details"]["min_margin"] is None
    validate_screen_record(record)


def test_symbolic_tier_is_inconclusive_for_undecided_truncation() -> None:
    # A truncation with a partial sum below 1 proves nothing about the tail.
    result = verify_function(
        coefficients=[0.25], property="starlike", max_cost="symbolic", truncation=True
    )
    assert result.outcome == "inconclusive_truncation"
    assert result.evidence_kind == "inconclusive"


def test_symbolic_tier_reports_c01_failure_as_not_a_proof() -> None:
    result = verify_function(coefficients=[1.0], property="starlike", max_cost="symbolic")
    assert result.outcome == "c01_fails_sufficient_condition"
    assert result.evidence_kind == "inconclusive"


def test_symbolic_tier_rejects_non_finite_coefficients() -> None:
    with pytest.raises(ValueError, match="finite"):
        verify_function(coefficients=[float("nan")], max_cost="symbolic")


def test_rigorous_tier_certifies_violation_for_non_starlike_polynomial() -> None:
    result = verify_function(coefficients=[1.0], property="starlike", max_cost="rigorous")
    assert result.tier == "rigorous"
    assert result.evidence_kind == "certified_enclosure"
    assert result.outcome == "certified_violation"
    assert result.witness_point is not None
    assert result.certified


def test_rigorous_tier_proves_starlike_for_safe_polynomial() -> None:
    result = verify_function(coefficients=[0.25], property="starlike", max_cost="rigorous")
    assert result.outcome == "proven"
    assert result.evidence_kind == "exact_proof"


def test_rigorous_tier_certifies_becker_criterion_violation() -> None:
    result = verify_function(
        coefficients=[1.0], property="becker_univalent", max_cost="rigorous"
    )
    assert result.outcome == "certified_violation"
    assert result.certified


def test_closed_form_polynomial_is_proven() -> None:
    zz = sp.symbols("z")
    closed_form = sp.expand(zz + zz**2 / 4)
    result = verify_function(closed_form=closed_form, max_cost="symbolic")
    assert result.outcome == "proven"
    assert result.evidence_kind == "exact_proof"


def test_closed_form_rational_is_not_silently_a_proof() -> None:
    zz = sp.symbols("z")
    result = verify_function(closed_form=zz / (1 - zz), max_cost="symbolic")
    assert result.outcome == "c01_fails_sufficient_condition"


def test_closed_form_rejects_unnormalized_function() -> None:
    zz = sp.symbols("z")
    with pytest.raises(InvalidInputError, match="normalized"):
        verify_function(closed_form=1 + zz, max_cost="symbolic")


def test_invalid_tier_is_rejected() -> None:
    with pytest.raises(InvalidInputError, match="max_cost"):
        verify_function(coefficients=[0.25], max_cost="exact")  # type: ignore[arg-type]


def test_invalid_property_is_rejected() -> None:
    with pytest.raises(InvalidInputError, match="property"):
        verify_function(coefficients=[0.25], property="not_a_property", max_cost="screen")


def test_to_dict_produces_a_valid_closed_record() -> None:
    result = verify_function(coefficients=[1.0], max_cost="rigorous")
    record = result.to_dict()
    assert record["record_type"] == "function_verification"
    assert record["tier"] == "rigorous"
    assert record["novelty_claim"] is False
    validate_screen_record(record)


def test_coefficient_length_is_bounded() -> None:
    with pytest.raises(ResourceLimitError):
        verify_function(coefficients=[0.01] * 300, max_cost="screen")


def test_tiers_are_exactly_the_documented_set() -> None:
    assert TIERS == ("screen", "symbolic", "rigorous")

"""Closed analysis records for screens, searches, verifications, and lab metrics."""

from __future__ import annotations

import pytest

from geometric_function_atlas.contracts import (
    CheckStatus,
    FailureState,
    VerificationCheck,
    VerificationReport,
)
from geometric_function_atlas.records import (
    SCREEN_RECORD_VERSION,
    RecordError,
    build_screen_record,
    validate_screen_record,
)


def _report() -> VerificationReport:
    return VerificationReport(
        checks=(
            VerificationCheck(
                name="grid_screen",
                checked="starlikeness on a sampled disk grid",
                expected="Re(z f'/f) > 0 on the grid",
                observed="min margin 0.31",
                status=CheckStatus.PASS,
                scope="float winding-number screen",
            ),
        )
    )


def test_screen_record_builds_and_validates() -> None:
    record = build_screen_record(
        record_type="class_admissibility",
        canonical_inputs={"class_key": "exponential"},
        method="ma_minda_admissibility_screens",
        evidence_kind="numerical_screen",
        tier="screen",
        assumptions=("phi is the named catalog generator",),
        source_references=("Mendiratta, Nagpal & Ravichandran (2015)",),
        verification=_report(),
        details={"admissible": True, "fraction_passed": 1.0},
    )
    assert record["schema_version"] == SCREEN_RECORD_VERSION
    assert record["failure_state"] is None
    validate_screen_record(record)


def test_unknown_record_type_is_rejected() -> None:
    record = build_screen_record(
        record_type="not_a_real_record",
        canonical_inputs={"x": 1},
        method="m",
        evidence_kind="numerical_screen",
        tier="screen",
        assumptions=("a",),
        source_references=("s",),
        verification=_report(),
    )
    with pytest.raises(RecordError, match="record_type"):
        validate_screen_record(record)


def test_unknown_evidence_kind_is_rejected() -> None:
    record = build_screen_record(
        record_type="class_admissibility",
        canonical_inputs={"class_key": "exponential"},
        method="m",
        evidence_kind="definitely_a_proof",
        tier="screen",
        assumptions=("a",),
        source_references=("s",),
        verification=_report(),
    )
    with pytest.raises(RecordError, match="evidence_kind"):
        validate_screen_record(record)


def test_failed_non_screen_record_requires_failure_state() -> None:
    failed = VerificationReport(
        checks=(
            VerificationCheck(
                name="interval_certification",
                checked="certified interval at the worst screened point",
                expected="threshold-separated enclosure",
                observed="unresolved",
                status=CheckStatus.FAIL,
                scope="mpmath interval arithmetic",
                failure_reason="evaluation is singular at the witness point",
            ),
        )
    )
    record = build_screen_record(
        record_type="witness_search",
        canonical_inputs={"property": "starlike", "coefficients": ["1/4"]},
        method="grid_search_then_interval_certification",
        evidence_kind="certified_enclosure",
        tier="rigorous",
        assumptions=("a",),
        source_references=("s",),
        verification=failed,
    )
    with pytest.raises(RecordError, match="failure_state"):
        validate_screen_record(record)


def test_failed_screen_may_carry_a_negative_finding_without_failure_state() -> None:
    failed = VerificationReport(
        checks=(
            VerificationCheck(
                name="subordination_winding_screen",
                checked="z f'/f lies inside the sampled boundary of phi(D)",
                expected="all sampled values inside",
                observed="383/384 inside",
                status=CheckStatus.FAIL,
                scope="float winding-number screen (not a proof)",
                failure_reason="grid value lies outside the sampled boundary",
            ),
        )
    )
    record = build_screen_record(
        record_type="class_membership",
        canonical_inputs={"class_key": "exponential", "coefficients": ["1/4"]},
        method="ma_minda_membership_winding_screen",
        evidence_kind="numerical_screen",
        tier="screen",
        assumptions=("a",),
        source_references=("s",),
        verification=failed,
    )
    validate_screen_record(record)
    assert record["verification"]["success"] is False
    assert record["failure_state"] is None


def test_successful_record_rejects_failure_state() -> None:
    record = build_screen_record(
        record_type="class_admissibility",
        canonical_inputs={"class_key": "exponential"},
        method="ma_minda_admissibility_screens",
        evidence_kind="numerical_screen",
        tier="screen",
        assumptions=("a",),
        source_references=("s",),
        verification=_report(),
        failure_state=FailureState.UNRESOLVED,
    )
    with pytest.raises(RecordError, match="failure_state"):
        validate_screen_record(record)


def test_record_type_specific_input_keys_are_enforced() -> None:
    record = build_screen_record(
        record_type="class_admissibility",
        canonical_inputs={"inner": "sine", "outer": "exponential"},
        method="ma_minda_admissibility_screens",
        evidence_kind="numerical_screen",
        tier="screen",
        assumptions=("a",),
        source_references=("s",),
        verification=_report(),
    )
    with pytest.raises(RecordError, match="canonical_inputs"):
        validate_screen_record(record)


def test_novelty_claim_is_always_false() -> None:
    record = build_screen_record(
        record_type="witness_search",
        canonical_inputs={"property": "starlike", "coefficients": ["1/2"]},
        method="grid_search_then_interval_certification",
        evidence_kind="certified_enclosure",
        tier="rigorous",
        assumptions=("f is the supplied finite polynomial",),
        source_references=("gft.pointwise parity fixture",),
        verification=_report(),
    )
    assert record["novelty_claim"] is False
    validate_screen_record(record)


def test_record_is_json_serializable() -> None:
    import json

    record = build_screen_record(
        record_type="class_containment",
        canonical_inputs={"inner": "sine", "outer": "exponential"},
        method="m",
        evidence_kind="numerical_screen",
        tier="screen",
        assumptions=("a",),
        source_references=("s",),
        verification=_report(),
        details={"contained": True, "margin": 0.1},
    )
    text = json.dumps(record, allow_nan=False)
    assert '"record_type": "class_containment"' in text

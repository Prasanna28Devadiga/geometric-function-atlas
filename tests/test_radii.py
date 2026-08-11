from __future__ import annotations

import json
from dataclasses import replace

import pytest

from geometric_function_atlas import (
    FailureState,
    RadiusReplayResult,
    RadiusStatus,
    list_radii,
    radius,
    replay_radius_certificate,
    verify_radius_certificate,
)
from geometric_function_atlas.contracts import ResourceLimitError

EXPECTED_COUNTS = {
    RadiusStatus.TOUCH_PROVEN_EXACT: 323,
    RadiusStatus.CLOSED_FORM_CONFIRMED: 140,
    RadiusStatus.TRIVIAL_CONTAINMENT: 142,
    RadiusStatus.UNIDENTIFIED: 85,
    RadiusStatus.AUDIT_REQUIRED: 12,
}


def test_radius_snapshot_preserves_every_status_and_direction() -> None:
    records = list_radii()
    assert len(records) == 702
    assert {record.status for record in records} == set(EXPECTED_COUNTS)
    assert {status: sum(record.status is status for record in records) for status in EXPECTED_COUNTS} == EXPECTED_COUNTS
    assert all(record.source_class != record.target_class for record in records)
    assert all(record.direction == f"{record.source_class}->{record.target_class}" for record in records)
    assert all(record.provenance.source_snapshot_commit for record in records)


def test_directed_lookup_keeps_exact_identity_and_review_metadata() -> None:
    record = radius("sine", "sigmoid")

    assert record.status is RadiusStatus.TOUCH_PROVEN_EXACT
    assert record.value_exact == "asin((E-1)/(E+1))"
    assert record.direction == "sine->sigmoid"
    assert record.inverse_branch_and_domain
    assert record.global_containment_route
    assert record.contact_and_attainment
    assert record.provenance.source_locator
    payload = record.to_dict()
    assert payload["result_type"] == "radius"
    assert payload["canonical_inputs"] == {"inner": "sine", "target": "sigmoid"}
    assert payload["exact_expressions"]["radius"] == record.value_exact
    assert payload["exact_expression_dag"]["roots"]["radius"]
    assert payload["novelty_claim"] is False


def test_reverse_direction_is_a_different_lookup() -> None:
    reverse = radius("sigmoid", "sine")
    forward = radius("sine", "sigmoid")
    assert reverse.direction == "sigmoid->sine"
    assert reverse.direction != forward.direction
    assert reverse.value_exact != forward.value_exact


def test_all_reviewed_exact_lanes_replay_with_verified_steps() -> None:
    reviewed = [record for record in list_radii() if record.certificate is not None]
    assert len(reviewed) == 8

    for record in reviewed:
        result = replay_radius_certificate(record)
        assert isinstance(result, RadiusReplayResult)
        assert result.status == "proven", result.to_dict()
        assert result.certified is True
        assert result.candidate == record.value_exact
        assert result.steps and all(step.verified for step in result.steps)


def test_replay_rejects_malformed_candidate_without_certifying() -> None:
    result = verify_radius_certificate(
        "sine", "sigmoid", candidate="asin((E-1)/(E+1)"
    )

    assert result.status == "invalid_input"
    assert result.certified is False
    assert result.failure_state is FailureState.INVALID_INPUT


def test_replay_reports_inexact_candidate_as_invalid_input() -> None:
    result = verify_radius_certificate("sine", "sigmoid", candidate="1.2")

    assert result.status == "invalid_input"
    assert result.certified is False
    assert result.failure_state is FailureState.INVALID_INPUT


def test_replay_rejects_wrong_direction_and_candidate_substitution() -> None:
    record = radius("sine", "sigmoid")
    mutated = replace(record, source_class="sigmoid", target_class="sine")
    result = replay_radius_certificate(mutated)

    assert result.status == "corrupt_artifact"
    assert result.certified is False
    assert "direction" in result.error.lower()

    result = verify_radius_certificate(
        "sine", "sigmoid", candidate="asinh((E-1)/(E+1))"
    )
    assert result.status == "candidate_mismatch"
    assert result.certified is False


def test_replay_rejects_missing_branch_or_evidence() -> None:
    record = radius("crescent", "lemniscate")
    missing_branch = replace(record, inverse_branch_and_domain="")
    missing_evidence = replace(record, global_containment_route="")

    for mutated in (missing_branch, missing_evidence):
        result = replay_radius_certificate(mutated)
        assert result.status == "corrupt_artifact"
        assert result.certified is False


def test_replay_rejects_changed_nonempty_certificate_evidence() -> None:
    record = radius("sine", "sigmoid")
    mutations = (
        replace(record, inverse_branch_and_domain="a different branch"),
        replace(record, global_containment_route="a different containment route"),
        replace(record, contact_and_attainment="a different contact point"),
        replace(record, assumptions=("a different assumption",)),
    )

    for mutated in mutations:
        result = replay_radius_certificate(mutated)
        assert result.status == "corrupt_artifact", result.to_dict()
        assert result.certified is False


def test_replay_rejects_source_hash_mismatch() -> None:
    record = radius("starlike", "order_0.75")
    provenance = replace(record.provenance, source_snapshot_commit="forged")
    result = replay_radius_certificate(replace(record, provenance=provenance))

    assert result.status == "corrupt_artifact"
    assert result.certified is False
    assert "source" in result.error.lower() or "hash" in result.error.lower()


def test_replay_has_a_bounded_resource_failure() -> None:
    with pytest.raises(ResourceLimitError):
        verify_radius_certificate(
            "sine", "sigmoid", candidate="1" * 10_000
        )


def test_radius_result_json_round_trip_is_deterministic() -> None:
    record = radius("exponential", "lemniscate")
    replay = replay_radius_certificate(record)

    assert json.loads(json.dumps(record.to_dict())) == record.to_dict()
    assert replay_radius_certificate(record.to_dict()).status == "proven"
    assert json.loads(json.dumps(replay.to_dict())) == replay.to_dict()


def test_radius_cli_commands_emit_typed_records() -> None:
    # Kept here as an API-level anchor; CLI coverage lives beside existing CLI tests.
    assert radius("exponential", "order_0.5").value_exact == "log(2)"
    assert replay_radius_certificate(radius("sine", "tanh")).status == "proven"

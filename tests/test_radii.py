from __future__ import annotations

import json
from dataclasses import replace

import pytest
import sympy as sp
from jsonschema import Draft202012Validator

from geometric_function_atlas import (
    FailureState,
    RadiusRecord,
    RadiusReplayResult,
    RadiusStatus,
    audit_radius,
    identify_radius,
    list_radii,
    radius,
    recompute_radius,
    replay_radius_certificate,
    verify_radius_attainment,
    verify_radius_certificate,
)
from geometric_function_atlas.contracts import (
    ResourceLimitError,
    _decode_expression_dag,
    load_result_schema,
    validate_result_payload,
)
from geometric_function_atlas.models import canonical_expression_dag

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


def test_radius_exact_dag_round_trips_through_closed_decoder() -> None:
    payload = radius("sine", "sigmoid").to_dict()
    dag = payload["exact_expression_dag"]

    decoded = _decode_expression_dag(dag, required_roots=("radius",))

    assert canonical_expression_dag(decoded) == dag


def test_radius_payload_is_validated_by_the_public_result_contract() -> None:
    payload = radius("sine", "sigmoid").to_dict()

    validate_result_payload(payload)
    Draft202012Validator(load_result_schema()).validate(payload)


def test_every_radius_snapshot_payload_is_closed_and_schema_valid() -> None:
    validator = Draft202012Validator(load_result_schema())

    for record in list_radii():
        payload = record.to_dict()
        validate_result_payload(payload)
        validator.validate(payload)


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


def test_reviewed_radius_replay_does_not_use_string_sympify(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("radius replay must not call sympify on a string")

    monkeypatch.setattr(sp, "sympify", forbidden)
    result = verify_radius_certificate("sine", "sigmoid")

    assert result.status == "proven"
    assert result.certified is True


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


def test_snapshot_row_without_bundled_certificate_is_not_replayable() -> None:
    record = radius("exponential", "sine")

    assert record.certificate is None
    assert record.status is RadiusStatus.TOUCH_PROVEN_EXACT

    result = replay_radius_certificate(record)

    assert result.status == "not_replayable"
    assert result.certified is False
    assert result.failure_state is FailureState.UNSUPPORTED
    assert result.error is not None
    assert "certificate" in result.error
    assert "touch_proven_exact" in result.error
    # A missing bundled certificate is not damage: the snapshot row keeps its
    # own evidence status and stays untouched.
    assert radius("exponential", "sine").status is RadiusStatus.TOUCH_PROVEN_EXACT
    assert record.to_dict()["evidence_status"] == "proven_exact_under_declared_assumptions"


def test_recompute_verify_and_attainment_report_unavailable_replay() -> None:
    results = {
        "recompute": recompute_radius("exponential", "sine"),
        "verify": verify_radius_certificate("exponential", "sine"),
        "attainment": verify_radius_attainment("exponential", "sine"),
    }

    for label, result in results.items():
        assert result.status == "not_replayable", label
        assert result.certified is False, label
        assert result.failure_state is FailureState.UNSUPPORTED, label


def test_radius_audit_reports_unavailable_replay_without_damaging_the_row() -> None:
    payload = audit_radius("exponential", "sine")

    assert payload["status"] == "not_replayable"
    assert payload["evidence_status"] == "touch_proven_exact"
    assert payload["attainment_verified"] is False
    assert payload["novelty_claim"] is False
    replay = payload["certificate_replay"]
    assert replay["failure_state"] == "unsupported"
    assert replay["certified"] is False
    assert replay["status"] == "not_replayable"


def test_mutated_certificate_bearing_record_stays_corrupt_artifact() -> None:
    record = radius("sine", "sigmoid")
    mutated = replace(record, value_exact="asin((E-1)/(E+2))")

    result = replay_radius_certificate(mutated)

    assert result.status == "corrupt_artifact"
    assert result.status != "not_replayable"
    assert result.failure_state is FailureState.CORRUPT_ARTIFACT
    assert result.certified is False


def _mutate_certificate(record: RadiusRecord, **changes: object) -> RadiusRecord:
    assert record.certificate is not None
    return replace(record, certificate=replace(record.certificate, **changes))


MUTATED_CERTIFICATE_RECORDS = {
    "value_exact": lambda record: replace(record, value_exact="asin((E-1)/(E+2))"),
    "assumptions": lambda record: replace(record, assumptions=("a different assumption",)),
    "branch": lambda record: replace(record, inverse_branch_and_domain="a different branch"),
    "containment": lambda record: replace(record, global_containment_route="a different route"),
    "attainment": lambda record: replace(record, contact_and_attainment="a different contact"),
    "provenance_hash": lambda record: replace(
        record, provenance=replace(record.provenance, fixture_sha256="0" * 64)
    ),
    "certificate_candidate": lambda record: _mutate_certificate(
        record, exact_candidate="asin((E-1)/(E+2))"
    ),
    "certificate_steps": lambda record: _mutate_certificate(
        record, machine_steps=("forged step",)
    ),
    "certificate_machine_status": lambda record: _mutate_certificate(
        record, machine_status="unverified"
    ),
    "certificate_baked_status": lambda record: _mutate_certificate(
        record, baked_status="unidentified"
    ),
}


@pytest.mark.parametrize("mutation", sorted(MUTATED_CERTIFICATE_RECORDS))
def test_every_mutated_certificate_bearing_record_fails_closed(mutation: str) -> None:
    mutated = MUTATED_CERTIFICATE_RECORDS[mutation](radius("sine", "sigmoid"))

    result = replay_radius_certificate(mutated)

    assert result.status == "corrupt_artifact", (mutation, result.to_dict())
    assert result.status != "not_replayable", mutation
    assert result.certified is False, mutation
    assert result.failure_state is FailureState.CORRUPT_ARTIFACT, mutation
    assert result.error, mutation


def test_not_replayable_payload_remains_deterministic_json() -> None:
    payload = replay_radius_certificate(radius("exponential", "sine")).to_dict()

    assert payload["status"] == "not_replayable"
    assert payload["failure_state"] == "unsupported"
    assert payload["certified"] is False
    assert json.loads(json.dumps(payload)) == payload


def test_removing_a_bundled_certificate_is_corrupt_artifact_not_unavailable() -> None:
    record = radius("sine", "sigmoid")
    assert record.certificate is not None

    result = replay_radius_certificate(replace(record, certificate=None))

    assert result.status == "corrupt_artifact"
    assert result.status != "not_replayable"
    assert result.failure_state is FailureState.CORRUPT_ARTIFACT
    assert result.certified is False
    assert result.error
    # The untouched reviewed lane still replays: only the mutation is condemned.
    assert replay_radius_certificate(record).status == "proven"


MUTATED_SNAPSHOT_ROW_WITHOUT_CERTIFICATE = {
    "value_exact": lambda record: replace(record, value_exact="1/7"),
    "value_decimal": lambda record: replace(record, value_decimal="0.123456789"),
    "value_float": lambda record: replace(record, value_float=0.123456789),
    "status": lambda record: replace(record, status=RadiusStatus.CLOSED_FORM_CONFIRMED),
    "provenance_commit": lambda record: replace(
        record, provenance=replace(record.provenance, source_snapshot_commit="forged")
    ),
    "provenance_hash": lambda record: replace(
        record, provenance=replace(record.provenance, fixture_sha256="0" * 64)
    ),
}


@pytest.mark.parametrize("mutation", sorted(MUTATED_SNAPSHOT_ROW_WITHOUT_CERTIFICATE))
def test_mutating_an_uncertificated_snapshot_row_is_corrupt_artifact(mutation: str) -> None:
    record = radius("exponential", "sine")
    assert record.certificate is None

    result = replay_radius_certificate(MUTATED_SNAPSHOT_ROW_WITHOUT_CERTIFICATE[mutation](record))

    assert result.status == "corrupt_artifact", (mutation, result.to_dict())
    assert result.status != "not_replayable", mutation
    assert result.failure_state is FailureState.CORRUPT_ARTIFACT, mutation
    assert result.certified is False, mutation
    assert result.error, mutation
    # ``unsupported`` describes only the pristine snapshot row, never its mutations.
    assert replay_radius_certificate(record).status == "not_replayable", mutation


def test_mapping_without_a_certificate_cannot_downgrade_a_reviewed_lane() -> None:
    payload = radius("sine", "sigmoid").to_dict()
    assert isinstance(payload["certificate"], dict)
    deleted = {key: value for key, value in payload.items() if key != "certificate"}
    explicit_none = dict(payload, certificate=None)

    for label, stripped in (("deleted", deleted), ("explicit_none", explicit_none)):
        result = replay_radius_certificate(stripped)

        assert result.status == "corrupt_artifact", (label, result.to_dict())
        assert result.status != "not_replayable", label
        assert result.failure_state is FailureState.CORRUPT_ARTIFACT, label
        assert result.certified is False, label

    # The intact mapping still replays, so the verdict flips only on the deletion.
    assert replay_radius_certificate(payload).status == "proven"


def test_mapping_form_of_a_pristine_uncertificated_row_stays_unavailable() -> None:
    result = replay_radius_certificate(radius("exponential", "sine").to_dict())

    assert result.status == "not_replayable"
    assert result.failure_state is FailureState.UNSUPPORTED
    assert result.certified is False


def test_uncertificated_row_absent_from_the_snapshot_is_corrupt_artifact() -> None:
    payload = radius("exponential", "sine").to_dict()
    payload["canonical_inputs"] = {"inner": "no_such_inner", "target": "no_such_target"}

    result = replay_radius_certificate(payload)

    # A direction that is not a trusted snapshot row is a consistency failure,
    # never benign unavailability.
    assert result.status == "corrupt_artifact"
    assert result.failure_state is FailureState.CORRUPT_ARTIFACT
    assert result.certified is False


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


def test_radius_recompute_identify_audit_and_attainment_are_bounded() -> None:
    record = radius("sine", "sigmoid")

    recomputed = recompute_radius("sine", "sigmoid")
    assert recomputed.certified is True
    assert recomputed.status == "proven"
    assert identify_radius(record.value_exact) == (record,)
    audit = audit_radius("sine", "sigmoid")
    assert audit["status"] == "proven"
    assert audit["attainment_verified"] is True
    assert verify_radius_attainment("sine", "sigmoid").certified is True

from __future__ import annotations

import json
import math

import pytest
import sympy as sp

from geometric_function_atlas import (
    RESULT_SCHEMA_VERSION,
    CheckStatus,
    FailureState,
    Generator,
    VerificationCheck,
    VerificationReport,
    failure_payload,
    fekete_szego,
    generator_series,
    get_trusted_implementation,
    load_error_schema,
    load_result_schema,
    validate_error_payload,
    validate_result_payload,
    z,
)


def test_phase_one_result_has_closed_versioned_contract() -> None:
    payload = generator_series("sine", order=4).to_dict()

    assert payload["schema_version"] == RESULT_SCHEMA_VERSION == 1
    assert payload["result_type"] == "generator_series"
    assert payload["canonical_inputs"] == {"generator": "sine", "order": 4}
    assert payload["exact_expressions"]["generator"] == "sin(z) + 1"
    assert payload["computational_status"] == payload["evidence_status"]
    assert payload["source_references"]
    assert payload["literature_status"] == "not_assessed"
    assert payload["novelty_claim"] is False
    assert payload["failure_state"] is None
    assert payload["verification"]["success"] is True
    assert json.loads(json.dumps(payload)) == payload
    validate_result_payload(payload)


def test_fekete_result_contract_keeps_exact_inputs_and_verification() -> None:
    payload = fekete_szego("exponential", mu="1/2").to_dict()

    assert payload["result_type"] == "fekete_szego"
    assert payload["canonical_inputs"] == {"generator": "exponential", "mu": "1/2"}
    assert payload["exact_expressions"]["value"] == "1/2"
    assert payload["verification"]["success"] is True
    validate_result_payload(payload)


def test_result_contract_requires_operation_specific_fields_and_consistency() -> None:
    payload = generator_series("sine", order=4).to_dict()

    missing = {**payload, "canonical_inputs": {"generator": "sine"}}
    with pytest.raises(ValueError, match="canonical_inputs.*order"):
        validate_result_payload(missing)

    inconsistent = {**payload, "order": 99}
    with pytest.raises(ValueError, match="order.*canonical_inputs"):
        validate_result_payload(inconsistent)


def test_result_contract_rejects_mismatched_exact_expression_and_legacy_fields() -> None:
    payload = generator_series("sine", order=4).to_dict()

    payload["exact_expressions"]["coefficients"] = ["99"]
    with pytest.raises(ValueError, match="exact_expressions.*coefficients"):
        validate_result_payload(payload)


def test_result_contract_rejects_wrong_schema_version_type() -> None:
    payload = generator_series("sine", order=2).to_dict()

    with pytest.raises(TypeError, match="schema_version"):
        validate_result_payload({**payload, "schema_version": True})


def test_result_contract_rejects_unhashable_discriminator_values() -> None:
    payload = generator_series("sine", order=2).to_dict()

    with pytest.raises(TypeError, match="result_type"):
        validate_result_payload({**payload, "result_type": {"execute": "id"}})
    with pytest.raises(TypeError, match="failure_state"):
        validate_result_payload({**payload, "failure_state": ["unresolved"]})


def test_failed_verification_serializes_as_explicit_unresolved_state() -> None:
    generator = generator_series("sine", order=2)
    failed = generator.__class__(
        generator=generator.generator,
        order=generator.order,
        coefficients=(99, 99),
    )

    payload = failed.to_dict()

    assert payload["failure_state"] == "unresolved"
    assert payload["computational_status"] == "unresolved"
    assert payload["verification"]["success"] is False
    validate_result_payload(payload)


def test_verification_report_fails_closed_for_required_skip_and_failure() -> None:
    skipped = VerificationReport(
        checks=(
            VerificationCheck(
                name="required-check",
                checked="an exact identity",
                expected="1",
                observed="unknown",
                status=CheckStatus.SKIP,
                scope="unit test",
            ),
        )
    )
    failed = VerificationReport(
        checks=(
            VerificationCheck(
                name="failed-check",
                checked="an exact identity",
                expected="1",
                observed="2",
                status=CheckStatus.FAIL,
                scope="unit test",
                failure_reason="mutation detected",
            ),
        )
    )

    assert skipped.success is False
    assert skipped.status == "skipped"
    assert failed.success is False
    assert failed.status == "failed"
    assert failed.to_dict()["checks"][0]["failure_reason"] == "mutation detected"


def test_verification_report_requires_at_least_one_required_passing_check() -> None:
    report = VerificationReport(
        checks=(
            VerificationCheck(
                name="optional-check",
                checked="an optional property",
                expected=True,
                observed=False,
                status=CheckStatus.SKIP,
                scope="unit test",
                required=False,
            ),
        )
    )

    assert report.success is False
    assert report.status == "skipped"


def test_failure_states_are_explicit_and_schema_is_closed() -> None:
    assert {state.value for state in FailureState} == {
        "unsupported",
        "unresolved",
        "invalid_input",
        "resource_limit",
        "corrupt_artifact",
    }
    payload = generator_series("sine", order=2).to_dict()
    payload["unexpected"] = "must be rejected"

    with pytest.raises(ValueError, match="unexpected"):
        validate_result_payload(payload)


def test_nested_canonical_and_exact_fields_are_closed_too() -> None:
    payload = generator_series("sine", order=2).to_dict()
    payload["canonical_inputs"]["execute"] = "__import__('os').system('id')"

    with pytest.raises(ValueError, match="canonical_inputs.*unexpected"):
        validate_result_payload(payload)


def test_verification_aggregate_cannot_be_mutated_to_success() -> None:
    payload = generator_series("sine", order=2).to_dict()
    check = payload["verification"]["checks"][0]
    check["status"] = "fail"
    check["failure_reason"] = "mutated normalization"

    with pytest.raises(ValueError, match="verification aggregate"):
        validate_result_payload(payload)


def test_result_value_fields_remain_non_executable_strings() -> None:
    payload = fekete_szego("sine", mu=0).to_dict()
    payload["value_exact"] = {"execute": "__import__('os').system('id')"}

    with pytest.raises(TypeError, match="value_exact"):
        validate_result_payload(payload)


def test_shipped_schemas_are_closed_and_failure_records_validate() -> None:
    result_schema = load_result_schema()
    error_schema = load_error_schema()

    assert result_schema["$id"].endswith("result-1.json")
    assert result_schema["additionalProperties"] is False
    assert error_schema["additionalProperties"] is False
    error = failure_payload(FailureState.CORRUPT_ARTIFACT, "checksum mismatch")
    validate_error_payload(error)

    with pytest.raises(ValueError, match="unexpected"):
        validate_error_payload({**error, "unexpected": "code"})

    with pytest.raises(TypeError, match="schema_version"):
        validate_error_payload({**error, "schema_version": "1"})
    with pytest.raises(TypeError, match="package_version"):
        validate_error_payload({**error, "package_version": 1})


def test_verification_values_reject_non_finite_json_numbers() -> None:
    check = VerificationCheck(
        name="finite",
        checked="finite value",
        expected=math.nan,
        observed=math.inf,
        status=CheckStatus.PASS,
        scope="unit test",
    )

    with pytest.raises(ValueError, match="finite JSON"):
        check.to_dict()


@pytest.mark.parametrize("value", [{1: "integer key"}, {1, 2}, frozenset({1, 2})])
def test_verification_values_reject_noncanonical_containers(value: object) -> None:
    check = VerificationCheck(
        name="strict",
        checked="strict JSON",
        expected=value,
        observed=None,
        status=CheckStatus.PASS,
        scope="unit test",
    )

    with pytest.raises((TypeError, ValueError), match="JSON|mapping|unordered"):
        check.to_dict()


def test_result_contract_requires_nonempty_operation_provenance() -> None:
    payload = generator_series("sine", order=2).to_dict()

    for key in ("assumptions", "source_references"):
        forged = {**payload, key: []}
        with pytest.raises(ValueError, match=key):
            validate_result_payload(forged)

    forged_artifacts = {**payload, "artifact_versions": {}}
    with pytest.raises(ValueError, match="artifact_versions"):
        validate_result_payload(forged_artifacts)

    forged_source = {
        **payload,
        "artifact_versions": {**payload["artifact_versions"], "source_commit": "forged"},
    }
    with pytest.raises(ValueError, match="source commit"):
        validate_result_payload(forged_source)


def test_result_contract_closes_evidence_and_literature_states() -> None:
    payload = generator_series("sine", order=2).to_dict()

    for key, value in (
        ("evidence_status", "caller_claimed"),
        ("method", "caller_method"),
        ("literature_status", "known"),
        ("provenance", "caller_supplied"),
    ):
        forged = {**payload, key: value}
        with pytest.raises(ValueError, match="status|method|literature|provenance"):
            validate_result_payload(forged)


def test_result_contract_rejects_partial_required_verification() -> None:
    payload = generator_series("sine", order=2).to_dict()
    payload["verification"]["checks"][0]["required"] = False

    with pytest.raises(ValueError, match="required|operation"):
        validate_result_payload(payload)


def test_result_contract_carries_bounded_authoritative_expression_dag() -> None:
    payload = generator_series("sine", order=2).to_dict()

    dag = payload["exact_expression_dag"]
    assert dag["roots"]["generator"]
    assert dag["nodes"]
    forged = {**payload, "exact_expression_dag": {**dag, "roots": {"generator": "missing"}}}
    with pytest.raises(ValueError, match="expression DAG"):
        validate_result_payload(forged)


def test_verification_check_names_are_non_empty_strings() -> None:
    with pytest.raises(ValueError, match="name"):
        VerificationCheck(
            name="",
            checked="finite value",
            expected=1,
            observed=1,
            status=CheckStatus.PASS,
            scope="unit test",
        )


def test_trusted_registry_has_only_known_callable_implementations() -> None:
    assert get_trusted_implementation("generator_series") is generator_series
    assert get_trusted_implementation("fekete_szego") is fekete_szego

    with pytest.raises(KeyError, match="unknown trusted implementation"):
        get_trusted_implementation("os.system")


def test_exact_result_values_reject_decimal_digit_and_evaluate_false_attacks() -> None:
    oversized = sp.Integer(10) ** 128
    with pytest.raises(ValueError, match="resource bound|128 decimal digits"):
        fekete_szego("sine", mu=oversized)

    with pytest.raises(ValueError, match="resource bound|128 decimal digits"):
        Generator(
            key="oversized",
            name="Oversized exact coefficient",
            expression=1 + sp.Pow(10, 128, evaluate=False) * z,
            citation="Test",
        )

    with pytest.raises(ValueError, match="integer exponents|resource bound"):
        Generator(
            key="deferred-power",
            name="Deferred oversized power",
            expression=1 + sp.Pow(z, 1000000, evaluate=False),
            citation="Test",
        )


def test_successful_fekete_payload_recomputes_authoritative_values() -> None:
    payload = fekete_szego("exponential", mu=0).to_dict()
    payload["exact_expressions"].update(
        {"B1": "2", "B2": "7", "value": "11/2"}
    )
    payload.update({"B1": "2", "B2": "7", "value_exact": "11/2"})
    for check in payload["verification"]["checks"]:
        check["expected"] = check["observed"]
        check["status"] = "pass"
        check["failure_reason"] = None
    payload["verification"].update({"status": "passed", "success": True})

    with pytest.raises(ValueError, match="authoritative|generator|closed form"):
        validate_result_payload(payload)


def test_fekete_evidence_status_is_derived_not_constructor_settable() -> None:
    result = fekete_szego("exponential", mu=0)
    with pytest.raises(TypeError, match="evidence_status"):
        result.__class__(
            generator=result.generator,
            mu=result.mu,
            b1=result.b1,
            b2=result.b2,
            value=result.value,
            evidence_status="forged",
        )


def test_expression_dag_rejects_unreachable_and_invalid_rational_nodes() -> None:
    payload = generator_series("sine", order=2).to_dict()
    dag = payload["exact_expression_dag"]
    unreachable = {
        "id": "n999",
        "op": "integer",
        "value": "1",
    }
    with pytest.raises(ValueError, match="unreachable|canonical"):
        validate_result_payload(
            {**payload, "exact_expression_dag": {**dag, "nodes": [*dag["nodes"], unreachable]}}
        )

    invalid_rational = {
        "id": dag["nodes"][0]["id"],
        "op": "rational",
        "numerator": "1",
        "denominator": "0",
    }
    with pytest.raises(ValueError, match="rational|denominator"):
        validate_result_payload(
            {
                **payload,
                "exact_expression_dag": {
                    **dag,
                    "nodes": [invalid_rational, *dag["nodes"][1:]],
                },
            }
        )

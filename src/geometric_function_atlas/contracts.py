"""Versioned, fail-closed result and verification contracts.

The contract module contains data-only records. It deliberately has no dynamic
imports, expression parsing, or execution from serialized input.
"""

from __future__ import annotations

import json
import math
import re
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from importlib import resources
from typing import Any

import sympy as sp

from .models import Z, canonical_expression_dag, validate_exact_expression
from .version import (
    COUNTEREXAMPLE_FIXTURE_ID,
    FEKETE_FIXTURE_ID,
    GENERATOR_CATALOG_VERSION,
    GENERATOR_FIXTURE_ID,
    SOURCE_ARTIFACT_COMMIT,
    __version__,
)

RESULT_SCHEMA_VERSION = 1
MAX_JSON_DEPTH = 128
MAX_JSON_NODES = 10_000
_RESULT_TYPES = {
    "counterexample_verification",
    "generator_series",
    "fekete_szego",
}
_PROVENANCE_STATES = {"built_in", "caller_supplied"}
_REQUIRED_ARTIFACT_KEYS = {"generator_catalog", "source_commit", "fixture_or_proof"}
_OPERATION_ASSUMPTIONS = {
    "generator_series": {
        "phi(0) = 1",
        "expression uses only the variable z",
    },
    "fekete_szego": {
        "phi is an admissible Ma-Minda generator",
        "phi has real Taylor coefficients",
        "B1 is positive",
    },
    "counterexample_verification": {
        "f(z) is the supplied normalized polynomial",
        "the witness point lies in the open unit disk",
        "inputs are interpreted as exact IEEE-754 binary64 values",
    },
}
_OPERATION_CHECKS = {
    "generator_series": {"generator_normalization", "exact_taylor_coefficients"},
    "fekete_szego": {
        "generator_normalization",
        "generator_taylor_coefficients",
        "positive_real_first_coefficient",
        "real_second_coefficient",
        "exact_functional_value",
    },
    "counterexample_verification": {
        "classification_matches_interval",
        "interval_is_ordered",
    },
}
_DAG_OPS = {"integer", "rational", "symbol", "add", "mul", "pow", "function"}
_DAG_FUNCTIONS = {"Abs", "Max", "cos", "cosh", "exp", "log", "sin", "sinh"}
_DAG_ID_PATTERN = re.compile(r"n[0-9]+", flags=re.ASCII)
_INTEGER_PATTERN = re.compile(r"[+-]?[0-9]+", flags=re.ASCII)
_DENOMINATOR_PATTERN = re.compile(r"\+?[0-9]+", flags=re.ASCII)
_MAX_JSON_INTEGER = 10**128


class CheckStatus(str, Enum):
    """Outcome of one independently reviewable verification check."""

    PASS = "pass"
    FAIL = "fail"
    SKIP = "skip"


class FailureState(str, Enum):
    """Explicit non-success states for computations and artifact replay."""

    UNSUPPORTED = "unsupported"
    UNRESOLVED = "unresolved"
    INVALID_INPUT = "invalid_input"
    RESOURCE_LIMIT = "resource_limit"
    CORRUPT_ARTIFACT = "corrupt_artifact"


class LiteratureStatus(str, Enum):
    """Literature reconciliation is separate from computational evidence."""

    NOT_ASSESSED = "not_assessed"
    KNOWN = "known"
    CANDIDATE_IMPROVEMENT = "candidate_improvement"
    NO_EXTRACTED_CLAIM = "no_extracted_claim"
    UNRESOLVED = "unresolved"


class InvalidInputError(ValueError):
    """Raised when a public operation receives malformed or invalid input."""

    failure_state = FailureState.INVALID_INPUT.value


class ResourceLimitError(ValueError):
    """Raised before symbolic work exceeds a documented resource bound."""

    failure_state = FailureState.RESOURCE_LIMIT.value


class UnsupportedError(RuntimeError):
    """Raised for an operation or artifact kind outside the package scope."""

    failure_state = FailureState.UNSUPPORTED.value


class UnresolvedError(RuntimeError):
    """Raised when the available evidence cannot discharge a claim."""

    failure_state = FailureState.UNRESOLVED.value


class CorruptArtifactError(RuntimeError):
    """Raised when a supplied artifact fails structural or checksum checks."""

    failure_state = FailureState.CORRUPT_ARTIFACT.value


@dataclass(frozen=True, slots=True)
class VerificationCheck:
    """One check in a verification report.

    ``expected`` and ``observed`` are intentionally typed as ``Any`` so exact
    expressions, intervals, and structured certificate values can be carried
    without coercing them to floating point. ``to_dict`` converts them to a
    JSON-safe representation.
    """

    name: str
    checked: str
    expected: Any
    observed: Any
    status: CheckStatus | str
    scope: str
    failure_reason: str | None = None
    required: bool = True

    def __post_init__(self) -> None:
        for field_name in ("name", "checked", "scope"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(
                    f"verification check {field_name} must be a non-empty string"
                )
        try:
            status = CheckStatus(self.status)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"unknown verification check status: {self.status!r}") from exc
        object.__setattr__(self, "status", status)
        if self.failure_reason is not None and not isinstance(self.failure_reason, str):
            raise TypeError("verification check failure_reason must be a string or null")
        if status is CheckStatus.FAIL and not self.failure_reason:
            raise ValueError("failed verification checks require a failure_reason")
        if not isinstance(self.required, bool):
            raise TypeError("verification check required must be a bool")

    def to_dict(self) -> dict[str, Any]:
        """Return the closed JSON representation of this check."""

        return {
            "name": self.name,
            "checked": self.checked,
            "expected": _json_value(self.expected),
            "observed": _json_value(self.observed),
            "status": CheckStatus(self.status).value,
            "scope": self.scope,
            "failure_reason": self.failure_reason,
            "required": self.required,
        }


@dataclass(frozen=True, slots=True)
class VerificationReport:
    """Fail-closed aggregate of independently reviewable checks."""

    checks: tuple[VerificationCheck, ...]

    def __post_init__(self) -> None:
        checks = tuple(self.checks)
        if any(not isinstance(check, VerificationCheck) for check in checks):
            raise TypeError("verification checks must be VerificationCheck objects")
        if len({check.name for check in checks}) != len(checks):
            raise ValueError("verification check names must be unique")
        object.__setattr__(self, "checks", checks)

    @property
    def required_checks(self) -> tuple[VerificationCheck, ...]:
        return tuple(check for check in self.checks if check.required)

    @property
    def success(self) -> bool:
        """True only when at least one required check exists and all pass."""

        required = self.required_checks
        return bool(required) and all(
            check.status is CheckStatus.PASS for check in required
        )

    @property
    def status(self) -> str:
        """Stable aggregate status derived only from required checks."""

        required = self.required_checks
        if self.success:
            return "passed"
        if any(check.status is CheckStatus.FAIL for check in required):
            return "failed"
        return "skipped"

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "success": self.success,
            "checks": [check.to_dict() for check in self.checks],
        }


def _json_value(value: Any) -> Any:
    """Convert exact and nested values to strict deterministic JSON data."""

    if isinstance(value, Enum):
        return _json_value(value.value)
    if value is None or isinstance(value, (bool, str)):
        return value
    if isinstance(value, int):
        if abs(value) >= _MAX_JSON_INTEGER:
            raise ValueError("JSON integers exceed the 128-decimal-digit resource bound")
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("verification values must be finite JSON numbers")
        return value
    if isinstance(value, Mapping):
        if not all(isinstance(key, str) for key in value):
            raise TypeError("JSON object keys must be strings")
        result: dict[str, Any] = {}
        for key in sorted(value):
            item = value[key]
            result[key] = _json_value(item)
        return result
    if isinstance(value, (tuple, list)):
        return [_json_value(item) for item in value]
    if isinstance(value, (set, frozenset)):
        raise TypeError("unordered containers are not valid deterministic JSON values")
    raise TypeError(f"unsupported JSON value type: {type(value).__name__}")


def _validate_json_value(
    value: Any,
    *,
    label: str = "value",
    depth: int = 0,
    nodes: list[int] | None = None,
) -> None:
    """Validate values without coercing them or relying on permissive JSON."""

    if nodes is None:
        nodes = [0]
    nodes[0] += 1
    if nodes[0] > MAX_JSON_NODES:
        raise ValueError(f"{label} exceeds JSON node limit {MAX_JSON_NODES}")
    if depth > MAX_JSON_DEPTH:
        raise ValueError(f"{label} exceeds JSON depth limit {MAX_JSON_DEPTH}")
    if value is None or isinstance(value, (bool, str)):
        return
    if isinstance(value, int):
        if abs(value) >= _MAX_JSON_INTEGER:
            raise ValueError(
                f"{label} exceeds the 128-decimal-digit JSON integer bound"
            )
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"{label} must contain finite JSON numbers")
        return
    if isinstance(value, Mapping):
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError(f"{label} object keys must be strings")
            _validate_json_value(
                item, label=f"{label}.{key}", depth=depth + 1, nodes=nodes
            )
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _validate_json_value(
                item, label=f"{label}[{index}]", depth=depth + 1, nodes=nodes
            )
        return
    raise TypeError(f"{label} contains unsupported JSON value type {type(value).__name__}")


def build_result_payload(
    *,
    result_type: str,
    canonical_inputs: Mapping[str, Any],
    exact_expressions: Mapping[str, Any],
    method: str,
    evidence_status: str,
    assumptions: tuple[str, ...] | list[str],
    source_references: tuple[str, ...] | list[str],
    artifact_versions: Mapping[str, str],
    verification: VerificationReport,
    legacy_fields: Mapping[str, Any],
    exact_expression_dag: Mapping[str, Any],
    provenance: str,
    literature_status: LiteratureStatus | str = LiteratureStatus.NOT_ASSESSED,
    failure_state: FailureState | str | None = None,
) -> dict[str, Any]:
    """Build the stable envelope while retaining Phase-1 legacy fields."""

    status = LiteratureStatus(literature_status)
    failure = None if failure_state is None else FailureState(failure_state)
    effective_status = evidence_status
    if not verification.success:
        failure = failure or FailureState.UNRESOLVED
        effective_status = failure.value
    payload: dict[str, Any] = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "result_type": result_type,
        "canonical_inputs": _json_value(canonical_inputs),
        "exact_expressions": _json_value(exact_expressions),
        "exact_expression_dag": _json_value(exact_expression_dag),
        "method": method,
        "evidence_status": effective_status,
        "computational_status": effective_status,
        "assumptions": list(assumptions),
        "source_references": list(source_references),
        "package_version": __version__,
        "artifact_versions": dict(artifact_versions),
        "literature_status": status.value,
        "novelty_claim": False,
        "failure_state": None if failure is None else failure.value,
        "verification": verification.to_dict(),
        "provenance": provenance,
    }
    payload.update(_json_value(legacy_fields))
    json.dumps(payload, allow_nan=False)
    validate_result_payload(payload)
    return payload


def failure_payload(
    state: FailureState | str,
    message: str,
) -> dict[str, Any]:
    """Return a stable JSON error record for CLI and future artifact loaders."""

    failure = FailureState(state)
    return {
        "schema_version": RESULT_SCHEMA_VERSION,
        "result_type": "error",
        "failure_state": failure.value,
        "error": message,
        "package_version": __version__,
        "literature_status": LiteratureStatus.NOT_ASSESSED.value,
        "novelty_claim": False,
    }


def load_result_schema() -> dict[str, Any]:
    """Load the shipped closed JSON Schema without evaluating its contents."""

    resource = resources.files("geometric_function_atlas").joinpath(
        "schema/result.schema.json"
    )
    return json.loads(resource.read_text(encoding="utf-8"))


def load_error_schema() -> dict[str, Any]:
    """Load the shipped closed JSON error schema."""

    resource = resources.files("geometric_function_atlas").joinpath(
        "schema/error.schema.json"
    )
    return json.loads(resource.read_text(encoding="utf-8"))


def validate_result_payload(payload: Mapping[str, Any]) -> None:
    """Validate a structured result against the closed contract.

    This small dependency-free validator is intentionally stricter than merely
    checking that ``json.dumps`` succeeds. It rejects unknown keys so schema
    drift cannot silently enter a released artifact.
    """

    _validate_json_value(payload, label="result")
    required = {
        "schema_version",
        "result_type",
        "canonical_inputs",
        "exact_expressions",
        "exact_expression_dag",
        "method",
        "evidence_status",
        "computational_status",
        "assumptions",
        "source_references",
        "package_version",
        "artifact_versions",
        "literature_status",
        "novelty_claim",
        "failure_state",
        "verification",
        "provenance",
    }
    allowed = required | {
        "generator",
        "generator_formula",
        "generator_citation",
        "order",
        "coefficients",
        "mu",
        "B1",
        "B2",
        "value_exact",
        "value_decimal",
        "theorem_reference",
        "property",
        "point",
        "interval",
        "threshold",
        "certified",
        "direction",
    }
    _check_mapping_keys(payload, allowed, "result")
    missing = required - payload.keys()
    if missing:
        raise ValueError(f"result is missing required keys: {sorted(missing)}")
    if isinstance(payload["schema_version"], bool) or not isinstance(
        payload["schema_version"], int
    ):
        raise TypeError("schema_version must be an integer")
    if payload["schema_version"] != RESULT_SCHEMA_VERSION:
        raise ValueError("unsupported result schema_version")
    if not isinstance(payload["result_type"], str):
        raise TypeError("result_type must be a string")
    if payload["result_type"] not in _RESULT_TYPES:
        raise ValueError(f"unsupported result_type: {payload['result_type']!r}")
    if not isinstance(payload["provenance"], str) or payload["provenance"] not in _PROVENANCE_STATES:
        raise ValueError("unknown provenance state")
    if not isinstance(payload["canonical_inputs"], Mapping):
        raise TypeError("canonical_inputs must be an object")
    if not isinstance(payload["exact_expressions"], Mapping):
        raise TypeError("exact_expressions must be an object")
    _check_mapping_keys(
        payload["canonical_inputs"],
        {
            "generator",
            "order",
            "mu",
            "inner",
            "target",
            "property",
            "coefficients",
            "point",
        },
        "canonical_inputs",
    )
    _check_mapping_keys(
        payload["exact_expressions"],
        {
            "generator",
            "coefficients",
            "B1",
            "B2",
            "value",
            "point",
            "interval",
            "threshold",
        },
        "exact_expressions",
    )
    for key in (
        "method",
        "evidence_status",
        "computational_status",
        "package_version",
    ):
        if not isinstance(payload[key], str) or not payload[key]:
            raise TypeError(f"{key} must be a non-empty string")
    if payload["computational_status"] != payload["evidence_status"]:
        raise ValueError("computational_status must match evidence_status")
    for key in ("assumptions", "source_references"):
        if not isinstance(payload[key], list) or not all(
            isinstance(item, str) and item for item in payload[key]
        ):
            raise ValueError(f"{key} must be a list of non-empty strings")
    if (
        not isinstance(payload["artifact_versions"], Mapping)
        or len(payload["artifact_versions"]) < len(_REQUIRED_ARTIFACT_KEYS)
    ):
        raise ValueError("artifact_versions must map strings to strings")
    if set(payload["artifact_versions"]) < _REQUIRED_ARTIFACT_KEYS:
        raise ValueError(
            "artifact_versions must include source_commit and fixture_or_proof"
        )
    if not all(
        isinstance(key, str) and isinstance(value, str) and value
        for key, value in payload["artifact_versions"].items()
    ):
        raise ValueError("artifact_versions must map strings to strings")
    string_fields = {
        "generator",
        "generator_formula",
        "generator_citation",
        "mu",
        "B1",
        "B2",
        "value_exact",
        "value_decimal",
        "theorem_reference",
        "property",
        "threshold",
        "direction",
    }
    for key in string_fields & payload.keys():
        if not isinstance(payload[key], str) or not payload[key]:
            raise TypeError(f"{key} must be a non-empty string")
    if "order" in payload and (
        isinstance(payload["order"], bool)
        or not isinstance(payload["order"], int)
        or payload["order"] < 1
    ):
        raise TypeError("order must be a positive integer")
    if "coefficients" in payload and (
        not isinstance(payload["coefficients"], list)
        or not all(isinstance(value, str) for value in payload["coefficients"])
    ):
        raise TypeError("coefficients must be a list of strings")
    for key in ("point", "interval"):
        if key in payload and (
            not isinstance(payload[key], list)
            or len(payload[key]) != 2
            or not all(isinstance(value, str) and value for value in payload[key])
        ):
            raise TypeError(f"{key} must be a two-item list of strings")
    if "certified" in payload and not isinstance(payload["certified"], bool):
        raise TypeError("certified must be a bool")
    if not isinstance(payload["literature_status"], str):
        raise TypeError("literature_status must be a string")
    if payload["literature_status"] not in {status.value for status in LiteratureStatus}:
        raise ValueError("unknown literature_status")
    if payload["novelty_claim"] is not False:
        raise ValueError("novelty_claim must be false")
    required_roots = {
        "generator_series": ("generator", "coefficients"),
        "fekete_szego": ("generator", "B1", "B2", "value"),
        "counterexample_verification": (
            "coefficients",
            "point",
            "interval",
            "threshold",
        ),
    }[payload["result_type"]]
    _validate_expression_dag(
        payload["exact_expression_dag"], required_roots=required_roots
    )
    _validate_report(payload["verification"])
    _validate_operation_contract(payload)
    _validate_authoritative_operation(payload)
    failure_state = payload["failure_state"]
    if failure_state is not None:
        if not isinstance(failure_state, str):
            raise TypeError("failure_state must be a string or null")
        if failure_state not in {state.value for state in FailureState}:
            raise ValueError("unknown result failure_state")
    if payload["verification"]["success"]:
        if failure_state is not None:
            raise ValueError("successful result failure_state must be null")
    elif failure_state is None:
        raise ValueError("failed result must declare a failure_state")
    elif payload["computational_status"] != failure_state:
        raise ValueError("failed result computational_status must match failure_state")


def validate_error_payload(payload: Mapping[str, Any]) -> None:
    """Validate a stable failure record."""

    allowed = {
        "schema_version",
        "result_type",
        "failure_state",
        "error",
        "package_version",
        "literature_status",
        "novelty_claim",
    }
    _check_mapping_keys(payload, allowed, "error")
    if set(payload) != allowed:
        raise ValueError(f"error is missing required keys: {sorted(allowed - payload.keys())}")
    if isinstance(payload["schema_version"], bool) or not isinstance(
        payload["schema_version"], int
    ):
        raise TypeError("schema_version must be an integer")
    if payload["schema_version"] != RESULT_SCHEMA_VERSION:
        raise ValueError("unsupported error schema_version")
    if not isinstance(payload["result_type"], str):
        raise TypeError("result_type must be a string")
    if payload["result_type"] != "error":
        raise ValueError("error result_type must be 'error'")
    if not isinstance(payload["failure_state"], str):
        raise TypeError("failure_state must be a string")
    if payload["failure_state"] not in {state.value for state in FailureState}:
        raise ValueError("unknown failure_state")
    if not isinstance(payload["error"], str) or not payload["error"]:
        raise TypeError("error must be a non-empty string")
    if not isinstance(payload["package_version"], str) or not payload["package_version"]:
        raise TypeError("package_version must be a non-empty string")
    if not isinstance(payload["literature_status"], str):
        raise TypeError("literature_status must be a string")
    if payload["literature_status"] != LiteratureStatus.NOT_ASSESSED.value:
        raise ValueError("failure literature_status must be not_assessed")
    if payload["novelty_claim"] is not False:
        raise ValueError("novelty_claim must be false")


def _check_mapping_keys(
    payload: Mapping[str, Any], allowed: set[str], label: str
) -> None:
    if not isinstance(payload, Mapping):
        raise TypeError(f"{label} must be an object")
    if not all(isinstance(key, str) for key in payload):
        raise TypeError(f"{label} object keys must be strings")
    unknown = set(payload) - allowed
    if unknown:
        raise ValueError(f"{label} contains unexpected keys: {sorted(unknown)}")


def _validate_operation_contract(payload: Mapping[str, Any]) -> None:
    """Require operation-specific inputs and preserve legacy-field consistency."""

    result_type = payload["result_type"]
    operation_fields = {
        "generator_series": {
            "generator",
            "generator_formula",
            "generator_citation",
            "order",
            "coefficients",
        },
        "fekete_szego": {
            "generator",
            "generator_formula",
            "generator_citation",
            "mu",
            "B1",
            "B2",
            "value_exact",
            "value_decimal",
            "theorem_reference",
        },
        "counterexample_verification": {
            "property",
            "coefficients",
            "point",
            "interval",
            "threshold",
            "certified",
            "direction",
        },
    }
    all_operation_fields = set().union(*operation_fields.values())
    misplaced = (set(payload) & all_operation_fields) - operation_fields[result_type]
    if misplaced:
        raise ValueError(
            f"fields do not belong to {result_type}: {sorted(misplaced)}"
        )
    if (
        result_type == "counterexample_verification"
        and not payload["verification"]["success"]
    ):
        raise ValueError(
            "counterexample results require a successful verification envelope"
        )
    canonical_inputs = payload["canonical_inputs"]
    exact_expressions = payload["exact_expressions"]
    if set(payload["assumptions"]) < _OPERATION_ASSUMPTIONS[result_type]:
        raise ValueError(f"{result_type} assumptions are incomplete")
    if not payload["source_references"]:
        raise ValueError(f"{result_type} source_references must be non-empty")
    expected_method = {
        "generator_series": "exact_symbolic_taylor_series",
        "fekete_szego": "ma_minda_fekete_szego_closed_form",
        "counterexample_verification": "certified_point_interval_evaluation",
    }[result_type]
    if payload["method"] != expected_method:
        raise ValueError(f"{result_type} method is not package-owned")
    if payload["literature_status"] != LiteratureStatus.NOT_ASSESSED.value:
        raise ValueError("literature status is not caller-settable in this release")
    expected_evidence = {
        "generator_series": "proven_exact_under_declared_assumptions",
        "fekete_szego": "proven_exact_under_declared_assumptions",
        "counterexample_verification": "certified_enclosure",
    }[result_type]
    if payload["verification"]["success"] and payload["evidence_status"] != expected_evidence:
        raise ValueError(f"{result_type} evidence status is not package-owned")
    if not payload["verification"]["success"] and payload["evidence_status"] != payload["failure_state"]:
        raise ValueError("failed evidence status must be derived from failure_state")
    expected_provenance = (
        "caller_supplied"
        if payload["artifact_versions"].get("generator_catalog") == "user-supplied"
        else "built_in"
    )
    expected_catalog = (
        "user-supplied"
        if expected_provenance == "caller_supplied"
        else GENERATOR_CATALOG_VERSION
    )
    if payload["artifact_versions"]["generator_catalog"] != expected_catalog:
        raise ValueError("generator catalog artifact identity is not package-owned")
    if payload["provenance"] != expected_provenance:
        raise ValueError("provenance does not match generator artifact identity")
    expected_fixture = {
        "generator_series": GENERATOR_FIXTURE_ID,
        "fekete_szego": FEKETE_FIXTURE_ID,
        "counterexample_verification": COUNTEREXAMPLE_FIXTURE_ID,
    }[result_type]
    expected_source = (
        "caller-supplied"
        if expected_provenance == "caller_supplied"
        else SOURCE_ARTIFACT_COMMIT
    )
    if payload["artifact_versions"]["source_commit"] != expected_source:
        raise ValueError("source commit artifact identity is not package-owned")
    if payload["artifact_versions"]["fixture_or_proof"] != expected_fixture:
        raise ValueError("fixture or proof artifact identity is not package-owned")
    expected_checks = _OPERATION_CHECKS[result_type]
    checks = payload["verification"]["checks"]
    if len(checks) != len(expected_checks) or {
        check["name"] for check in checks
    } != expected_checks:
        raise ValueError(f"{result_type} verification checks are incomplete")
    if not all(check["required"] for check in checks):
        raise ValueError(f"{result_type} verification checks must all be required")
    if result_type == "generator_series":
        canonical_required = {"generator", "order"}
        exact_required = {"generator", "coefficients"}
        if set(canonical_inputs) != canonical_required:
            raise ValueError(
                "canonical_inputs must contain exactly generator and order"
            )
        if set(exact_expressions) != exact_required:
            raise ValueError(
                "exact_expressions must contain exactly generator and coefficients"
            )
        _require_non_empty_string(canonical_inputs["generator"], "canonical_inputs.generator")
        if (
            isinstance(canonical_inputs["order"], bool)
            or not isinstance(canonical_inputs["order"], int)
            or canonical_inputs["order"] < 1
        ):
            raise TypeError("canonical_inputs.order must be a positive integer")
        _require_non_empty_string(exact_expressions["generator"], "exact_expressions.generator")
        _require_string_list(exact_expressions["coefficients"], "exact_expressions.coefficients")
        if payload.get("generator") != canonical_inputs["generator"]:
            raise ValueError("generator does not match canonical_inputs.generator")
        if payload.get("order") != canonical_inputs["order"]:
            raise ValueError("order does not match canonical_inputs.order")
        if payload.get("generator_formula") != exact_expressions["generator"]:
            raise ValueError("generator_formula does not match exact_expressions.generator")
        if payload.get("coefficients") != exact_expressions["coefficients"]:
            raise ValueError("coefficients do not match exact_expressions.coefficients")
    elif result_type == "fekete_szego":
        canonical_required = {"generator", "mu"}
        exact_required = {"generator", "B1", "B2", "value"}
        if set(canonical_inputs) != canonical_required:
            raise ValueError(
                "canonical_inputs must contain exactly generator and mu"
            )
        if set(exact_expressions) != exact_required:
            raise ValueError(
                "exact_expressions must contain exactly generator, B1, B2, and value"
            )
        _require_non_empty_string(canonical_inputs["generator"], "canonical_inputs.generator")
        _require_non_empty_string(canonical_inputs["mu"], "canonical_inputs.mu")
        for key in exact_required:
            _require_non_empty_string(exact_expressions[key], f"exact_expressions.{key}")
        for key in ("generator", "mu"):
            if payload.get(key) != canonical_inputs[key]:
                raise ValueError(f"{key} does not match canonical_inputs.{key}")
        legacy_pairs = {
            "generator_formula": "generator",
            "B1": "B1",
            "B2": "B2",
            "value_exact": "value",
        }
        for legacy_key, exact_key in legacy_pairs.items():
            if payload.get(legacy_key) != exact_expressions[exact_key]:
                raise ValueError(
                    f"{legacy_key} does not match exact_expressions.{exact_key}"
                )
    else:
        canonical_required = {"property", "coefficients", "point"}
        exact_required = {"coefficients", "point", "interval", "threshold"}
        if set(canonical_inputs) != canonical_required:
            raise ValueError(
                "canonical_inputs must contain exactly property, coefficients, and point"
            )
        if set(exact_expressions) != exact_required:
            raise ValueError(
                "exact_expressions must contain exactly coefficients, point, interval, and threshold"
            )
        _require_non_empty_string(
            canonical_inputs["property"], "canonical_inputs.property"
        )
        for label, value, length in (
            ("canonical_inputs.coefficients", canonical_inputs["coefficients"], None),
            ("canonical_inputs.point", canonical_inputs["point"], 2),
            ("exact_expressions.coefficients", exact_expressions["coefficients"], None),
            ("exact_expressions.point", exact_expressions["point"], 2),
            ("exact_expressions.interval", exact_expressions["interval"], 2),
        ):
            if (
                not isinstance(value, list)
                or not all(isinstance(item, str) and item for item in value)
                or (length is not None and len(value) != length)
            ):
                raise TypeError(f"{label} must be a valid list of strings")
        _require_non_empty_string(
            exact_expressions["threshold"], "exact_expressions.threshold"
        )
        if payload.get("property") != canonical_inputs["property"]:
            raise ValueError("property does not match canonical_inputs.property")
        try:
            canonical_coefficients = [
                float.fromhex(value) for value in canonical_inputs["coefficients"]
            ]
            canonical_point = [
                float.fromhex(value) for value in canonical_inputs["point"]
            ]
            exact_interval = [
                float(sp.Rational(value)) for value in exact_expressions["interval"]
            ]
            exact_threshold = float(sp.Rational(exact_expressions["threshold"]))
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError("counterexample numeric fields are not canonical") from exc
        if not all(
            math.isfinite(value)
            for value in [*canonical_coefficients, *canonical_point, *exact_interval, exact_threshold]
        ):
            raise ValueError("counterexample numeric fields must be finite")
        if payload.get("coefficients") != [repr(value) for value in canonical_coefficients]:
            raise ValueError("coefficients do not match canonical_inputs.coefficients")
        if payload.get("point") != [repr(value) for value in canonical_point]:
            raise ValueError("point does not match canonical_inputs.point")
        if payload.get("interval") != [repr(value) for value in exact_interval]:
            raise ValueError("interval does not match exact_expressions.interval")
        if payload.get("threshold") != repr(exact_threshold):
            raise ValueError("threshold does not match exact_expressions.threshold")


def _require_non_empty_string(value: Any, label: str) -> None:
    if not isinstance(value, str) or not value:
        raise TypeError(f"{label} must be a non-empty string")


def _require_string_list(value: Any, label: str) -> None:
    if not isinstance(value, list) or not all(
        isinstance(item, str) and item for item in value
    ):
        raise TypeError(f"{label} must be a list of non-empty strings")


def _validate_report(report: Any) -> None:
    if not isinstance(report, Mapping):
        raise TypeError("verification must be an object")
    _check_mapping_keys(report, {"status", "success", "checks"}, "verification")
    if set(report) != {"status", "success", "checks"}:
        raise ValueError("verification is missing required keys")
    if not isinstance(report["status"], str):
        raise TypeError("verification status must be a string")
    if report["status"] not in {"passed", "failed", "skipped"}:
        raise ValueError("unknown verification status")
    if not isinstance(report["success"], bool):
        raise TypeError("verification success must be a bool")
    if not isinstance(report["checks"], list) or not report["checks"]:
        raise ValueError("verification checks must be a non-empty list")
    names: set[str] = set()
    required_checks: list[Mapping[str, Any]] = []
    for check in report["checks"]:
        if not isinstance(check, Mapping):
            raise TypeError("verification checks must be objects")
        allowed = {
            "name",
            "checked",
            "expected",
            "observed",
            "status",
            "scope",
            "failure_reason",
            "required",
        }
        _check_mapping_keys(check, allowed, "verification check")
        if set(check) != allowed:
            raise ValueError("verification check is missing required keys")
        if (
            not isinstance(check["name"], str)
            or not check["name"]
            or check["name"] in names
        ):
            raise ValueError("verification check names must be unique strings")
        names.add(check["name"])
        if not isinstance(check["checked"], str) or not check["checked"]:
            raise ValueError("verification check checked must be a non-empty string")
        if not isinstance(check["scope"], str) or not check["scope"]:
            raise ValueError("verification check scope must be a non-empty string")
        if not isinstance(check["status"], str):
            raise TypeError("verification check status must be a string")
        if check["status"] not in {status.value for status in CheckStatus}:
            raise ValueError("unknown verification check status")
        if check["status"] == CheckStatus.FAIL.value and not check["failure_reason"]:
            raise ValueError("failed verification checks require a failure_reason")
        if check["status"] != CheckStatus.FAIL.value and check["failure_reason"] is not None:
            raise ValueError("passing or skipped verification checks require null failure_reason")
        if check["failure_reason"] is not None and not isinstance(
            check["failure_reason"], str
        ):
            raise TypeError("verification check failure_reason must be a string or null")
        if isinstance(check["failure_reason"], str) and not check["failure_reason"]:
            raise ValueError("verification check failure_reason must not be empty")
        if not isinstance(check["required"], bool):
            raise TypeError("verification check required must be a bool")
        if check["required"]:
            required_checks.append(check)

    expected_success = bool(required_checks) and all(
        check["status"] == CheckStatus.PASS.value for check in required_checks
    )
    expected_status = (
        "passed"
        if expected_success
        else (
            "failed"
            if any(check["status"] == CheckStatus.FAIL.value for check in required_checks)
            else "skipped"
        )
    )
    if report["success"] != expected_success or report["status"] != expected_status:
        raise ValueError("verification aggregate does not match required checks")


def _validate_expression_dag(dag: Any, *, required_roots: tuple[str, ...]) -> None:
    """Validate the closed DAG shape used as the authoritative exact identity."""

    if not isinstance(dag, Mapping):
        raise TypeError("expression DAG must be an object")
    _check_mapping_keys(dag, {"version", "nodes", "roots"}, "expression DAG")
    if set(dag) != {"version", "nodes", "roots"}:
        raise ValueError("expression DAG is missing required keys")
    if isinstance(dag["version"], bool) or dag["version"] != 1:
        raise ValueError("unsupported expression DAG version")
    nodes = dag["nodes"]
    if not isinstance(nodes, list) or not nodes or len(nodes) > MAX_JSON_NODES:
        raise ValueError("expression DAG nodes exceed resource bounds")
    expected_ids = [f"n{index}" for index in range(len(nodes))]
    node_by_id: dict[str, Mapping[str, Any]] = {}
    for index, node in enumerate(nodes):
        if not isinstance(node, Mapping):
            raise TypeError("expression DAG nodes must be objects")
        node_id = node.get("id")
        if (
            not isinstance(node_id, str)
            or _DAG_ID_PATTERN.fullmatch(node_id) is None
            or node_id in node_by_id
            or node_id != expected_ids[index]
        ):
            raise ValueError("expression DAG node ids must be canonical and unique")
        op = node.get("op")
        if op not in _DAG_OPS:
            raise ValueError("expression DAG contains an unknown operation")
        node_by_id[node_id] = node
        allowed = {
            "integer": {"id", "op", "value"},
            "rational": {"id", "op", "numerator", "denominator"},
            "symbol": {"id", "op", "value"},
            "add": {"id", "op", "args"},
            "mul": {"id", "op", "args"},
            "pow": {"id", "op", "args"},
            "function": {"id", "op", "name", "args"},
        }[op]
        _check_mapping_keys(node, allowed, "expression DAG node")
        if set(node) != allowed:
            raise ValueError("expression DAG node has missing or unexpected keys")
        if op == "integer":
            value = node["value"]
            if (
                not isinstance(value, str)
                or _INTEGER_PATTERN.fullmatch(value) is None
                or abs(int(value)) >= _MAX_JSON_INTEGER
            ):
                raise ValueError("expression DAG integer atom exceeds its bound")
        elif op == "symbol":
            if node["value"] != "z":
                raise ValueError("expression DAG contains an undeclared symbol")
        elif op == "rational":
            numerator = node["numerator"]
            denominator = node["denominator"]
            if (
                not isinstance(numerator, str)
                or _INTEGER_PATTERN.fullmatch(numerator) is None
                or not isinstance(denominator, str)
                or _DENOMINATOR_PATTERN.fullmatch(denominator) is None
                or int(denominator) == 0
                or abs(int(numerator)) >= _MAX_JSON_INTEGER
                or int(denominator) >= _MAX_JSON_INTEGER
            ):
                raise ValueError("expression DAG rational components are invalid")
        else:
            args = node["args"]
            if not isinstance(args, list) or not all(
                isinstance(item, str) and _DAG_ID_PATTERN.fullmatch(item)
                for item in args
            ):
                raise ValueError("expression DAG args must be a list of node ids")
            if op in {"add", "mul", "function"} and not args:
                raise ValueError("expression DAG operation requires arguments")
            if op == "pow" and len(args) != 2:
                raise ValueError("expression DAG power requires two arguments")
            if op == "function" and node["name"] not in _DAG_FUNCTIONS:
                raise ValueError("expression DAG contains an unknown function")
    roots = dag["roots"]
    if not isinstance(roots, Mapping) or set(roots) != set(required_roots):
        raise ValueError("expression DAG roots are incomplete")
    root_ids: list[str] = []
    for name in required_roots:
        root = roots[name]
        if name in {"coefficients", "point", "interval"}:
            if not isinstance(root, list):
                raise ValueError(f"expression DAG {name} roots must be a list")
            values = root
        else:
            if not isinstance(root, str):
                raise TypeError("expression DAG scalar roots must reference one node")
            values = [root]
        if not all(
            isinstance(item, str) and _DAG_ID_PATTERN.fullmatch(item)
            for item in values
        ):
            raise ValueError("expression DAG roots must reference node ids")
        root_ids.extend(values)
    if not all(root in node_by_id for root in root_ids):
        raise ValueError("expression DAG root references an unknown node")
    for node in nodes:
        for child in node.get("args", []):
            if child not in node_by_id:
                raise ValueError("expression DAG references an unknown node")
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node_id: str, depth: int) -> None:
        if depth > MAX_JSON_DEPTH:
            raise ValueError("expression DAG exceeds depth limit")
        if node_id in visiting:
            raise ValueError("expression DAG contains a cycle")
        if node_id in visited:
            return
        visiting.add(node_id)
        for child in node_by_id[node_id].get("args", []):
            visit(child, depth + 1)
        visiting.remove(node_id)
        visited.add(node_id)

    for root in root_ids:
        visit(root, 0)
    if len(visited) != len(nodes):
        raise ValueError("expression DAG contains unreachable nodes")


def _decode_expression_dag(
    dag: Mapping[str, Any], *, required_roots: tuple[str, ...]
) -> dict[str, sp.Expr | list[sp.Expr]]:
    """Decode only the bounded, already-validated opcode set into SymPy nodes."""

    _validate_expression_dag(dag, required_roots=required_roots)
    nodes = {node["id"]: node for node in dag["nodes"]}
    functions = {
        "Abs": sp.Abs,
        "Max": sp.Max,
        "cos": sp.cos,
        "cosh": sp.cosh,
        "exp": sp.exp,
        "log": sp.log,
        "sin": sp.sin,
        "sinh": sp.sinh,
    }
    decoded: dict[str, sp.Expr] = {}
    visiting: set[str] = set()

    def decode(node_id: str) -> sp.Expr:
        if node_id in decoded:
            return decoded[node_id]
        if node_id in visiting:
            raise ValueError("expression DAG contains a cycle")
        visiting.add(node_id)
        node = nodes[node_id]
        op = node["op"]
        if op == "integer":
            value = sp.Integer(int(node["value"]))
        elif op == "rational":
            value = sp.Rational(int(node["numerator"]), int(node["denominator"]))
        elif op == "symbol":
            value = Z
        elif op == "add":
            value = sp.Add(*(decode(child) for child in node["args"]))
        elif op == "mul":
            value = sp.Mul(*(decode(child) for child in node["args"]))
        elif op == "pow":
            value = sp.Pow(decode(node["args"][0]), decode(node["args"][1]))
        else:
            value = functions[node["name"]](*(decode(child) for child in node["args"]))
        visiting.remove(node_id)
        decoded[node_id] = value
        return value

    result: dict[str, sp.Expr | list[sp.Expr]] = {}
    for name in required_roots:
        root = dag["roots"][name]
        result[name] = (
            [decode(node_id) for node_id in root]
            if isinstance(root, list)
            else decode(root)
        )
    for value in result.values():
        values = value if isinstance(value, list) else [value]
        for expression in values:
            validate_exact_expression(expression)
    return result


def _validate_authoritative_operation(payload: Mapping[str, Any]) -> None:
    """Recompute successful Phase-1 values from the exact DAG, never its printer."""

    result_type = payload["result_type"]
    required_roots = {
        "generator_series": ("generator", "coefficients"),
        "fekete_szego": ("generator", "B1", "B2", "value"),
        "counterexample_verification": (
            "coefficients",
            "point",
            "interval",
            "threshold",
        ),
    }[result_type]
    roots = _decode_expression_dag(
        payload["exact_expression_dag"],
        required_roots=required_roots,
    )
    expressions: dict[str, sp.Expr | list[sp.Expr]] = {
        key: value for key, value in roots.items()
    }
    if canonical_expression_dag(expressions) != payload["exact_expression_dag"]:
        raise ValueError("expression DAG is not canonical")
    if not payload["verification"]["success"]:
        return

    exact_expressions = payload["exact_expressions"]
    if result_type == "counterexample_verification":
        coefficients = roots["coefficients"]
        point = roots["point"]
        interval = roots["interval"]
        threshold = roots["threshold"]
        assert isinstance(coefficients, list)
        assert isinstance(point, list)
        assert isinstance(interval, list)
        assert isinstance(threshold, sp.Expr)
        displays = {
            "coefficients": [sp.sstr(value) for value in coefficients],
            "point": [sp.sstr(value) for value in point],
            "interval": [sp.sstr(value) for value in interval],
            "threshold": sp.sstr(threshold),
        }
        if displays != exact_expressions:
            raise ValueError(
                "exact counterexample display does not match the authoritative DAG"
            )

        def exact_binary64(text: str) -> sp.Rational:
            value = float.fromhex(text)
            numerator, denominator = value.as_integer_ratio()
            return sp.Rational(numerator, denominator)

        if coefficients != [
            exact_binary64(value)
            for value in payload["canonical_inputs"]["coefficients"]
        ]:
            raise ValueError("authoritative coefficients do not match canonical inputs")
        if point != [
            exact_binary64(value) for value in payload["canonical_inputs"]["point"]
        ]:
            raise ValueError("authoritative point does not match canonical inputs")
        if len(point) != 2 or len(interval) != 2 or interval[0] > interval[1]:
            raise ValueError("authoritative point or interval shape is invalid")
        property_name = payload["property"]
        from .counterexamples import verify_counterexample

        canonical_coefficients = tuple(
            float.fromhex(value)
            for value in payload["canonical_inputs"]["coefficients"]
        )
        canonical_point = tuple(
            float.fromhex(value) for value in payload["canonical_inputs"]["point"]
        )
        recomputed = verify_counterexample(
            canonical_coefficients,
            point=(canonical_point[0], canonical_point[1]),
            property=property_name,
        )
        recomputed_lower = recomputed.interval_lower
        recomputed_upper = recomputed.interval_upper
        recomputed_threshold = recomputed.threshold
        recomputed_certified = recomputed.certified

        def rational_from_float(value: float) -> sp.Rational:
            numerator, denominator = value.as_integer_ratio()
            return sp.Rational(numerator, denominator)

        recomputed_interval = [
            rational_from_float(recomputed_lower),
            rational_from_float(recomputed_upper),
        ]
        if interval != recomputed_interval or threshold != rational_from_float(
            recomputed_threshold
        ):
            raise ValueError(
                "counterexample interval does not match the recomputed enclosure"
            )
        if payload["certified"] != bool(recomputed_certified):
            raise ValueError(
                "counterexample classification does not match the recomputed enclosure"
            )
        if property_name == "starlike":
            certified = interval[1] <= threshold
            direction = "disproves" if certified else "not_disproved"
        elif property_name in {"becker_univalent", "nehari_univalent"}:
            certified = interval[0] > threshold
            direction = "violates_criterion" if certified else "not_violated"
        else:
            raise ValueError("authoritative counterexample property is unsupported")
        certified_bool = bool(certified)
        if payload["certified"] != certified_bool or payload["direction"] != direction:
            raise ValueError("counterexample classification does not match its interval")
        return

    generator = roots["generator"]
    assert isinstance(generator, sp.Expr)
    if exact_expressions["generator"] != sp.sstr(generator):
        raise ValueError("exact generator display does not match the authoritative DAG")
    if payload["provenance"] == "built_in":
        from .catalog import get_generator

        try:
            built_in = get_generator(payload["canonical_inputs"]["generator"])
        except KeyError as exc:
            raise ValueError("built-in generator identity cannot be verified") from exc
        if canonical_expression_dag({"generator": built_in.expression}) != canonical_expression_dag(
            {"generator": generator}
        ):
            raise ValueError("exact DAG generator does not match the built-in artifact")
    if sp.simplify(generator.subs(Z, 0) - 1) != 0:
        raise ValueError("authoritative generator is not normalized")

    if result_type == "generator_series":
        coefficients = roots["coefficients"]
        assert isinstance(coefficients, list)
        if exact_expressions["coefficients"] != [sp.sstr(value) for value in coefficients]:
            raise ValueError("exact coefficient display does not match the authoritative DAG")
        order = payload["canonical_inputs"]["order"]
        expected = tuple(
            sp.simplify(
                sp.series(generator, Z, 0, order + 1).removeO().expand().coeff(Z, degree)
            )
            for degree in range(1, order + 1)
        )
        if tuple(coefficients) != expected:
            raise ValueError("authoritative generator coefficients do not match exact expansion")
        return

    b1 = roots["B1"]
    b2 = roots["B2"]
    value = roots["value"]
    assert isinstance(b1, sp.Expr) and isinstance(b2, sp.Expr) and isinstance(value, sp.Expr)
    if {
        "B1": sp.sstr(b1),
        "B2": sp.sstr(b2),
        "value": sp.sstr(value),
    } != {
        key: exact_expressions[key] for key in ("B1", "B2", "value")
    }:
        raise ValueError("exact Fekete-Szego display does not match the authoritative DAG")
    mu_text = payload["canonical_inputs"]["mu"]
    match = re.fullmatch(r"([+-]?[0-9]+)(?:/([+-]?[0-9]+))?", mu_text, flags=re.ASCII)
    if match is None:
        raise ValueError("authoritative mu is not a canonical rational")
    denominator = int(match.group(2) or "1")
    if denominator == 0:
        raise ValueError("authoritative mu has a zero denominator")
    mu = sp.Rational(int(match.group(1)), denominator)
    expected_b1, expected_b2 = tuple(
        sp.simplify(
            sp.series(generator, Z, 0, 3).removeO().expand().coeff(Z, degree)
        )
        for degree in (1, 2)
    )
    if (b1, b2) != (expected_b1, expected_b2):
        raise ValueError("authoritative Fekete-Szego coefficients do not match exact expansion")
    if expected_b1.is_real is not True or expected_b1.is_positive is not True:
        raise ValueError("authoritative generator does not satisfy positive-real B1")
    if expected_b2.is_real is not True:
        raise ValueError("authoritative generator does not satisfy real B2")
    expected_value = sp.simplify(
        expected_b1
        * sp.Max(1, sp.Abs(expected_b2 / expected_b1 + (1 - 2 * mu) * expected_b1))
        / 2
    )
    if value != expected_value:
        raise ValueError("authoritative Fekete-Szego value does not match the closed form")

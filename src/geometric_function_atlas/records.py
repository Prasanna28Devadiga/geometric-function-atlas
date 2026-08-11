"""Closed, versioned analysis records for screens, searches, and lab metrics.

The exact-result envelope (``result.schema.json``) remains reserved for
operations that emit ``proven_exact_under_declared_assumptions`` or
``certified_enclosure`` evidence. The class-screen, function-verification,
witness-search, and lab operations emit *analysis records* instead: still
versioned and fail-closed, but carrying an explicit ``evidence_kind`` and
``tier`` so a numerical screen can never be mistaken for a proof, an
enclosure for sharpness, or a benchmark metric for a security claim.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from typing import Any

from .contracts import (
    FailureState,
    VerificationReport,
    _json_value,
    _validate_report,
)
from .version import __version__

SCREEN_RECORD_VERSION = 1

_RECORD_TYPES = frozenset(
    {
        "class_admissibility",
        "class_membership",
        "class_containment",
        "function_verification",
        "witness_search",
        "lab_metrics",
    }
)
_EVIDENCE_KINDS = frozenset(
    {
        "numerical_screen",
        "certified_enclosure",
        "exact_proof",
        "inconclusive",
        "benchmark_metric",
        "empirical_metric",
    }
)
_TIERS = frozenset({"screen", "symbolic", "rigorous", "lab"})
_METHODS = frozenset(
    {
        "ma_minda_admissibility_screens",
        "ma_minda_membership_winding_screen",
        "ma_minda_containment_winding_screen",
        "tiered_function_verification",
        "grid_search_then_interval_certification",
        "sbox_benchmark_metrics",
        "image_quality_metrics",
        "image_transform",
    }
)
_INPUT_SCHEMAS: dict[str, frozenset[str]] = {
    "class_admissibility": frozenset({"class_key"}),
    "class_membership": frozenset({"class_key", "coefficients"}),
    "class_containment": frozenset({"inner", "outer"}),
    "function_verification": frozenset({"property", "coefficients", "tier"}),
    "witness_search": frozenset({"property", "coefficients"}),
    "lab_metrics": frozenset({"metric_family"}),
}
_REQUIRED_KEYS = frozenset(
    {
        "schema_version",
        "record_type",
        "canonical_inputs",
        "method",
        "evidence_kind",
        "tier",
        "assumptions",
        "source_references",
        "package_version",
        "failure_state",
        "novelty_claim",
        "verification",
        "details",
    }
)
_MAX_DETAILS_KEYS = 64


@dataclass(frozen=True, slots=True)
class RecordError(ValueError):
    """Raised when an analysis record violates the closed contract."""

    message: str

    def __str__(self) -> str:
        return self.message


class _RecordFailureState(str, Enum):
    """Failure states allowed on analysis records (subset of FailureState)."""

    UNSUPPORTED = FailureState.UNSUPPORTED.value
    UNRESOLVED = FailureState.UNRESOLVED.value
    INVALID_INPUT = FailureState.INVALID_INPUT.value
    RESOURCE_LIMIT = FailureState.RESOURCE_LIMIT.value
    CORRUPT_ARTIFACT = FailureState.CORRUPT_ARTIFACT.value


def _check_keys(payload: Mapping[str, Any], allowed: set[str], label: str) -> None:
    if not isinstance(payload, Mapping):
        raise RecordError(f"{label} must be an object")
    unknown = set(payload) - allowed
    if unknown:
        raise RecordError(f"{label} contains unexpected keys: {sorted(unknown)}")


def _require_string(value: Any, label: str) -> None:
    if not isinstance(value, str) or not value:
        raise RecordError(f"{label} must be a non-empty string")


def build_screen_record(
    *,
    record_type: str,
    canonical_inputs: Mapping[str, Any],
    method: str,
    evidence_kind: str,
    tier: str,
    assumptions: tuple[str, ...] | list[str],
    source_references: tuple[str, ...] | list[str],
    verification: VerificationReport,
    details: Mapping[str, Any] | None = None,
    failure_state: FailureState | str | None = None,
) -> dict[str, Any]:
    """Build a closed analysis record; raises :class:`RecordError` when invalid."""

    failure = None if failure_state is None else FailureState(failure_state)
    return {
        "schema_version": SCREEN_RECORD_VERSION,
        "record_type": record_type,
        "canonical_inputs": _json_value(dict(canonical_inputs)),
        "method": method,
        "evidence_kind": evidence_kind,
        "tier": tier,
        "assumptions": list(assumptions),
        "source_references": list(source_references),
        "package_version": __version__,
        "failure_state": None if failure is None else failure.value,
        "novelty_claim": False,
        "verification": verification.to_dict(),
        "details": {} if details is None else _json_value(dict(details)),
    }


def validate_screen_record(record: Mapping[str, Any]) -> None:
    """Validate an analysis record against the closed contract, fail-closed."""

    _check_keys(record, set(_REQUIRED_KEYS), "record")
    missing = _REQUIRED_KEYS - record.keys()
    if missing:
        raise RecordError(f"record is missing required keys: {sorted(missing)}")
    if (
        isinstance(record["schema_version"], bool)
        or not isinstance(record["schema_version"], int)
        or record["schema_version"] != SCREEN_RECORD_VERSION
    ):
        raise RecordError("unsupported analysis record schema_version")
    if record["record_type"] not in _RECORD_TYPES:
        raise RecordError(
            f"unknown record_type: {record['record_type']!r}; "
            f"allowed: {sorted(_RECORD_TYPES)}"
        )
    if record["evidence_kind"] not in _EVIDENCE_KINDS:
        raise RecordError(
            f"unknown evidence_kind: {record['evidence_kind']!r}; "
            f"allowed: {sorted(_EVIDENCE_KINDS)}"
        )
    if record["tier"] not in _TIERS:
        raise RecordError(
            f"unknown tier: {record['tier']!r}; allowed: {sorted(_TIERS)}"
        )
    for key in ("method", "evidence_kind", "tier"):
        _require_string(record[key], key)
    if record["method"] not in _METHODS:
        raise RecordError(
            f"method is not a package-owned value: {record['method']!r}"
        )
    _check_keys(record["canonical_inputs"], set(_INPUT_SCHEMAS[record["record_type"]]), "canonical_inputs")
    expected_inputs = _INPUT_SCHEMAS[record["record_type"]]
    if set(record["canonical_inputs"]) != expected_inputs:
        raise RecordError(
            f"canonical_inputs must contain exactly {sorted(expected_inputs)}"
        )
    for value in record["canonical_inputs"].values():
        _json_value(value)
    for key in ("assumptions", "source_references"):
        if not isinstance(record[key], list) or not all(
            isinstance(item, str) and item for item in record[key]
        ):
            raise RecordError(f"{key} must be a list of non-empty strings")
    if not record["source_references"]:
        raise RecordError("source_references must be non-empty")
    if not isinstance(record["package_version"], str) or not record["package_version"]:
        raise RecordError("package_version must be a non-empty string")
    if record["novelty_claim"] is not False:
        raise RecordError("novelty_claim must be false")
    if not isinstance(record["details"], Mapping) or len(record["details"]) > _MAX_DETAILS_KEYS:
        raise RecordError(f"details must be an object with at most {_MAX_DETAILS_KEYS} keys")
    _validate_report(record["verification"])
    failure_state = record["failure_state"]
    if failure_state is not None:
        if not isinstance(failure_state, str):
            raise RecordError("failure_state must be a string or null")
        try:
            _RecordFailureState(failure_state)
        except ValueError as exc:
            raise RecordError(f"unknown failure_state: {failure_state!r}") from exc
    if record["verification"]["success"]:
        if failure_state is not None:
            raise RecordError("successful record failure_state must be null")
    elif (
        failure_state is None
        and record["evidence_kind"] != "numerical_screen"
    ):
        # A numerical screen may legitimately conclude a negative finding
        # ("not admissible", "not a member", "not contained"); that is a
        # completed operation, not an operation failure. Non-screen records
        # remain fail-closed.
        raise RecordError("failed record must declare a failure_state")
    for check in record["verification"]["checks"]:
        if check["status"] == "fail" and not check["failure_reason"]:
            raise RecordError("failed verification checks require a failure_reason")


def _finite(value: Any) -> bool:
    if isinstance(value, bool):
        return True
    if isinstance(value, (int, float)):
        return math.isfinite(value)
    if isinstance(value, (list, tuple)):
        return all(_finite(item) for item in value)
    if isinstance(value, Mapping):
        return all(_finite(item) for item in value.values())
    return True


def screen_payload_finite(record: Mapping[str, Any]) -> bool:
    """Return whether every numeric field in the record is finite."""

    return _finite(record)

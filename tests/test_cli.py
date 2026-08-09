from __future__ import annotations

import json
import subprocess
import sys


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "geometric_function_atlas", *args],
        check=False,
        capture_output=True,
        text=True,
    )


def test_generators_command_emits_stable_json() -> None:
    completed = run_cli("generators", "--json")

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert [row["key"] for row in payload] == sorted(row["key"] for row in payload)
    assert next(row for row in payload if row["key"] == "sine")["formula"] == "sin(z) + 1"


def test_coefficients_command_emits_exact_strings() -> None:
    completed = run_cli("coefficients", "sine", "--order", "4", "--json")

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["generator"] == "sine"
    assert payload["order"] == 4
    assert payload["coefficients"] == ["1", "0", "-1/6", "0"]
    assert payload["evidence_status"] == "proven_exact_under_declared_assumptions"
    assert payload["package_version"] == "0.1.0"


def test_fekete_szego_command_emits_evidence_typed_result() -> None:
    completed = run_cli("fekete-szego", "exponential", "--mu", "0", "--json")

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["value_exact"] == "3/4"
    assert payload["evidence_status"] == "proven_exact_under_declared_assumptions"
    assert payload["novelty_claim"] is False


def test_cli_reports_unknown_generator_without_traceback() -> None:
    completed = run_cli("coefficients", "missing", "--order", "2")

    assert completed.returncode == 2
    assert "unknown generator 'missing'" in completed.stderr
    assert "Traceback" not in completed.stderr


def test_cli_rejects_excessive_order_and_precision() -> None:
    order = run_cli("coefficients", "sine", "--order", "65")
    precision = run_cli(
        "fekete-szego", "sine", "--mu", "0", "--precision", "1001"
    )

    assert order.returncode == 5
    assert "order must be at most 64" in order.stderr
    assert precision.returncode == 5
    assert "precision must be at most 1000" in precision.stderr


def test_fekete_szego_cli_reports_unknown_generator_without_traceback() -> None:
    completed = run_cli("fekete-szego", "missing", "--mu", "0")

    assert completed.returncode == 2
    assert "unknown generator 'missing'" in completed.stderr
    assert "Traceback" not in completed.stderr


def test_cli_json_failure_is_versioned_and_has_stable_invalid_input_code() -> None:
    completed = run_cli("coefficients", "missing", "--order", "2", "--json")

    assert completed.returncode == 2
    payload = json.loads(completed.stdout)
    assert payload["schema_version"] == 1
    assert payload["result_type"] == "error"
    assert payload["failure_state"] == "invalid_input"
    assert payload["novelty_claim"] is False
    assert completed.stderr == ""


def test_cli_json_resource_limit_has_distinct_stable_code() -> None:
    completed = run_cli("coefficients", "sine", "--order", "65", "--json")

    assert completed.returncode == 5
    payload = json.loads(completed.stdout)
    assert payload["failure_state"] == "resource_limit"


def test_cli_human_resource_limit_uses_same_stable_code() -> None:
    completed = run_cli("coefficients", "sine", "--order", "65")

    assert completed.returncode == 5
    assert "order must be at most 64" in completed.stderr


def test_cli_json_argument_parse_failures_are_structured() -> None:
    completed = run_cli("coefficients", "sine", "--order", "nope", "--json")

    assert completed.returncode == 2
    payload = json.loads(completed.stdout)
    assert payload["failure_state"] == "invalid_input"
    assert completed.stderr == ""

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
    assert payload["package_version"] == "0.2.1"


def test_fekete_szego_command_emits_evidence_typed_result() -> None:
    completed = run_cli("fekete-szego", "exponential", "--mu", "0", "--json")

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["value_exact"] == "3/4"
    assert payload["evidence_status"] == "proven_exact_under_declared_assumptions"
    assert payload["novelty_claim"] is False


def test_verify_counterexample_command_certifies_supplied_witness() -> None:
    completed = run_cli(
        "verify-counterexample",
        "--coefficients",
        "1",
        "--point=-0.75,0",
        "--json",
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["property"] == "starlike"
    assert payload["certified"] is True
    assert payload["direction"] == "disproves"
    assert float(payload["interval"][1]) < 0
    assert payload["schema_version"] == 1
    assert payload["result_type"] == "counterexample_verification"


def test_verify_counterexample_json_reports_singularity_as_unresolved() -> None:
    completed = run_cli(
        "verify-counterexample",
        "--coefficients",
        "1",
        "--point=-0.5,0",
        "--property",
        "becker_univalent",
        "--json",
    )

    assert completed.returncode == 4
    payload = json.loads(completed.stdout)
    assert payload["failure_state"] == "unresolved"
    assert "denominator" in payload["error"] or "singular" in payload["error"]
    assert completed.stderr == ""


def test_verify_counterexample_command_has_plain_language_output() -> None:
    completed = run_cli(
        "verify-counterexample",
        "--coefficients",
        "1",
        "--point=-0.75,0",
    )

    assert completed.returncode == 0, completed.stderr
    assert "CERTIFIED COUNTEREXAMPLE" in completed.stdout
    assert "starlike" in completed.stdout
    assert "Traceback" not in completed.stderr


def test_plot_command_writes_a_real_svg(tmp_path) -> None:
    output = tmp_path / "sine-domain.svg"
    completed = run_cli(
        "plot",
        "sine",
        "--order",
        "10",
        "--output",
        str(output),
    )

    assert completed.returncode == 0, completed.stderr
    assert output.is_file()
    assert "Wrote" in completed.stdout
    assert "Taylor order 10" in completed.stdout
    assert "<svg" in output.read_text(encoding="utf-8")


def test_plot_command_supports_advanced_supplied_coefficients(tmp_path) -> None:
    output = tmp_path / "polynomial.svg"
    completed = run_cli(
        "plot",
        "--coefficients",
        "1,-0.25",
        "--output",
        str(output),
    )

    assert completed.returncode == 0, completed.stderr
    assert output.is_file()


def test_version_command_is_an_installation_smoke_check() -> None:
    completed = run_cli("--version")

    assert completed.returncode == 0
    assert completed.stdout.strip() == "geometric-function-atlas 0.2.1"
    assert completed.stderr == ""


def test_walkthrough_is_a_concise_verified_first_run() -> None:
    completed = run_cli("walkthrough")

    assert completed.returncode == 0, completed.stderr
    assert "Geometric Function Atlas: first-run walkthrough" in completed.stdout
    assert "39 registered Ma-Minda generators" in completed.stdout
    assert "1 + sin(z)" in completed.stdout
    assert "1, 0, -1/6, 0, 1/120" in completed.stdout
    assert "Fekete-Szego" in completed.stdout
    assert "S*(phi) means normalized analytic functions" in completed.stdout
    assert "|a3 - mu*a2^2|" in completed.stdout
    assert "phi is an admissible Ma-Minda generator" in completed.stdout
    assert "phi has real Taylor coefficients" in completed.stdout
    assert "B1 is positive" in completed.stdout
    assert "exact value: 3/4" in completed.stdout
    assert "sine -> sigmoid" in completed.stdout
    assert "directed radius means" in completed.stdout
    assert "certificate: PROVEN" in completed.stdout
    assert "does not establish novelty" in completed.stdout
    assert "schema_version:" not in completed.stdout
    assert "exact_expression_dag:" not in completed.stdout
    assert completed.stderr == ""


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


def test_radii_command_lists_the_typed_snapshot() -> None:
    completed = run_cli("radii", "--status", "audit_required", "--json")

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert len(payload) == 12
    assert {row["status"] for row in payload} == {"audit_required"}
    assert all(row["direction"] for row in payload)


def test_radius_command_preserves_direction_and_exact_value() -> None:
    completed = run_cli("radius", "sine", "sigmoid", "--json")

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["canonical_inputs"] == {"inner": "sine", "target": "sigmoid"}
    assert payload["exact_expressions"]["radius"] == "asin((E-1)/(E+1))"
    assert payload["provenance_detail"]["crosswalk_commit"]


def test_verify_radius_certificate_command_replays_the_exact_chain() -> None:
    completed = run_cli(
        "verify-radius-certificate", "sine", "sigmoid", "--json"
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["status"] == "proven"
    assert payload["certified"] is True
    assert all(step["verified"] for step in payload["steps"])


def test_verify_radius_certificate_command_uses_fail_closed_exit_codes() -> None:
    completed = run_cli(
        "verify-radius-certificate",
        "sine",
        "sigmoid",
        "--candidate",
        "asinh((E-1)/(E+1))",
        "--json",
    )

    assert completed.returncode == 4
    payload = json.loads(completed.stdout)
    assert payload["status"] == "candidate_mismatch"
    assert payload["certified"] is False


def test_command_aliases_match_their_canonical_commands() -> None:
    pairs = [
        (
            ("coeffs", "sine", "--order", "4", "--json"),
            ("coefficients", "sine", "--order", "4", "--json"),
        ),
        (
            ("fs", "exponential", "--mu", "0", "--json"),
            ("fekete-szego", "exponential", "--mu", "0", "--json"),
        ),
        (
            (
                "disprove",
                "--coefficients",
                "1",
                "--at=-3/4,0",
                "--property",
                "starlike",
                "--json",
            ),
            (
                "verify-counterexample",
                "--coefficients",
                "1",
                "--point=-0.75,0",
                "--property",
                "starlike",
                "--json",
            ),
        ),
        (
            ("certify", "sine", "sigmoid", "--json"),
            ("verify-radius-certificate", "sine", "sigmoid", "--json"),
        ),
    ]
    for alias_args, canonical_args in pairs:
        alias_run = run_cli(*alias_args)
        canonical_run = run_cli(*canonical_args)
        assert alias_run.returncode == canonical_run.returncode == 0, (
            alias_run.stderr or canonical_run.stderr
        )
        assert alias_run.stdout == canonical_run.stdout


def test_human_output_is_a_curated_subset_with_a_json_pointer() -> None:
    completed = run_cli("coefficients", "sine", "--order", "5")

    assert completed.returncode == 0, completed.stderr
    assert completed.stderr == ""
    assert "generator: sine" in completed.stdout
    assert "generator_formula: sin(z) + 1" in completed.stdout
    assert "coefficients: ['1', '0', '-1/6', '0', '1/120']" in completed.stdout
    assert "evidence_status: proven_exact_under_declared_assumptions" in completed.stdout
    assert "--json" in completed.stdout
    assert "schema_version" not in completed.stdout
    assert "exact_expression_dag" not in completed.stdout

    functional = run_cli("fs", "exponential", "--mu", "0")

    assert functional.returncode == 0, functional.stderr
    assert functional.stderr == ""
    assert "generator: exponential" in functional.stdout
    assert "mu: 0" in functional.stdout
    assert "value_exact: 3/4" in functional.stdout
    assert "value_decimal: 0.75" in functional.stdout
    assert "evidence_status: proven_exact_under_declared_assumptions" in functional.stdout
    assert "schema_version" not in functional.stdout


def test_unknown_generator_suggests_a_close_match() -> None:
    completed = run_cli("coeffs", "sin", "--order", "2")

    assert completed.returncode == 2
    assert "unknown generator 'sin'" in completed.stderr
    assert "did you mean 'sine'" in completed.stderr

    typo = run_cli("fs", "exponental", "--mu", "0")

    assert typo.returncode == 2
    assert "did you mean 'exponential'" in typo.stderr


def test_unknown_generator_without_a_close_match_has_no_suggestion() -> None:
    completed = run_cli("coefficients", "missing", "--order", "2")

    assert completed.returncode == 2
    assert "unknown generator 'missing'" in completed.stderr
    assert "did you mean" not in completed.stderr


def test_witness_point_accepts_fractions_and_a_bare_real() -> None:
    for point_args in (("--point=-3/4,0",), ("--at=-3/4,0",), ("--at=-3/4",)):
        completed = run_cli(
            "disprove", "--coefficients", "1", *point_args, "--property", "starlike"
        )

        assert completed.returncode == 0, completed.stderr
        assert "CERTIFIED COUNTEREXAMPLE" in completed.stdout
        assert "Witness: z = -0.75 + 0i" in completed.stdout


def test_witness_point_rejects_non_real_input() -> None:
    completed = run_cli(
        "verify-counterexample",
        "--coefficients",
        "1",
        "--point=bogus",
        "--property",
        "starlike",
    )

    assert completed.returncode == 2
    assert "point must be comma-separated real numbers" in completed.stderr

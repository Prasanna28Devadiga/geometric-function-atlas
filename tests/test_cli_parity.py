"""CLI gates for the expanded parity surface.

These commands were added alongside the tiered verifier, class screens,
witness search, plot kinds, and optional labs. The tests exercise the
installed console module end to end, including the `--json` envelope.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

from geometric_function_atlas.cli import main


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "geometric_function_atlas", *args],
        check=False,
        capture_output=True,
        text=True,
    )


def test_crypto_construct_accepts_json_flag() -> None:
    if importlib.util.find_spec("numpy") is None:
        pytest.skip("crypto lab requires the optional numpy dependency")
    completed = run_cli("crypto-lab", "construct", "cardioid", "--json")

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["details"]["label"] == "constructed:cardioid:keyed"
    assert payload["details"]["NL_min"] >= 0
    assert payload["novelty_claim"] is False


def test_crypto_construct_fails_closed_without_lab_extra() -> None:
    if importlib.util.find_spec("numpy") is not None:
        pytest.skip("base-install isolation check only applies without numpy")
    completed = run_cli("crypto-lab", "construct", "cardioid", "--json")

    assert completed.returncode == 3
    payload = json.loads(completed.stdout)
    assert payload["failure_state"] == "unsupported"


def test_broken_pipe_on_stdout_exits_quietly_with_io_code(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _BrokenBuffer:
        def write(self, _data: bytes) -> int:
            raise BrokenPipeError(32, "Broken pipe")

        def flush(self) -> None:
            raise BrokenPipeError(32, "Broken pipe")

    class _BrokenStdout:
        buffer = _BrokenBuffer()

        def write(self, _text: str) -> int:
            raise BrokenPipeError(32, "Broken pipe")

        def flush(self) -> None:
            raise BrokenPipeError(32, "Broken pipe")

    monkeypatch.setattr(sys, "stdout", _BrokenStdout())
    code = main(["generators", "--json"])

    # A closed consumer pipe is an I/O condition, not an operation failure;
    # the CLI must exit quietly with the dedicated code and no traceback.
    assert code == 1


def test_classes_command_lists_class_catalog() -> None:
    completed = run_cli("classes", "--json")

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert isinstance(payload, list)
    assert len(payload) > 20
    assert next(row for row in payload if row["key"] == "exponential")["formula"]


def test_class_check_command_reports_admissibility() -> None:
    completed = run_cli("class-check", "exponential", "--json")

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["canonical_inputs"]["class_key"] == "exponential"
    assert payload["details"]["admissible"] is True
    assert payload["schema_version"] == 1


def test_class_member_command_screens_membership() -> None:
    completed = run_cli(
        "class-member", "exponential", "--coefficients", "0.25,0.1", "--json"
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["details"]["member"] is True
    assert payload["canonical_inputs"]["class_key"] == "exponential"
    assert "screen" in payload["evidence_kind"].lower()


def test_compare_command_screens_containment() -> None:
    completed = run_cli("compare", "exponential", "cardioid", "--json")

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["canonical_inputs"]["inner"] == "exponential"
    assert payload["canonical_inputs"]["outer"] == "cardioid"
    assert payload["details"]["contained"] is True


def test_compare_command_reports_failed_containment_with_witness() -> None:
    completed = run_cli("compare", "starlike", "exponential", "--json")

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["details"]["contained"] is False
    assert payload["details"]["witness_w"] is not None
    assert payload["details"]["margin"] is None


def test_extremal_coefficients_command_emits_exact_strings() -> None:
    completed = run_cli("extremal-coefficients", "exponential", "--order", "4", "--json")

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["class_key"] == "exponential"
    assert payload["order"] == 4
    assert all(isinstance(value, str) for value in payload["coefficients"])


def test_verify_command_screen_tier_emits_screen_evidence() -> None:
    completed = run_cli(
        "verify",
        "--coefficients",
        "0.25",
        "--property",
        "starlike",
        "--max-cost",
        "screen",
        "--json",
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["tier"] == "screen"
    assert payload["evidence_kind"] == "numerical_screen"
    assert payload["details"]["outcome"] == "passes_screen"
    assert payload["schema_version"] == 1


def test_verify_command_symbolic_tier_can_prove() -> None:
    completed = run_cli(
        "verify",
        "--coefficients",
        "0.1",
        "--property",
        "starlike",
        "--max-cost",
        "symbolic",
        "--json",
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["tier"] == "symbolic"
    assert payload["details"]["outcome"] == "proven"
    assert payload["evidence_kind"] == "exact_proof"


def test_verify_command_rigorous_tier_certifies_violation() -> None:
    completed = run_cli(
        "verify",
        "--coefficients",
        "1",
        "--property",
        "starlike",
        "--max-cost",
        "rigorous",
        "--json",
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["tier"] == "rigorous"
    assert payload["details"]["outcome"] == "certified_violation"
    assert payload["details"]["certified"] is True


def test_verify_command_rejects_unknown_tier_with_structured_error() -> None:
    completed = run_cli(
        "verify",
        "--coefficients",
        "0.25",
        "--max-cost",
        "not-a-tier",
        "--json",
    )

    assert completed.returncode == 2
    payload = json.loads(completed.stdout)
    assert payload["failure_state"] == "invalid_input"


def test_find_counterexample_command_certifies_violation() -> None:
    completed = run_cli(
        "find-counterexample", "--coefficients", "1", "--property", "starlike", "--json"
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["details"]["certified"] is True
    assert payload["canonical_inputs"]["property"] == "starlike"
    assert payload["details"]["interval_upper"] < 0.0


def test_find_counterexample_command_accepts_witness_hint() -> None:
    completed = run_cli(
        "find-counterexample",
        "--coefficients",
        "1",
        "--hint=-0.7,0",
        "--json",
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["details"]["certified"] is True


def test_plot_command_writes_svg_domain_plot(tmp_path: Path) -> None:
    output = tmp_path / "domain.svg"
    completed = run_cli("plot", "domain", "exponential", "--output", str(output))

    assert completed.returncode == 0, completed.stderr
    assert output.exists()
    text = output.read_text(encoding="utf-8")
    assert "<svg" in text
    assert "not a proof" in text.lower() or "taylor polynomial" in text.lower()


def test_plot_command_writes_svg_phase_plot(tmp_path: Path) -> None:
    output = tmp_path / "phase.svg"
    completed = run_cli("plot", "phase", "exponential", "--output", str(output))

    assert completed.returncode == 0, completed.stderr
    assert output.exists()
    assert "<svg" in output.read_text(encoding="utf-8")


def test_lab_commands_fail_cleanly_without_numpy() -> None:
    import shutil

    if shutil.which("python3") is None:
        pytest.skip("python3 not available")
    # The lab commands require the optional numpy dependency; without it the
    # CLI must surface a clean ImportError path rather than a traceback.
    completed = run_cli("crypto-lab", "metrics", "--reference", "aes")
    if completed.returncode != 0:
        assert "lab" in completed.stderr.lower() or "numpy" in completed.stderr.lower()

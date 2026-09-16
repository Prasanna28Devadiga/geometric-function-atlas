"""A failed sufficient test must not become a refutation."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

EXAMPLES = Path(__file__).resolve().parents[1] / "examples" / "research_workflows"


@pytest.mark.parametrize("a,status", [("1", False), ("1/2", True), ("2/5", True), ("3/4", False)])
def test_conjecture_workflow_solves_and_repairs(tmp_path: Path, a: str, status: bool) -> None:
    script = EXAMPLES / "conjecture_counterexample.py"
    assert script.is_file(), "executable conjecture-repair workflow missing"
    run = subprocess.run([sys.executable, str(script), "--a", a, "--output", str(tmp_path)], capture_output=True, text=True, check=False)
    assert run.returncode == 0, run.stderr
    data = json.loads((tmp_path / "conjecture_counterexample.json").read_text())
    assert data["starlike"] is status
    assert data["exact_parameter_range"] == "0 <= a <= 1/2"
    assert data["sufficient_test_control"]["starlike"] is True
    assert data["sufficient_test_control"]["coefficient_sum_exact"] == "53/27"
    assert data["sufficient_test_control"]["test_conclusive"] is False
    if not status:
        assert data["witness"]["logarithmic_derivative_is_negative"] is True
    if a == "1":
        assert data["witness"]["point_exact"] == "-3/4"
        assert data["witness"]["value_exact"] == "-2"
        assert data["public_witness_replay"]["certified"] is True
    assert (tmp_path / "conjecture_counterexample.svg").is_file()

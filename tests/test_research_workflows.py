"""End-to-end researcher problems, not only API availability."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

EXAMPLES = Path(__file__).resolve().parents[1] / "examples" / "research_workflows"


def test_coefficient_workflow_solves_starlike_problem(tmp_path: Path) -> None:
    script = EXAMPLES / "coefficient_comparison.py"
    assert script.is_file(), "the executable coefficient research workflow is missing"
    result = subprocess.run(
        [sys.executable, str(script), "--generator", "starlike", "--output", str(tmp_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    data = json.loads((tmp_path / "coefficient_comparison.json").read_text())
    assert data["transition_mu"] == ["1/2", "1"]
    assert data["novelty_claim"] is False
    by_mu = {row["mu"]: row for row in data["values"]}
    assert by_mu["0"]["bound"] == "3"
    assert by_mu["3/4"]["bound"] == "1"
    assert all(row["attained_value"] == row["bound"] for row in data["values"])
    assert by_mu["0"]["schwarz_function"] == "z"
    assert by_mu["3/4"]["schwarz_function"] == "z^2"
    assert "not a proof" in (tmp_path / "coefficient_comparison.svg").read_text()


def test_coefficient_workflow_changed_input_sine(tmp_path: Path) -> None:
    result = subprocess.run(
        [sys.executable, str(EXAMPLES / "coefficient_comparison.py"),
         "--generator", "sine", "--output", str(tmp_path)],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr
    data = json.loads((tmp_path / "coefficient_comparison.json").read_text())
    assert data["transition_mu"] == ["0", "1"]
    by_mu = {row["mu"]: row for row in data["values"]}
    assert by_mu["1/2"]["bound"] == "1/2"
    assert by_mu["2"]["bound"] == "3/2"
    assert all(row["bound"] == row["attained_value"] for row in data["values"])

"""An operator workflow must show its exact transferable identity."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

EXAMPLES = Path(__file__).resolve().parents[1] / "examples" / "research_workflows"


@pytest.mark.parametrize("generator,expected", [("starlike", ["1", "1", "1"]), ("sine", ["1/2", "1/6", "1/36"])])
def test_alexander_workflow_transfers_coefficients(tmp_path: Path, generator: str, expected: list[str]) -> None:
    script = EXAMPLES / "alexander_transform.py"
    assert script.is_file(), "Alexander problem-solving workflow missing"
    run = subprocess.run([sys.executable, str(script), "--generator", generator, "--output", str(tmp_path)], capture_output=True, text=True, check=False)
    assert run.returncode == 0, run.stderr
    data = json.loads((tmp_path / "alexander_transform.json").read_text())
    assert data["transformed_coefficients"][:3] == expected
    assert data["operator_identity_residual"] == "0"
    assert data["class_transfer_identity_residual"] == "0"
    assert data["truncation_inherits_convexity"] is False
    assert data["novelty_claim"] is False
    assert (tmp_path / "alexander_transform.svg").is_file()

"""Sharp radius: global proof and axis-only counterexample are distinct."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

EXAMPLES = Path(__file__).resolve().parents[1] / "examples" / "research_workflows"


@pytest.mark.parametrize("source,s,expected", [("sine", "1/2", "asin(3/4)"), ("sine", "7/10", "1"), ("off_axis", "1/4", None)])
def test_radius_workflow_solves_directed_problem(tmp_path: Path, source: str, s: str, expected: str | None) -> None:
    script = EXAMPLES / "sharp_radius.py"
    assert script.is_file(), "sharp radius workflow missing"
    run = subprocess.run([sys.executable, str(script), "--source", source, "--s", s, "--output", str(tmp_path)], capture_output=True, text=True, check=False)
    assert run.returncode == 0, run.stderr
    data = json.loads((tmp_path / "sharp_radius.json").read_text())
    assert data["novelty_claim"] is False
    if expected:
        assert data["radius_exact"] == expected
    if source == "off_axis":
        assert data["admissibility"]["normalized_coefficient_sum"] == "195/256"
        assert data["admissibility"]["positive_real_lower_bound"] == "367/1024"
        assert data["axis_shortcut_counterexample"]["excess_exact"] == "1327/131072"
        assert data["contact_direction"] == "imaginary_axis"
    elif s == "1/2":
        assert data["snapshot_anchor"]["status"] == "touch_proven_exact"
        assert data["snapshot_anchor"]["has_full_certificate"] is False
    assert (tmp_path / "sharp_radius.svg").is_file()
    assert (tmp_path / "radius_profile.svg").is_file()

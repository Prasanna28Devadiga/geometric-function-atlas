"""The plotted object must be the one the mathematical question asks about."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from xml.etree import ElementTree

import pytest

EXAMPLES = Path(__file__).resolve().parents[1] / "examples" / "research_workflows"


@pytest.mark.parametrize("generator,coefficients", [("starlike", ["2", "3", "4"]), ("sine", ["1", "1/2", "1/9"])])
def test_geometry_workflow_uses_canonical_member(tmp_path: Path, generator: str, coefficients: list[str]) -> None:
    script = EXAMPLES / "class_geometry.py"
    assert script.is_file(), "class geometry research workflow missing"
    run = subprocess.run([sys.executable, str(script), "--generator", generator, "--output", str(tmp_path)], capture_output=True, text=True, check=False)
    assert run.returncode == 0, run.stderr
    data = json.loads((tmp_path / "class_geometry.json").read_text())
    assert data["canonical_coefficients"][:3] == coefficients
    assert data["object_kind"] == "canonical_ma_minda_member"
    assert data["logarithmic_derivative_identity_residual"] == "0"
    assert data["truncation_is_not_class_certificate"] is True
    assert data["plot_status"] == "sampled_visualization"
    assert len(data["panels"]) == 3
    assert data["panels"][0]["object"] == "phi"
    assert data["panels"][1]["object"] == "f_phi"
    assert data["panels"][2]["object"] == "z_fprime_over_f"
    svg = ElementTree.parse(tmp_path / "class_geometry.svg").getroot()
    assert svg.tag.endswith("svg")
    assert "not a proof" in " ".join(svg.itertext())

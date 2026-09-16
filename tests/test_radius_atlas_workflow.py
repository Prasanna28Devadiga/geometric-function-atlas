"""The directed-radius atlas export must be deterministic and honesty-preserving."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

EXAMPLE = (
    Path(__file__).resolve().parents[1]
    / "examples"
    / "research_workflows"
    / "radius_atlas.py"
)


def _run(output: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(EXAMPLE), "--output", str(output)],
        capture_output=True,
        text=True,
        check=False,
    )


def test_radius_atlas_exports_all_directed_cells_deterministically(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    left = _run(first)
    right = _run(second)

    assert left.returncode == 0, left.stderr
    assert right.returncode == 0, right.stderr
    assert (first / "radius_atlas.json").read_bytes() == (
        second / "radius_atlas.json"
    ).read_bytes()
    assert (first / "radius_atlas.svg").read_bytes() == (
        second / "radius_atlas.svg"
    ).read_bytes()

    data = json.loads((first / "radius_atlas.json").read_text(encoding="utf-8"))
    assert data["workflow"] == "radius_atlas"
    assert data["class_count"] == 28
    assert data["record_count"] == 702
    assert data["directed_pair_denominator"] == 28 * 27
    assert data["missing_pair_count"] == 28 * 27 - 702
    assert len(data["cells"]) == 28 * 28
    assert data["status_counts"] == {
        "audit_required": 12,
        "closed_form_confirmed": 140,
        "touch_proven_exact": 323,
        "trivial_containment": 142,
        "unidentified": 85,
    }
    assert data["replayable_certificate_count"] == 8

    cells = {
        (cell["source"], cell["target"]): cell
        for cell in data["cells"]
    }
    assert cells[("sine", "sigmoid")]["value_exact"] == "asin((E-1)/(E+1))"
    assert cells[("sine", "sigmoid")]["has_replay_certificate"] is True
    assert cells[("sigmoid", "sine")]["value_exact"] == "1"
    assert cells[("sigmoid", "sine")]["status"] == "trivial_containment"
    assert cells[("sine", "sine")]["status"] == "diagonal_not_a_radius_problem"
    assert any(cell["status"] == "missing_snapshot_row" for cell in data["cells"])

    svg = (first / "radius_atlas.svg").read_text(encoding="utf-8")
    assert "Directed inclusion-radius atlas" in svg
    assert "missing snapshot row" in svg
    assert "source rows" in svg
    assert "target columns" in svg

    guide = (
        Path(__file__).resolve().parents[1]
        / "docs"
        / "workflows"
        / "radius_atlas.md"
    ).read_text(encoding="utf-8")
    assert "702" in guide
    assert "756" in guide
    assert "54" in guide
    assert "sine→sigmoid" in guide
    assert "sigmoid→sine" in guide

"""The directed-radius atlas export must be deterministic and honesty-preserving."""

from __future__ import annotations

import json
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

import sympy as sp

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
        / "reference"
        / "radii.md"
    ).read_text(encoding="utf-8")
    assert "702" in guide
    assert "756" in guide
    assert "54" in guide
    assert "sine→sigmoid" in guide
    assert "sigmoid→sine" in guide


def test_alias_inclusive_counts_do_not_masquerade_as_distinct_problems() -> None:
    root = Path(__file__).resolve().parents[1]
    data = root / "src" / "geometric_function_atlas" / "data"
    classes = json.loads((data / "classes.json").read_text())["classes"]
    z = sp.Symbol("z")
    assert classes["janowski_A0_B-1"]["phi_formula"] == "(1+(0)*z)/(1+(-1)*z)"
    assert classes["order_0.5"]["phi_formula"] == "(1+(1-2*(1/2))*z)/(1-z)"
    janowski = (1 + 0 * z) / (1 + (-1) * z)
    order_half = (1 + (1 - 2 * sp.Rational(1, 2)) * z) / (1 - z)
    assert sp.simplify(janowski - order_half) == 0
    assert sp.simplify(janowski - 1 / (1 - z)) == 0

    rows = json.loads((data / "radii_snapshot.json").read_text())["radii"]
    keys = {key for row in rows for key in (row["inner"], row["target"])}
    raw_directions = {(row["inner"], row["target"]) for row in rows}
    assert len(keys) == 28
    assert len(raw_directions) == len(rows) == 702
    missing = {(a, b) for a in keys for b in keys if a != b} - raw_directions
    assert len(missing) == 54
    assert {target for _, target in missing} == {"nephroid", "three_leaf"}

    def canonical(key: str) -> str:
        return "order_0.5" if key == "janowski_A0_B-1" else key

    groups = defaultdict(list)
    for row in rows:
        groups[canonical(row["inner"]), canonical(row["target"])].append(row)
    assert {key for key in groups if key[0] == key[1]} == {("order_0.5", "order_0.5")}
    distinct = {key: members for key, members in groups.items() if key[0] != key[1]}
    assert len(distinct) == 650
    assert Counter(members[0]["status"] for members in distinct.values()) == {
        "touch_proven_exact": 290,
        "closed_form_confirmed": 133,
        "trivial_containment": 133,
        "unidentified": 83,
        "audit_required": 11,
    }
    assert all(len({member["status"] for member in members}) == 1 for members in groups.values())
    assert all(len({member["value_exact"] for member in members}) == 1 for members in groups.values())

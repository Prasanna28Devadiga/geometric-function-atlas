"""A caller-defined class must run end to end with exact, reproducible output."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import sympy as sp

from geometric_function_atlas import verify_research_bundle_manifest

EXAMPLES = Path(__file__).resolve().parents[1] / "examples" / "research_workflows"


def _run(output: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(EXAMPLES / "custom_class.py"),
            "--alpha",
            "1/4",
            "--order",
            "4",
            "--output",
            str(output),
        ],
        capture_output=True,
        text=True,
        check=False,
    )


def test_custom_class_workflow_is_exact_labeled_and_deterministic(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    first_run = _run(first)
    second_run = _run(second)
    assert first_run.returncode == 0, first_run.stderr
    assert second_run.returncode == 0, second_run.stderr

    first_json = first / "custom_class.json"
    second_json = second / "custom_class.json"
    assert first_json.read_bytes() == second_json.read_bytes()
    data = json.loads(first_json.read_text(encoding="utf-8"))

    identity = data["generator"]["identity"]
    assert identity.startswith("user:starlike_order_1_4:")
    assert len(identity.rsplit(":", 1)[1]) == 64
    assert data["generator"]["formula"] == "(z/2 + 1)/(1 - z)"
    assert data["admissibility_screen"]["canonical_inputs"]["class_key"] == identity
    assert data["admissibility_screen"]["evidence_kind"] == "numerical_screen"
    assert data["canonical_member"]["logarithmic_derivative_identity_residual"] == "0"
    assert data["canonical_member"]["coefficients_a2_onward"][:3] == [
        "3/2",
        "15/8",
        "35/16",
    ]
    assert [row["mu"] for row in data["fekete_szego"]] == ["0", "1/2", "1"]
    assert [row["bound"] for row in data["fekete_szego"]] == ["15/8", "3/4", "3/4"]
    assert all(
        row["record"]["canonical_inputs"]["generator"] == identity
        for row in data["fekete_szego"]
    )
    assert data["finite_truncation_membership_screen"]["tier"] == "screen"
    assert data["containment_screen"]["tier"] == "screen"
    assert data["novelty_claim"] is False

    artifact_names = {
        "phi": "custom_class_phi.svg",
        "z*phi": "custom_class_z_times_phi.svg",
        "f_phi": "custom_class_f_phi.svg",
    }
    payloads = []
    for object_name, filename in artifact_names.items():
        assert data["plot_objects"][object_name]["generator_identity"] == identity
        assert data["plot_objects"][object_name]["object"] == object_name
        left = first / filename
        right = second / filename
        assert left.read_bytes() == right.read_bytes()
        payloads.append(left.read_bytes())
    assert len(set(payloads)) == 3
    assert b"Starlike of order 1/4" in payloads[0]

    first_manifest = first / "research_bundle_manifest.json"
    second_manifest = second / "research_bundle_manifest.json"
    assert first_manifest.read_bytes() == second_manifest.read_bytes()
    manifest = verify_research_bundle_manifest(first_manifest)
    assert manifest["workflow"] == "custom_class"
    assert manifest["entrypoint"] == "examples/research_workflows/custom_class.py"
    assert manifest["parameters"] == {"alpha": "1/4", "order": 4}
    assert manifest["primary_record"] == "custom_class.json"
    assert [artifact["path"] for artifact in manifest["artifacts"]] == [
        "custom_class.json",
        "custom_class_f_phi.svg",
        "custom_class_phi.svg",
        "custom_class_z_times_phi.svg",
    ]

    # Independent algebraic anchors: do not merely trust JSON strings.
    assert sp.Rational(data["canonical_member"]["coefficients_a2_onward"][1]) == sp.Rational(15, 8)

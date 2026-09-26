"""Release-scope regression: public keys survive canonical analysis."""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "src/geometric_function_atlas/data"
SCRIPT = ROOT / "scripts/build_radius_scope.py"


def test_scope_artifact_is_deterministic_and_preserves_public_keys():
    artifact = json.loads((DATA / "radius_scope_2026_09_27.json").read_text())
    actual = subprocess.run([sys.executable, str(SCRIPT), "--check"], cwd=ROOT,
                            capture_output=True, text=True, check=False)
    assert actual.returncode == 0, actual.stdout + actual.stderr
    scope = artifact["scope"]
    assert scope["source_key_count"] == 28
    assert scope["target_key_count"] == 26
    assert scope["never_source_keys"] == [
        "bean_tanh", "booth_0.3", "booth_0.7", "cardioid_exp", "cissoid_diocles",
        "epicycloid_3", "epicycloid_6", "four_leaf", "nonconvex_sec",
        "petal_arcsinh", "strip_arctan",
    ]
    assert scope["never_target_among_source_keys"] == ["nephroid", "three_leaf"]
    assert scope["full_catalog"] is False
    assert artifact["canonical_aliases"] == {"janowski_A0_B-1": "order_0.5"}
    assert artifact["next_release_todo"]["directed_questions"] == 1406
    assert artifact["counts"]["raw_key_rows"] == 702
    assert artifact["counts"]["canonical_questions"] == 650
    assert artifact["counts"]["alias_identity_rows"] == 2
    assert sum(artifact["counts"]["status_buckets"].values()) == 650
    raw = json.loads((DATA / "radii_snapshot.json").read_text())
    assert len(raw["radii"]) == 702
    assert any(r["inner"] == "janowski_A0_B-1" for r in raw["radii"])
    classes = json.loads((DATA / "classes.json").read_text())["classes"]
    assert "janowski_A0_B-1" in classes and "order_0.5" in classes

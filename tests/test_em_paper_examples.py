"""End-to-end reproduction and saved-input trust boundary for the paper examples."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples" / "em_paper"


def run_example(name, *args):
    return subprocess.run(
        [sys.executable, str(EXAMPLES / name), *map(str, args)],
        cwd=ROOT, capture_output=True, text=True, timeout=180, check=False,
    )


@pytest.fixture(scope="module")
def saved_inputs(tmp_path_factory):
    directory = tmp_path_factory.mktemp("em-paper-inputs")
    paths = []
    for command in ("radii", "artifact-classes"):
        result = subprocess.run(
            [sys.executable, "-m", "geometric_function_atlas", command, "--json"],
            cwd=ROOT, capture_output=True, text=True, check=True,
        )
        path = directory / f"{command}.json"
        path.write_text(result.stdout, encoding="utf-8")
        paths.append(path)
    return tuple(paths)


def test_saved_classes_reject_executable_formula_without_evaluating_it(saved_inputs, tmp_path):
    radii_path, classes_path = saved_inputs
    payload = json.loads(classes_path.read_text(encoding="utf-8"))
    payload["record"]["rows"][0]["phi_formula"] = "__import__('os').getpid()"
    altered = tmp_path / "altered.json"
    altered.write_text(json.dumps(payload), encoding="utf-8")
    result = run_example("contact_classification.py", radii_path, altered)
    assert result.returncode != 0
    assert "untrusted class formula" in result.stderr
    assert not result.stdout


def test_saved_classes_reject_key_tampering(saved_inputs, tmp_path):
    radii_path, classes_path = saved_inputs
    payload = json.loads(classes_path.read_text(encoding="utf-8"))
    payload["record"]["rows"][0]["key"] = "fake_class"
    altered = tmp_path / "altered-key.json"
    altered.write_text(json.dumps(payload), encoding="utf-8")
    result = run_example("contact_classification.py", radii_path, altered)
    assert result.returncode != 0
    assert "untrusted class" in result.stderr
    assert not result.stdout


def test_contact_classification_saved_inputs_match_paper(saved_inputs):
    result = run_example("contact_classification.py", *saved_inputs)
    assert result.returncode == 0, result.stderr
    counts = json.loads(result.stdout)
    assert counts == {
        "canonical_questions": 650, "paper_proved_exact": 19,
        "trivial_containment": 133, "audit_required": 11,
        "real_axis:total": 355, "real_axis:touch_proven_exact": 273,
        "real_axis:closed_form_confirmed": 76, "real_axis:unidentified": 6,
        "real_axis:single_sign": 315, "real_axis:mixed_sign": 40,
        "real_axis:formula_matches": 355,
        "off_axis:total": 132, "off_axis:closed_form_confirmed": 56,
        "off_axis:unidentified": 76, "off_axis:formula_matches": 1,
        "off_axis:formula_mismatch": 131, "taylor_order_tested": 22,
    }


def test_reciprocal_counts_from_saved_radii(saved_inputs, tmp_path):
    result = run_example("reciprocal_figure.py", "--radii", saved_inputs[0],
                         "--output", tmp_path / "figure.pdf")
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout.splitlines()[0]) == {
        "eligible": 557, "reciprocal_pairs": 240, "reciprocal_unequal": 234,
        "nontrivial": 424, "nontrivial_shared": 148, "shared_groups": 42,
    }


def test_theorem48_interval_bounds_are_positive():
    result = run_example("thm48_interval_check.py")
    assert result.returncode == 0, result.stderr
    assert "sine     bulk lower bound 9.067e-6 | H'' single-box 0.01309 | H'' 50-box 0.01357" in result.stdout
    assert "sigmoid  bulk lower bound 8.306e-8 | H'' single-box 0.01332 | H'' 50-box 0.01332" in result.stdout

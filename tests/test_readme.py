from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "geometric_function_atlas", *args],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )


def test_readme_uses_operation_language_not_public_release_phases() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "## Phase" not in readme
    assert "Later phases" not in readme
    assert "gfa plot sine --order 12 --output sine-domain.svg" in readme


def test_public_docs_do_not_expose_internal_phase_nomenclature() -> None:
    public_docs = (
        ROOT / "README.md",
        ROOT / "CHANGELOG.md",
        ROOT / "docs" / "INSTALL.md",
        ROOT / "docs" / "ROADMAP.md",
        ROOT / "docs" / "RESULT_CONTRACT.md",
        ROOT / "docs" / "WEB_PARITY.md",
    )

    for path in public_docs:
        text = path.read_text(encoding="utf-8")
        assert re.search(r"\bphase(?:s)?\b", text, re.IGNORECASE) is None, path


def test_readme_computation_examples_execute() -> None:
    commands = (
        ("generators",),
        ("coefficients", "sine", "--order", "5"),
        ("fekete-szego", "exponential", "--mu", "0"),
        (
            "verify-counterexample",
            "--coefficients",
            "1",
            "--point=-0.75,0",
        ),
    )

    for command in commands:
        completed = _run(*command)
        assert completed.returncode == 0, (command, completed.stderr)


def test_readme_plot_is_regenerated_not_hand_drawn(tmp_path: Path) -> None:
    generated = tmp_path / "sine-domain.svg"
    completed = _run(
        "plot",
        "sine",
        "--order",
        "12",
        "--output",
        str(generated),
    )

    assert completed.returncode == 0, completed.stderr
    assert generated.read_bytes() == (ROOT / "docs/assets/sine-domain.svg").read_bytes()


def test_readme_custom_plot_asset_is_regenerated(tmp_path: Path) -> None:
    generated = tmp_path / "polynomial.svg"
    completed = _run(
        "plot",
        "--coefficients",
        "1,-0.25",
        "--output",
        str(generated),
    )

    assert completed.returncode == 0, completed.stderr
    assert generated.read_bytes() == (ROOT / "docs/assets/polynomial.svg").read_bytes()


def test_readme_plot_controls_execute(tmp_path: Path) -> None:
    generated = tmp_path / "controlled.svg"
    completed = _run(
        "plot",
        "sine",
        "--order",
        "16",
        "--radius",
        "0.95",
        "--rings",
        "6",
        "--spokes",
        "16",
        "--output",
        str(generated),
    )

    assert completed.returncode == 0, completed.stderr
    assert generated.is_file()
    assert "Taylor order 16" in completed.stdout


def test_generated_plot_assets_are_included_in_source_distribution() -> None:
    manifest = (ROOT / "MANIFEST.in").read_text(encoding="utf-8")

    assert "recursive-include docs/assets *.svg" in manifest

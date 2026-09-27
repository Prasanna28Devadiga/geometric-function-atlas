"""Release identity, frozen publication, and installer holdback."""

import json
from pathlib import Path

from geometric_function_atlas import __version__

ROOT = Path(__file__).resolve().parents[1]


def test_060_identity_is_consistent() -> None:
    citation = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert __version__ == "0.6.0"
    assert "\nversion: 0.6.0\n" in citation
    assert "\ndate-released: 2026-09-27\n" in citation
    assert "\n## 0.6.0 — 2026-09-27\n" in changelog


def test_release_procedure_selects_single_current_wheel() -> None:
    procedure = (ROOT / "docs/RELEASING.md").read_text(encoding="utf-8")
    assert 'assert len(wheels) == 1' in procedure
    assert 'scripts/check_clean_install.py "$wheel"' in procedure
    assert 'scripts/check_uv_tool_install.py "$wheel" --python 3.12' in procedure
    assert 'dist/geometric_function_atlas-0.5.0-py3-none-any.whl' not in procedure


def test_installers_remain_at_published_050_until_pypi_060_is_live() -> None:
    wheel = "releases/download/v0.5.0/geometric_function_atlas-0.5.0-py3-none-any.whl"
    for name in ("install.sh", "install.ps1"):
        assert wheel in (ROOT / "scripts" / name).read_text(encoding="utf-8")


def test_frozen_pypi_manifest_targets_the_verified_060_release() -> None:
    manifest = json.loads((ROOT / ".github/pypi-publish.json").read_text(encoding="utf-8"))
    assert manifest["tag"] == "v0.6.0"
    assert manifest["assets"]["wheel"]["name"] == "geometric_function_atlas-0.6.0-py3-none-any.whl"

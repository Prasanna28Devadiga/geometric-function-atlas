"""Stable release-candidate identity and pre-publication installer boundary."""

from pathlib import Path

from geometric_function_atlas import __version__

ROOT = Path(__file__).resolve().parents[1]


def test_stable_050_identity_is_consistent() -> None:
    citation = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert __version__ == "0.5.0"
    assert "\nversion: 0.5.0\n" in citation
    assert "\ndate-released: 2026-09-27\n" in citation
    assert "\n## 0.5.0 — 2026-09-27\n" in changelog


def test_prepublication_installers_keep_the_public_040_wheel() -> None:
    wheel = "releases/download/v0.4.0/geometric_function_atlas-0.4.0-py3-none-any.whl"
    for name in ("install.sh", "install.ps1"):
        assert wheel in (ROOT / "scripts" / name).read_text(encoding="utf-8")

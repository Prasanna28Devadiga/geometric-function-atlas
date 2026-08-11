from __future__ import annotations

import json
import subprocess
import sys

from geometric_function_atlas import citation_export, citation_formats
from geometric_function_atlas.citation import CitationBundle


def test_registry_citation_export_matches_website_formats_without_clock_dependence() -> None:
    bundle = citation_export(
        {
            "key": "sine-family",
            "title": "Sine family",
            "author": "GFT Registry",
            "year": 2026,
            "url": "https://gft-registry.fly.dev/family/1",
            "kind": "family",
        }
    )

    assert isinstance(bundle, CitationBundle)
    assert set(bundle.formats) == {"BibTeX", "RIS", "Plain", "LaTeX"}
    assert "@misc{sine-family" in bundle.formats["BibTeX"]
    assert "\\bibitem{sine-family}" in bundle.formats["LaTeX"]
    assert "accessed" not in bundle.formats["Plain"]


def test_published_citation_uses_article_fields_and_explicit_access_date() -> None:
    formats = citation_formats(
        {
            "key": "paper-1",
            "title": "A result",
            "author": "A. Author",
            "year": 2024,
            "url": "https://doi.org/10/demo",
            "journal": "Journal",
            "doi": "10/demo",
        },
        accessed="2026-08-11",
    )

    assert "@article{paper-1" in formats["BibTeX"]
    assert "journal      = {Journal}" in formats["BibTeX"]
    assert "DO  - 10/demo" in formats["RIS"]
    assert "accessed 2026-08-11" in formats["Plain"]


def test_citation_helpers_are_top_level_exports() -> None:
    formats = citation_formats(
        key="registry", title="Registry", year=2026, url="https://example.org"
    )

    assert formats["LaTeX"].startswith("\\bibitem{registry}")
    assert citation_export(key="registry", title="Registry", year=2026, url="https://example.org").key == "registry"


def test_citation_cli_exports_all_four_formats() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "geometric_function_atlas",
            "citation",
            "--key",
            "registry",
            "--title",
            "Registry",
            "--year",
            "2026",
            "--url",
            "https://example.org",
            "--json",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert set(payload["formats"]) == {"BibTeX", "RIS", "Plain", "LaTeX"}

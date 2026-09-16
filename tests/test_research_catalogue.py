"""The research catalogue must cover the fixed thirty-example denominator."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_research_catalogue_has_one_terminal_route_for_every_example() -> None:
    catalogue = (ROOT / "docs" / "workflows" / "catalogue.md").read_text(
        encoding="utf-8"
    )
    identifiers = re.findall(r"^## (EX\d{2}) —", catalogue, flags=re.MULTILINE)

    assert identifiers == [f"EX{index:02d}" for index in range(1, 31)]
    assert catalogue.count("**Disposition:**") == 30
    assert catalogue.count("**Replay:**") == 30
    for identifier in ("EX21", "EX23", "EX25", "EX26", "EX27"):
        section = catalogue.split(f"## {identifier} —", 1)[1].split("\n## ", 1)[0]
        assert "bounded ABSTAIN" in section
        assert "does not" in section


def test_catalogue_preserves_key_epistemic_boundaries() -> None:
    catalogue = (ROOT / "docs" / "workflows" / "catalogue.md").read_text(
        encoding="utf-8"
    )

    assert "c01_fails_sufficient_condition" in catalogue
    assert "not a counterexample" in catalogue
    assert "direction is never inferred" in catalogue
    assert "only eight" in catalogue
    assert "numerical screen is not a containment theorem" in catalogue
    assert "No novelty claim" in catalogue

"""The research catalogue must keep all thirty ideas readable and accounted for."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_research_catalogue_has_one_terminal_route_for_every_example() -> None:
    catalogue = (ROOT / "docs" / "workflows" / "catalogue.md").read_text(
        encoding="utf-8"
    )
    identifiers = re.findall(r"^\*\*(EX\d{2}) —", catalogue, flags=re.MULTILINE)

    assert identifiers == [f"EX{index:02d}" for index in range(1, 31)]
    assert "## Ready to try" in catalogue
    assert "## Not yet supported" in catalogue
    assert "**Disposition:**" not in catalogue
    assert "**Replay:**" not in catalogue
    assert "bounded ABSTAIN" not in catalogue
    assert "| No. |" not in catalogue
    assert "### EX" not in catalogue
    assert len(catalogue.splitlines()) < 180


def test_catalogue_preserves_key_epistemic_boundaries() -> None:
    catalogue = (ROOT / "docs" / "workflows" / "catalogue.md").read_text(
        encoding="utf-8"
    )

    assert "does not disprove starlikeness" in catalogue
    assert "source and target cannot be swapped" in catalogue
    assert "eight have a local certificate" in catalogue
    assert "cannot prove containment" in catalogue
    for identifier in ("EX21", "EX23", "EX25", "EX26", "EX27"):
        section = catalogue.split(f"**{identifier} —", 1)[1].split("\n**EX", 1)[0]
        assert "**Not yet supported.**" in section

from __future__ import annotations

import json
from pathlib import Path

import pytest

from geometric_function_atlas import fekete_szego

_FIXTURE = Path(__file__).with_name("fixtures") / "fekete_szego_research_artifact.json"
_PAYLOAD = json.loads(_FIXTURE.read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", _PAYLOAD["cases"], ids=lambda case: case["id"])
def test_fekete_szego_matches_audited_research_artifact(case: dict[str, str]) -> None:
    result = fekete_szego(case["generator"], mu=case["mu"])
    assert str(result.value) == case["value_exact"]


def test_migration_fixture_records_source_and_scope() -> None:
    assert _PAYLOAD["source"]["repository"] == "gft-registry research artifact"
    assert _PAYLOAD["source"]["commit"] == "acee553"
    assert len(_PAYLOAD["cases"]) == 54

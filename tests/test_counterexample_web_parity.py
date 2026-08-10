from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from geometric_function_atlas import verify_counterexample

_FIXTURE = Path(__file__).with_name("fixtures") / "counterexample_web_parity.json"
_PAYLOAD = json.loads(_FIXTURE.read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", _PAYLOAD["cases"], ids=lambda case: case["id"])
def test_counterexample_intervals_match_web_verifier_fixture(
    case: dict[str, Any],
) -> None:
    result = verify_counterexample(
        case["coefficients"],
        point=tuple(case["point"]),
        property=case["property"],
    )

    assert [result.interval_lower, result.interval_upper] == pytest.approx(
        case["interval"], rel=0.0, abs=1e-12
    )
    assert result.certified is case["certified"]


def test_counterexample_fixture_records_web_source() -> None:
    assert _PAYLOAD["source"]["repository"] == "gft-registry research and web artifact"
    assert _PAYLOAD["source"]["commit"] == "acee553e03f9"
    assert len(_PAYLOAD["cases"]) == 6

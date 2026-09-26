"""Red-first checks for independently proved paper radius lanes."""
from dataclasses import replace

import pytest

from geometric_function_atlas import radius, replay_radius_certificate, verify_radius_certificate


@pytest.mark.parametrize("source,target,expected", [
    ("crescent", "exponential", "sin(1)"),
    ("exponential", "crescent", "asinh(1)"),
])
def test_reciprocal_paper_radii_replay_exactly(source, target, expected):
    row = radius(source, target)
    result = verify_radius_certificate(source, target)
    assert result.certified and result.status == "proven", result.to_dict()
    assert result.expected_candidate == expected
    assert result.steps and all(s.verified for s in result.steps)
    assert result.method == "paper_analytic_radius_replay"
    assert verify_radius_certificate(source, target, candidate="1/2").status == "candidate_mismatch"
    assert verify_radius_certificate(source, target, candidate="__import__(1)").status == "invalid_input"
    assert replay_radius_certificate(replace(row, value_exact=expected)).status == "corrupt_artifact"


def test_other_missing_paper_lanes_remain_unsupported():
    for source, target in [("sine", "rational_kr"), ("sigmoid", "rational_kr"), ("exponential", "sine")]:
        result = verify_radius_certificate(source, target)
        assert result.status == "not_replayable" and not result.certified

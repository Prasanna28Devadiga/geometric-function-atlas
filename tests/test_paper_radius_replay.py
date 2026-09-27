"""Red-first checks for independently proved paper radius lanes."""
from dataclasses import replace

import pytest

from geometric_function_atlas import (
    radius,
    replay_radius_certificate,
    verify_radius_certificate,
)


@pytest.mark.parametrize("source,target,expected", [
    ("crescent", "exponential", "sin(1)"),
    ("exponential", "crescent", "asinh(1)"),
])
def test_reciprocal_paper_radii_replay_exactly(source, target, expected):
    row = radius(source, target)
    result = verify_radius_certificate(source, target)
    assert not result.certified and result.status == "symbolic_replay_only", result.to_dict()
    assert result.expected_candidate == expected
    assert result.steps and all(s.verified for s in result.steps)
    assert result.method == "paper_symbolic_radius_replay"
    assert result.global_containment_check == "not_mechanized"
    assert result.to_dict()["global_containment_check"] == "not_mechanized"
    assert verify_radius_certificate(source, target, candidate="1/2").status == "candidate_mismatch"
    assert verify_radius_certificate(source, target, candidate="__import__(1)").status == "invalid_input"
    assert replay_radius_certificate(replace(row, value_exact="1/2")).status == "corrupt_artifact"
    assert row.to_dict()["computational_status"] == "unresolved"


def test_other_missing_paper_lanes_remain_unsupported():
    for source, target in [
        ("sine", "rational_kr"), ("sigmoid", "rational_kr"),
        ("cosh_sqrt", "lemniscate"), ("exponential", "sine"),
        ("rational_kr", "sine"), ("bell", "sine"),
        ("exponential", "bell"), ("sine", "exponential"), ("sine", "bell"),
    ]:
        result = verify_radius_certificate(source, target)
        assert result.status == "not_replayable" and not result.certified

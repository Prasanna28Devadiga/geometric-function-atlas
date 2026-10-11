"""Checks for the eleven paper radius lanes replayed outside the historical fixture."""
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
    ("cosh_sqrt", "lemniscate", "asinh(1)**2"),
    ("exponential", "sine", "log(1+sin(1))"),
    ("rational_kr", "sine", "(1+sqrt(2))/2*(sqrt(1+6*sin(1)+sin(1)**2)-1-sin(1))"),
    ("bell", "sine", "log(1+log(1+sin(1)))"),
    ("exponential", "bell", "1-exp(-1)"),
    ("sine", "exponential", "asin(1-exp(-1))"),
    ("sine", "bell", "asin(1-exp(exp(-1)-1))"),
    ("sine", "rational_kr", "asin(3-2*sqrt(2))"),
    ("sigmoid", "rational_kr", "log(2)/2"),
])
def test_paper_radii_replay_exactly(source, target, expected):
    row = radius(source, target)
    result = verify_radius_certificate(source, target)
    assert result.certified and result.status == "proven", result.to_dict()
    assert result.expected_candidate == expected
    assert result.steps and all(s.verified for s in result.steps)
    assert any(s.scope.startswith("cited written paper lemma") for s in result.steps)
    assert result.global_containment_check == "bounded_chain_replayed"
    assert verify_radius_certificate(source, target, candidate="1/2").status == "candidate_mismatch"
    assert verify_radius_certificate(source, target, candidate="__import__(1)").status == "invalid_input"
    assert replay_radius_certificate(replace(row, value_exact="1/2")).status == "corrupt_artifact"
    assert row.to_dict()["computational_status"] == "unresolved"

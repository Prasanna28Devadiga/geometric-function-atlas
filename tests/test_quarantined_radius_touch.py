"""Quarantined legacy touch failures: exact axis equations are not global proofs."""
import pytest

from geometric_function_atlas import radius, replay_radius_certificate
import geometric_function_atlas.radii as radius_module

PAIRS = [
    ("bell", "janowski_A0.75_B-0.25"),
    ("janowski_A0.5_B-0.5", "janowski_A0.75_B-0.25"),
    ("janowski_A0_B-1", "janowski_A0.75_B-0.25"),
    ("janowski_A1_B-0.5", "janowski_A0.75_B-0.25"),
    ("order_0.25", "janowski_A0.75_B-0.25"),
    ("order_0.5", "janowski_A0.75_B-0.25"),
    ("order_0.75", "janowski_A0.75_B-0.25"),
    ("starlike", "janowski_A0.75_B-0.25"),
    ("strongly_0.25", "janowski_A0.75_B-0.25"),
    ("strongly_0.5", "janowski_A0.75_B-0.25"),
    ("cardioid", "janowski_A1_B0"),
    ("cardioid", "order_0.75"),
]

@pytest.mark.parametrize("source,target", PAIRS)
def test_quarantined_axis_touch_is_exact_but_not_a_radius_proof(source, target):
    row = radius(source, target)
    result = radius_module._recheck_quarantined_axis_touch(row)
    assert result == "touch_equation_only"
    assert row.status.value == "audit_required"
    assert replay_radius_certificate(row).status == "not_replayable"

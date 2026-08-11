"""Witness search: grid search for a violation, then interval certification."""

from __future__ import annotations

import pytest

from geometric_function_atlas.counterexamples import find_counterexample
from geometric_function_atlas.records import validate_screen_record


def test_search_certifies_starlike_violation_for_z_plus_z_squared() -> None:
    result = find_counterexample([1.0], property="starlike")
    assert result.certified is True
    assert result.point is not None
    assert result.interval_upper is not None
    assert result.interval_upper < 0.0
    assert result.threshold == 0.0
    assert result.margin is not None and result.margin > 0.0


def test_search_finds_no_certified_violation_for_safe_polynomial() -> None:
    result = find_counterexample([0.25], property="starlike")
    assert result.certified is False
    assert result.point is not None  # the search still reports its best point


def test_search_certifies_becker_violation() -> None:
    result = find_counterexample([1.0], property="becker_univalent")
    assert result.certified is True
    assert result.interval_lower is not None
    assert result.interval_lower > 1.0


def test_search_certifies_nehari_violation() -> None:
    result = find_counterexample([1.0], property="nehari_univalent")
    assert result.certified is True
    assert result.interval_lower is not None
    assert result.interval_lower > 2.0


def test_witness_hint_is_tried_before_the_grid() -> None:
    result = find_counterexample(
        [1.0], property="starlike", witness_hint=(-0.95, 0.0)
    )
    assert result.certified is True
    assert result.point == pytest.approx((-0.95, 0.0), abs=1e-9)


def test_invalid_property_is_rejected() -> None:
    with pytest.raises(ValueError, match="property"):
        find_counterexample([1.0], property="not_real")  # type: ignore[arg-type]


def test_non_finite_coefficients_are_rejected() -> None:
    with pytest.raises(ValueError, match="finite"):
        find_counterexample([float("inf")])


def test_point_must_lie_inside_the_unit_disk() -> None:
    result = find_counterexample([1.0], property="starlike")
    assert result.point is not None
    real, imaginary = result.point
    assert real**2 + imaginary**2 < 1.0


def test_certified_record_is_closed() -> None:
    record = find_counterexample([1.0], property="starlike").to_dict()
    assert record["record_type"] == "witness_search"
    assert record["evidence_kind"] == "certified_enclosure"
    assert record["tier"] == "rigorous"
    assert record["novelty_claim"] is False
    validate_screen_record(record)


def test_uncertified_record_is_labeled_screen() -> None:
    record = find_counterexample([0.25], property="starlike").to_dict()
    assert record["evidence_kind"] == "numerical_screen"
    validate_screen_record(record)

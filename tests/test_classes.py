"""Ma–Minda class admissibility, membership, containment screens, and extremal coefficients."""

from __future__ import annotations

import pytest
import sympy as sp

from geometric_function_atlas.classes import (
    class_admissibility,
    class_containment_screen,
    class_extremal_coefficients,
    class_member_screen,
    list_classes,
)
from geometric_function_atlas.records import validate_screen_record


def test_list_classes_covers_the_catalog() -> None:
    keys = {item.key for item in list_classes()}
    assert len(keys) == 39
    assert {"starlike", "exponential", "sine", "petal_arcsinh"} <= keys


def test_exponential_class_is_admissible() -> None:
    result = class_admissibility("exponential")
    assert result.admissible is True
    names = {check.name for check in result.verification_report.checks}
    assert {"phi0_equals_1", "phi_prime0_positive", "re_phi_positive"} <= names
    assert result.exact_values["phi_prime0"] == "1"


def test_starlike_class_is_admissible() -> None:
    assert class_admissibility("starlike").admissible is True


def test_unknown_class_key_fails() -> None:
    with pytest.raises(KeyError, match="unknown generator"):
        class_admissibility("missing")


def test_admissibility_record_is_closed_and_labeled_screen() -> None:
    record = class_admissibility("sine").to_dict()
    assert record["record_type"] == "class_admissibility"
    assert record["evidence_kind"] == "numerical_screen"
    assert record["tier"] == "screen"
    validate_screen_record(record)


def test_extremal_of_j1_over_1_minus_z_is_z_over_one_minus_z() -> None:
    # phi = 1/(1-z): f_phi(z) = z exp(sum z^k/k) = z/(1-z) = z + z^2 + z^3 + ...
    coefficients = class_extremal_coefficients("janowski_A0_B-1", order=4)
    assert tuple(sp.sstr(value) for value in coefficients) == ("1", "1", "1", "1")


def test_extremal_of_exponential_matches_manual_recurrence() -> None:
    # phi = e^z: B_k = 1/k! -> a2 = 1, a3 = 3/4, a4 = 17/36
    coefficients = class_extremal_coefficients("exponential", order=3)
    assert tuple(sp.sstr(value) for value in coefficients) == ("1", "3/4", "17/36")


def test_extremal_of_sine_matches_manual_recurrence() -> None:
    # B: 1, 0, -1/6, 0  ->  a2 = 1, a3 = 1/2, a4 = 1/9
    coefficients = class_extremal_coefficients("sine", order=3)
    assert tuple(sp.sstr(value) for value in coefficients) == ("1", "1/2", "1/9")


def test_extremal_coefficients_are_exact() -> None:
    coefficients = class_extremal_coefficients("exponential", order=3)
    assert all(isinstance(value, sp.Rational) for value in coefficients)


def test_member_screen_accepts_the_class_extremal() -> None:
    extremal = class_extremal_coefficients("sine", order=8)
    result = class_member_screen("sine", [float(value) for value in extremal])
    assert result.member is True
    assert result.fraction_inside == 1.0


def test_member_screen_rejects_a_non_member() -> None:
    result = class_member_screen("exponential", [4.0])
    assert result.member is False
    assert result.fraction_inside < 1.0
    assert result.witness_w is not None


def test_member_screen_record_is_closed() -> None:
    record = class_member_screen("sine", [0.25]).to_dict()
    assert record["record_type"] == "class_membership"
    validate_screen_record(record)


def test_containment_screen_exponential_inside_starlike() -> None:
    result = class_containment_screen("exponential", "starlike")
    assert result.contained is True
    assert result.fraction_inside == 1.0


def test_containment_screen_starlike_not_inside_exponential() -> None:
    result = class_containment_screen("starlike", "exponential")
    assert result.contained is False
    assert result.witness_w is not None


def test_containment_screen_symmetric_for_identical_classes() -> None:
    result = class_containment_screen("sine", "sine")
    assert result.contained is True


def test_containment_record_is_closed() -> None:
    record = class_containment_screen("exponential", "starlike").to_dict()
    assert record["record_type"] == "class_containment"
    validate_screen_record(record)


def test_failed_containment_record_is_closed_without_nan() -> None:
    # The non-contained margin must serialize as null, never NaN, so the
    # closed JSON record remains machine-readable.
    record = class_containment_screen("starlike", "exponential").to_dict()
    assert record["details"]["contained"] is False
    assert record["details"]["margin"] is None
    assert record["details"]["witness_w"] is not None
    validate_screen_record(record)

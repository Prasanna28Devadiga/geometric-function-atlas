"""Ma–Minda class admissibility, membership, containment screens, and extremal coefficients."""

from __future__ import annotations

import pytest
import sympy as sp

import geometric_function_atlas as gfa
from geometric_function_atlas.classes import (
    class_admissibility,
    class_containment_screen,
    class_extremal_coefficients,
    class_member_screen,
    list_classes,
)
from geometric_function_atlas.coefficients import taylor_coefficients
from geometric_function_atlas.records import validate_screen_record


def _order_quarter_generator() -> gfa.Generator:
    alpha = sp.Rational(1, 4)
    return gfa.Generator(
        key="order_quarter",
        name="Starlike of order 1/4",
        expression=(1 + (1 - 2 * alpha) * gfa.z) / (1 - gfa.z),
        citation="Caller-specified family: alpha = 1/4",
    )


def test_list_classes_covers_the_catalog() -> None:
    keys = {item.key for item in list_classes()}
    assert len(keys) == 39
    assert {"starlike", "exponential", "sine", "petal_arcsinh"} <= keys


def test_public_class_catalog_entries_expose_exact_catalog_fields() -> None:
    starlike = next(item for item in list_classes() if item.key == "starlike")

    assert starlike["formula"] == starlike.formula
    assert starlike["phi_formula"] == starlike.formula
    assert starlike["phi_coeffs"][:2] == ("2", "2")


def test_top_level_class_catalog_uses_the_computational_generator_objects() -> None:
    item = next(item for item in gfa.list_classes() if item.key == "sine")

    assert item.expression.free_symbols == {item.variable}
    assert gfa.list_artifact_classes()[0]["key"] == "bean_tanh"


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


def test_custom_generator_flows_through_class_operations_with_exact_identity() -> None:
    custom = _order_quarter_generator()

    admissibility = class_admissibility(custom)
    assert admissibility.class_key == "order_quarter"
    assert admissibility.admissible is True
    record = admissibility.to_dict()
    assert record["canonical_inputs"]["class_key"].startswith(
        "user:order_quarter:"
    )
    assert record["details"]["generator_key"] == "order_quarter"
    assert record["details"]["generator_formula"] == custom.formula
    assert record["details"]["generator_provenance"] == "caller_supplied"
    assert custom.citation in record["source_references"]
    validate_screen_record(record)

    extremal = class_extremal_coefficients(custom, order=3)
    assert tuple(map(sp.simplify, extremal)) == (
        sp.Rational(3, 2),
        sp.Rational(15, 8),
        sp.Rational(35, 16),
    )

    membership = class_member_screen(
        custom,
        [float(value) for value in extremal],
        max_r=0.5,
    )
    assert membership.class_key == "order_quarter"
    assert membership.to_dict()["canonical_inputs"]["class_key"] == record[
        "canonical_inputs"
    ]["class_key"]

    containment = class_containment_screen(custom, "starlike", r_inner=0.9)
    assert containment.inner == "order_quarter"
    containment_record = containment.to_dict()
    assert containment_record["canonical_inputs"]["inner"] == record[
        "canonical_inputs"
    ]["class_key"]
    assert containment_record["canonical_inputs"]["outer"] == "starlike"
    validate_screen_record(containment_record)


def test_catalog_class_records_keep_catalog_keys_and_no_caller_metadata() -> None:
    admissibility = class_admissibility("sine").to_dict()
    membership = class_member_screen("sine", [0.1], max_r=0.5).to_dict()
    containment = class_containment_screen("sine", "starlike").to_dict()

    assert admissibility["canonical_inputs"]["class_key"] == "sine"
    assert membership["canonical_inputs"]["class_key"] == "sine"
    assert containment["canonical_inputs"] == {
        "inner": "sine",
        "outer": "starlike",
    }
    assert "generator_formula" not in admissibility["details"]
    assert "generator_formula" not in membership["details"]
    assert "inner_generator" not in containment["details"]
    assert "outer_generator" not in containment["details"]


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


def test_extremal_coefficients_are_exact_and_float_free() -> None:
    for key in ("exponential", "sine", "limacon_0.707", "parabolic", "rational_kr"):
        for value in class_extremal_coefficients(key, order=4):
            assert isinstance(value, sp.Expr)
            assert not value.has(sp.Float)


# Exact [a2, a3, a4, a5] of the canonical member at order 4. Algebraic and
# transcendental coefficients are as exact as rational ones.
EXTREMAL_ORDER_4_ANCHORS = (
    (
        "limacon_0.707",
        (sp.sqrt(2), sp.Rational(5, 4), 7 * sp.sqrt(2) / 12, sp.Rational(43, 96)),
    ),
    (
        "parabolic",
        (
            8 / sp.pi**2,
            8 * (sp.pi**2 + 12) / (3 * sp.pi**4),
            8 * (1440 + 23 * sp.pi**4 + 360 * sp.pi**2) / (135 * sp.pi**6),
            8 * (20160 + 99 * sp.pi**6 + 10080 * sp.pi**2 + 1708 * sp.pi**4)
            / (945 * sp.pi**8),
        ),
    ),
    (
        "rational_kr",
        (
            sp.sqrt(2) - 1,
            sp.Rational(9, 2) - 3 * sp.sqrt(2),
            sp.Rational(-77, 6) + 55 * sp.sqrt(2) / 6,
            sp.Rational(901, 24) - 53 * sp.sqrt(2) / 2,
        ),
    ),
    (
        "exponential",
        (
            sp.Integer(1),
            sp.Rational(3, 4),
            sp.Rational(17, 36),
            sp.Rational(19, 72),
        ),
    ),
    (
        "sine",
        (
            sp.Integer(1),
            sp.Rational(1, 2),
            sp.Rational(1, 9),
            sp.Rational(-1, 72),
        ),
    ),
    ("janowski_A0_B-1", (sp.Integer(1),) * 4),
    (
        "starlike",
        (sp.Integer(2), sp.Integer(3), sp.Integer(4), sp.Integer(5)),
    ),
)


@pytest.mark.parametrize(("key", "expected"), EXTREMAL_ORDER_4_ANCHORS)
def test_extremal_order_4_matches_independent_manually_derived_values(
    key: str, expected: tuple[sp.Expr, ...]
) -> None:
    coefficients = class_extremal_coefficients(key, order=4)

    assert len(coefficients) == len(expected)
    assert [sp.simplify(value - target) for value, target in zip(coefficients, expected)] == [
        sp.Integer(0)
    ] * len(expected)
    assert all(not value.has(sp.Float) for value in coefficients)


def test_extremal_of_limacon_matches_the_closed_form_of_its_generator() -> None:
    # phi = (1 + s z)^2 with s = sqrt(2)/2 gives (phi - 1)/t = 2 s + s^2 t, so
    # f_phi(z)/z = exp(2 s z + s^2 z^2 / 2) = exp(sqrt(2) z + z^2 / 4), and a_{n+1}
    # is the coefficient of z^n in that exponential.
    z = sp.Symbol("z")
    s = sp.sqrt(2) / 2
    series = sp.series(sp.exp(2 * s * z + s**2 * z**2 / 2), z, 0, 5).removeO()
    expected = tuple(series.coeff(z, degree) for degree in range(1, 5))

    coefficients = class_extremal_coefficients("limacon_0.707", order=4)

    assert [sp.simplify(value - target) for value, target in zip(coefficients, expected)] == [
        sp.Integer(0)
    ] * 4


def test_all_39_catalog_generators_have_exact_order_4_extremal_coefficients() -> None:
    keys = [item.key for item in list_classes()]
    assert len(keys) == 39

    exact = 0
    for key in keys:
        coefficients = class_extremal_coefficients(key, order=4)
        assert len(coefficients) == 4, key
        for value in coefficients:
            assert isinstance(value, sp.Expr), key
            assert not value.has(sp.Float), key
        # a2 is the generator's first Taylor coefficient for the canonical member.
        assert sp.simplify(coefficients[0] - taylor_coefficients(key, order=1)[0]) == 0, key
        exact += 1

    assert exact == 39, f"{exact}/39 catalog generators produced exact order-4 coefficients"


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

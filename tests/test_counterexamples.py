from __future__ import annotations

from fractions import Fraction

import pytest


def test_certifies_starlike_counterexample_at_supplied_point() -> None:
    from geometric_function_atlas import verify_counterexample

    # f(z) = z + z^2. At z = -3/4,
    # Re(z f'(z) / f(z)) = -2 < 0.
    result = verify_counterexample(
        coefficients=[1],
        point=(-0.75, 0.0),
        property="starlike",
    )

    assert result.certified is True
    assert result.property == "starlike"
    assert result.direction == "disproves"
    assert result.threshold == 0.0
    assert result.interval_upper < result.threshold


def test_nonviolating_point_is_not_reported_as_counterexample() -> None:
    from geometric_function_atlas import verify_counterexample

    result = verify_counterexample(
        coefficients=[1],
        point=(0.5, 0.0),
        property="starlike",
    )

    assert result.certified is False
    assert result.direction == "not_disproved"
    assert result.interval_lower > result.threshold


@pytest.mark.parametrize(
    ("property_name", "threshold"),
    [
        ("becker_univalent", 1.0),
        ("nehari_univalent", 2.0),
    ],
)
def test_certifies_supported_univalence_criterion_violations(
    property_name: str, threshold: float
) -> None:
    from geometric_function_atlas import verify_counterexample

    # f(z) = z + z^2 has f'(-0.4) = 0.2, making both criteria fail
    # decisively at this point.
    result = verify_counterexample(
        coefficients=[1],
        point=(-0.4, 0.0),
        property=property_name,
    )

    assert result.certified is True
    assert result.direction == "violates_criterion"
    assert result.threshold == threshold
    assert result.interval_lower > threshold


def test_derivative_interval_contains_exact_binary_float_polynomial_value() -> None:
    from geometric_function_atlas import verify_counterexample

    coefficient = -92.89151267176787
    radius = -0.0590422138758101
    result = verify_counterexample(
        coefficients=[0.0, coefficient],
        point=(radius, 0.0),
        property="starlike",
    )

    a = Fraction.from_float(coefficient)
    r = Fraction.from_float(radius)
    exact = (1 + 3 * a * r**2) / (1 + a * r**2)
    assert Fraction.from_float(result.interval_lower) <= exact
    assert exact <= Fraction.from_float(result.interval_upper)


def test_starlike_boundary_value_certifies_failure_of_strict_positivity() -> None:
    from geometric_function_atlas import verify_counterexample

    result = verify_counterexample(
        coefficients=[1],
        point=(-0.5, 0.0),
        property="starlike",
    )

    assert result.interval_lower == 0.0
    assert result.interval_upper == 0.0
    assert result.certified is True
    assert result.direction == "disproves"


def test_counterexample_rejects_point_outside_unit_disk() -> None:
    from geometric_function_atlas import verify_counterexample

    with pytest.raises(ValueError, match="inside the open unit disk"):
        verify_counterexample(
            coefficients=[1],
            point=(1.0, 0.0),
            property="starlike",
        )


@pytest.mark.parametrize("coefficients", ["1", b"1", {"2": 0}, {1.0}])
def test_counterexample_rejects_non_sequence_coefficient_containers(
    coefficients: object,
) -> None:
    from geometric_function_atlas import verify_counterexample

    with pytest.raises(TypeError, match="sequence of real numbers"):
        verify_counterexample(
            coefficients=coefficients,  # type: ignore[arg-type]
            point=(0.25, 0.0),
            property="starlike",
        )


def test_starlike_origin_uses_the_removable_limit() -> None:
    from geometric_function_atlas import verify_counterexample

    result = verify_counterexample(
        coefficients=[2, -3],
        point=(0.0, 0.0),
        property="starlike",
    )

    assert result.interval_lower == 1.0
    assert result.interval_upper == 1.0
    assert result.certified is False
    assert result.direction == "not_disproved"


@pytest.mark.parametrize(
    ("property_name", "coefficients", "point"),
    [
        ("starlike", [2], (-0.5, 0.0)),
        ("becker_univalent", [1], (-0.5, 0.0)),
        ("nehari_univalent", [1], (-0.5, 0.0)),
    ],
)
def test_true_denominator_singularities_are_unresolved(
    property_name: str,
    coefficients: list[float],
    point: tuple[float, float],
) -> None:
    from geometric_function_atlas import UnresolvedError, verify_counterexample

    with pytest.raises(UnresolvedError, match="denominator|singular"):
        verify_counterexample(
            coefficients=coefficients,
            point=point,
            property=property_name,
        )


def test_complex_witness_with_nonzero_cubic_is_finite() -> None:
    from geometric_function_atlas import verify_counterexample

    result = verify_counterexample(
        coefficients=[0.25, -0.125],
        point=(0.2, 0.3),
        property="nehari_univalent",
    )

    assert result.interval_lower >= 0.0
    assert result.interval_lower <= result.interval_upper
    assert result.interval_upper < float("inf")

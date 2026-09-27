"""Tiered function verification: numerical screen, symbolic proof, rigorous enclosure."""

from __future__ import annotations

from copy import deepcopy

import jsonschema
import pytest
import sympy as sp

from geometric_function_atlas.contracts import (
    InvalidInputError,
    ResourceLimitError,
)
from geometric_function_atlas.records import (
    load_verify_result_schema,
    validate_screen_record,
)
from geometric_function_atlas.verify import (
    TIERS,
    verify_function,
)


def test_screen_tier_detects_non_starlike_polynomial() -> None:
    result = verify_function(coefficients=[1.0], property="starlike", max_cost="screen")
    assert result.tier == "screen"
    assert result.evidence_kind == "numerical_screen"
    assert result.outcome == "fails_screen"
    assert result.min_margin < 0
    # The screen executed consistently; the verdict lives in `outcome`.
    assert result.verification_report.success


def test_screen_tier_passes_for_c01_safe_polynomial() -> None:
    result = verify_function(coefficients=[0.25], property="starlike", max_cost="screen")
    assert result.outcome == "passes_screen"
    assert result.min_margin > 0
    assert result.verification_report.success


def test_symbolic_tier_proves_starlike_for_polynomial() -> None:
    result = verify_function(coefficients=[0.25], property="starlike", max_cost="symbolic")
    assert result.tier == "symbolic"
    assert result.evidence_kind == "exact_proof"
    assert result.outcome == "proven"
    names = {check.name for check in result.verification_report.checks}
    assert {"c01_exact_sum", "alexander_convexity_sum"} <= names


def test_symbolic_tier_proves_convex_and_univalent_by_implication() -> None:
    result = verify_function(coefficients=[0.25], property="convex", max_cost="symbolic")
    assert result.outcome == "proven"
    assert result.details["convex_sum"] == "1"


def test_symbolic_tier_convex_uses_alexander_sum() -> None:
    # z + 0.3z^2: C01 sum 0.6 <= 1 but sum(n^2|a_n|) = 1.2 > 1, and
    # 1 + z f''/f' < 0 for real z < -1/1.2, so it is not convex.
    result = verify_function(coefficients=[0.3], property="convex", max_cost="symbolic")
    assert result.outcome == "convex_fails_sufficient_condition"
    assert result.evidence_kind == "inconclusive"
    checks = {check.name: check for check in result.verification_report.checks}
    assert checks["alexander_convexity_sum"].status.value == "fail"
    proven = verify_function(coefficients=[0.2], property="convex", max_cost="symbolic")
    assert proven.outcome == "proven"
    assert proven.evidence_kind == "exact_proof"


def test_rigorous_tier_certified_violation_beats_c01_for_convex() -> None:
    result = verify_function(coefficients=[0.3], property="convex", max_cost="rigorous")
    assert result.outcome == "certified_violation"
    assert result.certified
    assert verify_function(
        coefficients=[0.2], property="convex", max_cost="rigorous"
    ).outcome == "proven"


@pytest.mark.parametrize("property_name", ["starlike", "convex", "becker_univalent", "nehari_univalent"])
def test_rigorous_truncation_never_certifies_the_unknown_tail(property_name: str) -> None:
    result = verify_function(coefficients=[0.3], property=property_name,
                             max_cost="rigorous", truncation=True)
    assert result.outcome not in {"proven", "certified_violation"}
    assert not result.certified
    assert result.evidence_kind != "certified_enclosure"
    assert result.details["polynomial"] is False
    assert not result.verification_report.success


def test_closed_form_exact_coefficient_controls_boundary_proof() -> None:
    z = sp.Symbol("z")
    coefficient = sp.Rational(1, 4) + sp.Rational(1, 10**20)
    result = verify_function(closed_form=z + coefficient * z**2,
                             property="convex", max_cost="symbolic")
    assert result.outcome != "proven"
    assert result.exact_coefficients == (sp.sstr(coefficient),)
    assert result.details["convex_sum"] == sp.sstr(4 * coefficient)
    assert not result.verification_report.success


def test_closed_form_rounded_interval_cannot_certify_original() -> None:
    z = sp.Symbol("z")
    result = verify_function(closed_form=z + (sp.Rational(3, 10) + sp.Rational(1, 10**20)) * z**2,
                             property="convex", max_cost="rigorous")
    assert not result.certified
    assert result.outcome != "certified_violation"


def test_declared_truncation_on_closed_form_never_proves_full_function() -> None:
    z = sp.Symbol("z")
    result = verify_function(closed_form=z + z**2 / 8, property="convex",
                             max_cost="rigorous", truncation=True)
    assert result.outcome != "proven"
    assert not result.certified


def test_convex_report_requires_alexander_not_c01() -> None:
    result = verify_function([0.3], property="convex", max_cost="symbolic")
    checks = {check.name: check for check in result.verification_report.checks}
    assert checks["alexander_convexity_sum"].required
    assert not checks["c01_exact_sum"].required
    assert not result.verification_report.success
    assert "convex" in result.outcome


@pytest.mark.parametrize("property_name", ["becker_univalent", "nehari_univalent"])
def test_criterion_violation_does_not_disprove_univalence(property_name: str) -> None:
    result = verify_function([1.0], property=property_name, max_cost="rigorous")
    assert result.outcome == "certified_violation"
    assert result.details["violation_scope"] == "sufficient criterion only; not univalence"
    assert result.verification_report.success


def test_nonpolynomial_closed_form_interval_cannot_certify_truncation() -> None:
    z = sp.Symbol("z")
    result = verify_function(closed_form=z / (1 + 2*z), property="starlike",
                             max_cost="rigorous")
    assert result.outcome == "no_certified_violation_on_grid"
    assert not result.certified
    assert not result.verification_report.success
    checks = {check.name: check for check in result.verification_report.checks}
    assert checks["interval_certification"].status.value == "skip"


def test_becker_symbolic_proof_states_it_comes_from_c01() -> None:
    result = verify_function(
        coefficients=[0.25], property="becker_univalent", max_cost="symbolic"
    )
    assert result.outcome == "proven"
    assert "C01" in result.details["proven_via"]


def test_symbolic_tier_record_serializes_without_nan() -> None:
    # The symbolic tier has no grid margin; its record must serialize as a
    # closed JSON payload with min_margin null (NaN breaks the JSON contract).
    result = verify_function(coefficients=[0.25], property="starlike", max_cost="symbolic")
    assert result.min_margin is None
    record = result.to_dict()
    assert record["details"]["min_margin"] is None
    validate_screen_record(record)


def test_symbolic_tier_is_inconclusive_for_undecided_truncation() -> None:
    # A truncation with a partial sum below 1 proves nothing about the tail.
    result = verify_function(
        coefficients=[0.25], property="starlike", max_cost="symbolic", truncation=True
    )
    assert result.outcome == "inconclusive_truncation"
    assert result.evidence_kind == "inconclusive"


def test_symbolic_tier_reports_c01_failure_as_not_a_proof() -> None:
    result = verify_function(coefficients=[1.0], property="starlike", max_cost="symbolic")
    assert result.outcome == "c01_fails_sufficient_condition"
    assert result.evidence_kind == "inconclusive"


def test_symbolic_tier_rejects_non_finite_coefficients() -> None:
    with pytest.raises(ValueError, match="finite"):
        verify_function(coefficients=[float("nan")], max_cost="symbolic")


def test_rigorous_tier_certifies_violation_for_non_starlike_polynomial() -> None:
    result = verify_function(coefficients=[1.0], property="starlike", max_cost="rigorous")
    assert result.tier == "rigorous"
    assert result.evidence_kind == "certified_enclosure"
    assert result.outcome == "certified_violation"
    assert result.witness_point is not None
    assert result.certified


def test_rigorous_tier_proves_starlike_for_safe_polynomial() -> None:
    result = verify_function(coefficients=[0.25], property="starlike", max_cost="rigorous")
    assert result.outcome == "proven"
    assert result.evidence_kind == "exact_proof"


def test_rigorous_tier_certifies_becker_criterion_violation() -> None:
    result = verify_function(
        coefficients=[1.0], property="becker_univalent", max_cost="rigorous"
    )
    assert result.outcome == "certified_violation"
    assert result.certified


def test_closed_form_polynomial_is_proven() -> None:
    zz = sp.symbols("z")
    closed_form = sp.expand(zz + zz**2 / 4)
    result = verify_function(closed_form=closed_form, max_cost="symbolic")
    assert result.outcome == "proven"
    assert result.evidence_kind == "exact_proof"


@pytest.mark.parametrize("tier", TIERS)
def test_closed_form_distinct_tail_has_distinct_canonical_identity(tier: str) -> None:
    z = sp.Symbol("z")
    base = verify_function(closed_form=z / (1 - z), max_cost=tier,
                           grid_r=2, grid_theta=4).to_dict()
    tail = verify_function(closed_form=z / (1 - z) + z**41, max_cost=tier,
                           grid_r=2, grid_theta=4).to_dict()
    assert base["canonical_inputs"]["coefficients"] == tail["canonical_inputs"]["coefficients"]
    assert base["canonical_inputs"]["closed_form_srepr"] == sp.srepr(z / (1 - z))
    assert tail["canonical_inputs"]["closed_form_srepr"] == sp.srepr(z / (1 - z) + z**41)
    assert base["canonical_inputs"] != tail["canonical_inputs"]
    assert base != tail
    for record in (base, tail):
        jsonschema.validate(record, load_verify_result_schema())
        validate_screen_record(record)


def test_closed_form_rational_is_not_silently_a_proof() -> None:
    zz = sp.symbols("z")
    result = verify_function(closed_form=zz / (1 - zz), max_cost="symbolic")
    assert result.outcome == "c01_fails_sufficient_condition"


def test_closed_form_rejects_unnormalized_function() -> None:
    zz = sp.symbols("z")
    with pytest.raises(InvalidInputError, match="normalized"):
        verify_function(closed_form=1 + zz, max_cost="symbolic")


def test_invalid_tier_is_rejected() -> None:
    with pytest.raises(InvalidInputError, match="max_cost"):
        verify_function(coefficients=[0.25], max_cost="exact")  # type: ignore[arg-type]


def test_invalid_property_is_rejected() -> None:
    with pytest.raises(InvalidInputError, match="property"):
        verify_function(coefficients=[0.25], property="not_a_property", max_cost="screen")


def test_to_dict_produces_a_valid_closed_record() -> None:
    result = verify_function(coefficients=[1.0], max_cost="rigorous")
    record = result.to_dict()
    assert record["record_type"] == "function_verification"
    assert record["tier"] == "rigorous"
    assert record["novelty_claim"] is False
    validate_screen_record(record)


def test_coefficient_length_is_bounded() -> None:
    with pytest.raises(ResourceLimitError):
        verify_function(coefficients=[0.01] * 300, max_cost="screen")


def test_tiers_are_exactly_the_documented_set() -> None:
    assert TIERS == ("screen", "symbolic", "rigorous")


@pytest.mark.parametrize("rmax", [10, 1, 0, -0.2, float("nan"), float("inf"), True, "0.5"])
@pytest.mark.parametrize("tier", ["screen", "rigorous", "symbolic"])
def test_invalid_grid_radius_is_rejected_even_for_symbolic(tier: str, rmax: object) -> None:
    with pytest.raises((TypeError, ValueError), match="rmax"):
        verify_function([0.2], property="nehari_univalent", max_cost=tier, rmax=rmax)


@pytest.mark.parametrize("grid_r,grid_theta", [(0, 4), (2, 0), (True, 4), (2, 1.5), (2, 1000001)])
def test_invalid_grid_resolution_fails_closed(grid_r: object, grid_theta: object) -> None:
    with pytest.raises((TypeError, ValueError), match="grid_"):
        verify_function([0.2], grid_r=grid_r, grid_theta=grid_theta)


def test_all_screened_witnesses_stay_inside_unit_disk() -> None:
    for tier in ("screen", "rigorous"):
        result = verify_function([0.2], property="nehari_univalent", max_cost=tier,
                                 rmax=0.999999, grid_r=2, grid_theta=4)
        assert result.witness_point is not None
        assert sum(x*x for x in result.witness_point) < 1


def test_truncation_changes_canonical_inputs() -> None:
    whole = verify_function([0.2], max_cost="symbolic").to_dict()
    partial = verify_function([0.2], max_cost="symbolic", truncation=True).to_dict()
    assert whole["canonical_inputs"]["truncation"] is False
    assert partial["canonical_inputs"]["truncation"] is True
    assert whole["canonical_inputs"] != partial["canonical_inputs"]


def test_coefficient_input_has_explicit_null_closed_form_identity() -> None:
    record = verify_function([0.2], max_cost="symbolic").to_dict()
    assert record["canonical_inputs"]["closed_form_srepr"] is None
    jsonschema.validate(record, load_verify_result_schema())
    validate_screen_record(record)


def test_closed_form_identity_is_bounded_before_series_expansion() -> None:
    z = sp.Symbol("z")
    huge_symbol = sp.Symbol("x" * 65536)
    with pytest.raises(ResourceLimitError, match="representation exceeds limit"):
        verify_function(closed_form=z + huge_symbol, max_cost="symbolic")


def test_shared_dag_is_rejected_before_srepr_expansion(monkeypatch: pytest.MonkeyPatch) -> None:
    z = sp.Symbol("z")
    expression = z
    expanded_length = len(sp.srepr(z))
    for _ in range(17):
        expression = sp.Add(expression, expression, evaluate=False)
        expanded_length = len("Add(, )") + 2 * expanded_length
    assert expanded_length > 65536

    def forbidden_srepr(*args: object, **kwargs: object) -> str:
        raise AssertionError("srepr must not expand the shared DAG")

    monkeypatch.setattr(sp, "srepr", forbidden_srepr)
    with pytest.raises(ResourceLimitError, match="representation exceeds limit"):
        verify_function(closed_form=expression, max_cost="symbolic")


def test_shipped_verification_schema_accepts_all_tiers_and_cli_shape() -> None:
    schema = load_verify_result_schema()
    jsonschema.Draft202012Validator.check_schema(schema)
    for tier in TIERS:
        for truncation in (False, True):
            for property_name in ("starlike", "convex", "becker_univalent", "nehari_univalent"):
                for coefficient in (0.2, 1.0):
                    record = verify_function([coefficient], property=property_name, max_cost=tier,
                                             truncation=truncation).to_dict()
                    jsonschema.validate(record, schema)
                    validate_screen_record(record)
    jsonschema.validate(verify_function([0.2], property="univalent", max_cost="symbolic").to_dict(), schema)


@pytest.mark.parametrize("mutate", [
    lambda r: r.update(extra=1),
    lambda r: r["canonical_inputs"].update(extra=True),
    lambda r: r["canonical_inputs"].update(truncation="false"),
    lambda r: r["canonical_inputs"].pop("truncation"),
    lambda r: r["canonical_inputs"].pop("closed_form_srepr"),
    lambda r: r["canonical_inputs"].update(closed_form_srepr=""),
    lambda r: r["canonical_inputs"].update(closed_form_srepr="x" * 65537),
    lambda r: r["details"].update(outcome="invented"),
    lambda r: r["details"].update(certified="true"),
    lambda r: r["details"].update(witness_point=[10, 0]),
    lambda r: r["details"].update(unknown_detail=1),
    lambda r: r.update(evidence_kind="certified_enclosure"),
    lambda r: r["canonical_inputs"].update(tier="symbolic"),
])
def test_verification_contract_rejects_adversarial_payloads(mutate) -> None:
    record = deepcopy(verify_function([0.2], max_cost="rigorous").to_dict())
    mutate(record)
    with pytest.raises((jsonschema.ValidationError, ValueError, TypeError)):
        jsonschema.validate(record, load_verify_result_schema())


@pytest.mark.parametrize("field", ["witness_point", "worst_point"])
def test_schema_is_only_a_coordinate_bound_not_a_disk_proof(field: str) -> None:
    record = deepcopy(verify_function([0.2], max_cost="screen").to_dict())
    record["details"][field] = [0.9, 0.9]
    # Draft 2020-12 validates each coordinate, not x² + y² < 1.
    jsonschema.validate(record, load_verify_result_schema())
    with pytest.raises(ValueError, match="open unit disk"):
        validate_screen_record(record)

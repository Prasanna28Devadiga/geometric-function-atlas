"""Regression anchors for the versioned coefficient supplement."""
import copy
import json
from importlib.resources import files

import pytest
import sympy as sp
from jsonschema import Draft202012Validator

from geometric_function_atlas import artifacts
from geometric_function_atlas.cli import main


def test_booth_fekete_certificates_are_replayable():
    for key in ("booth_0.3", "booth_0.7"):
        for mu in ("0", "0.25", "0.5", "0.75", "1", "2"):
            name = f"{key}__fekete_szego_mu{mu}"
            result = artifacts.verify_certificate(name)
            assert result["sharpness_proven"] is True
            assert result["functional_value_exact"] == result["candidate_exact"]


def test_hankel_table_distinguishes_attainment_and_sharpness():
    rows = artifacts.coefficient_table("hankel3_1")
    assert len(rows["rows"]) == 38
    assert rows["rows"]["starlike"]["value_exact"] == "4/9"
    assert rows["rows"]["starlike"]["status"] == "literature_sharp"
    assert rows["rows"]["sine"]["status"] == "attained_lower_bound"
    assert rows["rows"]["sine"]["value_exact"] == "1/9"
    assert rows["rows"]["booth_0.3"]["value_exact"] == "1/9"
    assert "janowski_A0_B-1" not in rows["rows"]


def test_coefficient_maxima_include_interior_extremal():
    result = artifacts.coefficient_table("a2a3")["rows"]["lemniscate"]
    x = sp.sympify(result["extremal_r_squared"])
    assert 0 < x < 1
    b1, b2 = sp.Rational(1, 2), sp.Rational(-1, 8)
    value = b1 * sp.sqrt(x) * (b1 + (sp.Abs(b2+b1*b1)-b1)*x)/2
    assert sp.simplify(value - sp.sympify(result["value_exact"])) == 0
    assert result["status"] == "analytic_sharp"


def test_coefficient_maxima_cover_distinct_catalog():
    for functional in ("a3", "a2a3"):
        rows = artifacts.coefficient_table(functional)["rows"]
        assert len(rows) == 38
        assert rows["starlike"]["status"] == "analytic_sharp"
        assert rows["starlike"]["value_exact"] == ("3" if functional == "a3" else "6")


def test_cli_coefficient_table_is_versioned(capsys):
    assert main(["coefficient-table", "hankel3_1", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["result_type"] == "coefficient_table"
    assert payload["record"]["rows"]["sine"]["status"] == "attained_lower_bound"
    assert payload["artifact_versions"]["coefficient_supplement"] == "gfa_coefficients:2026.09.27-coefficients-v1"
    assert payload["evidence_status"] == "mixed_row_level_claims"
    assert payload["computational_status"] == "mixed_row_level_claims"
    rows = payload["record"]["rows"]
    assert rows["sine"]["optimization_status"] == "global_upper_bound_not_established_here"
    assert rows["sine"]["citation"] is None
    assert rows["starlike"]["status"] == "literature_sharp"
    assert rows["starlike"]["citation"]["locator"] == "10.1515/forum-2021-0308"
    schema = json.loads(files("geometric_function_atlas").joinpath("schema/result.schema.json").read_text())
    Draft202012Validator(schema).validate(payload)


@pytest.mark.parametrize("row,field,value", [
    ("starlike", "citation", None),
    ("starlike", "citation", {}),
    ("starlike", "citation", {"theorem": "claim", "locator": ""}),
    ("starlike", "citation", {"theorem": "claim"}),
    ("starlike", "optimization_status", "global_upper_bound_not_established_here"),
    ("sine", "status", "literature_sharp"),
    ("sine", "citation", {"theorem": "claim", "locator": "doi"}),
    ("sine", "optimization_status", "published_direct_class_upper_bound; not_reproved_by_package"),
    ("sine", "status", "analytic_sharp"),
    ("sine", "value_exact", None),
])
def test_h3_claim_schema_rejects_row_mutations(capsys, row, field, value):
    assert main(["coefficient-table", "hankel3_1", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    validator = Draft202012Validator(json.loads(files("geometric_function_atlas").joinpath("schema/result.schema.json").read_text()))
    assert validator.is_valid(payload)
    mutated = copy.deepcopy(payload)
    mutated["record"]["rows"][row][field] = value
    assert not validator.is_valid(mutated), (row, field, value)
    del mutated["record"]["rows"][row][field]
    assert not validator.is_valid(mutated), (row, field, "missing")


@pytest.mark.parametrize("functional", ["a3", "a2a3"])
def test_other_coefficient_tables_remain_valid(capsys, functional):
    assert main(["coefficient-table", functional, "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    schema = json.loads(files("geometric_function_atlas").joinpath("schema/result.schema.json").read_text())
    Draft202012Validator(schema).validate(payload)


def test_cli_supplement_proof_and_replay_provenance(capsys):
    name = "booth_0.3__fekete_szego_mu0.25"
    for command in ("proof", "verify-certificate"):
        assert main([command, name, "--json"]) == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["artifact_versions"]["coefficient_supplement"] == "gfa_coefficients:2026.09.27-coefficients-v1"
        assert "Ma–Minda" in payload["assumptions"][0]
        if command == "proof":
            assert payload["record"]["method_label"] == "closed-form-single-harmonic"
            assert "unknown" not in payload["record"]["method_label"]
        else:
            assert payload["record"]["matched"] is True
            assert payload["evidence_status"] == "proven_exact_under_declared_assumptions"
    assert main(["proof", "starlike__fekete_szego_mu1", "--json"]) == 0
    legacy = json.loads(capsys.readouterr().out)
    assert "coefficient_supplement" not in legacy["artifact_versions"]


@pytest.mark.parametrize("filters,origins,count", [
    (["--class", "booth_0.3"], {"website_snapshot", "coefficient_supplement"}, 8),
    (["--class", "booth_0.3", "--functional", "fekete_szego_mu0.25"], {"coefficient_supplement"}, 1),
    (["--class", "booth_0.3", "--functional", "inv_a3"], {"website_snapshot"}, 1),
    (["--class", "booth_0.3", "--search", "not-present"], set(), 0),
])
def test_filtered_proof_gallery_identifies_each_source(capsys, filters, origins, count):
    assert main(["proofs", *filters, "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    schema = json.loads(files("geometric_function_atlas").joinpath("schema/result.schema.json").read_text())
    Draft202012Validator(schema).validate(payload)
    rows = payload["record"]["rows"]
    assert payload["record"]["count"] == count == len(rows)
    assert {row["artifact_source"] for row in rows} == origins
    assert payload["canonical_inputs"]["class_key"] == "booth_0.3"
    assert ("coefficient_supplement" in payload["artifact_versions"]) == ("coefficient_supplement" in origins)
    if "coefficient_supplement" in origins:
        version = payload["artifact_versions"]["coefficient_supplement"]
        assert all(row["artifact_version"] == version for row in rows if row["artifact_source"] == "coefficient_supplement")
        assert any("supplement" in reference.lower() for reference in payload["source_references"])
    if "website_snapshot" in origins:
        version = payload["artifact_versions"]["fixture_or_proof"]
        assert all(row["artifact_version"] == version for row in rows if row["artifact_source"] == "website_snapshot")
    if origins == {"coefficient_supplement"}:
        assert not any("transcribed" in assumption for assumption in payload["assumptions"])
    if len(origins) == 2:
        assert any("supplement" in assumption.lower() for assumption in payload["assumptions"])


def test_gallery_schema_rejects_missing_row_origin(capsys):
    assert main(["proofs", "--class", "booth_0.3", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    schema = json.loads(files("geometric_function_atlas").joinpath("schema/result.schema.json").read_text())
    del payload["record"]["rows"][0]["artifact_version"]
    assert not Draft202012Validator(schema).is_valid(payload)

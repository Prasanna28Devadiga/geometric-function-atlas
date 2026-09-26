"""Regression anchors for the versioned coefficient supplement."""
import json

import sympy as sp

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
    assert payload["artifact_versions"]["fixture_or_proof"]

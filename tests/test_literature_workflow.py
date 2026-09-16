"""Reproduce a literal source claim without trusting its printed expansion."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
import sympy as sp

from geometric_function_atlas.models import Z
from geometric_function_atlas.schur import member_coefficients

EXAMPLE = Path(__file__).resolve().parents[1] / "examples/research_workflows/literature_coefficient_audit.py"


def test_canonical_member_falsifies_literal_preprint_bound(tmp_path: Path) -> None:
    assert EXAMPLE.is_file(), "source-bound research example is missing"
    run = subprocess.run(
        [sys.executable, str(EXAMPLE), "--output", str(tmp_path)],
        capture_output=True, text=True, check=False,
    )
    assert run.returncode == 0, run.stderr
    data = json.loads((tmp_path / "literature_coefficient_audit.json").read_text())
    assert data["member_coefficients_a2_a5"] == ["1", "3/4", "7/12", "5/12"]
    assert data["excess_over_claim"] == "1/12"
    assert data["claim_outcome"] == "FALSIFIED"
    assert data["functional_equation_residual_through_degree4"] == "0"
    assert data["replacement_sharp_bound"] == "5/12"
    assert data["upper_bound_monotonicity_residual"] == "0"
    assert data["source_version"] == "arxiv:2412.04819v1"
    assert "not a proof" in (tmp_path / "literature_coefficient_audit.svg").read_text()


@pytest.mark.parametrize("dilation,a5,outcome", [
    ("3/4", "135/1024", "NO_VIOLATION_FROM_SELECTED_MEMBER"),
    ("0", "0", "NO_VIOLATION_FROM_SELECTED_MEMBER"),
    ("31/32", "4617605/12582912", "FALSIFIED"),
])
def test_audit_changed_dilations(tmp_path: Path, dilation: str, a5: str, outcome: str) -> None:
    run = subprocess.run(
        [sys.executable, str(EXAMPLE), "--dilation", dilation, "--output", str(tmp_path)],
        capture_output=True, text=True, check=False,
    )
    assert run.returncode == 0, run.stderr
    data = json.loads((tmp_path / "literature_coefficient_audit.json").read_text())
    assert data["member_coefficients_a2_a5"][3] == a5
    assert data["claim_outcome"] == outcome
    assert data["truncation_is_not_class_certificate"] is True
    assert len(data["plot_rows"]) == 65
    for row in data["plot_rows"]:
        assert sp.Rational(row["a5"]) == sp.Rational(5,12)*sp.Rational(row["dilation"])**4


@pytest.mark.parametrize("value", ["-1", "2", "1/0", "0.5", "1e-1"])
def test_audit_rejects_inputs_outside_declared_grammar(tmp_path: Path, value: str) -> None:
    run = subprocess.run(
        [sys.executable, str(EXAMPLE), "--dilation", value, "--output", str(tmp_path)],
        capture_output=True, text=True, check=False,
    )
    assert run.returncode == 2
    assert not (tmp_path / "literature_coefficient_audit.json").exists()


@pytest.mark.parametrize("n", [1,2,3,4,5])
@pytest.mark.parametrize("scale", [sp.Integer(1), sp.Rational(1,2)])
def test_exponential_extremal_finite_anchors_not_all_order_proof(n: int, scale: sp.Rational) -> None:
    b = [scale**k/sp.factorial(k) for k in range(1,n+1)]
    a = member_coefficients(b, [0]*(n-1)+[1], order=n)
    f_over_z = 1 + sum(value*Z**(k+1) for k,value in enumerate(a))
    logarithm = sp.series(sp.log(f_over_z), Z, 0, n+1).removeO().expand()
    assert logarithm.coeff(Z,n)/2 == scale/(2*n)

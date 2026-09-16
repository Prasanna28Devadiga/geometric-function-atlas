"""Test a starlikeness conjecture, construct a witness, and repair the claim."""

from __future__ import annotations

import argparse
import json
from fractions import Fraction
from pathlib import Path

import sympy as sp
from _curves import write_panels
from class_geometry import sample_curve

from geometric_function_atlas import verify_counterexample
from geometric_function_atlas.version import __version__


def solve(a: Fraction) -> dict:
    if a < 0 or a > 10:
        raise ValueError("this worked example accepts 0 <= a <= 10")
    starlike = a <= Fraction(1, 2)
    witness = None
    replay = {"status": "not_needed"}
    radius = 0.9
    if not starlike:
        t = min((a + Fraction(1, 2)) / 2, Fraction(3, 4))
        point = -t / a
        value = (1 - 2 * t) / (1 - t)
        if not -1 < point < 0 or value >= 0:
            raise ArithmeticError("the constructed witness does not violate starlikeness inside D")
        witness = {"point_exact": str(point), "value_exact": str(value), "logarithmic_derivative_is_negative": True}
        radius = float(abs(point))
        if Fraction.from_float(float(a)) == a and Fraction.from_float(float(point)) == point:
            result = verify_counterexample((float(a),), point=(float(point), 0.0), property="starlike")
            if not result.certified:
                raise ArithmeticError("public witness replay failed for exact binary-representable inputs")
            replay = {"status": "replayed", "certified": result.certified, "interval": [result.interval_lower, result.interval_upper], "same_exact_inputs": True}
        else:
            replay = {"status": "not_run", "reason": "public witness API takes binary floats; exact rational witness retained without silently changing the object"}
    af = float(a)
    f = lambda z: z + af * z**2
    q = lambda z: (1 + 2 * af * z) / (1 + af * z)
    panels = [
        {"title": "Polynomial image f_a(D_r)", "curves": [{"label": "f_a on the sampled circle", "points": sample_curve(f, radius)}], "notes": [f"a={a}; sampled radius r={radius:.6g}", "A picture alone does not prove univalence."]},
        {"title": "Logarithmic derivative z f'/f", "curves": [{"label": "logarithmic derivative on the same circle", "points": sample_curve(q, radius)}], "notes": ["Starlikeness requires positive real part.", f"Exact interior violation: {witness['value_exact']}" if witness else "The full-disk proof is in the workflow notes."]},
    ]
    if witness:
        value = float(Fraction(witness["value_exact"]))
        panels[1]["curves"].append({"label": "exact negative-real witness (cross marker)", "comparison": True, "points": [[value - 0.04, -0.04], [value + 0.04, 0.04], [value, 0], [value - 0.04, 0.04], [value + 0.04, -0.04]]})
    t = sp.Rational(1, 4)
    coefficient_sum = sp.factor((1 + t) / (1 - t)**3 - 1)
    return {
        "workflow": "W4", "question": "For which a>=0 is z+a*z^2 starlike on D?", "a_exact": str(a),
        "starlike": starlike, "exact_parameter_range": "0 <= a <= 1/2",
        "classification_method": "exact elementary theorem explained in workflow notes; not a sampled verdict",
        "witness": witness, "public_witness_replay": replay,
        "boundary_infimum_exact": str((1 - 2*a)/(1-a)) if starlike else None,
        "derivative_zero_exact": str(-1/(2*a)) if a else None,
        "extra_function_zero_exact": str(-1/a) if a else None,
        "sufficient_test_control": {
            "function": "z/(1-z/4)^2", "starlike": True,
            "reason": "normalized Koebe dilation; z*f'/f=(1+z/4)/(1-z/4) has positive real part on D",
            "test": "sum_{n>=2} n*|a_n| <= 1 (sufficient, not necessary)",
            "coefficient_sum_exact": str(coefficient_sum), "test_conclusive": False,
        },
        "domain": "open unit disk; a real and nonnegative", "plot_radius": radius,
        "plot_status": "sampled_visualization", "novelty_claim": False,
        "package_version": __version__, "panels": panels,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--a", type=Fraction, default=Fraction(1))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    data = solve(args.a)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "conjecture_counterexample.json").write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    write_panels(args.output / "conjecture_counterexample.svg", f"Repair the conjecture: f(z)=z+({args.a})z^2", data["panels"])
    print(f"a={args.a}: starlike={data['starlike']}; exact range 0<=a<=1/2; witness={data['witness']}")


if __name__ == "__main__":
    main()

"""Turn a starlike problem into a convex one through the Alexander transform."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import mpmath as mp
import sympy as sp
from _curves import write_panels
from class_geometry import canonical_expression, sample_curve

from geometric_function_atlas import class_extremal_coefficients, get_generator, z
from geometric_function_atlas.version import __version__


def solve(generator: str, radius: float = 0.7) -> dict:
    if not 0 < radius < 1:
        raise ValueError("radius must lie strictly between zero and one")
    member = canonical_expression(generator)
    t = sp.Symbol("t")
    integrand = sp.cancel(member / z).subs(z, t)
    transformed = z / (1-z) if generator == "starlike" else sp.Integral(integrand, (t, 0, z))
    gp = sp.diff(transformed, z)
    operator_residual = sp.simplify(z * gp - member)
    class_residual = sp.simplify(1 + z * sp.diff(gp, z) / gp - get_generator(generator).expression)
    if operator_residual != 0 or class_residual != 0:
        raise ArithmeticError("Alexander identities did not simplify exactly")
    coefficients = class_extremal_coefficients(generator, 12)
    transformed_coefficients = [a / n for n, a in enumerate(coefficients, 2)]
    evaluate_member = sp.lambdify(z, member, "mpmath")

    def evaluate_transform(point):
        if generator == "starlike":
            return point / (1-point)
        # Integrate on a straight path in D. This is numerical visualization,
        # not the argument establishing the analytic transform or convexity.
        return point * mp.quad(lambda u: mp.exp(mp.si(point*u)), [0, 1])

    panels = [
        {"title": "Before: starlike member f(D_r)", "curves": [], "notes": ["Full analytic member, sampled.", "Starlikeness concerns z f'/f."]},
        {"title": "After: convex transform g(D_r)", "curves": [], "notes": ["g = integral f(t)/t dt, sampled.", "Convexity concerns 1+z g''/g'."]},
    ]
    with mp.workdps(25):
        for fraction in (0.5, 1):
            for panel, evaluator in zip(panels, (evaluate_member, evaluate_transform), strict=True):
                panel["curves"].append({"label": f"analytic function, r={radius*fraction:g}", "points": sample_curve(evaluator, radius*fraction, samples=64)})
        value = evaluate_transform(mp.mpf("0.5"))
    with mp.workdps(40):
        higher_precision_value = evaluate_transform(mp.mpf("0.5"))
        difference = abs(higher_precision_value - value)
    return {
        "workflow": "W5", "generator": generator,
        "source_member_exact": str(member), "transform_exact": str(transformed),
        "canonical_coefficients": [str(a) for a in coefficients],
        "transformed_coefficients": [str(a) for a in transformed_coefficients],
        "operator_identity_residual": str(operator_residual), "class_transfer_identity_residual": str(class_residual),
        "class_implication": "f in S*(phi) iff Alexander(f) in C(phi), under normalized analytic defining conditions",
        "nonvanishing": "g'=f/z, nonzero for these exponential-form canonical members, with g'(0)=1",
        "truncation_inherits_convexity": False,
        "plot_status": "sampled_visualization", "sampling": {"radius": radius, "rings": 2, "angular_intervals": 64, "dps": 25},
        "quadrature_comparison_at_half": {"dps": [25, 40], "absolute_difference": str(difference), "scope": "one-point numerical consistency check, not a global quadrature error bound"},
        "source": "Classical Alexander relation; identity derived in accompanying workflow. No novel operator theorem claimed.",
        "novelty_claim": False, "package_version": __version__, "panels": panels,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--generator", choices=("starlike", "sine"), default="starlike")
    parser.add_argument("--radius", type=float, default=0.7)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    data = solve(args.generator, args.radius)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "alexander_transform.json").write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    write_panels(args.output / "alexander_transform.svg", f"Alexander transform: from starlike to convex ({args.generator})", data["panels"])
    print(f"{args.generator}: z*g'-f residual={data['operator_identity_residual']}; class-transfer residual={data['class_transfer_identity_residual']}")


if __name__ == "__main__":
    main()

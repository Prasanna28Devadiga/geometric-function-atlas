"""Compare a Ma–Minda generator, its canonical member and logarithmic derivative."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import mpmath as mp
import sympy as sp
from _curves import write_panels

from geometric_function_atlas import class_extremal_coefficients, get_generator, z
from geometric_function_atlas.version import __version__


def canonical_expression(generator: str) -> sp.Expr:
    """The two analytically specified members in this worked example."""
    if generator == "starlike":
        return z / (1 - z)**2
    if generator == "sine":
        return z * sp.exp(sp.Si(z))
    raise ValueError("this workflow supports starlike and sine")


def sample_curve(evaluator, radius: float, samples: int = 128) -> list[list[float]]:
    return [
        [float(mp.re(value)), float(mp.im(value))]
        for value in (evaluator(radius * mp.exp(2j * mp.pi * k / samples)) for k in range(samples + 1))
    ]


def solve(generator: str, radius: float = 0.7, order: int = 12) -> dict:
    if not 0 < radius < 1:
        raise ValueError("radius must lie strictly between zero and one")
    if not 2 <= order <= 12:
        raise ValueError("order must be between 2 and 12; comparison doubles it")
    phi = get_generator(generator).expression
    member = canonical_expression(generator)
    residual = sp.simplify(z * sp.diff(member, z) / member - phi)
    if residual != 0:
        raise ArithmeticError("canonical-member logarithmic derivative identity failed")
    coefficients = class_extremal_coefficients(generator, order)
    higher = class_extremal_coefficients(generator, 2 * order)
    polynomial = z + sum(a * z**n for n, a in enumerate(coefficients, 2))
    high_polynomial = z + sum(a * z**n for n, a in enumerate(higher, 2))
    evaluate_phi = sp.lambdify(z, phi, "mpmath")
    evaluate_member = sp.lambdify(z, member, "mpmath")
    evaluate_polynomial = sp.lambdify(z, polynomial, "mpmath")
    evaluate_higher = sp.lambdify(z, high_polynomial, "mpmath")
    # A polynomial logarithmic derivative can have poles even when f_phi has none.
    # Only the full analytic identity is plotted in panel 3; do not hide such poles.
    evaluate_logarithmic = sp.lambdify(z, sp.cancel(z * sp.diff(member, z) / member), "mpmath")
    panels = [
        {"object": "phi", "title": "Generator image: phi(D_r)", "curves": [], "notes": ["This constrains z f'/f, not f(D)."]},
        {"object": "f_phi", "title": "Canonical member: f_phi(D_r)", "curves": [], "notes": ["Blue: full analytic member, sampled.", f"Orange: finite polynomial, degree {order+1}."]},
        {"object": "z_fprime_over_f", "title": "Logarithmic derivative: z f'/f", "curves": [], "notes": ["Matches phi by an exact identity.", "At zero the value is defined by continuation."]},
    ]
    with mp.workdps(40):
        for fraction in (0.25, 0.5, 0.75, 1):
            r = radius * fraction
            for panel, function in zip(panels, (evaluate_phi, evaluate_member, evaluate_logarithmic), strict=True):
                panel["curves"].append({"label": f"analytic function at radius {r:g}", "points": sample_curve(function, r)})
        panels[1]["curves"].append({"label": "finite Taylor polynomial, outer sampled ring", "comparison": True, "points": sample_curve(evaluate_polynomial, radius)})
        points = [radius * mp.exp(2j * mp.pi * k / 128) for k in range(128)]
        errors = {
            str(order + 1): str(max(abs(evaluate_member(p) - evaluate_polynomial(p)) for p in points)),
            str(2 * order + 1): str(max(abs(evaluate_member(p) - evaluate_higher(p)) for p in points)),
        }
    return {
        "workflow": "W1", "generator": generator, "object_kind": "canonical_ma_minda_member",
        "phi_exact": str(phi), "member_exact": str(member),
        "canonical_coefficients": [str(a) for a in coefficients],
        "logarithmic_derivative_identity_residual": str(residual),
        "truncation_is_not_class_certificate": True,
        "plot_status": "sampled_visualization", "sampling": {"radius": radius, "rings": 4, "angular_intervals": 128, "dps": 40},
        "sampled_truncation_errors_by_degree": errors,
        "error_scope": "maximum on 128 sampled outer-ring points only, not a uniform tail bound",
        "normalization": "f(0)=0, f'(0)=1; phi(0)=1",
        "source": "Canonical member solves z*f'/f=phi; see package Ma-Minda class provenance and accompanying derivation.",
        "novelty_claim": False, "package_version": __version__, "panels": panels,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--generator", choices=("starlike", "sine"), default="starlike")
    parser.add_argument("--radius", type=float, default=0.7)
    parser.add_argument("--order", type=int, default=12)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    data = solve(args.generator, args.radius, args.order)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "class_geometry.json").write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    write_panels(args.output / "class_geometry.svg", f"{args.generator}: three different mathematical objects (r={args.radius:g})", data["panels"])
    print(f"{args.generator}: exact logarithmic-derivative residual = {data['logarithmic_derivative_identity_residual']}; sampled approximation errors = {data['sampled_truncation_errors_by_degree']}")


if __name__ == "__main__":
    main()

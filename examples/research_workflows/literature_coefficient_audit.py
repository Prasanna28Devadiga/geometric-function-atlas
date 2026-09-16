"""Audit and repair a recent coefficient bound using an exact analytic member.

Maintained replay example. The existing package reconstructs coefficients;
the workflow notes supply the human proof, not a sampled membership claim.
"""

from __future__ import annotations

import argparse
import json
import re
from fractions import Fraction
from pathlib import Path

import sympy as sp

from geometric_function_atlas.coefficients import taylor_coefficients
from geometric_function_atlas.models import Generator, Z
from geometric_function_atlas.schur import member_coefficients
from geometric_function_atlas.version import __version__


def solve(dilation: sp.Rational) -> dict:
    """Compare one admissible dilation against the literal and repaired bounds."""
    if not isinstance(dilation, sp.Rational) or not 0 <= dilation <= 1:
        raise ValueError("dilation must be an exact rational in [0,1]")
    generator = Generator(
        key="literature-nc-v1", name="Non-convex-domain source",
        expression=(1 + Z) / sp.cos(Z),
        citation="Kumar and Giri, arXiv:2412.04819v1, Eq.(7), Theorem 12",
        reference_url="https://arxiv.org/abs/2412.04819v1",
    )
    b = taylor_coefficients(generator, order=4)
    coefficients = member_coefficients(b, [dilation], order=4)
    f = Z + sum(value * Z**(index + 2) for index, value in enumerate(coefficients))
    q = 1 + sum(value * dilation**index * Z**index for index, value in enumerate(b, 1))
    residual = sp.series(Z * sp.diff(f, Z) - f * q, Z, 0, 6).removeO().expand()
    # This is a coefficient identity, NOT a class assertion about polynomial f.
    if residual != 0:
        raise ArithmeticError("reconstructed member violates its coefficient equation")
    t = sp.Symbol("t", real=True)
    majorant = 48 + 8*t + 8*t**2 - t**4
    monotonicity = sp.expand(sp.diff(majorant, t) - (8 + 4*t*(4-t**2)))
    upper = sp.simplify(majorant.subs(t, 2) / 192)
    excess = sp.simplify(coefficients[3] - sp.Rational(1, 3))
    if monotonicity != 0:
        raise ArithmeticError("upper-bound derivative identity failed")
    canonical_a5 = member_coefficients(b, [1], order=4)[3]
    if canonical_a5 != upper:
        raise ArithmeticError("canonical member does not attain the repaired bound")
    rows = [
        {"dilation": str(sp.Rational(j, 64)),
         "a5": str(canonical_a5 * sp.Rational(j, 64)**4)}
        for j in range(65)
    ]
    return {
        "question": "Does the literal v1 fifth-coefficient bound hold, and how can it be repaired?",
        "source_version": "arxiv:2412.04819v1",
        "source_url": generator.reference_url,
        "source_locator": "Theorem 12 and Eq.(8), p.6; canonical expansion Eq.(6), p.3",
        "source_scope": "checked preprint v1 only; separate journal correction status unresolved",
        "dilation": str(dilation),
        "exact_member": "f_d(z)=z*exp(integral_0^z (phi(d*t)-1)/t dt); phi(z)=(1+z)/cos(z)",
        "member_coefficients_a2_a5": list(map(str, coefficients)),
        "generator_coefficients_B1_B4": list(map(str, b)),
        "functional_equation_residual_through_degree4": str(residual),
        "literal_upper_bound": "1/3",
        "excess_over_claim": str(excess),
        "claim_outcome": "FALSIFIED" if excess > 0 else "NO_VIOLATION_FROM_SELECTED_MEMBER",
        "replacement_sharp_bound": str(upper),
        "upper_bound_monotonicity_residual": str(monotonicity),
        "upper_bound_proof": "192|a5|<=M(t)=48+8t+8t^2-t^4, t=|p1| in [0,2]; M'=8+4t(4-t^2)>=8. See workflow notes for coupled p1,p2 inequality.",
        "violation_threshold": str((sp.Rational(1, 3)/canonical_a5)**sp.Rational(1, 4)),
        "threshold_scope": "strict violation iff dilation exceeds threshold; equality is not violation",
        "plot_rows": rows,
        "plot_status": "sampled display of exact a5(d)=5*d^4/12; not a proof",
        "truncation_is_not_class_certificate": True,
        "novelty_claim": False,
        "package_version": __version__,
    }


def write_plot(data: dict, path: Path) -> None:
    """Show the failed source bound and sharp replacement on one parameter axis."""
    x = lambda value: 80 + 650 * float(value)
    y = lambda value: 360 - 600 * float(value)
    points = " ".join(
        f"{x(Fraction(row['dilation'])):.3f},{y(Fraction(row['a5'])):.3f}"
        for row in data["plot_rows"]
    )
    d = Fraction(data["dilation"])
    a5 = Fraction(data["member_coefficients_a2_a5"][3])
    path.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="840" height="480" viewBox="0 0 840 480">'
        '<title>Repair a recent fifth-coefficient bound</title>'
        '<desc>Sampled display of an exact formula, not a proof.</desc>'
        '<rect width="840" height="480" fill="white"/>'
        '<text x="30" y="35" font-size="21">From a counterexample to a sharp replacement</text>'
        '<text x="30" y="62">Canonical dilations: a5(d) = 5 d^4 / 12, 0 &lt;= d &lt;= 1</text>'
        '<path d="M80 90 V360 H730" stroke="black" fill="none"/>'
        f'<line x1="80" y1="{y(Fraction(1,3))}" x2="730" y2="{y(Fraction(1,3))}" stroke="#ba561b" stroke-dasharray="6 4"/>'
        f'<line x1="80" y1="{y(Fraction(5,12))}" x2="730" y2="{y(Fraction(5,12))}" stroke="#347647" stroke-dasharray="6 4"/>'
        '<text x="90" y="150" fill="#9c4414">1/3: literal v1 bound (false)</text>'
        '<text x="90" y="100" fill="#285e37">5/12: sharp replacement</text>'
        f'<polyline points="{points}" stroke="#2457a7" stroke-width="3" fill="none"/>'
        f'<circle cx="{x(d)}" cy="{y(a5)}" r="5" fill="#17233b"/>'
        '<text x="25" y="93">a5</text><text x="55" y="365">0</text>'
        '<text x="77" y="385">0</text><text x="727" y="385">1</text>'
        '<text x="650" y="407">dilation d</text>'
        f'<text x="30" y="430">Selected d={d}: a5={a5}; excess over 1/3 = {data["excess_over_claim"]}</text>'
        '<text x="30" y="457">Exact analytic members, not polynomial-membership claims. See notes for the proof.</text>'
        '</svg>\n', encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dilation", default="1")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"[0-9]{1,6}(?:/[0-9]{1,6})?", args.dilation):
        parser.error("dilation requires a bounded integer or integer/integer")
    try:
        value = Fraction(args.dilation)
        exact = sp.Rational(value.numerator, value.denominator)
        assert isinstance(exact, sp.Rational)
        data = solve(exact)
    except (ValueError, ZeroDivisionError) as exc:
        parser.error(str(exc))
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "literature_coefficient_audit.json").write_text(
        json.dumps(data, indent=2) + "\n", encoding="utf-8",
    )
    write_plot(data, args.output / "literature_coefficient_audit.svg")
    print(f"{data['claim_outcome']}: a5={data['member_coefficients_a2_a5'][3]}; excess={data['excess_over_claim']}; sharp replacement=5/12")


if __name__ == "__main__":
    main()

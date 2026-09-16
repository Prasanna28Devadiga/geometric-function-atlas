"""Solve a parameter-dependent Fekete–Szegő problem and explain equality.

Run from an installed geometric-function-atlas environment. The only theorem
implementation used for the bound is the public package; equality examples are
computed independently from the defining subordination coefficients.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from xml.sax.saxutils import escape

import sympy as sp

from geometric_function_atlas import fekete_szego
from geometric_function_atlas.version import __version__


def solve(generator: str) -> dict:
    """Recover exact transition points and an attaining example at each input."""
    anchor = fekete_szego(generator, mu=0)
    b1, b2 = anchor.b1, anchor.b2
    transitions = [
        sp.simplify((b1**2 + b2 - b1) / (2 * b1**2)),
        sp.simplify((b1**2 + b2 + b1) / (2 * b1**2)),
    ]
    values = []
    for numerator in range(-8, 17):
        mu = sp.Rational(numerator, 8)
        result = fekete_szego(generator, mu=str(mu))
        # omega(z)=z: a2=B1, 2*a3-a2^2=B2.
        axis_value = sp.simplify(abs((b1**2 + b2) / 2 - mu * b1**2))
        # omega(z)=z^2: a2=0, 2*a3=B1.
        quadratic_value = b1 / 2
        use_axis = bool(axis_value >= quadratic_value)
        attained = axis_value if use_axis else quadratic_value
        if sp.simplify(attained - result.value) != 0:
            raise ArithmeticError("the explicit equality example does not attain the bound")
        values.append(
            {
                "mu": str(mu),
                "bound": str(result.value),
                "attained_value": str(attained),
                "schwarz_function": "z" if use_axis else "z^2",
                "equality_nonunique_at_transition": mu in transitions,
            }
        )
    return {
        "workflow": "W3",
        "question": "How does the sharp bound for |a3-mu*a2^2| change with real mu?",
        "generator": generator,
        "B1": str(b1),
        "B2": str(b2),
        "transition_mu": [str(value) for value in transitions],
        "regimes": {
            "outside_transition_interval": "|B1^2+B2-2*mu*B1^2|/2; omega=z attains",
            "inside_transition_interval": "B1/2; omega=z^2 attains",
            "at_transitions": "both displayed examples attain; no uniqueness claim",
        },
        "values": values,
        "scope": "normalized analytic f with z*f'/f subordinate to an admissible phi; real mu",
        "assumptions": "full Ma-Minda admissibility is a theorem hypothesis, not certified by a coefficient check",
        "explanation": "Write omega=c1*z+c2*z^2+...: a2=B1*c1 and 2*a3=B1*c2+(B2+B1^2)*c1^2. The Schwarz coefficient bound |c2|<=1-|c1|^2 gives the maximum of the two displayed endpoint values.",
        "source": "Ma and Minda (1994), A unified treatment of some special classes of univalent functions, pp. 157-169; see package theorem provenance. Formula-level primary-source review pending.",
        "novelty_claim": False,
        "package_version": __version__,
        "plot_status": "sampled display of an exact piecewise formula; not a proof",
    }


def write_plot(data: dict, path: Path) -> None:
    """Export a small standalone parameter plot, not a conformal image plot."""
    rows = data["values"]
    points = [(float(sp.Rational(row["mu"])), float(sp.sympify(row["bound"]))) for row in rows]
    ymax = max(y for _, y in points)
    xmap = lambda x: 65 + (x + 1) * 700 / 3
    ymap = lambda y: 365 - y * 265 / ymax
    coords = " ".join(f"{xmap(x):.3f},{ymap(y):.3f}" for x, y in points)
    markers = []
    for exact in data["transition_mu"]:
        x = float(sp.sympify(exact))
        if -1 <= x <= 2:
            markers.append(
                f'<line x1="{xmap(x):.3f}" y1="90" x2="{xmap(x):.3f}" y2="365" stroke="#888" stroke-dasharray="4 4"/>'
                f'<text x="{xmap(x):.3f}" y="390" text-anchor="middle">{escape(exact)}</text>'
            )
    title = escape(f"{data['generator']}: sharp |a3 - mu a2^2| bound")
    path.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="840" height="465" viewBox="0 0 840 465">'
        f'<title>{title}</title><desc>Parameter plot with exact transition labels. Sampled display, not a proof.</desc>'
        '<rect width="840" height="465" fill="white"/>'
        f'<text x="35" y="35" font-size="20">{title}</text>'
        '<text x="35" y="62">Solid curve: theorem bound. Dashed lines: extremal transitions.</text>'
        '<path d="M65 90 V365 H765" fill="none" stroke="black"/>'
        f'<polyline points="{coords}" fill="none" stroke="#2457a7" stroke-width="3"/>'
        + "".join(markers)
        + '<text x="65" y="390">-1</text><text x="765" y="390">2</text>'
        + f'<text x="15" y="105">{ymax:g}</text><text x="30" y="367">0</text>'
        + '<text x="770" y="412">mu</text>'
        + '<text x="35" y="442">Known theorem under stated hypotheses. Visualization is not a proof; see JSON and workflow notes.</text></svg>\n',
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--generator", choices=("starlike", "sine"), default="starlike")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    data = solve(args.generator)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "coefficient_comparison.json").write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    write_plot(data, args.output / "coefficient_comparison.svg")
    print(f"{args.generator}: transition mu = {', '.join(data['transition_mu'])}; explicit examples attain every tabulated bound.")
    print(f"Artifacts: {args.output.resolve()}")


if __name__ == "__main__":
    main()

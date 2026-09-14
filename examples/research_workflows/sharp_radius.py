"""Explain a sharp radius and a real-axis shortcut's failure on a changed source."""

from __future__ import annotations

import argparse
import json
import math
from fractions import Fraction
from pathlib import Path

import mpmath as mp
import sympy as sp
from _curves import write_panels
from class_geometry import sample_curve

from geometric_function_atlas import get_generator, radius, z
from geometric_function_atlas.version import __version__


def exact_radius(source: str, s: sp.Rational) -> tuple[sp.Expr, str]:
    """Select a stratum exactly; finite Taylor bounds can explicitly abstain."""
    if s <= 0 or s**2 > sp.Rational(1, 2):
        raise ValueError("target admissibility requires 0 < s <= 1/sqrt(2)")
    if source == "off_axis":
        if s >= sp.Rational(9, 32):
            return sp.Integer(1), "whole_disk"
        x = sp.Symbol("r")
        return sp.CRootOf(x**3 + 8*x - 32*s, 0), "proper_radius"
    if source != "sine":
        raise ValueError("source must be sine or off_axis")
    q = 2*s - s*s
    partial = sp.Integer(0)
    for k in range(32):
        partial += sp.Rational((-1)**k, math.factorial(2*k+1))
        if k % 2 == 0 and q >= partial:
            return sp.Integer(1), "whole_disk"
        if k % 2 == 1 and q <= partial:
            return sp.asin(q), "proper_radius"
    raise ValueError("ABSTAIN: cap stratum unresolved within 32 exact sine-series terms")


def solve(source: str, parameter: Fraction) -> dict:
    s = sp.Rational(parameter.numerator, parameter.denominator)
    assert isinstance(s, sp.Rational)
    exact, stratum = exact_radius(source, s)
    phi = get_generator("sine").expression if source == "sine" else (1 + z/4 - z**3/32)**2
    inverse = sp.cos(z/2) + sp.sin(z/2) - 1 if source == "sine" else z/4 - z**3/32
    if sp.trigsimp(sp.expand((1+inverse)**2-phi)) != 0:
        raise ArithmeticError("inverse-coordinate identity failed")
    admissibility = {"scope": "source/target analytic hypotheses and branch justified in the attached workflow proof"}
    shortcut = None
    if source == "off_axis":
        p = sp.expand(2*(phi-1))
        coefficient_sum = sum(n*abs(p.coeff(z,n)) for n in range(2,7))
        lower = 1-2*sp.Rational(9,32)-sp.Rational(9,32)**2
        if coefficient_sum >= 1 or lower <= 0:
            raise ArithmeticError("source admissibility sufficient inequalities failed")
        admissibility.update(normalized_coefficient_sum=str(coefficient_sum), positive_real_lower_bound=str(lower))
        r_witness = sp.Rational(15,16)
        # This named counterexample is always against L_{1/4}, not an
        # arbitrary caller's s. Its scope must travel with the witness.
        excess = r_witness/4+r_witness**3/32-sp.Rational(1,4)
        shortcut = {"target_parameter": "1/4", "point_exact": "15*I/16", "excess_exact": str(excess), "real_axis_max": "7/32", "claim_refuted": "containment on the real diameter implies full generator-image containment", "not_a_refutation_of_published_theorem": True}
    numeric = float(sp.N(exact,40))
    before = numeric*0.9
    after = (numeric+1)/2 if stratum == "proper_radius" else 1.0
    source_eval = sp.lambdify(z,phi,"mpmath")
    inverse_eval = sp.lambdify(z,inverse,"mpmath")
    sf = mp.mpf(str(sp.N(s,40)))
    panels = [
        {"title": "Generator containment in L_s(D)", "curves": [], "notes": [f"Blue: source at r={before:.5g} and {after:.5g}.", "Orange: target boundary (not f(D))."]},
        {"title": "Inverse coordinates: sqrt(phi)-1", "curves": [], "notes": [f"Target becomes the disk of radius s={parameter}.", "Off-axis vs real-axis contact is visible here."]},
    ]
    with mp.workdps(40):
        for panel,evaluator in zip(panels,(source_eval,inverse_eval),strict=True):
            for rvalue in (before,after):
                panel["curves"].append({"label": f"source at r={rvalue:.10g}", "points": sample_curve(evaluator,rvalue,256)})
        panels[0]["curves"].append({"label": "L_s unit-circle boundary", "comparison": True, "points": sample_curve(lambda w:(1+sf*w)**2,1.0,256)})
        panels[1]["curves"].append({"label": "inverse target boundary", "comparison": True, "points": sample_curve(lambda w:sf*w,1.0,256)})
        # The formula is exact. This table is only a sampled view of its parameter dependence.
        profile = []
        for j in range(1,45):
            target = sp.Rational(j,64)
            assert isinstance(target, sp.Rational)
            value,_ = exact_radius(source,target)
            profile.append({"s": str(target), "radius_exact": str(value), "radius_decimal": str(sp.N(value,20))})
    snapshot = None
    if source == "sine" and s in (sp.Rational(3,10),sp.Rational(1,2)):
        record = radius("sine", "limacon_0.3" if s==sp.Rational(3,10) else "limacon_0.5")
        snapshot = {"direction": record.direction, "value_exact": record.value_exact, "status": record.status.value, "has_full_certificate": record.certificate is not None, "source_snapshot_commit": record.provenance.source_snapshot_commit, "agreement": "exact expression string matches" if record.value_exact == str(exact) else "not an exact string match", "warning": "Snapshot touch status is not upgraded by this workflow; family proof has separate provenance."}
    return {
        "workflow": "W2", "source": source, "target": "(1+s*z)^2", "target_parameter_exact": str(s),
        "direction": "S*(source_phi) -> S*((1+s*z)^2)", "source_phi_exact": str(phi),
        "radius_exact": str(exact), "radius_decimal": str(sp.N(exact,40)), "stratum": stratum,
        "contact_direction": "negative_real_axis" if source=="sine" else "imaginary_axis",
        "global_maximum": "1-cos(r/2)+sin(r/2)" if source=="sine" else "r/4+r^3/32",
        "admissibility": admissibility, "axis_shortcut_counterexample": shortcut, "snapshot_anchor": snapshot,
        "proof_origin": "docs/workflows/sharp_radius.md; sine lemma from pinned registry proof, off-axis argument derived there",
        "sine_source_proof": "https://github.com/Prasanna28Devadiga/gft-registry/blob/456432b5f6945ea6db46f420aa12bf0730619cf1/data/proofs/RADIUS_SINE_LIMACON_FAMILY.md",
        "novelty_claim": False, "plot_status": "sampled_visualization", "plot_radii": [before,after],
        "package_version": __version__, "parameter_profile": profile, "panels": panels,
    }


def write_profile(data: dict,path: Path) -> None:
    coords = " ".join(f"{60+float(sp.Rational(row['s']))*900:.3f},{360-float(row['radius_decimal'])*280:.3f}" for row in data["parameter_profile"])
    path.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="780" height="460" viewBox="0 0 780 460">'
                    '<title>Sharp radius versus target parameter</title><rect width="780" height="460" fill="white"/>'
                    '<text x="30" y="30" font-size="20">Sharp radius R(s): enlargement of the target</text>'
                    '<path d="M60 65 V360 H730" fill="none" stroke="black"/>'
                    f'<polyline points="{coords}" fill="none" stroke="#2457a7" stroke-width="3"/>'
                    '<text x="25" y="85">1</text><text x="30" y="360">0</text><text x="710" y="390">s</text>'
                    '<text x="60" y="390">0</text><text x="650" y="390">0.7</text>'
                    '<text x="30" y="423">Cap R=1 means whole-disk inclusion. Rational parameter samples, not a proof.</text></svg>\n',encoding="utf-8")


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source",choices=("sine","off_axis"),default="sine")
    parser.add_argument("--s",type=Fraction,default=Fraction(1,2))
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    data=solve(args.source,args.s)
    args.output.mkdir(parents=True,exist_ok=True)
    (args.output/"sharp_radius.json").write_text(json.dumps(data,indent=2)+"\n",encoding="utf-8")
    write_panels(args.output/"sharp_radius.svg",f"Sharp directed radius: {args.source}, s={args.s}",data["panels"])
    write_profile(data,args.output/"radius_profile.svg")
    print(f"{args.source} -> L_{args.s}: R={data['radius_exact']} ({data['stratum']}); contact={data['contact_direction']}")


if __name__ == "__main__":
    main()

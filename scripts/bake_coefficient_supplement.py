"""Deterministically bake coefficient gaps without rewriting the frozen 0.4.0 corpus.

The separate supplement is checksummed in the existing artifact manifest. The
six direct-class literature attributions were checked against local paper OCR
extractions; they remain citations, not machine reproofs of the upper bound.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import sympy as sp

from geometric_function_atlas.exact import parse_exact_expression

DATA = Path(__file__).resolve().parents[1] / "src/geometric_function_atlas/data"
# Direct-class sharp theorems, not the n-fold symmetric subfamily theorem.
SHARP = {
    "starlike": ("Kowalczyk, Lecko & Thomas, Forum Math. 34 (2022), 1249–1254", "10.1515/forum-2021-0308"),
    "lemniscate": ("Banga & Sivaprasad Kumar, Theorem 2.1", "https://arxiv.org/abs/1906.02681"),
    "exponential": ("Third Hankel determinant for a class of starlike functions associated with exponential function, Theorem 2.1", "https://arxiv.org/abs/2206.13707"),
    "cardioid_exp": ("A Conjecture on H_3(1) For Certain Starlike Functions, Theorem 2.1", "https://arxiv.org/abs/2208.02975"),
    "bean_tanh": ("On Estimation of Hankel Determinants for Certain Class of Starlike Functions, Theorem 2.5", "https://arxiv.org/abs/2405.07995"),
    "nonconvex_sec": ("Starlike Functions Associated with a Non-Convex Domain, Theorem 14", "https://arxiv.org/abs/2412.04819"),
}


def exact(value: sp.Expr) -> str:
    text = sp.sstr(sp.simplify(value))
    if sp.simplify(parse_exact_expression(text) - value) != 0:
        raise ValueError(f"unparseable constant: {text}")
    return text


def maxima(b1: sp.Expr, b2: sp.Expr, functional: str) -> dict:
    # Schur: c1=r, |c2|<=1-r², and a3=(B1*c2+(B2+B1²)*r²)/2.
    # The phase aligns with the real C term, so for x=r² the exact objective is
    # (B1*(1-x)+|B2+B1²|*x)/2, times B1*sqrt(x) for |a2*a3|.
    q = sp.simplify(sp.Abs(b2 + b1**2))
    delta = sp.simplify(q-b1)
    xs: list[sp.Expr] = [sp.Integer(0), sp.Integer(1)] if functional == "a3" else [sp.Integer(1)]
    if functional == "a2a3" and delta < 0:
        root = sp.simplify(-b1/(3*delta))
        if 0 < root < 1:
            xs.append(root)
    def objective(x: sp.Expr) -> sp.Expr:
        base = (b1+delta*x)/2
        return base if functional == "a3" else b1*sp.sqrt(x)*base
    chosen = xs[0]
    for x in xs[1:]:
        difference = sp.simplify(objective(x) - objective(chosen))
        if difference.is_positive is True:
            chosen = x
        elif difference.is_nonpositive is not True:
            raise ValueError(f"cannot compare exact extrema: {difference}")
    # For x in (0,1), choose c2 phase to align with B2+B1².
    gamma1 = "1" if b2+b1**2 >= 0 else "-1"
    if chosen == 1:
        gamma1 = "0"  # c2=0 at the boundary
    return {
        "value_exact": exact(objective(chosen)),
        "extremal_r_squared": exact(chosen),
        "extremal_gamma1": gamma1,
        "extremal_omega": "z" if chosen == 1 else ("z^2" if chosen == 0 and gamma1 == "1" else "Schur(gamma0=sqrt(x), gamma1=sign(B2+B1**2))"),
        "status": "analytic_sharp",
        "method": "single_harmonic_schur_phase_and_one_variable_maximum",
    }


def main() -> None:
    classes = json.loads((DATA / "classes.json").read_text())["classes"]
    certs = {}
    tables = {"hankel3_1": {}, "a3": {}, "a2a3": {}}
    for key, record in sorted(classes.items()):
        # The duplicate is represented by its canonical order-0.5 key.
        if key == "janowski_A0_B-1":
            continue
        b1, b2 = map(parse_exact_expression, record["phi_coeffs"][:2])
        for f in ("a3", "a2a3"):
            tables[f][key] = maxima(b1,b2,f)
        row = {
            "value_exact": exact(b1**2/9),
            "B1": exact(b1),
            "extremal_omega": "z^3",
            "method": "exact_attainment_at_schwarz_z_cubed",
            "status": "attained_lower_bound",
            "optimization_status": "global_upper_bound_not_established_here",
            "citation": None,
        }
        if key in SHARP:
            row["status"] = "literature_sharp"
            row["optimization_status"] = "published_direct_class_upper_bound; not_reproved_by_package"
            row["citation"] = {"theorem": SHARP[key][0], "locator": SHARP[key][1]}
        tables["hankel3_1"][key] = row
        if key not in ("booth_0.3", "booth_0.7"):
            continue
        for mu in ("0", "0.25", "0.5", "0.75", "1", "2"):
            m = sp.Rational(mu)
            k = sp.simplify(b2+(1-2*m)*b1*b1)
            value = sp.simplify(sp.Max(b1, sp.Abs(k))/2)
            # omega=z gives |k|/2; omega=z² gives B1/2.
            gamma = ["1", "0"] if sp.Abs(k) >= b1 else ["0", "1"]
            name = f"{key}__fekete_szego_mu{mu}"
            certs[name] = {
                "name": name, "class": key, "functional": f"fekete_szego_mu{mu}",
                "status": "PROVED", "engine": "closed-form-single-harmonic",
                "bound": exact(value), "bound_float": float(value), "slack": 0.0,
                "statement": f"Sharp |a3-{mu}a2²| = {exact(value)} under Ma–Minda assumptions",
                "sharp": {
                    "proven": True, "exact": True,
                    "reference": "Ma–Minda Fekete–Szegő single-harmonic formula; linear maximum in r²",
                    "extremal_gammas": gamma,
                    "candidate": {"value_exact": exact(value), "value_float": float(value)},
                },
            }
    supplement = {
        "schema_version": 1, "supplement_version": "2026.09.27-coefficients-v1",
        "source_class_artifact": "classes.json:2026.08.11",
        "theorem_scope": "Ma–Minda admissibility of each named generator",
        "certificates": certs, "tables": tables,
    }
    path = DATA / "coefficient_supplement.json"
    path.write_text(json.dumps(supplement, sort_keys=True, indent=1, ensure_ascii=False)+"\n")
    manifest_path = DATA / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["files"][path.name] = {"schema_version": 1, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    manifest_path.write_text(json.dumps(manifest, sort_keys=True, indent=1, ensure_ascii=False)+"\n")
    print(f"{len(certs)} certificates; {[len(tables[k]) for k in tables]} table rows; {len(SHARP)} cited sharp classes")


if __name__ == "__main__":
    main()

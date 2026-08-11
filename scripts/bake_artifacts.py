#!/usr/bin/env python3
"""Bake versioned scientific artifacts from the Geometric Function Atlas website.

Development-only generator (NOT shipped in the wheel). It transforms the
website/research repository's immutable baked artifacts into the package's
versioned, checksummed data directory ``src/geometric_function_atlas/data/``:

  * expansions.json       — Schur-parameter coefficient expansions (22 classes)
  * bounds.json           — coefficient-bound catalog (39 classes, 306 entries)
  * classes.json          — 39 Ma–Minda classes with exact phi coefficients B1..B5
  * certificates.json     — 306 machine certificates (leaves_parts stripped)
  * open_problems.json    — 12 certified enclosures + 97 numerical conjectures
  * reconciliation.json   — literature-reconciliation rows from RECONCILIATION.md
  * proof_meta.json       — functional labels, known-result citations, lemma notes
  * references.md         — method references companion document
  * manifest.json         — schema versions, source commit, per-file SHA-256

Transformation rules:
  * Website source is read-only. Only the files named above are consumed.
  * Exact strings must round-trip through the package's restricted parser
    (no eval); the bake FAILS on any string the package cannot parse back.
  * Where the website publishes phi coefficients (expansions.json LaTeX), the
    bake cross-checks the extracted B coefficients against them.
  * leaves_parts pointers into the 6.4 GB proof leaf corpus are stripped and
    replaced by a count; the certificates themselves are fully retained.

Usage:
    python3 scripts/bake_artifacts.py [--source /root/workspace/gft-registry]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

import sympy as sp

SOURCE_DEFAULT = Path("/root/workspace/gft-registry")
PACKAGE_DATA = (
    Path(__file__).resolve().parents[1] / "src" / "geometric_function_atlas" / "data"
)
ARTIFACT_VERSION = "2026.08.11"
SNAPSHOT_DATE = "2026-08-11"
SCHEMA_VERSION = 1
MAX_PHI_ORDER = 5

# Classes covered by the site's expansion formulas (expansions.json).
_EXPANSION_CLASSES = {
    "bean_tanh", "bell", "cardioid", "cardioid_exp", "cissoid_diocles",
    "cosh_sqrt", "crescent", "epicycloid_3", "epicycloid_6", "exponential",
    "four_leaf", "lemniscate", "nephroid", "nonconvex_sec", "petal_arcsinh",
    "rational_kr", "sigmoid", "sine", "starlike", "strip_arctan", "tanh",
    "three_leaf",
}

# Ma-Minda class definitions mirroring gft/maminda.py CATALOG (source commit
# recorded in the manifest). Formulas are sympy-parseable in z.
_NAMED = {
    "starlike": ("Starlike S* (half-plane)", "(1+z)/(1-z)",
                 "Janowski 1973 (A=1, B=-1); classical S*"),
    "lemniscate": ("Lemniscate S*_L", "sqrt(1+z)", "Sokol & Stankiewicz 1996"),
    "exponential": ("Exponential S*_e", "exp(z)",
                    "Mendiratta, Nagpal & Ravichandran 2015"),
    "cardioid": ("Cardioid S*_C", "1 + 4*z/3 + 2*z**2/3",
                 "Sharma, Jain & Ravichandran 2016"),
    "sine": ("Sine S*_sin", "1 + sin(z)",
             "Cho, Kumar, Kumar & Ravichandran 2019"),
    "rational_kr": ("Rational S*_R",
                    "1 + z*((1+sqrt(2))+z)/((1+sqrt(2))*((1+sqrt(2))-z))",
                    "Kumar & Ravichandran 2016 (k = 1+sqrt 2)"),
    "crescent": ("Crescent / lune", "z + sqrt(1+z**2)", "Raina & Sokol 2015"),
    "nephroid": ("Nephroid S*_Ne", "1 + z - z**3/3", "Wani & Swaminathan 2021"),
    "sigmoid": ("Sigmoid S*_SG", "2/(1+exp(-z))", "Goel & Kumar 2020"),
    "bell": ("Bell numbers S*_B", "exp(exp(z)-1)",
             "Cho, Kumar, Kumar & Ravichandran 2019 (Bell numbers)"),
    "tanh": ("Tanh S*_tanh", "1 + tanh(z)", "Ullah, Srivastava et al. 2021"),
    "three_leaf": ("Three-leaf", "1 + 4*z/5 + z**4/5", "Gandhi 2020"),
    "parabolic": ("Parabolic (uniformly convex) S_p",
                  "1 + (2/pi**2)*log((1+sqrt(z))/(1-sqrt(z)))**2",
                  "Ronning 1993; Kanas & Wisniowska conic domains"),
    "cosh_sqrt": ("Cosh-sqrt", "cosh(sqrt(z))", "Mundalia & Swaminathan (cosh sqrt)"),
    "cardioid_exp": ("Cardioid S*_℘ (1+z e^z)", "1 + z*exp(z)",
                     "Kumar & Gangania 2021 — a cardioid domain (Anal. Math. Phys.)"),
    "petal_arcsinh": ("Petal S*_ρ (1+sinh⁻¹ z)", "1 + asinh(z)",
                      "Arora & Kumar 2022 — petal-shaped domain (Bull. Korean Math. Soc.)"),
    "strip_arctan": ("Strip S*_τ (1+arctan z)", "1 + atan(z)",
                     "Kumar & Verma 2023 — strip domain"),
    "bean_tanh": ("Bean S*_𝔅 (√(1+tanh z))", "sqrt(1 + tanh(z))",
                  "Kumar & Yadav 2024 — bean-shaped domain"),
    "nonconvex_sec": ("Non-convex S*_nc ((1+z)/cos z)", "(1+z)/cos(z)",
                      "Kumar & Giri 2024 — non-convex domain"),
    "four_leaf": ("Four-leaf S*_{4L}", "1 + 5*z/6 + z**5/6",
                  "Gandhi; Sunthrayuth et al. 2022 — four-leaf domain (J. Function Spaces)"),
    "cissoid_diocles": ("Cissoid of Diocles S*_cs", "1 + z/((1-z)*(1+z/3))",
                        "Masih, Ebadian & Yalçın 2019 — cissoid of Diocles (Math. Slovaca)"),
}


def _grid_classes() -> dict[str, tuple[str, str, str]]:
    out: dict[str, tuple[str, str, str]] = {}
    for alpha in (sp.Rational(1, 4), sp.Rational(1, 2), sp.Rational(3, 4)):
        out[f"order_{float(alpha):g}"] = (
            f"Starlike of order {alpha}", f"(1+(1-2*({alpha}))*z)/(1-z)",
            "Robertson 1936 (order alpha)")
    for A, B in ((1, 0), (sp.Rational(1, 2), sp.Rational(-1, 2)),
                 (1, sp.Rational(-1, 2)), (sp.Rational(3, 4), sp.Rational(-1, 4)),
                 (0, -1)):
        out[f"janowski_A{float(A):g}_B{float(B):g}"] = (
            f"Janowski S*[{A},{B}]", f"(1+({A})*z)/(1+({B})*z)", "Janowski 1973")
    for beta in (sp.Rational(1, 4), sp.Rational(1, 2), sp.Rational(3, 4)):
        out[f"strongly_{float(beta):g}"] = (
            f"Strongly starlike SS*({beta})", f"((1+z)/(1-z))**({beta})",
            "Brannan & Kirwan 1969; Stankiewicz")
    for s in (sp.Rational(3, 10), sp.Rational(1, 2), sp.sqrt(2) / 2):
        out[f"limacon_{float(s):.3g}"] = (
            f"Limacon (1+sz)^2, s={float(s):.3g}", f"(1+({s})*z)**2",
            "Masih & Kanas 2020")
    for a in (sp.Rational(3, 10), sp.Rational(7, 10)):
        out[f"booth_{float(a):g}"] = (
            f"Booth lemniscate BS({a})", f"1 + z/(1-({a})*z**2)",
            "Kargar, Ebadian & Sokol 2019")
    for n in (3, 6):
        out[f"epicycloid_{n}"] = (
            f"Epicycloid S*_{{{n}ℒ}} ({n - 1} cusps)",
            f"1 + {n}*z/{n + 1} + z**{n}/{n + 1}",
            "Gandhi, Gupta, Nagpal & Ravichandran 2022 — epicycloid (Hacettepe J. Math. Stat.)")
    return out


def _phi_exprs() -> dict[str, sp.Expr]:
    z = sp.Symbol("z")
    classes = dict(_NAMED)
    classes.update(_grid_classes())
    return {key: sp.sympify(formula, locals={"z": z})
            for key, (_, formula, _) in classes.items()}


def _phi_coefficients(expr: sp.Expr, order: int) -> list[sp.Expr]:
    """Exact B1..B_order of phi via the t = sqrt(z) substitution.

    phi(t^2) has only even powers of t for admissible phi; B_k is the
    coefficient of t^(2k). Odd powers of t indicate a half-integer power of z
    and fail the bake.
    """
    z = sp.Symbol("z")
    t = sp.Symbol("t")
    series = sp.series(expr.subs(z, t**2), t, 0, 2 * order + 3).removeO()
    odd = [n for n in range(1, 2 * order + 3, 2) if sp.simplify(series.coeff(t, n)) != 0]
    if odd:
        raise ValueError(f"phi has half-integer powers of z at t^{odd[0]}")
    return [sp.simplify(series.coeff(t, 2 * n)) for n in range(1, order + 1)]


def _to_exact_string(value: sp.Expr) -> str:
    """Format an exact constant as a string accepted by the package parser.

    The parser is deliberately stricter than sympy's printer, so the bake
    validates the round trip here and fails on anything the package cannot
    parse back.
    """
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    from geometric_function_atlas.exact import parse_exact_expression

    text = sp.sstr(value)
    parsed = parse_exact_expression(text)
    if sp.simplify(parsed - value) != 0:
        raise ValueError(f"exact string {text!r} does not round-trip {value}")
    return text


_LATEX_FRACTION = re.compile(r"^-?\\frac\{([0-9]+)\}\{([0-9]+)\}$")
_LATEX_INTEGER = re.compile(r"^-?[0-9]+$")


def _parse_latex_fraction(text: str) -> sp.Expr | None:
    """Parse the restricted phi-coefficient LaTeX forms used by the site.

    Supports signed fractions (``- \\frac{1}{8}``), signed integers, and the
    ``N ± M \\sqrt{2}`` forms used by the rational generator. The sqrt forms
    are normalized and parsed with the package's restricted (eval-free)
    parser so the cross-check uses the same grammar the runtime uses.
    """
    cleaned = text.strip().replace(" ", "")
    if _LATEX_INTEGER.fullmatch(cleaned):
        return sp.Integer(int(cleaned))
    match = _LATEX_FRACTION.fullmatch(cleaned)
    if match:
        value = sp.Rational(int(match.group(1)), int(match.group(2)))
        return -value if cleaned.startswith("-") else value
    if "\\sqrt{2}" in cleaned:
        normalized = cleaned.replace("\\sqrt{2}", "sqrt(2)")
        normalized = re.sub(r"([0-9])\s*(sqrt)", r"\1*\2", normalized)
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
        from geometric_function_atlas.exact import (
            ExactExpressionError,
            parse_exact_expression,
        )
        try:
            return parse_exact_expression(normalized)
        except ExactExpressionError:
            return None
    return None


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(data_dir: Path, name: str, payload: dict) -> None:
    path = data_dir / name
    path.write_text(
        json.dumps(payload, indent=1, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {path.name} ({path.stat().st_size} bytes)")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=SOURCE_DEFAULT)
    args = parser.parse_args()

    source = args.source.resolve()
    static_site = source / "static-site"
    proofs_dir = source / "data" / "proofs"
    for required in (static_site / "expansions.json", static_site / "bounds.json",
                     proofs_dir / "open_conjectures.json", proofs_dir / "RECONCILIATION.md",
                     proofs_dir / "REFERENCES.md"):
        if not required.is_file():
            print(f"missing source artifact: {required}", file=sys.stderr)
            return 2

    # ── 1. classes.json: 39 classes with exact phi coefficients ────────────
    phi_exprs = _phi_exprs()
    classes_payload: dict = {}
    for key in sorted(phi_exprs):
        name, formula, citation = (dict(_NAMED) | _grid_classes())[key]
        coefficients = _phi_coefficients(phi_exprs[key], MAX_PHI_ORDER)
        classes_payload[key] = {
            "name": name,
            "phi_formula": formula,
            "citation": citation,
            "phi_coeffs": [_to_exact_string(value) for value in coefficients],
        }

    # ── 2. expansions.json: site expansions, cross-checked against B's ─────
    expansions_raw = json.loads((static_site / "expansions.json").read_text(encoding="utf-8"))
    expansion_classes: dict = {}
    mismatches: list[str] = []
    for key, entry in sorted(expansions_raw.items()):
        phi_latex = entry.get("phi_latex", "")
        phi_coeffs_latex = entry.get("phi_coeffs", [])
        parsed_latex: list[sp.Expr] = []
        for text in phi_coeffs_latex:
            value = _parse_latex_fraction(text)
            if value is None:
                mismatches.append(f"{key}: unparseable phi_coeffs {text!r}")
                continue
            parsed_latex.append(value)
        baked = [sp.sympify(text) for text in classes_payload[key]["phi_coeffs"]]
        for index, value in enumerate(parsed_latex):
            if sp.simplify(baked[index] - value) != 0:
                mismatches.append(
                    f"{key}: B{index + 1} baked {baked[index]} != site {value}"
                )
        if key not in classes_payload:
            mismatches.append(f"{key}: expansion class missing from class catalog")
        expansion_classes[key] = {
            "phi_latex": phi_latex,
            "phi_coeffs_latex": list(phi_coeffs_latex),
            "coeffs": entry.get("coeffs", []),
        }
    missing = _EXPANSION_CLASSES - set(expansions_raw)
    if missing:
        mismatches.append(f"expansion classes missing from site data: {sorted(missing)}")
    if mismatches:
        print("expansion cross-check FAILED:", file=sys.stderr)
        for line in mismatches[:40]:
            print("  " + line, file=sys.stderr)
        return 2

    # ── 3. bounds.json: coefficient-bound catalog (as published) ────────────
    bounds_raw = json.loads((static_site / "bounds.json").read_text(encoding="utf-8"))
    bounds_classes = {key: dict(entries) for key, entries in sorted(bounds_raw.items())}

    # ── 4. certificates.json: 306 certificates, leaves stripped ─────────────
    cert_payload: dict = {}
    for path in sorted(proofs_dir.glob("*.json")):
        if path.name == "open_conjectures.json":
            continue
        cert = json.loads(path.read_text(encoding="utf-8"))
        if "class" not in cert or "functional" not in cert:
            continue
        name = path.name[:-5]
        transformed = dict(cert)
        leaves_parts = transformed.pop("leaves_parts", [])
        transformed["n_leaves_parts"] = len(leaves_parts)
        transformed["name"] = name
        cert_payload[name] = transformed

    # ── 5. open_problems.json: enclosures + numerical conjectures ───────────
    enclosures = []
    for name, cert in sorted(cert_payload.items()):
        sharp = cert.get("sharp") or {}
        candidate = sharp.get("candidate") or {}
        if cert.get("status") != "PROVED" or sharp.get("proven") or not candidate:
            continue
        enclosures.append({
            "name": name,
            "class_key": cert["class"],
            "functional_key": cert["functional"],
            "bound_exact": cert.get("bound"),
            "candidate_exact": candidate.get("value_exact"),
            "candidate_float": candidate.get("value_float"),
            "candidate_method": candidate.get("method"),
            "bracket_lo": sharp.get("bracket_lo"),
            "bracket_hi": sharp.get("bracket_hi"),
            "slack": cert.get("slack"),
            "extremal_gammas": [str(value) for value in (sharp.get("extremal_gammas") or [])],
            "note": sharp.get("note"),
        })
    conjectures_raw = json.loads(
        (proofs_dir / "open_conjectures.json").read_text(encoding="utf-8")
    )
    conjectures = []
    for functional_key, classes in sorted(conjectures_raw.items()):
        for class_key, entry in sorted(classes.items()):
            conjectures.append({
                "class_key": class_key,
                "functional_key": functional_key,
                "candidate_exact": entry.get("candidate"),
                "candidate_float": entry.get("candidate_float"),
                "candidate_kind": entry.get("candidate_kind"),
                "numeric_max": entry.get("numeric_max"),
                "extremal_omega": entry.get("extremal_omega"),
                "extremal_gammas": [str(value) for value in (entry.get("extremal_gammas") or [])],
                "m": entry.get("m"),
            })

    # ── 6. reconciliation.json: rows + counts from RECONCILIATION.md ────────
    reconciliation_text = (proofs_dir / "RECONCILIATION.md").read_text(encoding="utf-8")
    counts: dict[str, int] = {}
    for match in re.finditer(r"^\*\*([A-D])\s+—.*?[:：]\s*(\d+)\*\*\s*$",
                             reconciliation_text, re.MULTILINE):
        counts[match.group(1)] = int(match.group(2))
    rows = []
    for line in reconciliation_text.splitlines():
        match = re.match(r"^\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*(.*?)\s*\|$", line)
        if not match:
            continue
        class_key, functional_key, value, slack, category, notes = match.groups()
        if class_key == "class" or set(class_key) == {"-"}:
            continue
        rows.append({
            "class_key": class_key.strip(),
            "functional_key": functional_key.strip(),
            "value_exact": value.strip(),
            "slack": slack.strip(),
            "category": category.strip(),
            "notes": notes.strip(),
        })

    # ── 7. proof_meta.json: functional labels, known results, lemmas ────────
    proof_meta = {
        "functionals": {
            "fekete_szego_mu1": ("Fekete–Szegő (μ=1)", r"|a_3-a_2^{2}|"),
            "fekete_szego_mu0.5": ("Fekete–Szegő (μ=½)", r"|a_3-\tfrac12 a_2^{2}|"),
            "hankel2_2": ("Hankel H₂(2)", r"|a_2a_4-a_3^{2}|"),
            "zalcman_a3sq_a5": ("Zalcman (n=3)", r"|a_3^{2}-a_5|"),
            "hankel3_1": ("Hankel H₃(1)", r"|H_{3}(1)|"),
            "log_gamma2": ("Logarithmic γ₂", r"|\gamma_2|"),
            "log_gamma3": ("Logarithmic γ₃", r"|\gamma_3|"),
            "inv_a3": ("Inverse coeff. |A₃|", r"|A_3|=|2a_2^{2}-a_3|"),
            "inv_a4": ("Inverse coeff. |A₄|", r"|A_4|"),
            "zalcman_a2a3_a4": ("Gen. Zalcman (2,3)", r"|a_2a_3-a_4|"),
            "zalcman_a2a4_a5": ("Gen. Zalcman (2,4)", r"|a_2a_4-a_5|"),
        },
        "known": [
            {"class_key": ck, "functional_key": fk, "citation": cite}
            for (ck, fk), cite in sorted(
                {
                    ("starlike", "hankel3_1"): "Kowalczyk–Lecko–Thomas 2022",
                    ("starlike", "fekete_szego_mu1"): "Fekete–Szegő 1933 (classical)",
                    ("starlike", "zalcman_a3sq_a5"): "Krushkal (Zalcman conjecture, n=3)",
                    ("starlike", "log_gamma2"): "|γₙ| ≤ 1/n for S* (classical)",
                    ("starlike", "inv_a3"): "Reduces to Fekete–Szegő (μ=2); |A₃| ≤ 5 sharp for S*",
                    ("starlike", "zalcman_a2a3_a4"): "Generalized Zalcman, Ravichandran–Verma 2016",
                    ("starlike", "zalcman_a2a4_a5"): "Generalized Zalcman, Ravichandran–Verma 2016",
                    ("lemniscate", "hankel3_1"): "Banga & Sivaprasad Kumar 2020 (Math. Slovaca; #294)",
                    ("lemniscate", "zalcman_a3sq_a5"): "Banga & Sivaprasad Kumar 2020 (Math. Slovaca; #294)",
                    ("lemniscate", "hankel2_2"): "Lee, Ravichandran & Supramaniam 2013 (#455)",
                    ("sigmoid", "hankel2_2"): "Riaz, Raza & Thomas 2022 (Forum Math.)",
                    ("bean_tanh", "hankel2_2"): "Kumar & Verma 2025 (Filomat)",
                }.items()
            )
        ],
        "lemmas": {
            "schur-onto-coefficient-body": {
                "title": "Schur parametrisation is exact",
                "plain": "The Schur recursion maps the closed polydisc exactly onto the "
                         "admissible coefficient vectors of the class. Ranging the Schur "
                         "parameters over the polydisc sweeps every member's coefficients.",
                "cite": "Schur 1917; Foias–Frazho; Simon, OPUC.",
            },
            "rotation-reduction": {
                "title": "Rotation normalisation",
                "plain": "The functional is weight-homogeneous under rotation, so its maximum "
                         "is attained on the rotation-normalised slice (gamma_0 >= 0 real).",
                "cite": "Elementary weight homogeneity.",
            },
            "ieee754-forward-error": {
                "title": "Floating-point arithmetic is sound",
                "plain": "Every float64 operation in the interval evaluation is widened by its "
                         "IEEE-754 forward-error bound, so each computed interval rigorously "
                         "encloses the true real value.",
                "cite": "IEEE-754 rounding; standard interval arithmetic.",
            },
            "bisection-partition": {
                "title": "The box partition is complete",
                "plain": "Boxes are bisected at exactly representable midpoints; the union of "
                         "the certified leaf boxes is provably the entire domain.",
                "cite": "Exact dyadic subdivision.",
            },
            "extremal-second-variation": {
                "title": "The constant is sharp at the extremal",
                "plain": "At the recognised extremal Schur parameters the functional is a strict "
                         "local maximum and the certified upper bound equals that attained value.",
                "cite": "Local second-variation at the attaining member.",
            },
            "fekete-szego-single-harmonic": {
                "title": "Sharp in closed form (single-harmonic reduction)",
                "plain": "For the Fekete–Szegő functional the reduced problem has one free angle "
                         "and the functional is affine in it, so its maximum is |A| + |C| exactly.",
                "cite": "Keogh & Merkes (1969), single-angle Schur reduction.",
            },
        },
    }

    # ── 8. references.md ────────────────────────────────────────────────────
    references_text = (proofs_dir / "REFERENCES.md").read_text(encoding="utf-8")
    references_text = (
        "# References for the machine-certification method\n\n"
        "*Versioned companion of the Geometric Function Atlas website document "
        "`data/proofs/REFERENCES.md` at source commit "
        f"{_source_commit(source)}. All citations were verified by the website "
        "authors to a DOI / publisher / arXiv record; the package ships the "
        "document unchanged except for this header.*\n\n"
        + references_text.split("---", 1)[-1]
    )

    # ── write everything ────────────────────────────────────────────────────
    data_dir = PACKAGE_DATA
    data_dir.mkdir(parents=True, exist_ok=True)
    payloads = {
        "classes.json": {"schema_version": SCHEMA_VERSION, "classes": classes_payload},
        "expansions.json": {"schema_version": SCHEMA_VERSION, "classes": expansion_classes},
        "bounds.json": {"schema_version": SCHEMA_VERSION, "classes": bounds_classes},
        "certificates.json": {"schema_version": SCHEMA_VERSION, "certificates": cert_payload},
        "open_problems.json": {
            "schema_version": SCHEMA_VERSION,
            "enclosures": enclosures,
            "conjectures": conjectures,
        },
        "reconciliation.json": {
            "schema_version": SCHEMA_VERSION,
            "counts": counts,
            "rows": rows,
        },
        "proof_meta.json": {"schema_version": SCHEMA_VERSION, **proof_meta},
        "references.md": references_text,
    }
    for name, payload in payloads.items():
        if name.endswith(".md"):
            (data_dir / name).write_text(payload, encoding="utf-8")
        else:
            _write_json(data_dir, name, payload)

    manifest_files: dict[str, dict] = {}
    for name in payloads:
        path = data_dir / name
        manifest_files[name] = {
            "sha256": _sha256(path),
            "schema_version": SCHEMA_VERSION,
        }
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "artifact_version": ARTIFACT_VERSION,
        "snapshot_date": SNAPSHOT_DATE,
        "source_repo": "gft-registry",
        "source_commit": _source_commit(source),
        "recipe": "scripts/bake_artifacts.py",
        "files": manifest_files,
    }
    _write_json(data_dir, "manifest.json", manifest)
    print(f"\nbaked {len(payloads)} artifacts into {data_dir}")
    print(f"certificates: {len(cert_payload)}  enclosures: {len(enclosures)}  "
          f"conjectures: {len(conjectures)}  reconciliation rows: {len(rows)}")
    return 0


def _source_commit(source: Path) -> str:
    import subprocess

    result = subprocess.run(
        ["git", "-C", str(source), "rev-parse", "HEAD"],
        capture_output=True, text=True, check=False,
    )
    if result.returncode != 0:
        print("cannot determine source commit", file=sys.stderr)
        return "unknown"
    return result.stdout.strip()


if __name__ == "__main__":
    raise SystemExit(main())

"""Classify the unfinished directed radius questions in the Atlas by where the
source image first meets the target boundary.

Reproduces the counts used in Section 6 (Table 4) of the Experimental
Mathematics paper. Input comes from the installed package's radius snapshot.
With no arguments the script runs `gfa radii --json` and
`gfa artifact-classes --json` itself; saved copies can be passed instead:

    python examples/em_paper/contact_classification.py [radii.json classes.json]

Checks, for every nontrivial record:
  1. contact mode (real axis vs interior/off-axis), from the stored touch data;
  2. for real-axis records, whether the stored radius equals
        R = min{ r in (0,1): phi1(r) = phi2(1) } U { r: phi1(-r) = phi2(-1) }
     (tolerance 1e-6);
  3. for real-axis records, the sign pattern of the first N Taylor coefficients
     of psi = phi2^{-1} o phi1, adjusted to the contact side: a single sign means
     the majorant bound of Lemma 4.1 is exact at the contact point (evidence
     only; it is not a proof for all orders);
  4. for off-axis records, whether the axis formula happens to give the value.

The alias class janowski_A0_B-1 (= order_0.5) is merged: rows that involve it
are dropped, leaving 650 distinct directed questions, as in the package's
alias/self-pair accounting (data/radius_scope_2026_09_27.json). Records proved
in the paper (status paper_proved_exact) are counted separately.
"""
import argparse
import collections
import json
import math

import sympy as sp
from _gfa import gfa_json
from mpmath import mp, mpf, taylor

mp.dps = 40
N = 22  # Taylor order tested
TOL_RADIUS = 1e-6
ALIASES = {"janowski_A0_B-1"}


def load(radii_path=None, classes_path=None):
    radii = gfa_json(radii_path, "radii")
    classes = {r["key"]: r for r in gfa_json(classes_path, "artifact-classes")["record"]["rows"]}
    z = sp.symbols("z")
    funcs = {
        k: sp.lambdify(z, sp.sympify(r["phi_formula"].replace("^", "**"),
                                     locals={"z": z, "E": sp.E}), "mpmath")
        for k, r in classes.items()
    }
    return radii, funcs


def real_value(f, x):
    try:
        v = complex(f(mpf(x)))
    except Exception:  # noqa: BLE001  (a branch cut or pole means "no real value")
        return None
    return v.real if abs(v.imag) < 1e-12 else None


def solve_on_axis(f, target, sign):
    """Smallest r in (0,1) with f(sign*r) = target, by bisection; None if no crossing."""
    if target is None or not math.isfinite(target):
        return None
    lo, hi = mpf("1e-12"), mpf(1) - mpf("1e-9")
    glo, ghi = real_value(f, sign * lo), real_value(f, sign * hi)
    if glo is None or ghi is None or (glo - target) * (ghi - target) > 0:
        return None
    flo = glo - target
    for _ in range(120):
        mid = (lo + hi) / 2
        gm = real_value(f, sign * mid)
        if gm is None:
            return None
        if (gm - target) * flo > 0:
            lo, flo = mid, gm - target
        else:
            hi = mid
    return float((lo + hi) / 2)


def mul(a, b):
    c = [mpf(0)] * (N + 1)
    for i, x in enumerate(a):
        if x:
            for j, y in enumerate(b[: N + 1 - i]):
                c[i + j] += x * y
    return c


def compose(outer, inner):
    res, power = [mpf(0)] * (N + 1), [mpf(1)] + [mpf(0)] * N
    for k, a in enumerate(outer):
        if k:
            power = mul(power, inner)
        res = [r + a * q for r, q in zip(res, power)]
    return res


def revert(a):
    b = [mpf(0), 1 / a[1]] + [mpf(0)] * (N - 1)
    for n in range(2, N + 1):
        b[n] -= compose(a, b)[n] / a[1]
    return b


def main(radii_path=None, classes_path=None):
    radii, funcs = load(radii_path, classes_path)
    series, inverses = {}, {}
    counts = collections.Counter()
    for rec in radii:
        if rec["inner"] in ALIASES or rec["target"] in ALIASES:
            continue
        counts["canonical_questions"] += 1
        status = rec["status"]
        if status in ("trivial_containment", "audit_required", "paper_proved_exact"):
            counts[status] += 1
            continue
        on_axis = rec.get("mode") in ("axis", "axis_bisect")
        group = "real_axis" if on_axis else "off_axis"
        counts[(group, "total")] += 1
        counts[(group, status)] += 1
        f1, f2 = funcs[rec["inner"]], funcs[rec["target"]]
        edge = mpf(1) - mpf("1e-15")
        roots = [r for r in (solve_on_axis(f1, real_value(f2, edge), 1),
                             solve_on_axis(f1, real_value(f2, -edge), -1)) if r is not None]
        predicted = min(roots) if roots else 1.0
        counts[(group, "formula_matches" if abs(predicted - float(rec["value_float"])) < TOL_RADIUS
                else "formula_mismatch")] += 1
        if not on_axis:
            continue
        for key in (rec["inner"], rec["target"]):
            if key not in series:
                series[key] = [mpf(c) for c in taylor(funcs[key], mpf(0), N)]
        if rec["target"] not in inverses:
            inverses[rec["target"]] = revert([mpf(0)] + series[rec["target"]][1:])
        psi = compose(inverses[rec["target"]], [mpf(0)] + series[rec["inner"]][1:])
        angle = abs(float(rec.get("touch_angle") or 0.0)) % (2 * math.pi)
        minus_side = abs(angle - math.pi) < 1e-6
        coeffs = [psi[n] * ((-1) ** n if minus_side else 1) for n in range(1, N + 1)]
        tol = mpf(10) ** -25
        single_sign = all(c >= -tol for c in coeffs) or all(c <= tol for c in coeffs)
        counts[("real_axis", "single_sign" if single_sign else "mixed_sign")] += 1
    out = {f"{k[0]}:{k[1]}" if isinstance(k, tuple) else k: v for k, v in sorted(counts.items(), key=str)}
    out["taylor_order_tested"] = N
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("radii", nargs="?", help="saved `gfa radii --json` output (default: run gfa)")
    parser.add_argument("classes", nargs="?",
                        help="saved `gfa artifact-classes --json` output (default: run gfa)")
    args = parser.parse_args()
    main(args.radii, args.classes)

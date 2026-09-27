"""Reciprocal-pair statistics and Figure 1 (reciprocal_asymmetry.pdf) of the
Experimental Mathematics paper.

Input: `gfa radii --json` from the installed package's radius snapshot (run
automatically unless a saved copy is given with --radii). Counting rules
follow the package's alias/self-pair accounting
(data/radius_scope_2026_09_27.json): the alias class janowski_A0_B-1
(= order_0.5) is dropped; a record is eligible unless its status is
unidentified or audit_required; a reciprocal pair has both directions eligible
and is unequal when the stored decimal values differ; a radius is nontrivial
when it is below 1 - 1e-10.

    python examples/em_paper/reciprocal_figure.py [--radii radii.json] [--output fig.pdf]

The counts are always printed. The figure needs matplotlib and is skipped
with a message if matplotlib is not installed.
"""
import argparse
import collections
import json
import sys
import tempfile
from pathlib import Path

from _gfa import gfa_json

parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
parser.add_argument("--radii", help="saved `gfa radii --json` output (default: run gfa)")
parser.add_argument("--output", type=Path,
                    default=Path(tempfile.gettempdir()) / "gfa-em-paper" / "reciprocal_asymmetry.pdf")
args = parser.parse_args()

ALIASES = {"janowski_A0_B-1"}
radii = gfa_json(args.radii, "radii")
rows = {(r["inner"], r["target"]): r for r in radii
        if r["inner"] not in ALIASES and r["target"] not in ALIASES
        and r["status"] not in ("unidentified", "audit_required")}
pairs = [(a, b) for (a, b) in rows if a < b and (b, a) in rows]
unequal = [(a, b) for a, b in pairs
           if rows[(a, b)]["value_decimal"] != rows[(b, a)]["value_decimal"]]
nontrivial = [r for r in rows.values() if r["value_float"] < 1 - 1e-10]
groups = collections.Counter(r["value_decimal"] for r in nontrivial)
shared = [r for r in nontrivial if groups[r["value_decimal"]] > 1]
print(json.dumps({"eligible": len(rows), "reciprocal_pairs": len(pairs),
                  "reciprocal_unequal": len(unequal), "nontrivial": len(nontrivial),
                  "nontrivial_shared": len(shared),
                  "shared_groups": sum(1 for v in groups.values() if v > 1)}))

try:
    import matplotlib
except ImportError:
    print("matplotlib is not installed; skipping Figure 1")
    sys.exit(0)
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams.update({"font.family": "serif", "font.size": 8})
fig, ax = plt.subplots(figsize=(3.2, 3.2))
ax.plot([0, 1], [0, 1], "k--", lw=0.7)
for eq, style in ((False, {"marker": "o", "s": 7, "color": "#2F6F8F", "lw": 0}),
                  (True, {"marker": "D", "s": 22, "color": "#E0A33A", "edgecolor": "#555", "lw": 0.5})):
    pts = [sorted((rows[(a, b)]["value_float"], rows[(b, a)]["value_float"]))
           for a, b in pairs if ((a, b) in unequal) != eq]
    ax.scatter([p[0] for p in pts], [p[1] for p in pts], zorder=3,
               label=f"{'equal' if eq else 'unequal'} ({len(pts)})", **style)
x, y = sorted((rows[("crescent", "exponential")]["value_float"],
               rows[("exponential", "crescent")]["value_float"]))
ax.scatter([x], [y], s=40, facecolor="none", edgecolor="#A45542", lw=1, zorder=4)
ax.annotate("crescent / exponential:\n$\\sin 1$ vs $\\log(1+\\sqrt{2})$", (x, y),
            xytext=(0.03, 0.30), color="#A45542", fontsize=7,
            arrowprops={"arrowstyle": "-", "color": "#A45542", "lw": 0.6})
ax.set(xlim=(0, 1), ylim=(0, 1), xlabel="smaller radius of the pair",
       ylabel="larger radius of the pair", aspect="equal")
ax.grid(lw=0.3, alpha=0.5)
ax.legend(loc="lower right", frameon=False)
fig.tight_layout()
args.output.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(args.output)
print(f"Figure 1 written to {args.output}")

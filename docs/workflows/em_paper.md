# Reproducing the Experimental Mathematics paper

Three scripts in `examples/em_paper/` recompute the numbers in the
Experimental Mathematics paper on the Geometric Function Atlas: the interval
bounds in Theorem 4.8, the reciprocal-pair counts and Figure 1 in Section 2,
and the contact classification in Section 6 (Table 4).

## Before you start

Install `gfa` as described in [Getting started](../getting-started.md#install).
The scripts live in the source repository; set up a checkout as described in
[Before you run an example](README.md#before-you-run-an-example) and run the
commands below from its root directory.

The radius values and contact points used in the paper come from the package's
stored snapshot. `gfa radius <source> <target>` shows a single directed radius,
and `gfa radii --json` lists all of them. The two counting scripts read that
list by calling `gfa` themselves; contact classification also uses the installed
class catalog. Saved `radii.json` and `classes.json` can be supplied, but saved
class keys/formulas must exactly match the installed catalog and are never
parsed as executable expressions.

Of the 19 manuscript written-proof lanes, **eight** have bounded certificate
replay via `gfa verify-radius-certificate <source> <target>` (for example,
`sine -> sigmoid`); **two** reciprocal lanes have symbolic-identity-only replay
(`certified: false`, global containment not mechanized); the remaining **nine**
have no local replay. A written paper proof, a stored radius, and a successful
bounded replay are different kinds of evidence; none makes the whole manuscript
proof automatically machine-checked.

Two conventions are used in the counts:

- `janowski_A0_B-1` and `order_0.5` are two names for the same class, the
  starlike functions of order $1/2$. Every row that uses the first name is
  dropped so the same question is not counted twice.
- A *directed question* is an ordered pair (source class, target class) of
  different classes; the radius from $A$ to $B$ can differ from the radius
  from $B$ to $A$. With the alias removed, the radius list covers 650 of them.

## Theorem 4.8: interval bounds

This script checks specific interval inequalities used in the two Theorem 4.8
arguments with outward-rounded arithmetic (`mpmath.iv`):
(a) $\arcsin(3-2\sqrt2)$ for the sine source and (b) $\tfrac12\log 2$ for the
sigmoid source. In both cases the target is the rational class `rational_kr`.
It needs only `sympy` and `mpmath`, not the radius list. Its interval boxes
bound the paper's implicit boundary polynomial along the source circle and
its endpoint second derivative; the script also checks selected algebraic
identities and a radius enclosure. It does **not** mechanize the full theorem:
the correspondence between the polynomial sign and the target's correct
interior component, global containment, and sharpness rely on the written
geometric argument. The displayed boundary-extremum sample is numerical,
not an interval certificate.

```bash
uv run python examples/em_paper/thm48_interval_check.py
```

It takes about a minute. The summary at the end gives the certified lower
bounds, for (a) and (b) in turn:

```text
  sine     bulk lower bound 9.067e-6 | H'' single-box 0.01309 | H'' 50-box 0.01357
  sigmoid  bulk lower bound 8.306e-8 | H'' single-box 0.01332 | H'' 50-box 0.01332
```

Every reported interval lower bound is positive. These checks support the
specific polynomial inequalities, not the unmechanized geometric steps above.

## Section 2 and Figure 1: reciprocal pairs

A reciprocal pair is two classes $A$ and $B$ with a known radius in both
directions, $A\to B$ and $B\to A$. Rows whose value has not been identified,
and rows that fail a consistency check, are left out.

```bash
uv run --with matplotlib python examples/em_paper/reciprocal_figure.py
```

It takes a few seconds and prints

```text
{"eligible": 557, "reciprocal_pairs": 240, "reciprocal_unequal": 234,
 "nontrivial": 424, "nontrivial_shared": 148, "shared_groups": 42}
```

So 234 of the 240 reciprocal pairs have different radii in the two directions.
Of the 424 radii smaller than 1, 148 share their value with another radius,
in 42 groups of equal values. Figure 1 is saved to
`reciprocal_asymmetry.pdf` in your temporary directory; use `--output` to
choose another path. Without matplotlib (`uv run python ...`), the script
prints the counts and skips the figure.

## Section 6 and Table 4: contact classification

The remaining directed questions are those not proved in the paper, with a
radius below 1, and passing the package's consistency check. This script
groups them by the snapshot's stored contact mode (real axis or off axis); it
does **not** independently search for the first boundary contact or establish
that the stored contact realizes the global inclusion radius. It compares an
axis-root heuristic against stored values, without proving smallest-root or
global containment claims. For real-axis contacts, it also checks the signs of
the first 22 Taylor coefficients of $\psi=\phi_2^{-1}\circ\phi_1$, where
$\phi_1$ is the source generator and $\phi_2$ the target generator. When all
signs agree (after adjusting for the side of the contact), this is finite-order
evidence compatible with the majorant bound of Lemma 4.1 being exact at the
contact point; it does not prove the sign condition at all orders.

```bash
uv run python examples/em_paper/contact_classification.py
```

It takes a few seconds. The expected counts are:

| Group | Count |
|---|---|
| Directed questions | 650 |
| Proved in the paper | 19 |
| Target contains the source (radius 1) | 133 |
| Consistency check failed | 11 |
| Real-axis contact | 355 (273 touch equation proved, 76 closed form confirmed, 6 unidentified) |
| Real-axis, one Taylor sign / mixed signs | 315 / 40 |
| Off-axis contact | 132 (56 closed form confirmed, 76 unidentified) |

The JSON output uses the package's status names, for example
`real_axis:touch_proven_exact` and `audit_required`.

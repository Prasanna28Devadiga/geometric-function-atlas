# Directed radii

Browse immutable directed-radius records, inspect provenance, recompute supported
values, and replay or audit the evidence attached to a released row.

## Released radius data

The released dataset covers **28 catalog keys**: 756 possible non-diagonal
key directions, 702 stored records, and 54 missing key pairs. These are
alias-inclusive counts, not counts of distinct mathematical classes or
independent radius problems. In particular, `janowski_A0_B-1` and `order_0.5`
both define the exact same generator $1/(1-z)$; their two directed records
between each other are identity/containment rows, not distinct-class radius
problems. The 54 missing key pairs are all incoming directions to the
`nephroid` and `three_leaf` targets from other keys.

Identifying only that proven alias (without filling any missing rows) gives
27 distinct generator expressions, 702 original records mapping to 651
canonical ordered cells: one diagonal identity cell and 650 distinct
non-diagonal directed cells. Of those 650, 133 are stored trivial-containment
rows and 517 are nontrivial under the discovery input's `trivial == false`
predicate. This quotient is an **audit view**, not a replacement for the
released snapshot or a certification of those 517 radii. The package APIs
continue to expose the original keys, directions, statuses, and provenance.

Direction matters. For example,
`sine→sigmoid` has the exact value $\arcsin((e-1)/(e+1))$ with a local
certificate, while `sigmoid→sine` has radius $1$ by full containment.

The `radius_atlas.py` example exports all rows and columns as JSON and SVG for
data inspection. It is a view of the stored records, not a substitute for the
proof of any individual radius.

::: geometric_function_atlas.radii
    options:
      members_order: source
      show_root_heading: true
      show_source: false

# Directed radii

Browse immutable directed-radius records, inspect provenance, recompute supported
values, and replay or audit the evidence attached to a released row.

## Released radius data

The released dataset covers 28 classes: 756 possible non-diagonal directions,
702 stored records, and 54 missing pairs. Direction matters. For example,
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

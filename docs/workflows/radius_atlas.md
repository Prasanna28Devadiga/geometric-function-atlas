# Read the directed-radius atlas

**Problem.** A list of inclusion radii is hard to audit for direction, missing pairs, and evidence strength. A symmetric heatmap is worse: reversing source and target is generally a different mathematical problem.

Generate the deterministic atlas:

```sh
python examples/research_workflows/radius_atlas.py \
  --output /tmp/gfa-radius-atlas
```

The workflow writes `radius_atlas.json` and `radius_atlas.svg`. In the current immutable package snapshot there are 28 class labels, hence 756 possible non-diagonal directed pairs. The snapshot contains 702 records and leaves 54 directed pairs absent. The exporter includes every matrix cell and labels those 54 cells `missing_snapshot_row`; it does not invent a value or infer one from the reverse direction.

## Direction is mathematical data

The anchor pair makes the asymmetry visible:

- `sine→sigmoid` has exact value
  $\arcsin((e-1)/(e+1))$, status `touch_proven_exact`, and a bundled replay certificate;
- `sigmoid→sine` has value $1$, status `trivial_containment`, and no local replay certificate.

These entries are not interchangeable. JSON uses source rows and target columns, and each cell repeats its full `source->target` direction.

## Read the evidence colors

The SVG colors reproduce the snapshot's five evidence statuses:

- `touch_proven_exact`;
- `closed_form_confirmed`;
- `trivial_containment`;
- `unidentified`; and
- `audit_required`.

Gray cells are missing snapshot rows, and pale diagonal cells are not stored radius problems. A color is a compact status display, not a proof. Hovering a cell shows its direction, exact value when present, status label, and whether a local replay certificate exists.

Read the current `record_count` and `replayable_certificate_count` from the generated JSON. For the snapshot shipped with this release they are 702 and 8, respectively. Other exact-looking strings remain immutable snapshot data with their own evidence status; the atlas does not upgrade them. Use `verify_radius_certificate(source, target)` only on a reviewed certificate lane, and treat `not_replayable` as unavailable local evidence rather than artifact corruption.

## Use the JSON as a shortlist

`radius_atlas.json` records status counts, the 756-pair denominator, missing-pair count, certificate count, class order, and all 784 cells including the diagonal. Filter cells by `status == "audit_required"` or `status == "unidentified"` to form an investigation list. Reconcile sources and prove branch, containment, contact, and sharpness obligations before promoting any row.

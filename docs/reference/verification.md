# Function verification

Tiered verification for normalized analytic functions. Read each result's outcome,
checks, and assumptions; numerical screens are not silently promoted to proofs.

`gfa verify --json` and `verify_function(...).to_dict()` emit a closed analysis
record validated by the packaged `schema/verify-result.schema.json` (load with
`geometric_function_atlas.records.load_verify_result_schema`). It is not an
exact-result envelope and must not be passed to `result.schema.json`.
`canonical_inputs.truncation` distinguishes a supplied whole polynomial from
an unknown-tail truncation. Grid radii must be at least 0.05 and strictly
below 1; no certified witness outside the open unit disk is admitted.

::: geometric_function_atlas.verify
    options:
      members_order: source
      show_root_heading: true
      show_source: false

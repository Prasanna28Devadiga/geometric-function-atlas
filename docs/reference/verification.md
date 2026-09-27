# Function verification

Tiered verification for normalized analytic functions. Read each result's outcome,
checks, and assumptions; numerical screens are not silently promoted to proofs.

`gfa verify --json` and `verify_function(...).to_dict()` emit a closed analysis
record whose JSON shape and tier constraints are checked by the packaged
`schema/verify-result.schema.json` (load with
`geometric_function_atlas.records.load_verify_result_schema`). JSON Schema
Draft 2020-12 bounds each point coordinate to (-1, 1), but **does not prove**
`x*x + y*y < 1`: `[0.9, 0.9]` passes the schema. Consumers must also call
`geometric_function_atlas.records.validate_screen_record(record)` on parsed
records before trusting `details.witness_point` or `details.worst_point` as
inside the open unit disk. The Python validator enforces that geometric check;
the schema alone is not a geometric certificate. This is not an
exact-result envelope and must not be passed to `result.schema.json`.
`canonical_inputs.truncation` distinguishes a supplied whole polynomial from
an unknown-tail truncation. Grid radii must be at least 0.05 and strictly
below 1; no certified witness outside the open unit disk is admitted.

`canonical_inputs.closed_form_srepr` is required: `null` for coefficient
sequences (including the CLI, which accepts only `--coefficients`), or the
exact SymPy `srepr` of the preconstructed Python `closed_form` expression.
The first 39 Taylor coefficients of a nonpolynomial expression are only a
finite projection; this field preserves the full supplied expression's
structural identity, including a tail beyond that projection. It is bounded
to 65,536 characters; larger expressions fail with `ResourceLimitError`
before series expansion. A DAG-aware preflight rejects expressions whose conservative
expanded-size bound exceeds the limit, deeply nested expressions, and
unsupported/custom printers before calling `srepr`; a small representation
can therefore be rejected when its bound is too conservative. The final
length check still enforces the exact cap for accepted inputs. Treat the
string as inert data, never pass it to
`eval` or a parser. SymPy's printed representation may change between SymPy
versions, so pin the version for cross-run textual comparisons. This is not
a proof that two syntactically different expressions define different
mathematical functions.

::: geometric_function_atlas.verify
    options:
      members_order: source
      show_root_heading: true
      show_source: false

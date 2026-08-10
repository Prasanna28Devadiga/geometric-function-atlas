# Evidence and provenance policy

## Claim boundary

A returned number is not enough. Structured result objects and CLI records identify:

1. the canonical mathematical problem;
2. exact inputs and formulas;
3. the algorithm or theorem used;
4. declared assumptions;
5. evidence status;
6. source references;
7. package and artifact versions;
8. whether any literature-novelty claim is being made.

The versioned schema and fail-closed check semantics are specified in
`docs/RESULT_CONTRACT.md`; the shipped JSON schemas are under
`src/geometric_function_atlas/schema/`.

Low-level exact helpers may return bare SymPy expressions or tuples for use in
other symbolic programs. Their structured counterparts (`generator_series`,
the theorem result objects, and CLI JSON) carry the full record above.

## Evidence statuses

The package will use explicit, non-overlapping statuses:

- `screened`: numerical evidence only;
- `certified_enclosure`: a machine-checkable interval containing the sharp value;
- `proven_exact_under_declared_assumptions`: exact theorem or certificate with stated assumptions;
- `disproven`: certified counterexample or contradiction to the computational proposition;
- `unresolved`: no conclusive computation.

Literature reconciliation is a separate taxonomy. A computationally proven result may be known, a candidate improvement, absent from the indexed corpus, or still under human review. “No indexed match” is never emitted as “novel.”

## Built-in and custom generators

Built-in formulas and citations are versioned package data. Exact coefficient
operations also accept custom generators as preconstructed SymPy expressions.
String expressions are rejected because SymPy's general string parser is
eval-based; undeclared free symbols are rejected as well. For a custom generator,
the package checks only the algebraic preconditions documented by the operation;
it does not silently certify all analytic Ma–Minda admissibility hypotheses.
Structured records mark this input as `provenance: "caller_supplied"` and retain
the caller-supplied source/fixture identity explicitly; they never relabel it as
the built-in catalog.

CLI rational parameters use a bounded signed-integer or `integer/integer`
grammar. Exponent notation is intentionally unsupported, and rational
components are capped before symbolic arithmetic begins.

## Migration from the research artifact

The original registry repository is treated as a research artifact and source of candidate algorithms/data. Code is not copied wholesale. Each migrated operation receives:

- a minimal public interface;
- independent anchor tests;
- explicit path and data injection;
- no Flask, deployment, OCR, or private-review dependency;
- a provenance note naming the originating artifact and the audit performed;
- clean wheel/sdist installation verification.

# Reproducibility roadmap

The package is developed as vertical, independently testable slices. A phase is complete only when its public API, CLI, provenance schema, wheel/sdist contents, anchors, and clean-install tests pass.

Across the phases, public operations converge on a small typed model layer:
`Generator`, `CoefficientProblem`, `RadiusProblem`, `EvidenceState`, `Certificate`,
and `LiteratureVerdict`. Canonical problem identity preserves direction,
normalization, functional parameters, claim type, and provenance. JSON schemas and
CLI exit codes are versioned public contracts; internal expression-DAG nodes and
search implementation details are not.

## Phase 1 — exact generator and Fekete–Szegő operations

Status: implemented in 0.1.0.

- Immutable generator definitions with bibliographic provenance.
- Exact Taylor coefficients `B_1, …, B_n`.
- Exact Ma–Minda Fekete–Szegő constants under declared assumptions.
- Classical starlike anchors and JSON-capable CLI.

The initial built-in catalog contains the generators needed by the paper’s ten-result radius portfolio plus the classical starlike control. The complete 36-class paper snapshot will be migrated only after each formula and citation is checked.

## Phase 2 — sharp inclusion-radius certificate replay

- Stable source/target problem identity.
- Exact candidate parsing and numerical localization.
- Replay of inverse-composition and positive-majorant proofs.
- Symbolic boundary-contact and global-axis certificate checks.
- The ten paper portfolio as immutable versioned fixtures.
- One command that actually replays all ten global proofs rather than checking
  only their baked table/manifest consistency.
- The reciprocal crescent/exponential pair and selected additional positive and
  negative anchors.
- Known positive and negative anchors.

## Phase 3 — coefficient certificate replay

- Versioned certificate schema independent of repository paths.
- DAG expression parser and interval evaluator.
- Fekete–Szegő, logarithmic, inverse, Hankel, and Zalcman functionals.
- Exact general-theorem hypothesis checks, the 11-row `H_2(2)` landscape, and
  its negative anchor.
- Explicit distinction between attained lower bounds, certified enclosures, and proven-exact values.
- Resource limits and resumable verification for expensive certificates.

## Phase 4 — registry snapshots and reconciliation

- Downloadable, checksummed registry snapshots rather than a mutable bundled database.
- Schema validation, an archive-wide integrity manifest, and immutable snapshot identity.
- Deterministic joins between computations and extracted literature claims.
- Typed verdicts: known general, specific known, candidate improvement, contradiction, no extracted claim, unresolved.
- No automated novelty declaration.

## Phase 5 — paper-level reproduction

- One command reproduces every lightweight quantitative table and figure input.
- Optional plotting support regenerates all eight paper figures strictly from
  regenerated reports rather than embedded counts.
- A manifest identifies operations requiring expensive computation, external literature access, or human review.
- Environment and artifact hashes are recorded in the output.
- Machine-readable and human-readable reports share one result model.

## Phase 6 — publication and long-term hosting

Recommended public stack:

- source and issue tracking: GitHub;
- Python releases: PyPI;
- immutable research releases and DOI: Zenodo linked to GitHub releases;
- API documentation: Read the Docs or GitHub Pages;
- large registry snapshots: Zenodo release assets or an S3-compatible object store with checksums;
- live registry: separately deployable web frontend/API consuming a versioned public snapshot.

The Python package must remain useful without the live website. The website must display the package and snapshot versions used for every computed claim.

## Deliberately excluded from the reusable package

OCR, OpenAlex/arXiv harvesting, metadata cleanup, literature-PDF storage,
review-ledger mutation, usefulness/expert sign-off, reviewer-deck generation,
submission packaging, site baking, and deployment remain repository or service
operations. The package may contain a pure deterministic comparator for structured
claims, but it must not perform editorial decisions or automatically declare
literature novelty.

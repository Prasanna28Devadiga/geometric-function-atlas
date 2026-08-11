# Capability inventory

The package is developed as vertical, independently testable slices. A capability
is complete only when its public API, CLI, provenance schema, wheel/sdist
contents, anchors, and clean-install tests pass.

Public operations converge on a small typed model layer: `Generator`,
`CoefficientProblem`, `RadiusProblem`, `EvidenceState`, `Certificate`, and
`LiteratureVerdict`. Canonical problem identity preserves direction,
normalization, functional parameters, claim type, and provenance. JSON schemas
and CLI exit codes are versioned public contracts; internal expression-DAG
nodes and search implementation details are not.

## Exact generator and Fekete–Szegő operations

Status: shipped.

- Immutable generator definitions with bibliographic provenance (39 built-in
  Ma–Minda generators).
- Exact Taylor coefficients `B_1, …, B_n` via `generator_series`.
- Exact Ma–Minda Fekete–Szegő constants under declared assumptions via
  `fekete_szego`.
- Classical starlike anchors and JSON-capable CLI.

## Function verification, class screens, and witness replay

Status: shipped.

- Tiered verification (`screen` / `symbolic` / `rigorous`) of normalized
  functions from coefficients or preconstructed SymPy closed forms.
  Numerical screens are never presented as proofs.
- Ma–Minda class operations: admissibility checks, membership screens,
  containment screens, and exact extremal coefficients. Screens are labelled
  as screens unless a certified theorem is attached.
- Counterexample witness replay and grid-search-plus-interval-certification
  via `verify_counterexample` and `find_counterexample`.

## Plot reproduction

Status: shipped.

- Dependency-free SVG plots: conformal domain grids, coefficient magnitudes,
  real-part heatmaps, and phase portraits, from built-in generators or custom
  coefficients. Plots visualize a finite Taylor polynomial; they are not
  proofs of the full image domain.

## Optional application labs

Status: shipped behind the `lab` extra (NumPy).

- Cryptography Lab: S-box construction and benchmark metrics (bijection,
  nonlinearity, SAC, BIC, differential uniformity, linear probability) with
  deterministic AES and identity anchors. Crypto outputs are benchmark
  metrics, never security claims.
- Image Lab: full-reference quality metrics (MSE, RMSE, MAE, PSNR, PCC, SSIM,
  GMSD) and convolution transforms (smooth, sharpen, edge) on deterministic
  generated arrays. Image outputs are empirical.

## Registry snapshots and reconciliation

Planned. The registry database is a separately versioned snapshot with
schemas and checksums; snapshot selection and integrity checks are internal.
Typed verdicts (known general, specific known, candidate improvement,
contradiction, no extracted claim, unresolved) will be separate from
computational evidence, and no automated novelty declaration will be emitted.

## Paper-level reproduction

Planned. A future command will reproduce every lightweight quantitative table
and figure input, with a manifest identifying operations that require
expensive computation, external literature access, or human review.

## Publication and long-term hosting

Recommended public stack:

- source and issue tracking: GitHub;
- Python releases: PyPI;
- immutable research releases and DOI: Zenodo linked to GitHub releases;
- API documentation: Read the Docs or GitHub Pages;
- large registry snapshots: Zenodo release assets or an S3-compatible object
  store with checksums;
- live registry: separately deployable web frontend/API consuming a versioned
  public snapshot.

The Python package must remain useful without the live website. The website
must display the package and snapshot versions used for every computed claim.

## Deliberately excluded from the reusable package

OCR, OpenAlex/arXiv harvesting, metadata cleanup, literature-PDF storage,
review-ledger mutation, usefulness/expert sign-off, reviewer-deck generation,
submission packaging, site baking, and deployment remain repository or service
operations. The package may contain a pure deterministic comparator for
structured claims, but it must not perform editorial decisions or
automatically declare literature novelty.

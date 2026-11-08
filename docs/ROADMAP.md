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

- Immutable generator definitions with bibliographic provenance (39 catalog keys, 38 distinct generator formulas).
  `janowski_A0_B-1` and `order_0.5` are the same exact function `1/(1-z)`;
  keep both public keys for compatibility and historical source locators.
- Exact Taylor coefficients `B_1, …, B_n` via `generator_series`.
- Exact Ma–Minda Fekete–Szegő constants under declared assumptions via
  `fekete_szego`.
- Bounded low-level exact convex member jets via Alexander + the existing real
  Schur recurrence, and signed inverse logarithmic coefficients through Gamma4.
  Exact linear subordinations (1-alpha)f/z+alpha*f'=phi(omega), including
  bounded turning, and ordinary logarithms through gamma4 use the same engine.
  Formal inverse jets through A5 and Schippers sigma3/sigma4 at the origin
  have independent composition/differential anchors; disk norms remain out of scope.
  `schwarzian_derivative_origin` supplies the ordinary S_f'(0), distinct from
  Schippers sigma4(0), with an independent generic differential identity test.
  - `mixed_derivative_coefficients`: nonlinear derivative/convex interpolation,
    distinct from the linear class; `product_subordination_coefficients`:
    exact normalized base times phi(omega). Both reuse real Schur composition,
    return bounded jets only, and have direct equation/product anchors.
  - `ruscheweyh_coefficients`: apply/undo integer-degree0..64 binomial
    multipliers on exact a2..a9 jets; independent derivative-definition anchors.
  - `bernardi_coefficients`: normalized integral multiplier (gamma+1)/(gamma+n),
    gamma rational>=0; `q_al_oboudi_coefficients`: integer-lam1..64
    [1+(n-1)*lam]_q**degree multipliers, degree0..64, exact rational0<q<=1.
    Both apply/undo bounded exact jets a2..a9, not functional inversion or
    a global preservation theorem; independent ODE/integral/Jackson anchors.
  These API-only transforms return bare SymPy tuples; no new theorem/evidence
  envelope or automatic sharp-bound claim is introduced.
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

Status: shipped as a user-supplied snapshot boundary. The registry database is
not bundled in the wheel and this package does not currently publish a
canonical snapshot URL. Users install a database plus matching manifest with
`gfa snapshot install SOURCE DESTINATION --manifest MANIFEST`; the manifest
records hashes, populations, and an optional HTTPS `source_url`. Snapshot
selection and integrity checks are local and fail closed. Typed verdicts
(known general, specific known, candidate improvement, contradiction, no
extracted claim, unresolved) remain separate from computational evidence, and
no automated novelty declaration is emitted.

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

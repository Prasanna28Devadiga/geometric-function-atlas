# Package coverage

The Python package is the local reproduction layer for the Geometric Function Atlas. Public work is organized by mathematical operation rather than internal release planning.

A website operation belongs in the package when it has:

1. a short, copyable `gfa` command;
2. a typed Python function;
3. an honest evidence label;
4. a parity fixture against a named website or research snapshot;
5. versioned machine-readable output when the operation returns a scientific claim.

## Shipped operations

- Built-in Ma–Minda generator catalog with citations.
- Exact generator Taylor coefficients.
- Exact Ma–Minda Fekete–Szegő constants under declared assumptions.
- Interval-certified re-evaluation of supplied starlikeness, Becker, and Nehari witnesses.
- Standalone SVG conformal-grid plots for named generators and supplied normalized polynomials.
- Closed result/error contracts with exact expressions, verification checks, and provenance.

## Website operations outside current package coverage

- Function-family and alias search.
- Facts, instances, evidence, and verification-run inspection.
- Stored coefficient bounds and Schur-parameter expansions.
- Directed inclusion-radius lookup and certificate replay.
- Stored proof and coefficient-certificate replay.
- Class comparisons, hierarchy, and application cross-tabs.
- Paper and reconciliation-record inspection.
- Image Lab transformations and metrics.
- Cryptography Lab benchmark inspection and metric recomputation.
- Versioned registry-snapshot statistics.

The source website remains the visual interface while an operation is being migrated. A package command must not merely expose an internal row ID or replay an unverified baked value: it must preserve the operation's direction, assumptions, evidence state, and source snapshot.

## Data boundaries

The mutable SQLite registry is not silently embedded in the wheel. Registry-backed operations use an explicitly versioned, checksummed snapshot, while lightweight immutable fixtures required for a computation may ship with the package.

OCR, literature harvesting, metadata cleanup, editorial review, novelty decisions, site baking, and deployment are research-workspace operations rather than end-user package commands. The package can compare structured claims, but it does not automatically declare mathematical novelty.

## Publication and durability

- Source and issue tracking: GitHub.
- Python releases: PyPI through credential-free Trusted Publishing.
- Immutable research artifacts and registry snapshots: independently versioned releases with checksums.
- Live visual atlas: the separately deployed website consuming a named public snapshot.

The package must remain useful without the live website. The website should identify the package and snapshot versions used for each reproducible computation.

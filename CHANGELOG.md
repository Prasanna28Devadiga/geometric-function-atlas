# Changelog

All notable changes to Geometric Function Atlas are recorded here.

## 0.2.0 — 2026-08-11

### Added

- Tiered function verification (`screen` / `symbolic` / `rigorous`) for
  normalized functions from coefficients or preconstructed SymPy closed
  forms, with explicit epistemic labels that never present a numerical
  screen as a proof.
- Ma–Minda class operations: admissibility checks, membership screens,
  containment screens, and exact extremal coefficients. Screens are labelled
  as screens unless a certified theorem is attached.
- Counterexample witness search: grid search locates a candidate violation
  and interval arithmetic certifies the final point.
- Website plot reproduction as dependency-free SVG: conformal domain grids,
  coefficient magnitudes, real-part heatmaps, and phase portraits.
- Optional application labs behind the `lab` extra: Cryptography Lab S-box
  construction and benchmark metrics with deterministic AES and identity
  anchors, and Image Lab quality metrics and convolution transforms on
  deterministic generated arrays. Crypto outputs are benchmark metrics,
  never security claims; image outputs are empirical.
- `lab` extra and CI coverage for the optional labs.
- Python 3.10-compatible typing in the snapshot module and neutral-install
  checks for the public CLI.
- Certificate replay records that distinguish artifact lookup, candidate
  attainment, upper-bound consistency/certification, and independently proven
  sharpness. Non-sharp source records remain `certified_enclosure`.
- Citation-aware paper facets (`journal`, `doi`, `citation`) and optional
  acquisition URLs preserved in snapshot manifests.
- Valid 3x3, 5x5, and 7x7 image-lab tap handling and XML-valid SVG metadata.

## 0.1.1 — 2026-08-10

Contract-integrity repair release.

### Fixed

- The shipped Draft 2020-12 result schema now couples exact-result evidence,
  computational, verification, and failure states as strictly as the Python
  validator.
- The public counterexample API rejects strings, bytes, mappings, sets, and
  other non-sequence coefficient containers instead of coercing them.

## 0.1.0 — 2026-08-10

First software release.

### Included

- Exact Taylor coefficients for the built-in Ma–Minda generator catalog.
- Exact Ma–Minda Fekete–Szegő constants under declared assumptions.
- Certified interval re-evaluation of supplied starlikeness, Becker, and Nehari
  witnesses without claiming global counterexample discovery.
- Human-readable `gfa` commands with optional versioned JSON output.
- Closed result, verification, provenance, and failure contracts.
- Python-free installation through `uv` on macOS, Linux, and Windows.
- Distribution, clean-install, managed-Python, Linux, and Windows release gates.

### Scope

This release does not include registry search, radius-certificate replay,
mutable registry data, literature novelty decisions, or PyPI publication.
Plots, the application labs, and the remaining website capabilities were
added after this release.

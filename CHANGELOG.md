# Changelog

All notable changes to Geometric Function Atlas are recorded here.

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

This release does not include registry search, radius-certificate replay, plots,
image or cryptography labs, mutable registry data, literature novelty decisions,
or PyPI publication. Those remain separate future phases.

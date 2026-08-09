# Releasing `geometric-function-atlas`

This document describes the release path. Creating the public source repository
and preparing release automation are separate from publishing a package or a
registry snapshot. Do not publish either artifact until the scientific scope,
provenance records, and clean-install checks are ready.

## Software release

1. Start from a clean `main` checkout and inspect the complete staged diff.
2. Update `src/geometric_function_atlas/version.py`, `CITATION.cff`, and the
   changelog/release notes together. The package version and registry snapshot
   version are independent.
3. Run the local gate:

   ```bash
   python -m pip install -e '.[test,build]'
   python -m ruff check src tests scripts
   python -m mypy src --ignore-missing-imports
   python -W error -m pytest -q
   rm -rf dist build
   python -m build
   python -m twine check dist/*
   python scripts/check_distribution.py dist
   ```

4. Install both the wheel and sdist in fresh virtual environments from a
   directory outside the repository. Exercise the Python API, `python -m
   geometric_function_atlas`, and the `geometric-function-atlas` console entry
   point.
5. Commit the verified version change and create a signed/tagged `vX.Y.Z`
   release only after CI is green.
6. GitHub Actions publishes to PyPI through Trusted Publishing. Configure the
   PyPI project and its `pypi` environment/trusted publisher once; do not store
   a PyPI token in the repository.
7. Create the GitHub release from the tag and attach human-readable notes. The
   DOI/archive record should be made through the connected Zenodo integration.

## Registry-data release

Registry snapshots are not bundled into the Python wheel. Each snapshot gets an
independent tag such as `registry-YYYY.MM.DD` and must include:

- a transactionally consistent SQLite file;
- a schema dump;
- a machine-readable manifest with source commit, snapshot date, row counts,
  checksums, and population definitions;
- SHA-256 sums for every asset;
- `PRAGMA quick_check` and `PRAGMA integrity_check` results.

The manifest must identify the exact package version and source snapshot used by
paper tables or figures. A changing living-atlas count is expected across
releases; reproducibility means naming and checksumming the snapshot used, not
freezing all future counts.

## Before the first public release

- [ ] Complete the radius and coefficient certificate-replay APIs.
- [ ] Add immutable paper-reproduction fixtures and their provenance records.
- [ ] Decide which registry data can be redistributed and document its license.
- [ ] Configure GitHub branch protection, issue templates, and CI status checks.
- [ ] Configure PyPI Trusted Publishing and Zenodo only after the source tree is
      public and the release candidate has passed clean-install verification.
- [ ] Have an independent reviewer inspect the final staged diff and archive
      contents.
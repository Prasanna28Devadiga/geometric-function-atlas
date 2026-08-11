# Releasing `geometric-function-atlas`

This is the maintained release procedure. The first GitHub software release is
separate from PyPI publication and from versioned registry-data snapshots.

## Free-tier GitHub policy

The repository is public. CI uses only standard `ubuntu-24.04` and
`windows-2025` GitHub-hosted runners, which GitHub documents as free for public
repositories. The workflow does not use larger runners, Actions artifact uploads,
or persistent Actions caches. Release files are attached directly to the GitHub
release; GitHub documents no total release-size or bandwidth limit, subject to a
2 GiB limit per asset.

Do not add larger runners, paid products, or persistent Actions storage without
explicit approval from the repository owner.

## Software release

1. Start from a clean `main` checkout.
2. Update `src/geometric_function_atlas/version.py`, `CITATION.cff`, and
   `CHANGELOG.md` together.
3. Run the local gate:

   ```bash
   uv sync --extra test --extra build --locked
   uv run --frozen --extra test python -m ruff check src tests scripts
   uv run --frozen --extra test python -m mypy src --ignore-missing-imports
   uv run --frozen --extra test python -W error -m pytest -q
   rm -rf dist build
   uv run --frozen --extra build python -m build
   uv run --frozen --extra build python -m twine check dist/*
   uv run --frozen python scripts/check_distribution.py dist
   uv run --frozen python scripts/check_clean_install.py \
     dist/geometric_function_atlas-0.2.0-py3-none-any.whl
   uv run --frozen python scripts/check_uv_tool_install.py \
     dist/geometric_function_atlas-0.2.0-py3-none-any.whl --python 3.12
   ```

4. Obtain an independent review of the exact diff.
5. Push a branch, open a pull request, and wait for every Linux and Windows CI
   job to pass.
6. Merge to `main` and verify the merge commit is green.
7. Build once more from the clean merge commit. Record SHA-256 sums.
8. Create tag `vX.Y.Z` and a GitHub release with the wheel, sdist, checksums, and
   notes from `CHANGELOG.md`.
9. Download the published assets and rerun the clean-install check against the
   downloaded wheel.
10. Run both public installer commands and verify `gfa --version`.

## PyPI publication

PyPI publication is a separate, explicitly triggered step after a GitHub release
has passed every gate above. The `publish-pypi.yml` workflow uses PyPI Trusted
Publishing; no PyPI password or API token belongs in this repository.

1. Update and independently review `.github/pypi-publish.json` so it pins the
   release tag, commit, exact asset names, and independently recorded SHA-256
   digests.
2. Confirm that the PyPI trusted publisher matches this public repository,
   `.github/workflows/publish-pypi.yml`, and the `pypi` GitHub environment.
3. Manually dispatch **Publish to PyPI**. It accepts no release input; the
   reviewed manifest is the sole publication target.
4. The workflow verifies the pinned tag/commit, downloads the exact wheel,
   sdist, and `SHA256SUMS`, checks both the manifest-pinned digests and the
   release checksum file, and runs the metadata and distribution-content gates.
5. A separate minimal OIDC job downloads and reverifies the pinned distribution
   digests before uploading only those artifacts through
   short-lived OpenID Connect credentials.
6. Verify the new PyPI release through its JSON API and install it by name in a
   fresh uv-managed Python environment.

The workflow uses a standard public-repository runner and does not upload Actions
artifacts or use persistent Actions caches. Release and CI environments are
resolved from the committed `uv.lock` with `--locked`/`--frozen`; `uv`, Python
for publishing, and every third-party Action are pinned (Actions by full commit
SHA). Runtime dependency ranges remain compatible library metadata, while the
lockfile is the exact reproducibility record. Do not enable automatic
tag-triggered publishing, mutable Action tags, dependency caches, or long-lived
PyPI credentials.

## Maintained scripts

The `scripts/` directory contains only permanent entry points:

- `install.sh` and `install.ps1`: supported end-user installers;
- `check_distribution.py`: wheel/sdist content contract;
- `check_clean_install.py`: clean wheel API/CLI test;
- `check_uv_tool_install.py`: fresh uv-managed-Python installation test.

Do not commit ad hoc migration, profiling, review, or release-upload scripts.

## Registry-data releases

Registry snapshots are not bundled into the wheel. Each snapshot is versioned
independently and needs a consistent SQLite file, schema dump, manifest,
checksums, population definitions, and successful SQLite integrity checks.

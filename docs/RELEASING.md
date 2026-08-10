# Releasing `geometric-function-atlas`

This is the maintained release procedure. The first GitHub software release is
separate from PyPI publication and from versioned registry-data snapshots.

## Free-tier GitHub policy

The repository is public. CI uses only standard `ubuntu-latest` and
`windows-latest` GitHub-hosted runners, which GitHub documents as free for public
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
   uv run --extra test python -m ruff check src tests scripts
   uv run --extra test python -m mypy src --ignore-missing-imports
   uv run --extra test python -W error -m pytest -q
   rm -rf dist build
   uv run --extra build python -m build
   uv run --extra build python -m twine check dist/*
   uv run python scripts/check_distribution.py dist
   uv run python scripts/check_clean_install.py \
     dist/geometric_function_atlas-0.1.1-py3-none-any.whl
   uv run python scripts/check_uv_tool_install.py \
     dist/geometric_function_atlas-0.1.1-py3-none-any.whl --python 3.12
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

There is deliberately no tag-triggered PyPI workflow. PyPI Trusted Publishing
will be configured and reviewed as a separate future step. No PyPI token belongs
in this repository.

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

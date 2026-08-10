# geometric-function-atlas

`geometric-function-atlas` is a standalone Python package for independently reproducing and reviewing computations published by the Geometric Function Atlas.

Source repository: <https://github.com/Prasanna28Devadiga/geometric-function-atlas>

This repository is intentionally separate from the registry website and its research workspace. It provides local commands and Python functions for reproducing the website's mathematical computations. It does not contain the Flask application, deployment configuration, private review state, or mutable registry database.

## Phase 1

The first release provides:

- a typed catalog of the Ma–Minda generators used by the paper’s exact-radius portfolio;
- exact Taylor coefficients of a generator using SymPy;
- exact Ma–Minda Fekete–Szegő constants and their derivation metadata;
- certified re-evaluation of supplied counterexample witnesses;
- versioned structured result and fail-closed verification reports;
- JSON-capable command-line output suitable for independent checks.

Later phases will expose the remaining plots, certificates, registry queries, and application labs already available on the website.

## Install — Python is not required

The supported user installation uses `uv` as an isolated tool manager. It
downloads Python 3.12 and every runtime dependency automatically.

macOS and Linux:

```bash
curl -LsSf https://raw.githubusercontent.com/Prasanna28Devadiga/geometric-function-atlas/main/scripts/install.sh | sh
```

Windows PowerShell:

```powershell
irm https://raw.githubusercontent.com/Prasanna28Devadiga/geometric-function-atlas/main/scripts/install.ps1 | iex
```

After restarting the terminal, run `gfa --version`. Existing `uv` users can
install the GitHub release wheel directly:

```bash
uv tool install --managed-python --python 3.12 https://github.com/Prasanna28Devadiga/geometric-function-atlas/releases/download/v0.1.1/geometric_function_atlas-0.1.1-py3-none-any.whl
```

See `docs/INSTALL.md` for removal and maintainer installation from a local wheel.

## Python API

```python
from geometric_function_atlas import Generator, fekete_szego, generator_series, z

# phi(z) = 1 + sin(z) = 1 + z - z^3/6 + ...
series = generator_series("sine", order=4)
assert tuple(map(str, series.coefficients)) == (
    "1", "0", "-1/6", "0"
)
print(series.to_dict())

# Exact sharp constant under the declared Ma–Minda assumptions.
result = fekete_szego("exponential", mu=0)
assert str(result.value) == "3/4"
print(result.to_dict())
```

Custom normalized generators use preconstructed SymPy expressions; formula
strings are deliberately rejected rather than passed to an eval-based parser:

```python
custom = Generator(
    key="custom",
    name="Example",
    expression=1 + 2*z + 3*z**2,
    citation="User supplied",
)
```

Computations are not restricted to the built-in catalog. Analytic admissibility
of custom input remains an explicit caller assumption, and undeclared free
symbols are rejected.

## Command line

```bash
gfa generators
gfa coefficients sine --order 5
gfa fekete-szego exponential --mu 1/2

# Re-check the witness z=-3/4 for f(z)=z+z².
gfa verify-counterexample --coefficients "1" --point=-0.75,0
```

The longer command name, `geometric-function-atlas`, is also supported. Add
`--json` to any command when machine-readable output is useful.

`--mu` accepts an exact signed integer or `integer/integer` fraction. Decimal
and scientific notation are rejected so untrusted short inputs cannot trigger
unbounded symbolic integer construction.

See `docs/WEB_PARITY.md` for the website-to-package checklist,
`docs/PROVENANCE.md` for claim semantics, and `docs/ROADMAP.md` for the
incremental implementation path.
The versioned result envelope, verification checks, failure states, and CLI
exit codes are specified in `docs/RESULT_CONTRACT.md`.

## Development

```bash
uv sync --extra test
uv run pytest
```

## Scientific status

Every result reports its method and evidence status. Numerical screens are never presented as proofs, computational certification is distinct from literature novelty, and bibliographic review remains a separate human process.

## License

MIT

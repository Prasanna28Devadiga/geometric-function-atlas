# gft-registry

`gft-registry` is a standalone Python package for independently reproducing and reviewing computations published by the GFT Registry.

This repository is intentionally separate from the registry website and its research workspace. It contains only researcher-facing mathematical APIs, compact reference data, machine-readable provenance, tests, and command-line workflows. It does not contain the Flask application, OCR pipeline, deployment configuration, private review state, or mutable registry database.

## Phase 1

The first release provides:

- a typed catalog of the Ma–Minda generators used by the paper’s exact-radius portfolio;
- exact Taylor coefficients of a generator using SymPy;
- exact Ma–Minda Fekete–Szegő constants and their derivation metadata;
- JSON-capable command-line output suitable for independent checks.

Later phases will add sharp-radius certificate replay, general coefficient-certificate replay, registry snapshot validation, and literature-reconciliation audit tools.

## Python API

```python
from gft_registry import Generator, fekete_szego, generator_series, z

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
gft-registry generators --json
gft-registry coefficients sine --order 5 --json
gft-registry fekete-szego exponential --mu 1/2 --precision 40 --json
```

`--mu` accepts an exact signed integer or `integer/integer` fraction. Decimal
and scientific notation are rejected so untrusted short inputs cannot trigger
unbounded symbolic integer construction.

See `docs/PROVENANCE.md` for claim semantics and `docs/ROADMAP.md` for the
incremental path to full registry and paper reproduction.

## Development

```bash
python -m pip install -e '.[test]'
pytest
```

## Scientific status

Every result reports its method and evidence status. Numerical screens are never presented as proofs, computational certification is distinct from literature novelty, and bibliographic review remains a separate human process.

## License

MIT

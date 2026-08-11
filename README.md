# geometric-function-atlas

`geometric-function-atlas` is a standalone Python package for independently reproducing and reviewing computations published by the [Geometric Function Atlas](https://gft-registry.fly.dev).

Source repository: <https://github.com/Prasanna28Devadiga/geometric-function-atlas>

This repository is intentionally separate from the registry website and its research workspace. It provides local commands and Python functions for reproducing the website's mathematical computations. It does not contain the Flask application, deployment configuration, private review state, or mutable registry database.

## What you can do

Every scientific operation on the website has a local command and a Python function. The table below is the complete shipped surface.

| Website capability | CLI | Python function |
|---|---|---|
| Browse the generator catalog (39 Ma–Minda generators) | `gfa generators` | `list_generators()` |
| Exact Taylor coefficients of a generator | `gfa coefficients <gen> --order N` | `generator_series()` |
| Exact Ma–Minda Fekete–Szegő constants | `gfa fekete-szego <gen> --mu M` | `fekete_szego()` |
| Re-check a supplied counterexample witness | `gfa verify-counterexample` | `verify_counterexample()` |
| Search for and certify a violation point | `gfa find-counterexample` | `find_counterexample()` |
| Verify a function at a cost tier | `gfa verify --max-cost <tier>` | `verify_function()` |
| List Ma–Minda classes | `gfa classes` | `list_classes()` |
| Check Ma–Minda admissibility of a class | `gfa class-check <key>` | `class_admissibility()` |
| Screen membership of f in a class | `gfa class-member <key> --coefficients ...` | `class_member_screen()` |
| Screen class containment | `gfa compare <inner> <outer>` | `class_containment_screen()` |
| Exact extremal coefficients of a class | `gfa extremal-coefficients <key>` | `class_extremal_coefficients()` |
| Reproduce website plots | `gfa plot <kind> <gen> --output out.svg` | `write_plot()` and friends |
| Cryptography Lab S-box metrics (optional) | `gfa crypto-lab ...` | `geometric_function_atlas.lab.*` |
| Image Lab metrics and transforms (optional) | `gfa image-lab ...` | `geometric_function_atlas.lab.*` |

Result-printing commands accept `--json` for machine-readable output;
file-writing commands (`plot`, `image-lab transform`, `image-lab sample`)
write their artifact instead.

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

The optional Image Lab and Cryptography Lab operations need NumPy. Install with
the `lab` extra:

```bash
uv tool install geometric-function-atlas --extra lab   # once published on PyPI
# or locally:
uv tool install --with "numpy>=1.24" dist/geometric_function_atlas-*.whl
```

## Python API

### Exact generator series

```python
from geometric_function_atlas import Generator, generator_series, z

# phi(z) = 1 + sin(z) = 1 + z - z^3/6 + ...
series = generator_series("sine", order=4)
assert tuple(map(str, series.coefficients)) == (
    "1", "0", "-1/6", "0"
)
print(series.to_dict())
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

### Exact Fekete–Szegő constants

```python
from geometric_function_atlas import fekete_szego

# Exact sharp constant under the declared Ma–Minda assumptions.
result = fekete_szego("exponential", mu=0)
assert str(result.value) == "3/4"
print(result.to_dict())
```

### Tiered function verification

The website's verification sandbox exposes three cost tiers. The package
mirrors them with explicit epistemic labels: a numerical screen is never
presented as a proof.

```python
from geometric_function_atlas import verify_function

# Screen: float grid evaluation of the starlikeness criterion.
screen = verify_function([0.25], property="starlike", max_cost="screen")
assert screen.outcome == "passes_screen"   # numerical screen, not a proof

# Symbolic: exact arithmetic on a sufficient condition.
# For a finite polynomial, sum(n*|a_n|) <= 1 proves starlikeness.
proof = verify_function([0.1], property="starlike", max_cost="symbolic")

# Rigorous: symbolic checks plus certified interval evaluation at the
# worst screened point.
rigorous = verify_function([1.0], property="starlike", max_cost="rigorous")
assert rigorous.outcome == "certified_violation"
```

`verify_function` accepts either `coefficients` (`[a2, a3, ...]` for
`f(z) = z + a2*z**2 + ...`) or a preconstructed SymPy `closed_form` expression.
Supported properties: `starlike`, `convex`, `univalent`, `becker_univalent`,
`nehari_univalent`. Univalence has no pointwise screen; use the symbolic tier
or the Becker/Nehari criteria.

### Counterexample witness replay and search

```python
from geometric_function_atlas import find_counterexample, verify_counterexample

# Rigorously re-check the website's witness z = -3/4 for f(z) = z + z^2.
check = verify_counterexample([1.0], point=(-0.75, 0.0), property="starlike")
assert check.certified is True
print(check.to_dict())

# Grid search locates a candidate violation, interval arithmetic certifies it.
search = find_counterexample([1.0], property="starlike")
assert search.certified is True
```

### Class screens

Ma–Minda class operations are screens unless a certified theorem is attached:
exact normalization checks plus sampled-region evaluation. They are never
presented as proofs.

```python
from geometric_function_atlas import (
    class_admissibility,
    class_containment_screen,
    class_extremal_coefficients,
    class_member_screen,
    list_classes,
)

list_classes()                    # all 39 Ma–Minda classes
class_admissibility("exponential")  # exact phi(0)=1, phi'(0)>0 + region screens

# Screen f(z) = z + 0.25 z^2 + 0.1 z^3 for membership in S*(exp(z)).
member = class_member_screen("exponential", [0.25, 0.1])
assert member.member is True

# Screen phi_inner(D) subset phi_outer(D).
contained = class_containment_screen("exponential", "cardioid")

# Exact extremal coefficients from the class definition.
coeffs = class_extremal_coefficients("exponential", order=8)
```

### Plots

Four plot kinds reproduce the website's plots as dependency-free SVG:
`domain` (conformal grid image), `coefficients` (coefficient magnitudes),
`real-part` (heatmap of Re f), and `phase` (phase portrait).

```python
from geometric_function_atlas import write_plot

write_plot("domain", "/tmp/exponential-domain.svg", generator="exponential")
write_plot("phase", "/tmp/exponential-phase.svg", generator="exponential")
```

Plots visualize a finite Taylor polynomial; they are not proofs of the full
image domain. Custom coefficient input is supported via `coefficients=...`.

### Optional labs (NumPy required)

The Cryptography Lab and Image Lab operations live behind the `lab` extra.
**Crypto outputs are benchmark metrics, never security claims; image outputs
are empirical.**

```python
from geometric_function_atlas.lab import AES_SBOX, IDENTITY_SBOX, sbox_metrics

# Deterministic anchors: the AES S-box and the identity permutation.
aes = sbox_metrics(AES_SBOX)       # NL 112, DP 4/256, LP 1/16, ...
identity = sbox_metrics(IDENTITY_SBOX)  # poor metrics by construction

from geometric_function_atlas.lab import image_metrics, sample_image

ref = sample_image(seed=0, size=32)       # deterministic generated array
metrics = image_metrics(ref, ref)         # PSNR inf, SSIM 1, GMSD 0
```

See `docs/WEB_PARITY.md` for the website-to-package checklist and
`docs/PROVENANCE.md` for claim semantics. The versioned result envelope,
verification checks, failure states, and CLI exit codes are specified in
`docs/RESULT_CONTRACT.md`.

## Command line

```bash
gfa generators
gfa coefficients sine --order 5
gfa fekete-szego exponential --mu 1/2

# Re-check the witness z=-3/4 for f(z)=z+z².
gfa verify-counterexample --coefficients "1" --point=-0.75,0

# Search for and certify a starlikeness violation.
gfa find-counterexample --coefficients "1"

# Tiered verification.
gfa verify --coefficients "1" --property starlike --max-cost screen
gfa verify --coefficients "1" --property starlike --max-cost symbolic
gfa verify --coefficients "1" --property starlike --max-cost rigorous

# Class operations.
gfa classes
gfa class-check exponential
gfa class-member exponential --coefficients "0.25,0.1"
gfa compare exponential cardioid
gfa extremal-coefficients exponential --order 8

# Plots (SVG).
gfa plot domain exponential --output /tmp/domain.svg
gfa plot phase exponential --output /tmp/phase.svg

# Optional labs (NumPy required).
gfa crypto-lab metrics --reference aes
gfa crypto-lab metrics --reference identity
gfa crypto-lab metrics --sbox "25,1,47,..."          # 256 integers
gfa crypto-lab construct cardioid
gfa image-lab sample --output ref.npy --seed 0 --size 32
gfa image-lab metrics --ref ref.npy --test ref.npy
gfa image-lab transform --input ref.npy --output out.npy --operation edge
```

The longer command name, `geometric-function-atlas`, is also supported. Add
`--json` to result-printing commands when machine-readable output is useful.

`--mu` accepts an exact signed integer or `integer/integer` fraction. Decimal
and scientific notation are rejected so untrusted short inputs cannot trigger
unbounded symbolic integer construction.

## Development

```bash
uv sync --extra test
uv run pytest
```

## Scientific status

Every result reports its method and evidence status. Numerical screens are
never presented as proofs, computational certification is distinct from
literature novelty, enclosures are not sharpness claims, application tags are
not effectiveness claims, crypto metrics are benchmark metrics rather than
security claims, and bibliographic review remains a separate human process.

## License

MIT

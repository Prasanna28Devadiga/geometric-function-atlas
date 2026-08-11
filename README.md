# geometric-function-atlas

`geometric-function-atlas` is a standalone Python package for independently reproducing and reviewing computations published by the [Geometric Function Atlas](https://gft-registry.fly.dev).

Source repository: <https://github.com/Prasanna28Devadiga/geometric-function-atlas>

This repository is intentionally separate from the registry website and its research workspace. It provides local commands and Python functions for reproducing the website's mathematical computations. It does not contain the Flask application, deployment configuration, private review state, or mutable registry database.

## What you can do

Every operation represented in the package's parity table has a local command
and a Python function. The table below is the complete shipped surface; browser-
only panels and research-workspace workflows are explicit non-goals.

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
| Inspect/verify baked scientific artifacts | `gfa artifact-snapshot`, `gfa proofs`, `gfa expansion`, `gfa coefficient-bound`, `gfa reconciliation` | `snapshot_info()`, `list_proofs()`, `expansion()`, `coefficient_bound()`, `reconciliation()` |
| Replay a baked exact certificate | `gfa verify-certificate <name>` | `verify_certificate()` |
| Browse/replay directed inclusion radii | `gfa radii`, `gfa radius`, `gfa verify-radius-certificate` | `list_radii()`, `radius()`, `verify_radius_certificate()` |
| Verify/install an immutable registry snapshot | `gfa snapshot info|verify|install` | `verify_snapshot()`, `install_snapshot()`, `RegistrySnapshot.open()` |
| Query snapshot statistics, families, papers, evidence, and applications | `gfa stats|search|families|family|facts|evidence|runs|papers|paper|applications` | `RegistrySnapshot.stats()`, `.search()`, `.families()`, `.family()`, `.facts()`, `.evidence()`, `.runs()`, `.papers()`, `.paper()`, `.applications()` |
| Query aliases, hierarchy, and stored witnesses | `gfa aliases|normalize-class|hierarchy|counterexamples` | `RegistrySnapshot.aliases()`, `.normalize_class()`, `.hierarchy()`, `.counterexamples()` |
| Cryptography Lab S-box metrics (optional) | `gfa crypto-lab ...` | `geometric_function_atlas.lab.*` |
| Image Lab finite coefficient-derived filters, metrics, and transforms (optional) | `gfa image-lab ...` | `geometric_function_atlas.lab.*` |

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
uv tool install --managed-python --python 3.12 https://github.com/Prasanna28Devadiga/geometric-function-atlas/releases/download/v0.2.0/geometric_function_atlas-0.2.0-py3-none-any.whl
```

See `docs/INSTALL.md` for removal and maintainer installation from a local wheel.

## Registry snapshot boundary

The package does not bundle the mutable registry database, and no canonical snapshot URL is bundled.
Snapshot users provide a user-supplied HTTPS database and matching manifest
(the manifest can preserve its `source_url`), then verify
and install it locally:

```bash
gfa snapshot install https://example.org/registry.sqlite \
  ~/.cache/gft-registry/registry.sqlite --manifest registry.manifest.json
gfa papers --citation 10.example/record \
  --snapshot ~/.cache/gft-registry/registry.sqlite --manifest registry.manifest.json
```

The URL above is an illustrative caller input, not a package-hosted release
asset. Snapshot hashes, required tables, populations, and SQLite integrity
checks are authoritative; a snapshot does not certify the underlying claims.

The optional Image Lab and Cryptography Lab operations need NumPy. Install with
the `lab` extra:

```bash
uv tool install geometric-function-atlas --extra lab   # once published on PyPI
# or locally:
uv tool install --with "numpy>=1.24" dist/geometric_function_atlas-*.whl
```

The optional crypto lab deliberately covers five named registry functions and
two deterministic S-box constructions. Its outputs are benchmark metrics, never security claims; invertibility and empirical comparisons do not amount to
provable cryptographic security. The image lab is likewise an empirical
transform/metric sandbox. It exposes the finite coefficient-derived filter
subset used by the website's named functions, but does not claim analytic
special-function or conformal-warp parity.

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

The checked-in examples below are generated by the package itself:

![Sine conformal-domain visualization](docs/assets/sine-domain.svg)

![Supplied-polynomial visualization](docs/assets/polynomial.svg)

### Versioned scientific artifacts

The website's proof, bounds, expansion, open-problem, reconciliation, and
reference records are shipped as a checksummed read-only package snapshot.
These are lookups or bounded certificate replays; they do not turn a numerical
screen into a proof, an enclosure into a sharp result, or a literature
no-match into a novelty claim.

```python
from geometric_function_atlas import (
    coefficient_bound,
    expansion,
    get_proof,
    list_proofs,
    open_problems,
    reconciliation,
    snapshot_info,
    snapshot_verify,
    verify_certificate,
)

artifact = snapshot_info()
assert artifact["artifact_version"]
assert snapshot_verify()["checks"]["success"] is True
assert expansion("starlike")["class_key"] == "starlike"
assert coefficient_bound("starlike")["count"] > 0
assert list_proofs()["count"] > 0
assert get_proof("starlike__fekete_szego_mu1")["name"]
assert open_problems("enclosure")["counts"]["enclosures"] == 12
assert reconciliation()["total"] > 0
assert verify_certificate("starlike__fekete_szego_mu1")["matched"] is True
```

The corresponding commands are:

```bash
gfa artifact-snapshot info --json
gfa artifact-snapshot verify --json
gfa artifact-classes --json
gfa class starlike --json
gfa expansion starlike --json
gfa coefficient-bound starlike --json
gfa proofs --search fekete --json
gfa proof starlike__fekete_szego_mu1 --json
gfa open-problems --kind enclosure --json
gfa reconciliation --json
gfa references --json
gfa verify-certificate starlike__fekete_szego_mu1 --json
```

### Directed inclusion radii

Radius rows preserve direction and the website's five evidence statuses. Only
the eight reviewed exact lanes are replayable by the package; the other rows
remain snapshot records with their original status and provenance.

```python
from geometric_function_atlas import (
    list_radii,
    radius,
    replay_radius_certificate,
    verify_radius_certificate,
)

rows = list_radii(status="audit_required")
record = radius("sine", "sigmoid")
assert record.direction == "sine->sigmoid"
assert replay_radius_certificate(record).certified is True
assert verify_radius_certificate("sine", "sigmoid").certified is True
```

```bash
gfa radii --status audit_required --json
gfa radius sine sigmoid --json
gfa verify-radius-certificate sine sigmoid --json
```

The radius certificate replay checks the declared branch, containment,
contact/attainment evidence, exact candidate, and bounded symbolic steps. A
stored decimal or a candidate expression is not silently upgraded to a global
sharpness proof.

### Immutable registry snapshot queries

The large relational registry database is a separately distributed artifact;
it is not embedded in the wheel. After obtaining a database and its matching
manifest, inspect and verify it before querying:

```bash
gfa snapshot info registry.sqlite --manifest registry-manifest.json --json
gfa snapshot verify registry.sqlite --manifest registry-manifest.json --json
gfa snapshot install registry.sqlite installed.sqlite --manifest registry-manifest.json --json
```

All local snapshot queries use `RegistrySnapshot.open(...)` and have matching
task-oriented commands:

| Operation | Command | Python API |
|---|---|---|
| Statistics | `gfa stats SNAPSHOT` | `snapshot.stats()` |
| Search | `gfa search QUERY SNAPSHOT` | `snapshot.search()` |
| Family list/detail | `gfa families`, `gfa family ID` | `snapshot.families()`, `snapshot.family()` |
| Facts/evidence/runs | `gfa facts`, `gfa evidence`, `gfa runs` | `snapshot.facts()`, `snapshot.evidence()`, `snapshot.runs()` |
| Paper search/detail | `gfa papers`, `gfa paper ID` | `snapshot.papers()`, `snapshot.paper()` |
| Applications | `gfa applications [AREA]` | `snapshot.applications()` |
| Stored witnesses | `gfa counterexamples [FAMILY]` | `snapshot.counterexamples()` |
| Alias lookup | `gfa aliases [TEXT]`, `gfa normalize-class TEXT` | `snapshot.aliases()`, `snapshot.normalize_class()` |
| Property hierarchy | `gfa hierarchy [PROPERTY]` | `snapshot.hierarchy()` |

Snapshot query results preserve corpus facts, evidence, verification-run
metadata, and conservative application associations. Application labels are
literature/keyword associations, not effectiveness claims.

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
gfa plot sine --order 12 --output sine-domain.svg
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

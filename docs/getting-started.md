# Getting started

Install the Geometric Function Atlas command-line package, run one exact calculation,
certify a counterexample, and replay a directed-radius certificate. The installer
provides its own managed Python, so no existing Python installation is required.

## 0. Install

=== "macOS / Linux"

    ```bash
    curl --proto '=https' --tlsv1.2 -LsSf https://gft-registry.fly.dev/install.sh | sh
    ```

    This downloads and runs the version-pinned GFA installer. You can
    [read the hosted installer](https://gft-registry.fly.dev/install.sh) before
    running it.

=== "Windows PowerShell"

    ```powershell
    powershell -ExecutionPolicy Bypass -c "irm https://gft-registry.fly.dev/install.ps1 | iex"
    ```

    You can [read the PowerShell installer](https://gft-registry.fly.dev/install.ps1)
    before running it.

The hosted installer installs or finds [uv](https://docs.astral.sh/uv/), installs a
managed Python 3.12, installs the released `gfa` command in an isolated tool
environment, updates the user path, and verifies the result with `gfa --version`.
It does not require administrator privileges or replace the system Python.

### Review before running

If you prefer to inspect the complete Unix installer before executing it:

```bash
curl -LsSf https://gft-registry.fly.dev/install.sh -o gfa-install.sh
less gfa-install.sh
sh gfa-install.sh
rm gfa-install.sh
```

The short pipeline is convenient, but it sends the HTTPS response directly to the
shell. The download-first route lets you read the complete file before choosing to
run it.

On Windows, download `install.ps1`, inspect it in an editor, and then run it in a new
PowerShell process:

```powershell
Invoke-WebRequest https://gft-registry.fly.dev/install.ps1 -OutFile gfa-install.ps1
notepad gfa-install.ps1
powershell -ExecutionPolicy Bypass -File .\gfa-install.ps1
Remove-Item .\gfa-install.ps1
```

### Already have uv?

Install the package directly as an isolated managed-Python tool:

```bash
uv tool install --managed-python --python 3.12 geometric-function-atlas
```

Restart the terminal once if `gfa` is not immediately found, then verify:

```bash
gfa --version
```

### Optional labs

The Image Lab and Cryptography Lab operations require NumPy. Install the package
with its `lab` extra:

```bash
uv tool install --managed-python --python 3.12 'geometric-function-atlas[lab]'
```

Image outputs are empirical transforms, and cryptography outputs are benchmark
metrics rather than security claims.

### Upgrade or remove

Rerun the hosted installer to move to the version it currently pins, or upgrade an
existing uv-managed tool directly:

```bash
uv tool upgrade geometric-function-atlas
```

Remove the isolated tool without touching the system Python:

```bash
uv tool uninstall geometric-function-atlas
```

Maintainers testing local wheels should follow the
[release procedure](RELEASING.md), which exercises the checked-in installer with
an explicit `GFA_PACKAGE_SPEC`.

## 1. Run the first walkthrough

```bash
gfa walkthrough
```

The walkthrough introduces the notation, one exact generator expansion, one
Fekete–Szegő calculation, and one radius-certificate replay. It is the quickest
way to confirm the installation and see the package's evidence language.

!!! note "Reading rule"
    Exact computation, numerical screening, certified disproof, and certificate
    replay are different outcomes. The package labels them separately.

## 2. Browse generators

A Ma–Minda class $\mathcal{S}^*(\phi)$ is identified by its generator $\phi$.
List the package keys and exact formulas:

```bash
gfa generators
```

Abridged output:

```text
exponential: exp(z)
sine: sin(z) + 1
cardioid: 2*z**2/3 + 4*z/3 + 1
lemniscate: sqrt(z + 1)
sigmoid: 2/(1 + exp(-z))
```

Use a short key such as `sine` or `exponential` in later commands.

## 3. Compute exact generator coefficients

For

$$
\phi(z)=1+\sum_{k\geq1}B_kz^k=1+\sin z,
$$

return $B_1,\ldots,B_5$, the coefficients of $z,\ldots,z^5$ after the normalized
constant term $\phi(0)=1$:

```bash
gfa coefficients sine --order 5 --json
```

Abridged output:

```json
{
  "coefficients": ["1", "0", "-1/6", "0", "1/120"],
  "generator_formula": "sin(z) + 1",
  "evidence_status": "proven_exact_under_declared_assumptions"
}
```

These are exact symbolic coefficients, not fitted decimals. The complete JSON
record also carries assumptions, source references, verification checks, and
artifact versions.

## 4. Evaluate a coefficient functional

For the exponential Ma–Minda class, calculate the sharp theorem-backed value of
$|a_3-\mu a_2^2|$ at $\mu=0$:

```bash
gfa fekete-szego exponential --mu 0 --json
```

```json
{
  "value_exact": "3/4",
  "value_decimal": "0.7500000000000000",
  "evidence_status": "proven_exact_under_declared_assumptions"
}
```

Try an exact rational parameter without introducing floating-point input:

```bash
gfa fekete-szego exponential --mu 1/2 --json
```

Inspect `assumptions` and `source_references` before applying a value to a new
problem. Ordinary output is intentionally abbreviated; use `--json` for the full
record.

## 5. Certify a disproof

Write $f(z)=z+z^2$ by supplying $a_2=1$, then check the proposed interior witness
$z=-3/4$ against starlikeness:

```bash
gfa verify-counterexample --coefficients 1 --point=-0.75,0 --property starlike
```

```text
CERTIFIED COUNTEREXAMPLE
Criterion: starlikeness
Witness: z = -0.75 + 0i
Certified value: [-2, -2]
Counterexample condition: value <= 0
```

A certified interior witness is a rigorous disproof for this function. It does not
prove a broader statement about an entire function class.

!!! warning
    **A numerical screen is not a proof.** The command checks the supplied point
    with interval arithmetic before reporting a certified violation.

## 6. Replay a directed-radius certificate

Replay the released certificate for the inclusion from the sine class to the
sigmoid class:

```bash
gfa verify-radius-certificate sine sigmoid
```

```text
PROVEN: sine->sigmoid
  PASS psi composition reduces to the logarithmic sine form
  PASS d/dz atanh(sin z) = sec z
  PASS |cos(x+iy)|^2 = cos^2 x + sinh^2 y
  PASS angular-bound remainder is sinh(b)^2 >= 0
  PASS 2*atanh(sin(r*)) = 1
```

The stored exact radius is `asin((E-1)/(E+1))`. Inspect the full record separately:

```bash
gfa radius sine sigmoid --json
```

Read the [underlying mathematical argument](https://gft-registry.fly.dev/proofs/radius-sine-sigmoid)
on the live Atlas. A certificate replay does not establish novelty: it checks the
released computational artifact, while literature priority and applicability to a
new problem still require review.

## 7. Make a plot

```bash
gfa plot domain exponential --output exponential-domain.svg
```

Open `exponential-domain.svg` in a browser or vector-graphics program. It is built
from a finite Taylor representation and is a visualization, not a proof of the
full image domain.

## 8. Use the same operations from Python

```python
from geometric_function_atlas import fekete_szego, generator_series

series = generator_series("sine", order=5)
print(series.to_dict())

result = fekete_szego("exponential", mu="1/2")
payload = result.to_dict()
print(payload["value_exact"])
print(payload["assumptions"])
print(payload["source_references"])
```

The command line and Python API call the same package operations. Use structured
records when assumptions, references, checks, or artifact identity matter.

## Read the evidence labels

- **Proven exact under declared assumptions** means an exact theorem-backed
  calculation was carried out under assumptions recorded with the result.
- **Certified counterexample** means a rigorous witness disproves the stated
  property for the supplied function.
- **Certificate replay** means the registered checks for a released artifact pass;
  it does not establish literature novelty.
- **Screen** means finite numerical or symbolic evidence only.
- **Bundle verified** means declared bytes match a closed checksum manifest; bundle
  integrity does not certify the mathematics recorded inside those files.

## Choose a research workflow

Continue with the [research workflow index](workflows/README.md) to investigate a
custom class, understand class geometry, derive a sharp radius, inspect the radius
atlas, compare coefficient bounds, repair a conjecture, transfer results through
the Alexander transform, or prepare a deterministic collaborator bundle.

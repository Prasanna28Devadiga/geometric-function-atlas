# Install Geometric Function Atlas

You do **not** need Python. The installer obtains `uv`, Python 3.12, and all
package dependencies, then installs the `gfa` command in an isolated environment.

## macOS and Linux

```bash
curl -LsSf https://raw.githubusercontent.com/Prasanna28Devadiga/geometric-function-atlas/main/scripts/install.sh | sh
```

## Windows PowerShell

```powershell
irm https://raw.githubusercontent.com/Prasanna28Devadiga/geometric-function-atlas/main/scripts/install.ps1 | iex
```

Restart the terminal once, then check the installation:

```text
gfa --version
```

Try a calculation:

```bash
gfa coefficients sine --order 5
gfa fekete-szego exponential --mu 1/2
gfa verify-counterexample --coefficients "1" --point=-0.75,0
gfa plot sine --output sine-domain.svg
```

## Already have uv?

Install the package from PyPI in an isolated, uv-managed Python environment:

```bash
uv tool install --managed-python --python 3.12 geometric-function-atlas
```

To reproduce an immutable release exactly, pin its version:

```bash
uv tool install --managed-python --python 3.12 geometric-function-atlas==0.2.0
```

## Optional labs

The Cryptography Lab and Image Lab operations need NumPy. Install the package
with the `lab` extra:

```bash
uv tool install --with "numpy>=1.24" https://github.com/Prasanna28Devadiga/geometric-function-atlas/releases/download/v0.2.0/geometric_function_atlas-0.2.0-py3-none-any.whl
```

Crypto outputs are benchmark metrics, never security claims; image outputs are
empirical.

## Remove

```bash
uv tool uninstall geometric-function-atlas
```

To upgrade after a later GitHub release, rerun the installer shown above. The
installer always performs a forced replacement and verifies `gfa --version`.

## Maintainer and local-wheel installation

The checked-in installers are permanent user-facing installation entry points,
not release-time helper scripts. Maintainers can exercise the same path against a
local wheel:

```bash
GFA_PACKAGE_SPEC=dist/geometric_function_atlas-0.2.0-py3-none-any.whl sh scripts/install.sh
```

PowerShell:

```powershell
$env:GFA_PACKAGE_SPEC = "dist/geometric_function_atlas-0.2.0-py3-none-any.whl"
.\scripts\install.ps1
```

The project does not modify or depend on an existing Python installation. No
administrator privileges, `pip`, virtual-environment activation, snapshot hash,
or internal database path is required.

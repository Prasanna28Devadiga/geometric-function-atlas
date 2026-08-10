# Installation without Python

Geometric Function Atlas is installed as an isolated command-line tool. You do
**not** need to install Python, create a virtual environment, or manage package
dependencies. [`uv`](https://docs.astral.sh/uv/) downloads a managed Python and
installs all dependencies for `gfa`.

> These public URLs become active when the first package release is published.
> Before then, contributors should use the local-wheel command below.

## macOS and Linux

```bash
curl -LsSf https://raw.githubusercontent.com/Prasanna28Devadiga/geometric-function-atlas/main/scripts/install.sh | sh
```

## Windows PowerShell

```powershell
irm https://raw.githubusercontent.com/Prasanna28Devadiga/geometric-function-atlas/main/scripts/install.ps1 | iex
```

Restart the terminal once, then verify the installation:

```text
gfa --version
```

The installers:

1. install `uv` from Astral's official installer if it is absent;
2. ask `uv` for a managed Python 3.12;
3. install `geometric-function-atlas`, SymPy, mpmath, and future runtime
   dependencies into an isolated tool environment;
4. add the tool directory to the user's shell path;
5. execute `gfa --version` as a smoke test.

The project does not modify or depend on an existing Python installation.

## Already have uv?

```bash
uv tool install --managed-python --python 3.12 geometric-function-atlas
```

No `pip`, environment activation, or administrator privileges are required.

## Upgrade or remove

```bash
uv tool upgrade geometric-function-atlas
uv tool uninstall geometric-function-atlas
```

## Install a release wheel before PyPI publication

From a checkout containing the built wheel:

```bash
GFA_PACKAGE_SPEC=dist/geometric_function_atlas-0.1.0-py3-none-any.whl sh scripts/install.sh
```

PowerShell:

```powershell
$env:GFA_PACKAGE_SPEC = "dist/geometric_function_atlas-0.1.0-py3-none-any.whl"
.\scripts\install.ps1
```

## Website “Run locally” pattern

Every reproducible website item should use the same compact panel:

```text
Run locally
1. Install once: [platform installer]
2. Reproduce:    gfa <task-oriented command>
```

For example:

```bash
gfa verify-counterexample --coefficients "1" --point=-0.75,0
```

JSON, snapshots, provenance identifiers, and diagnostic controls remain optional
advanced features rather than installation requirements.

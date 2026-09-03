from __future__ import annotations

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_posix_installer_uses_uv_as_a_managed_python_tool(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    tool_bin = tmp_path / "tool-bin"
    bin_dir.mkdir()
    tool_bin.mkdir()
    log = tmp_path / "uv.log"
    fake_uv = bin_dir / "uv"
    fake_uv.write_text(
        "#!/bin/sh\n"
        "printf '%s\\n' \"$*\" >> \"$UV_TEST_LOG\"\n"
        "if [ \"$1 $2 $3\" = 'tool dir --bin' ]; then printf '%s\\n' \"$UV_TEST_TOOL_BIN\"; fi\n",
        encoding="utf-8",
    )
    fake_uv.chmod(0o755)
    fake_gfa = tool_bin / "gfa"
    fake_gfa.write_text(
        "#!/bin/sh\nprintf 'geometric-function-atlas 0.2.0\\n'\n",
        encoding="utf-8",
    )
    fake_gfa.chmod(0o755)

    completed = subprocess.run(
        ["sh", str(ROOT / "scripts" / "install.sh")],
        check=False,
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "PATH": f"{bin_dir}:/usr/bin:/bin",
            "UV_TEST_LOG": str(log),
            "UV_TEST_TOOL_BIN": str(tool_bin),
            "GFA_PACKAGE_SPEC": "local-wheel.whl",
            "GFA_PYTHON_VERSION": "3.12",
        },
    )

    assert completed.returncode == 0, completed.stderr
    invocations = log.read_text(encoding="utf-8")
    assert "tool install --managed-python --python 3.12 --force local-wheel.whl" in invocations
    assert "tool update-shell" in invocations
    assert "tool dir --bin" in invocations
    assert "geometric-function-atlas 0.2.0" in completed.stdout


def test_windows_installer_has_the_same_managed_python_contract() -> None:
    script = (ROOT / "scripts" / "install.ps1").read_text(encoding="utf-8")

    assert "https://astral.sh/uv/install.ps1" in script
    assert "[scriptblock]::Create" in script
    assert "-ExecutionPolicy" not in script
    assert "tool install --managed-python --python" in script
    assert "GFA_PACKAGE_SPEC" in script
    assert "tool update-shell" in script
    assert "gfa.exe" in script
    assert "--version" in script


def test_installers_default_to_the_latest_github_release_wheel() -> None:
    release_wheel = (
        "https://github.com/Prasanna28Devadiga/geometric-function-atlas/"
        "releases/download/v0.2.0/"
        "geometric_function_atlas-0.2.0-py3-none-any.whl"
    )

    posix = (ROOT / "scripts" / "install.sh").read_text(encoding="utf-8")
    windows = (ROOT / "scripts" / "install.ps1").read_text(encoding="utf-8")

    assert release_wheel in posix
    assert release_wheel in windows


def test_ci_uses_only_free_public_standard_runners_without_persistent_storage() -> None:
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(
        encoding="utf-8"
    )

    assert "runs-on: ubuntu-24.04" in workflow
    assert "runs-on: windows-2025" in workflow
    assert "-latest" not in workflow
    assert "larger-runner" not in workflow
    assert "upload-artifact" not in workflow
    assert "enable-cache: true" not in workflow
    assert "enable-cache: false" in workflow
    assert 'branches: [main, "release/**"]' not in workflow


def test_clean_install_smoke_covers_the_plotting_operation() -> None:
    smoke = (ROOT / "scripts" / "check_clean_install.py").read_text(
        encoding="utf-8"
    )

    assert "write_domain_plot" in smoke
    assert '"plot"' in smoke
    assert "not a proof of the full image domain" in smoke

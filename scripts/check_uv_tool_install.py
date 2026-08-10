"""Install a wheel as a uv tool with a fresh uv-managed Python."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wheel", type=Path)
    parser.add_argument("--python", default="3.12")
    args = parser.parse_args(argv)
    wheel = args.wheel.resolve()
    if wheel.suffix != ".whl" or not wheel.is_file():
        parser.error(f"expected an existing wheel archive: {wheel}")
    uv = shutil.which("uv")
    if uv is None:
        parser.error("uv is required to exercise the no-Python installation path")

    with tempfile.TemporaryDirectory(prefix="gfa-uv-tool-") as temporary:
        root = Path(temporary)
        tool_bin = root / "bin"
        env = {
            **os.environ,
            "PYTHONPATH": "",
            "UV_PYTHON_INSTALL_DIR": str(root / "python"),
            "UV_TOOL_DIR": str(root / "tools"),
            "UV_TOOL_BIN_DIR": str(tool_bin),
            "UV_LINK_MODE": "copy",
        }
        subprocess.run(
            [
                uv,
                "tool",
                "install",
                "--managed-python",
                "--python",
                args.python,
                "--force",
                str(wheel),
            ],
            check=True,
            cwd=root,
            env=env,
        )
        suffix = ".exe" if os.name == "nt" else ""
        gfa = tool_bin / f"gfa{suffix}"
        version = subprocess.run(
            [str(gfa), "--version"],
            check=True,
            capture_output=True,
            text=True,
            cwd=root,
            env=env,
        ).stdout.strip()
        if not version.startswith("geometric-function-atlas "):
            raise AssertionError(f"unexpected installed version output: {version!r}")
        result = subprocess.run(
            [
                str(gfa),
                "verify-counterexample",
                "--coefficients",
                "1",
                "--point=-0.75,0",
                "--json",
            ],
            check=True,
            capture_output=True,
            text=True,
            cwd=root,
            env=env,
        )
        payload = json.loads(result.stdout)
        if not (
            payload["result_type"] == "counterexample_verification"
            and payload["schema_version"] == 1
            and payload["certified"] is True
            and payload["verification"]["success"] is True
        ):
            raise AssertionError(f"unexpected installed counterexample result: {payload!r}")

    print(f"uv managed-Python tool install: PASS ({wheel.name}, Python {args.python})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

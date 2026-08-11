"""Exercise a built wheel from a neutral directory and fresh virtualenv."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

_SMOKE = r"""
import json
import geometric_function_atlas as gfa

assert gfa.__version__
result = gfa.generator_series("sine", order=3).to_dict()
assert result["schema_version"] == 1
assert result["verification"]["success"] is True
assert gfa.load_result_schema()["additionalProperties"] is False

mutated = dict(result)
mutated["verification"] = dict(result["verification"])
mutated["verification"]["checks"] = list(result["verification"]["checks"])
mutated["verification"]["checks"][0] = dict(mutated["verification"]["checks"][0])
mutated["verification"]["checks"][0]["status"] = "fail"
mutated["verification"]["checks"][0]["failure_reason"] = "mutation"
try:
    gfa.validate_result_payload(mutated)
except ValueError:
    pass
else:
    raise AssertionError("mutated verification unexpectedly validated")

try:
    gfa.get_trusted_implementation("os.system")
except KeyError:
    pass
else:
    raise AssertionError("untrusted implementation unexpectedly resolved")

counterexample = gfa.verify_counterexample(
    [1], point=(-0.75, 0.0), property="starlike"
)
assert counterexample.certified is True
counterexample_payload = counterexample.to_dict()
assert counterexample_payload["schema_version"] == 1
assert counterexample_payload["result_type"] == "counterexample_verification"
assert counterexample_payload["verification"]["success"] is True
gfa.validate_result_payload(counterexample_payload)

plot = gfa.write_domain_plot("sine.svg", generator="sine", order=3)
assert plot.output.name == "sine.svg"
assert "<svg" in open("sine.svg", encoding="utf-8").read()
"""


def _python_in(venv: Path) -> Path:
    relative = Path("Scripts/python.exe") if os.name == "nt" else Path("bin/python")
    return venv / relative


def _install(python: Path, archive: Path, cwd: Path) -> None:
    uv = shutil.which("uv")
    if uv:
        command = [uv, "pip", "install", "--python", str(python), str(archive)]
    else:
        command = [
            str(python),
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            str(archive),
        ]
    subprocess.run(command, cwd=cwd, check=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wheel", type=Path)
    args = parser.parse_args(argv)
    archive = args.wheel.resolve()
    if archive.suffix != ".whl" or not archive.is_file():
        parser.error(f"expected an existing wheel archive: {archive}")

    with tempfile.TemporaryDirectory(prefix="gfa-clean-install-") as temporary:
        root = Path(temporary)
        venv = root / "venv"
        neutral = root / "neutral"
        neutral.mkdir()
        subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True)
        python = _python_in(venv)
        _install(python, archive, neutral)
        subprocess.run(
            [str(python), "-c", _SMOKE],
            cwd=neutral,
            check=True,
            env={**os.environ, "PYTHONPATH": ""},
        )
        script = venv / ("Scripts/gfa.exe" if os.name == "nt" else "bin/gfa")
        version = subprocess.run(
            [str(script), "--version"],
            cwd=neutral,
            check=True,
            capture_output=True,
            text=True,
            env={**os.environ, "PYTHONPATH": ""},
        )
        if not version.stdout.startswith("geometric-function-atlas "):
            raise AssertionError(f"unexpected installed version: {version.stdout!r}")
        counterexample = subprocess.run(
            [
                str(script),
                "verify-counterexample",
                "--coefficients",
                "1",
                "--point=-0.75,0",
                "--json",
            ],
            cwd=neutral,
            check=True,
            capture_output=True,
            text=True,
            env={**os.environ, "PYTHONPATH": ""},
        )
        if not json.loads(counterexample.stdout)["certified"]:
            raise AssertionError("installed gfa command did not certify the witness")
        plot_path = neutral / "sine.svg"
        plot = subprocess.run(
            [
                str(script),
                "plot",
                "sine",
                "--order",
                "3",
                "--output",
                str(plot_path),
            ],
            cwd=neutral,
            check=True,
            capture_output=True,
            text=True,
            env={**os.environ, "PYTHONPATH": ""},
        )
        if not plot_path.is_file() or "not a proof of the full image domain" not in plot.stdout:
            raise AssertionError("installed gfa command did not generate the plot")
        try:
            invalid = subprocess.run(
                [
                    str(python),
                    "-m",
                    "geometric_function_atlas",
                    "fekete-szego",
                    "sine",
                    "--mu",
                    "1e1000000000",
                    "--json",
                ],
                cwd=neutral,
                check=False,
                capture_output=True,
                text=True,
                timeout=2,
                env={**os.environ, "PYTHONPATH": ""},
            )
        except subprocess.TimeoutExpired as exc:
            raise AssertionError("unsafe-input smoke exceeded its two-second timeout") from exc
        if invalid.returncode != 2 or invalid.stderr:
            raise AssertionError(
                f"unsafe-input smoke failed: rc={invalid.returncode}, stderr={invalid.stderr!r}"
            )
        error = json.loads(invalid.stdout)
        if error["failure_state"] != "invalid_input":
            raise AssertionError(f"unexpected unsafe-input result: {error!r}")

    print(f"clean install: PASS ({archive.name})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

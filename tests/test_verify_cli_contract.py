"""The public CLI emits the same closed verification contract as the API."""
import json
import subprocess
import sys

import jsonschema
import pytest

from geometric_function_atlas.records import load_verify_result_schema


@pytest.mark.parametrize("truncation", [False, True])
def test_verify_cli_json_contract(truncation: bool) -> None:
    args = [sys.executable, "-m", "geometric_function_atlas", "verify", "--coefficients", "0.2",
            "--property", "nehari_univalent", "--max-cost", "rigorous"]
    if truncation:
        args.append("--truncation")
    result = subprocess.run([*args, "--json"], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
    record = json.loads(result.stdout)
    jsonschema.validate(record, load_verify_result_schema())
    assert record["canonical_inputs"]["truncation"] is truncation
    assert record["details"]["outcome"] != "certified_violation"

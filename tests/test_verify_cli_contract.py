"""The public CLI emits the same closed verification contract as the API."""
import json
import subprocess
import sys

import jsonschema
import pytest

from geometric_function_atlas.contracts import load_error_schema
from geometric_function_atlas.records import (
    load_verify_result_schema,
    validate_screen_record,
)


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
    validate_screen_record(record)
    assert record["canonical_inputs"]["truncation"] is truncation
    assert record["canonical_inputs"]["closed_form_srepr"] is None
    assert record["details"]["outcome"] != "certified_violation"


@pytest.mark.parametrize("arguments", [
    ["--coefficients", "not-a-number", "--property", "starlike"],
    ["--coefficients", "0.2", "--property", "not-a-property"],
])
def test_verify_cli_invalid_input_uses_error_schema(arguments: list[str]) -> None:
    result = subprocess.run(
        [sys.executable, "-m", "geometric_function_atlas", "verify", *arguments, "--json"],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 2, result.stderr
    payload = json.loads(result.stdout)
    jsonschema.validate(payload, load_error_schema())
    assert payload["result_type"] == "error"
    assert payload["failure_state"] == "invalid_input"
    assert result.stderr == ""
